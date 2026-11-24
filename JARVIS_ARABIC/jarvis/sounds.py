"""مؤثرات صوتية سينمائية تُولَّد برمجيًا (لا ملفات خارجية ولا حقوق)."""
from __future__ import annotations

import os
import wave
from pathlib import Path

import numpy as np

from .config import Config, sounds_dir

SR = 22050

# اسم: قائمة (تردد_بداية, تردد_نهاية, مدة_ثانية, شدة)
SOUNDS = {
    "boot": [(330, 330, .10, .5), (440, 440, .10, .5), (660, 660, .10, .5), (880, 1480, .40, .6)],
    "wake": [(600, 900, .09, .6), (900, 1300, .13, .6)],
    "done": [(880, 700, .08, .4), (700, 990, .10, .4)],
    "error": [(240, 170, .30, .6)],
    "off": [(900, 500, .15, .5), (500, 250, .20, .5)],
}


def _render(notes) -> np.ndarray:
    chunks = []
    for f0, f1, dur, vol in notes:
        n = int(SR * dur)
        freq = np.linspace(f0, f1, n)
        phase = 2 * np.pi * np.cumsum(freq) / SR
        wave_ = np.sin(phase) + 0.30 * np.sin(2 * phase) + 0.10 * np.sin(3 * phase)
        env = np.ones(n)
        a, r = max(1, int(0.005 * SR)), max(1, int(0.35 * n))
        env[:a] = np.linspace(0, 1, a)
        env[-r:] = np.linspace(1, 0, r)
        chunks.append(wave_ * env * vol)
    sig = np.concatenate(chunks)
    # صدى خفيف يعطي إحساس «هولوغرام»
    d = int(0.16 * SR)
    out = np.zeros(len(sig) + 2 * d)
    out[:len(sig)] += sig
    out[d:d + len(sig)] += 0.35 * sig
    out[2 * d:2 * d + len(sig)] += 0.12 * sig
    out /= max(1.0, float(np.max(np.abs(out)))) * 1.25
    return out


def ensure_sounds(folder: Path | None = None) -> dict[str, Path]:
    folder = folder or sounds_dir()
    paths = {}
    for name, notes in SOUNDS.items():
        p = folder / f"{name}.wav"
        if not p.exists():
            data = (np.clip(_render(notes), -1, 1) * 32767).astype("<i2")
            with wave.open(str(p), "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(SR)
                w.writeframes(data.tobytes())
        paths[name] = p
    return paths


class SoundFx:
    """تشغيل المؤثرات عبر QSoundEffect (يُنشأ في خيط الواجهة)."""

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.paths = ensure_sounds()
        self._fx: dict = {}

    def play(self, name: str) -> None:
        if not self.cfg.sounds_enabled or name not in self.paths or os.environ.get("JARVIS_NO_AUDIO"):
            return
        try:
            from PySide6.QtCore import QUrl
            from PySide6.QtMultimedia import QMediaDevices, QSoundEffect
            if not QMediaDevices.audioOutputs():  # لا يوجد جهاز إخراج صوت
                return
            fx = self._fx.get(name)
            if fx is None:
                fx = QSoundEffect()
                fx.setSource(QUrl.fromLocalFile(str(self.paths[name])))
                fx.setVolume(0.45)
                self._fx[name] = fx
            fx.play()
        except Exception:
            pass
