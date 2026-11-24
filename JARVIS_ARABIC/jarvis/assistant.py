"""منسّق التطبيق: يربط الاستماع ← الفهم ← التنفيذ/الذكاء الاصطناعي ← النطق، ويدير حالة المحادثة."""
from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from PySide6.QtCore import QObject, Signal

from . import nlu, wake
from .actions import DANGEROUS, INFO_ACTIONS, Actions
from .config import Config
from .listener import ListenerThread
from .llm import LLMClient
from .stt import Transcriber
from .textutil import detect_lang, norm
from .tts import TTSEngine

log = logging.getLogger(__name__)

_YES = set(norm(x) for x in ["نعم", "ايوه", "ايه", "اه", "اكيد", "تمام", "نفذ", "yes", "yeah", "sure", "confirm",
                             "ok", "okay", "اوكي", "ايوا", "طبعا", "yep"])
_NO = set(norm(x) for x in ["لا", "لأ", "الغي", "الغ", "كنسل", "توقف", "no", "cancel", "stop", "nope", "ماتعمل", "خلص"])

_CONFIRM_TEXT = {
    "shutdown": ("هل أنت متأكد أنك تريد إطفاء الجهاز؟ قل نعم للتأكيد.", "Are you sure you want to shut down? Say yes to confirm."),
    "restart": ("هل أنت متأكد أنك تريد إعادة التشغيل؟ قل نعم للتأكيد.", "Are you sure you want to restart? Say yes to confirm."),
    "sleep": ("هل تريد أن أضع الجهاز في وضع السكون؟ قل نعم للتأكيد.", "Put the PC to sleep? Say yes to confirm."),
}


@dataclass
class Reply:
    speak: str
    display: str = ""
    lang: str = "ar"
    ok: bool = True
    sound: str = ""
    quit_after: bool = False
    end_conv: bool = False


