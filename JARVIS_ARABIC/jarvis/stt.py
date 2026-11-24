"""التعرف على الكلام: faster-whisper (مفتوح المصدر، يعمل محليًا بدون إنترنت بعد تحميل النموذج لأول مرة)."""
from __future__ import annotations

import logging
import os
import threading

import numpy as np

from .config import Config, models_dir
from .textutil import norm

log = logging.getLogger(__name__)

_HALLUCINATIONS = [norm(x) for x in [
    "ترجمة نانسي قنقر", "اشترك في القناة", "اشتركوا في القناة", "شكرا على المشاهدة", "شكرا للمشاهدة",
    "شكرا لكم على المشاهدة", "نراكم في الحلقة القادمة", "اشتركوا بالقناة", "تابعونا", "مترجم",
    "thanks for watching", "thank you for watching", "subtitles by", "amara.org", "please subscribe",
    "like and subscribe", "you", "bye", "الله يعطيك العافية",
]]


def is_hallucination(text: str) -> bool:
    n = norm(text)
    if not n or len(n) < 2:
        return True
    if n in ("you", "bye", "thank you", "thanks"):
        return True
    return any(h in n for h in _HALLUCINATIONS if len(h) > 6)


class Transcriber:
    PROMPT_AR = "يا لونا، افتح كروم، سكر المتصفح، ارفع الصوت، شغل أغنية، خذ سكرين شوت، كم الساعة؟"
    PROMPT_EN = "Luna, open Chrome, close Notepad, volume up, play a song, take a screenshot."

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self._model = None
        self._loaded_name = None
        self._lock = threading.Lock()

    @property
    def loaded(self) -> bool:
        return self._model is not None and self._loaded_name == self.cfg.stt_model

    def load(self) -> None:
        with self._lock:
            if self.loaded:
                return
            from faster_whisper import WhisperModel  # استيراد متأخر (ثقيل)
            threads = max(2, min(8, (os.cpu_count() or 4)))
            log.info("loading whisper model %s", self.cfg.stt_model)
            self._model = WhisperModel(self.cfg.stt_model, device="cpu", compute_type="int8",
                                       cpu_threads=threads, download_root=str(models_dir()))
            self._loaded_name = self.cfg.stt_model

    def transcribe(self, audio: np.ndarray) -> str:
        if not self.loaded:
            self.load()
        lang = None if self.cfg.stt_language == "auto" else self.cfg.stt_language
        prompt = self.PROMPT_EN if lang == "en" else self.PROMPT_AR
        segments, _info = self._model.transcribe(
            audio.astype(np.float32), language=lang, beam_size=1, vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 400}, condition_on_previous_text=False,
            temperature=0.0, initial_prompt=prompt, without_timestamps=True)
        parts = []
        for s in segments:
            if s.no_speech_prob > 0.6 and s.avg_logprob < -0.8:
                continue
            if s.avg_logprob < -1.3:
                continue
            parts.append(s.text.strip())
        text = " ".join(p for p in parts if p).strip()
        return "" if is_hallucination(text) else text
