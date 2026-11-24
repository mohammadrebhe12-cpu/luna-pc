"""أدوات معالجة النص العربي/الإنجليزي."""
from __future__ import annotations

import re

_DIAC = re.compile(r"[ؐ-ًؚ-ٰٟۖ-ۭـ]")
_MAP = str.maketrans({
    "أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ى": "ي", "ة": "ه", "ؤ": "و", "ئ": "ي",
    "گ": "ك", "چ": "ج", "پ": "ب", "ڤ": "ف",
    **{chr(0x0660 + i): str(i) for i in range(10)},
    **{chr(0x06F0 + i): str(i) for i in range(10)},
})
_NONWORD = re.compile(r"[^\w\s.]", re.UNICODE)
_LONE_DOT = re.compile(r"(?<!\w)\.|\.(?!\w)")
_WS = re.compile(r"\s+")


def norm(text: str) -> str:
    """توحيد النص: إزالة التشكيل، توحيد الألف والياء والتاء المربوطة، حذف الترقيم."""
    s = (text or "").lower()
    s = _DIAC.sub("", s)
    s = s.translate(_MAP)
    s = s.replace("_", " ")
    s = _NONWORD.sub(" ", s)
    s = _LONE_DOT.sub(" ", s)
    return _WS.sub(" ", s).strip()


def strip_al(word: str) -> str:
    """إزالة «ال» التعريف من بداية الكلمة (للمطابقة فقط)."""
    return word[2:] if word.startswith("ال") and len(word) > 4 else word


def detect_lang(text: str) -> str:
    ar = len(re.findall(r"[؀-ۿ]", text or ""))
    la = len(re.findall(r"[A-Za-z]", text or ""))
    return "ar" if ar >= la else "en"


def is_arabic(text: str) -> bool:
    return detect_lang(text) == "ar"


def clean_for_tts(text: str) -> str:
    """تنظيف النص قبل النطق (إزالة رموز ماركداون وإيموجي)."""
    s = re.sub(r"[`*_#>~|]+", " ", text or "")
    s = re.sub(r"https?://\S+", " ", s)
    s = re.sub(r"[\U0001F000-\U0001FAFF☀-➿]", " ", s)
    return _WS.sub(" ", s).strip()


_NUM_WORDS = {
    "صفر": 0, "zero": 0,
    "عشره": 10, "ten": 10, "عشرين": 20, "twenty": 20, "ثلاثين": 30, "thirty": 30,
    "اربعين": 40, "forty": 40, "خمسين": 50, "fifty": 50, "نص": 50, "نصف": 50, "half": 50,
    "ستين": 60, "sixty": 60, "سبعين": 70, "seventy": 70, "ثمانين": 80, "eighty": 80,
    "تسعين": 90, "ninety": 90, "مايه": 100, "ميه": 100, "مئه": 100, "hundred": 100,
    "خمسه": 5, "five": 5, "خمس": 5, "ربع": 25,
}


def extract_number(normalized: str) -> int | None:
    """استخراج رقم 0-100 من نص موحّد (أرقام أو كلمات)."""
    m = re.search(r"(?<![\w.])(\d{1,3})(?![\w.])", normalized)
    if m:
        return int(m.group(1))
    for w in normalized.split():
        w2 = strip_al(w)
        if w2 in _NUM_WORDS:
            return _NUM_WORDS[w2]
    return None
