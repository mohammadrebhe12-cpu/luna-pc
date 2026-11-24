"""خيط الاستماع: يلتقط المايك، يكشف الكلام، ويحوّله إلى نص."""
from __future__ import annotations

import logging
import queue

from PySide6.QtCore import QThread, Signal

from .config import Config
from .stt import Transcriber
from .vad import FRAME, SAMPLE_RATE, VadSegmenter

log = logging.getLogger(__name__)


def list_input_devices() -> list[tuple[str, str]]:
    """[(المعرّف, الاسم)] لأجهزة الإدخال؛ فارغ إن لم تتوفر sounddevice."""
    try:
        import sounddevice as sd
        out = []
        for i, d in enumerate(sd.query_devices()):
            if d.get("max_input_channels", 0) > 0:
                out.append((str(i), f"{d['name']}"))
        return out
    except Exception:
        return []


class ListenerThread(QThread):
    status = Signal(str)        # loading | ready | transcribing
    level = Signal(float)       # 0..1
    heard_speech = Signal()
    transcript = Signal(str)
    failed = Signal(str)

    def __init__(self, cfg: Config, transcriber: Transcriber, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self.transcriber = transcriber
        self._stop = False
        self._paused = False

    def pause(self, value: bool) -> None:
        self._paused = value

    def stop(self) -> None:
        self._stop = True

    def run(self) -> None:  # noqa: C901
        try:
            if not self.transcriber.loaded:
                self.status.emit("loading")
            self.transcriber.load()
        except Exception as e:
            log.exception("model load failed")
            self.failed.emit(f"تعذّر تحميل نموذج التعرف على الصوت (تحتاج إنترنت أول مرة): {e}")
            return
        try:
            import sounddevice as sd
        except Exception as e:
            self.failed.emit(f"مكتبة الصوت sounddevice غير متوفرة: {e}")
            return

        q: queue.Queue = queue.Queue(maxsize=600)

        def callback(indata, frames, time_info, status):  # noqa: ARG001
            try:
                q.put_nowait(indata[:, 0].copy())
            except queue.Full:
                pass

        dev = self.cfg.mic_device
        device = int(dev) if str(dev).isdigit() else (dev or None)
        seg = VadSegmenter(sensitivity=self.cfg.vad_sensitivity)
        try:
            stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32",
                                    blocksize=FRAME, device=device, callback=callback)
            stream.start()
        except Exception as e:
            log.exception("mic open failed")
            self.failed.emit(f"تعذّر فتح المايكروفون: {e}")
            return

        self.status.emit("ready")
        was_paused = False
        try:
            while not self._stop:
                try:
                    frame = q.get(timeout=0.25)
                except queue.Empty:
                    continue
                if self._paused:
                    if not was_paused:
                        seg.reset()
                        self.level.emit(0.0)
                        was_paused = True
                    continue
                if was_paused:
                    was_paused = False
                    while not q.empty():  # تجاهل ما التُقط أثناء كلام جارفيس
                        q.get_nowait()
                    continue
                audio = seg.feed(frame)
                self.level.emit(seg.level)
                if seg.just_started:
                    self.heard_speech.emit()
                if audio is not None:
                    self.status.emit("transcribing")
                    text = ""
                    try:
                        text = self.transcriber.transcribe(audio)
                    except Exception as e:
                        log.exception("transcribe failed")
                        self.failed.emit(f"فشل التعرف على الكلام: {e}")
                    while not q.empty():
                        q.get_nowait()
                    seg.reset()
                    self.status.emit("ready")
                    if text and not self._stop:
                        self.transcript.emit(text)
        finally:
            try:
                stream.stop()
                stream.close()
            except Exception:
                pass
