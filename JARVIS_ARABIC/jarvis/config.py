"""الإعدادات والمسارات."""
from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import dataclass, field, fields
from pathlib import Path

from . import APP_NAME

log = logging.getLogger(__name__)


def app_dir() -> Path:
    """مجلد بيانات التطبيق (%APPDATA%\\JarvisArabic على ويندوز)."""
    override = os.environ.get("JARVIS_HOME")
    if override:
        p = Path(override)
    elif sys.platform == "win32":
        base = Path(os.environ.get("APPDATA") or (Path.home() / "AppData" / "Roaming"))
        p = base / APP_NAME
    else:
        p = Path(os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config")) / APP_NAME
    p.mkdir(parents=True, exist_ok=True)
    return p


def _sub(name: str) -> Path:
    p = app_dir() / name
    p.mkdir(parents=True, exist_ok=True)
    return p


def models_dir() -> Path:
    return _sub("models")


def cache_dir() -> Path:
    return _sub("tts_cache")


def sounds_dir() -> Path:
    return _sub("sounds")


def log_file() -> Path:
    return app_dir() / "jarvis.log"


def resource_path(rel: str) -> Path:
    """مسار ملف مرفق (يعمل داخل PyInstaller أيضًا)."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base / rel


@dataclass
class Config:
    # --- الصوت (TTS) ---
    tts_enabled: bool = True
    voice: str = "ar-JO-SanaNeural"          # صوت أردني أنثوي (ar-JO-TaimNeural للذكر)
    english_voice: str = "en-GB-SoniaNeural"  # صوت إنجليزي أنثوي
    tts_rate: int = 0                        # نسبة السرعة %
    tts_pitch: int = 0                       # Hz
    # --- التعرف على الكلام (STT) ---
    stt_model: str = "small"                 # tiny/base/small/medium
    stt_language: str = "ar"                 # ar / en / auto
    mic_device: str = ""                     # فارغ = الافتراضي
    vad_sensitivity: float = 3.0             # أقل = أكثر حساسية
    # --- كلمة التنبيه والمحادثة ---
    wake_enabled: bool = True
    wake_words: list = field(default_factory=lambda: ["لونا", "luna"])
    conversation_timeout: int = 25           # ثواني بقاء المحادثة مفتوحة بدون كلمة التنبيه
    greet_on_start: bool = True
    honorific: str = "سيدي"
    # --- الذكاء الاصطناعي (Ollama محلي ومجاني) ---
    llm_enabled: bool = True
    llm_url: str = "http://localhost:11434"
    llm_model: str = "qwen2.5:3b"
    # --- النظام ---
    sounds_enabled: bool = True
    autostart: bool = False
    start_minimized: bool = False
    music_folder: str = ""
    custom_apps: dict = field(default_factory=dict)   # {"اسم": "C:\\path\\app.exe"}

    # ---- حفظ/تحميل ----
    @classmethod
    def path(cls) -> Path:
        return app_dir() / "config.json"

    @classmethod
    def load(cls) -> "Config":
        cfg = cls()
        try:
            data = json.loads(cls.path().read_text(encoding="utf-8"))
        except FileNotFoundError:
            return cfg
        except Exception as e:  # ملف تالف
            log.warning("config unreadable: %s", e)
            return cfg
        known = {f.name: f for f in fields(cls)}
        for k, v in data.items():
            if k not in known:
                continue
            cur = getattr(cfg, k)
            try:
                if isinstance(cur, bool):
                    v = bool(v)
                elif isinstance(cur, int):
                    v = int(v)
                elif isinstance(cur, float):
                    v = float(v)
                elif isinstance(cur, str):
                    v = str(v)
                elif isinstance(cur, list):
                    v = [str(x) for x in v]
                elif isinstance(cur, dict):
                    v = {str(a): str(b) for a, b in dict(v).items()}
            except Exception:
                continue
            setattr(cfg, k, v)
        return cfg

    def save(self) -> None:
        data = {f.name: getattr(self, f.name) for f in fields(self)}
        tmp = self.path().with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.path())