class Assistant(QObject):
    state_changed = Signal(str)      # idle | loading | listening | thinking | speaking
    message = Signal(str, str)       # (user|jarvis|system, text)
    level = Signal(float)
    status_text = Signal(str)
    mic_changed = Signal(bool)
    sound = Signal(str)
    quit_requested = Signal()
    _done = Signal(int, object)      # (turn, Reply) من الخيط العامل

    def __init__(self, cfg: Config, tts=None, llm=None, actions=None, transcriber=None, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self.tts = tts or TTSEngine(cfg, self)
        self.llm = llm or LLMClient(cfg)
        self.actions = actions or Actions(cfg)
        self.transcriber = transcriber or Transcriber(cfg)
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="jarvis-worker")
        self.listener: ListenerThread | None = None
        self._retired: list[ListenerThread] = []
        self.mic_on = False
        self.state = "idle"
        self.conv_until = 0.0
        self.pending: tuple[str, dict, str, float] | None = None
        self.history: list[dict] = []
        self._busy = False
        self._turn = 0
        self._after: Reply | None = None
        self._greeted = False
        self._fallback_hint_shown = False
        self.tts.started.connect(self._on_tts_started)
        self.tts.finished.connect(self._on_tts_finished)
        self.tts.failed.connect(self._on_tts_failed)
        self._done.connect(self._on_done)

    # ------------------------------------------------------------ الحالة
    def _set_state(self, s: str) -> None:
        if s != self.state:
            self.state = s
            self.state_changed.emit(s)

    def in_conversation(self) -> bool:
        return time.monotonic() < self.conv_until

    def _idle_state(self) -> str:
        return "listening" if self.mic_on else "idle"

    # ------------------------------------------------------------ المايك
    def toggle_mic(self) -> None:
        self.stop_mic() if self.mic_on else self.start_mic()

    def start_mic(self) -> None:
        if self.mic_on:
            return
        self.listener = ListenerThread(self.cfg, self.transcriber, self)
        self.listener.status.connect(self._on_listener_status)
        self.listener.level.connect(self.level)
        self.listener.heard_speech.connect(lambda: None)
        self.listener.transcript.connect(self.on_transcript)
        self.listener.failed.connect(self._on_listener_failed)
        self.mic_on = True
        self.mic_changed.emit(True)
        self._set_state("loading" if not self.transcriber.loaded else "listening")
        self.listener.start()

    def stop_mic(self) -> None:
        if not self.mic_on:
            return
        lt = self.listener
        self.mic_on = False
        self.listener = None
        if lt is not None:
            lt.stop()
            for sig in (lt.status, lt.level, lt.transcript, lt.failed):
                try:
                    sig.disconnect()
                except Exception:
                    pass
            self._retired.append(lt)
            lt.finished.connect(lambda lt=lt: self._retired.remove(lt) if lt in self._retired else None)
        self.mic_changed.emit(False)
        self.level.emit(0.0)
        if not self._busy:
            self._set_state("idle")
        self.sound.emit("off")

    def restart_mic(self) -> None:
        if self.mic_on:
            self.stop_mic()
            self.start_mic()

    def _on_listener_status(self, s: str) -> None:
        if s == "loading":
            self._set_state("loading")
            self.status_text.emit("جاري تحميل نموذج التعرف على الصوت… (أول مرة يحتاج إنترنت وقد يستغرق دقائق)")
        elif s == "ready":
            if not self._busy:
                self._set_state("listening")
            self.status_text.emit("")
            self.sound.emit("boot") if not self._greeted else None
            if not self._greeted:
                self._greeted = True
                if self.cfg.greet_on_start and self.cfg.tts_enabled:
                    self._say(Reply(f"مرحباً {self.cfg.honorific}، لونا جاهزة.", lang="ar"), show=False)
        elif s == "transcribing":
            if not self._busy:
                self._set_state("thinking")
            self.status_text.emit("جاري تحويل الصوت إلى نص…")

    def _on_listener_failed(self, msg: str) -> None:
        self.message.emit("system", msg)
        self.sound.emit("error")
        self.status_text.emit("")
        if self.listener is not None and not self.listener.isRunning():
            self.mic_on = True  # لكي يعمل stop_mic بشكل نظيف
            self.stop_mic()

    # ------------------------------------------------------------ استقبال الكلام
    def on_transcript(self, text: str) -> None:
        text = (text or "").strip()
        if not text:
            return
        if self._busy:
            return
        cmd = text
        now = time.monotonic()
        if self.cfg.wake_enabled:
            found, rest = wake.extract(text, self.cfg.wake_words)
            if not found and not self.in_conversation() and not self.pending:
                self.status_text.emit(f"سمعتُ: «{text}» — لم أسمع كلمة التنبيه")
                if self._busy is False:
                    self._set_state("listening")
                return
            if found:
                cmd = rest
                self.sound.emit("wake")
                if not cmd.strip():
                    self.conv_until = now + self.cfg.conversation_timeout
                    self._say(Reply(f"نعم {self.cfg.honorific}؟", lang="ar"), show=True)
                    return
        self.status_text.emit("")
        self.handle_text(cmd)

    # ------------------------------------------------------------ معالجة النص
    def handle_text(self, text: str) -> None:
        """نقطة الدخول المشتركة للصوت والكتابة."""
        text = (text or "").strip()
        if not text:
            return
        if self._busy:
            self.tts.stop()
        lang = detect_lang(text)
        self.message.emit("user", text)
        self._turn += 1
        turn = self._turn
        self._busy = True
        self._set_state("thinking")
        if self.listener:
            self.listener.pause(True)

        # --- انتظار تأكيد أمر خطير
        if self.pending:
            act, args, plang, deadline = self.pending
            self.pending = None
            n = norm(text)
            if time.monotonic() < deadline and set(n.split()) & _YES and not set(n.split()) & _NO:
                self.executor.submit(self._run_action, turn, act, args, plang)
                return
            if set(n.split()) & _NO or time.monotonic() >= deadline:
                self._say(Reply("تمام، ألغيت الأمر." if lang == "ar" else "Cancelled.", lang=lang))
                return
            # غير ذلك: عامله كأمر جديد

        intent = nlu.parse(text, self.cfg.custom_apps)
        if intent and intent.name.startswith("ctl_"):
            self._control(intent, lang)
        elif intent and intent.name in DANGEROUS:
            self.pending = (intent.name, intent.args, lang, time.monotonic() + 30)
            ar, en = _CONFIRM_TEXT[intent.name]
            self._say(Reply(ar if lang == "ar" else en, lang=lang))
        elif intent:
            self.executor.submit(self._run_action, turn, intent.name, intent.args, lang)
        else:
            self.executor.submit(self._run_llm, turn, text, lang)

    def _control(self, intent: nlu.Intent, lang: str) -> None:
        name = intent.name
        if name == "ctl_stop_speaking":
            self.tts.stop()
            self._finish_turn()
            return
        text = nlu.canned_reply(name, lang, self.cfg.honorific)
        self._say(Reply(text, lang=lang, quit_after=(name == "ctl_exit"), end_conv=(name == "ctl_end_conversation")))

    # ------------------------------------------------------------ الخيط العامل
    def _run_action(self, turn: int, name: str, args: dict, lang: str) -> None:
        res = self.actions.run(name, args, lang)
        self._done.emit(turn, Reply(res.speak, res.display, lang, res.ok, "done" if res.ok else "error"))

    def _run_llm(self, turn: int, text: str, lang: str) -> None:
        ar = lang == "ar"
        if not self.cfg.llm_enabled or not self.llm.available():
            hint = ""
            if not self._fallback_hint_shown:
                self._fallback_hint_shown = True
                hint = (" للمحادثة وفهم الأوامر المعقدة ثبّت Ollama وشغّله (راجع التعليمات)." if ar
                        else " For chat and complex commands, install and start Ollama (see README).")
            msg = ("ما فهمت الأمر. جرّب مثلاً: افتح كروم، ارفع الصوت، كم الساعة." if ar
                   else "I didn't understand. Try: open Chrome, volume up, what time is it.") + hint
            self._done.emit(turn, Reply(msg, lang=lang, ok=False, sound="error"))
            return
        try:
            r = self.llm.chat(self.history, text)
        except Exception as e:
            log.warning("llm failed: %s", e)
            msg = ("تعذّر الاتصال بالنموذج الذكي، تأكد أن Ollama شغّال." if ar else "I couldn't reach the AI model. Is Ollama running?")
            self._done.emit(turn, Reply(msg, display=str(e), lang=lang, ok=False, sound="error"))
            return
        self.history += [{"role": "user", "content": text}, {"role": "assistant", "content": r.reply}]
        self.history = self.history[-20:]
        speak, display, ok = r.reply, "", True
        if r.action:
            if r.action in DANGEROUS:
                self.pending = (r.action, r.args, lang, time.monotonic() + 30)
                ar_t, en_t = _CONFIRM_TEXT[r.action]
                self._done.emit(turn, Reply(ar_t if ar else en_t, lang=lang))
                return
            res = self.actions.run(r.action, r.args, lang)
            ok, display = res.ok, res.display
            if r.action in INFO_ACTIONS or not speak or not res.ok:
                speak = res.speak
        if not speak:
            speak = "تمام." if ar else "Done."
        self._done.emit(turn, Reply(speak, display, lang, ok, "done" if ok else "error"))

    # ------------------------------------------------------------ الرد والنطق
    def _on_done(self, turn: int, reply: Reply) -> None:
        if turn != self._turn:
            return  # نتيجة قديمة
        self._say(reply)

    def _say(self, reply: Reply, show: bool = True) -> None:
        self._after = reply
        if show and (reply.speak or reply.display):
            text = reply.speak
            if reply.display:
                text = f"{reply.speak}\n{reply.display}" if reply.speak else reply.display
            self.message.emit("jarvis", text)
        if reply.sound:
            self.sound.emit(reply.sound)
        self._busy = True
        if self.listener:
            self.listener.pause(True)
        if self.cfg.tts_enabled and reply.speak:
            self._set_state("thinking")
            self.tts.speak(reply.speak)
        else:
            self._finish_turn()

    def _on_tts_started(self) -> None:
        self._set_state("speaking")

    def _on_tts_finished(self) -> None:
        self._finish_turn()

    def _on_tts_failed(self, msg: str) -> None:
        self.message.emit("system", msg)
        self.sound.emit("error")
        self._finish_turn()

    def _finish_turn(self) -> None:
        after = self._after
        self._after = None
        self._busy = False
        if after and after.end_conv:
            self.conv_until = 0.0
        else:
            self.conv_until = time.monotonic() + max(0, self.cfg.conversation_timeout)
        if self.listener and self.mic_on:
            self.listener.pause(False)
        self._set_state(self._idle_state())
        if after and after.quit_after:
            self.quit_requested.emit()

    def stop_speaking(self) -> None:
        self.tts.stop()
        if self._busy:
            self._finish_turn()

    def shutdown(self) -> None:
        self.tts.stop()
        if self.mic_on:
            self.stop_mic()
        for lt in list(self._retired):
            lt.wait(1500)
        self.executor.shutdown(wait=False, cancel_futures=True)
