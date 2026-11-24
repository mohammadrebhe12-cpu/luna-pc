"""النطق: edge-tts (أصوات مايكروسوفت العصبية المجانية، ومنها الأردنية ar-JO) مع بديل بدون إنترنت (pyttsx3/SAPI)."""
from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import queue
import threading

from PySide6.QtCore import QObject, QUrl, Signal, Slot
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

from .config import Config, cache_dir
from .textutil import clean_for_tts, detect_lang

log = logging.getLogger(__name__)

ARABIC_VOICES = [
    ("ar-JO-TaimNeural", "عربي أردني - ذكر (تيم)"),
    ("ar-JO-SanaNeural", "عربي أردني - أنثى (سناء)"),
    ("ar-SA-HamedNeural", "عربي سعودي - ذكر"),
    ("ar-SA-ZariyahNeural", "عربي سعودي - أنثى"),
    ("ar-EG-ShakirNeural", "عربي مصري - ذكر"),
    ("ar-EG-SalmaNeural", "عربي مصري - أنثى"),
    ("ar-AE-HamdanNeural", "عربي إماراتي - ذكر"),
    ("ar-LB-RamiNeural", "عربي لبناني - ذكر"),
    ("ar-LB-LaylaNeural", "عربي لبناني - أنثى"),
]
ENGLISH_VOICES = [
    ("en-GB-RyanNeural", "English UK - Ryan"),
    ("en-GB-SoniaNeural", "English UK - Sonia"),
    ("en-US-GuyNeural", "English US - Guy"),
    ("en-US-AriaNeural", "English US - Aria"),
]


async def _synth(text: str, voice: str, rate: str, pitch: str, path: str) -> None:
    import edge_tts
    comm = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    await asyncio.wait_for(comm.save(path), timeout=25)


def _prune_cache(limit: int = 300) -> None:
    try:
        files = sorted(cache_dir().glob("*.mp3"), key=lambda p: p.stat().st_mtime)
        for p in files[:-limit]:
            p.unlink(missing_ok=True)
    except Exception:
        pass


class TTSEngine(QObject):
    started = Signal()
    finished = Signal()
    failed = Signal(str)
    _play_file = Signal(str)

    def __init__(self, cfg: Config, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self._q: queue.Queue = queue.Queue()
        self._gen = 0
        self._pending = 0
        self._lock = threading.Lock()
        self._done = threading.Event()
        self._player: QMediaPlayer | None = None
        self._audio: QAudioOutput | None = None
        self._play_file.connect(self._on_play_file)
        self._thread = threading.Thread(target=self._worker, name="jarvis-tts", daemon=True)
        self._thread.start()

    # ------------------------------------------------------------ واجهة عامة
    def speak(self, text: str) -> None:
        text = clean_for_tts(text)
        if not text:
            return
        with self._lock:
            self._pending += 1
            gen = self._gen
        self._q.put((gen, text))

    def stop(self) -> None:
        with self._lock:
            self._gen += 1
            self._pending = 0
        try:
            while True:
                self._q.get_nowait()
        except queue.Empty:
            pass
        self._done.set()
        if self._player is not None:
            self._player.stop()

    # ------------------------------------------------------------ خيط التوليد
    def _voice_for(self, text: str) -> str:
        return self.cfg.voice if detect_lang(text) == "ar" else self.cfg.english_voice

    def _synth_to_file(self, text: str) -> str | None:
        voice = self._voice_for(text)
        rate = f"{int(self.cfg.tts_rate):+d}%"
        pitch = f"{int(self.cfg.tts_pitch):+d}Hz"
        key = hashlib.sha1(f"{voice}|{rate}|{pitch}|{text}".encode("utf-8")).hexdigest()
        path = cache_dir() / f"{key}.mp3"
        if path.exists() and path.stat().st_size > 1000:
            return str(path)
        tmp = str(path) + ".part"
        try:
            asyncio.run(_synth(text, voice, rate, pitch, tmp))
            if os.path.getsize(tmp) < 500:
                raise RuntimeError("empty audio")
            os.replace(tmp, path)
            _prune_cache()
            return str(path)
        except Exception as e:
            log.warning("edge-tts failed (%s); falling back to offline voice", e)
            try:
                os.remove(tmp)
            except OSError:
                pass
            return None

    def _speak_offline(self, text: str) -> bool:
        try:
            import pyttsx3
            eng = pyttsx3.init()
            ar = detect_lang(text) == "ar"
            for v in eng.getProperty("voices"):
                blob = f"{v.name} {v.id} {getattr(v, 'languages', '')}".lower()
                if (ar and ("arab" in blob or "ar-" in blob or "hoda" in blob or "naayf" in blob)) or \
                        (not ar and ("english" in blob or "en-" in blob)):
                    eng.setProperty("voice", v.id)
                    break
            eng.setProperty("rate", 175 + int(self.cfg.tts_rate))
            eng.say(text)
            eng.runAndWait()
            return True
        except Exception as e:
            log.warning("offline tts failed: %s", e)
            return False

    def _worker(self) -> None:
        while True:
            gen, text = self._q.get()
            if gen != self._gen:
                continue
            path = self._synth_to_file(text)
            if gen != self._gen:
                continue
            ok = True
            if path:
                self._done.clear()
                self._play_file.emit(path)
                if not self._done.wait(timeout=180):
                    log.warning("playback timeout")
            else:
                self.started.emit()
                ok = self._speak_offline(text)
                if not ok:
                    self.failed.emit("تعذّر النطق: لا يوجد إنترنت لصوت edge-tts ولا صوت ويندوز بديل.")
            with self._lock:
                if gen != self._gen:
                    continue
                self._pending = max(0, self._pending - 1)
                last = self._pending == 0
            if last:
                self.finished.emit()

    # ------------------------------------------------------------ التشغيل (خيط الواجهة)
    def _ensure_player(self) -> QMediaPlayer:
        if self._player is None:
            self._audio = QAudioOutput(self)
            self._audio.setVolume(1.0)
            self._player = QMediaPlayer(self)
            self._player.setAudioOutput(self._audio)
            self._player.mediaStatusChanged.connect(self._on_status)
            self._player.errorOccurred.connect(self._on_error)
        return self._player

    @Slot(str)
    def _on_play_file(self, path: str) -> None:
        p = self._ensure_player()
        p.setSource(QUrl.fromLocalFile(path))
        p.play()
        self.started.emit()

    def _on_status(self, status) -> None:
        if status in (QMediaPlayer.MediaStatus.EndOfMedia, QMediaPlayer.MediaStatus.InvalidMedia):
            self._done.set()

    def _on_error(self, error, message: str = "") -> None:
        log.warning("player error: %s %s", error, message)
        self.failed.emit(f"خطأ في تشغيل الصوت: {message}")
        self._done.set()
