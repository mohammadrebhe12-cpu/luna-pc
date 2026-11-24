"""كشف الكلام (VAD) بالطاقة مع تقدير تكيّفي للضجيج. يعتمد على numpy فقط."""
from __future__ import annotations

from collections import deque

import numpy as np

SAMPLE_RATE = 16000
FRAME = 512  # 32ms


class VadSegmenter:
    def __init__(self, sensitivity: float = 3.0, end_silence: float = 0.85, max_seconds: float = 15.0,
                 min_speech: float = 0.30):
        self.sensitivity = sensitivity
        self.end_frames = int(end_silence * SAMPLE_RATE / FRAME)
        self.max_frames = int(max_seconds * SAMPLE_RATE / FRAME)
        self.min_frames = int(min_speech * SAMPLE_RATE / FRAME)
        self.reset()

    def reset(self) -> None:
        self.floor = 0.004
        self.speaking = False
        self.just_started = False
        self.level = 0.0
        self._voiced_run = 0
        self._silence = 0
        self._voiced_total = 0
        self._buf: list[np.ndarray] = []
        self._pre: deque[np.ndarray] = deque(maxlen=10)

    @property
    def threshold(self) -> float:
        return max(self.floor * self.sensitivity, 0.012)

    def feed(self, frame: np.ndarray):
        """يضيف إطارًا؛ يرجع مقطع الكلام (float32) عند انتهاء الجملة وإلا None."""
        frame = np.asarray(frame, dtype=np.float32)
        rms = float(np.sqrt(np.mean(frame * frame))) if frame.size else 0.0
        self.level = min(1.0, rms * 8.0)
        self.just_started = False
        voiced = rms > self.threshold

        if not self.speaking:
            if not voiced:
                self.floor = 0.95 * self.floor + 0.05 * rms  # تقدير الضجيج
                self.floor = max(self.floor, 0.0015)
            self._pre.append(frame)
            self._voiced_run = self._voiced_run + 1 if voiced else 0
            if self._voiced_run >= 3:
                self.speaking = True
                self.just_started = True
                self._buf = list(self._pre)
                self._silence = 0
                self._voiced_total = self._voiced_run
            return None

        self._buf.append(frame)
        if voiced or rms > self.threshold * 0.6:
            self._silence = 0
            self._voiced_total += 1 if voiced else 0
        else:
            self._silence += 1
        if self._silence >= self.end_frames or len(self._buf) >= self.max_frames:
            seg = np.concatenate(self._buf) if self._buf else None
            ok = self._voiced_total >= self.min_frames
            self.speaking = False
            self._voiced_run = 0
            self._buf = []
            self._pre.clear()
            return seg if ok else None
        return None
