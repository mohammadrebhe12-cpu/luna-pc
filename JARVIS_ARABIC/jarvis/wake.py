"""كشف كلمة التنبيه «يا جارفيس» من نص التعرف على الكلام (مطابقة تقريبية لأخطاء Whisper)."""
from __future__ import annotations

from difflib import SequenceMatcher

from .textutil import norm

# صيغ شائعة يكتب بها Whisper الاسم
_VARIANTS = ["جارفيس", "جارفس", "جارفيز", "جاريفس", "جارويس", "جاروس", "جارفيش", "جرفيس",
             "جارفيسس", "جارفيص", "جارفيث", "jarvis", "jarviss", "jarves", "garvis", "service"]
_LUNA = ["لونا", "لونه", "لوني", "لونى", "luna", "loona", "loona", "lunna", "لونة", "لوناا"]
_PREFIX = {"يا", "هاي", "هي", "اوكي", "اوك", "ok", "okay", "hey", "hi", "hello", "اهلا", "هلا", "اي", "ايه", "اسمع"}


def _wake_forms(words: list[str]) -> list[str]:
    forms = {norm(w) for w in words if w.strip()}
    if any(w in forms for w in ("جارفيس", "jarvis")):
        forms |= {norm(v) for v in _VARIANTS if v != "service"}
    if any(w in forms for w in ("لونا", "luna")):
        forms |= {norm(v) for v in _LUNA}
    return sorted(forms)


def _close(a: str, b: str) -> bool:
    if a == b:
        return True
    if min(len(a), len(b)) < 5:
        return False
    return SequenceMatcher(None, a, b).ratio() >= 0.78


def extract(text: str, wake_words: list[str]) -> tuple[bool, str]:
    """يرجع (وُجدت_كلمة_التنبيه, باقي_الجملة_بعد_حذفها)."""
    forms = _wake_forms(wake_words)
    toks = (text or "").split()
    ntoks = [norm(t) for t in toks]
    n = len(toks)
    for i in range(n):
        # كلمة واحدة
        if ntoks[i] and any(_close(ntoks[i], f) for f in forms):
            return True, _rest(toks, ntoks, i, i + 1)
        # كلمتان ملتصقتان («جار فيس»)
        if i + 1 < n and ntoks[i] and ntoks[i + 1]:
            joined = ntoks[i] + ntoks[i + 1]
            if any(_close(joined, f) for f in forms):
                return True, _rest(toks, ntoks, i, i + 2)
    return False, text


def _rest(toks, ntoks, start, end) -> str:
    before = toks[:start]
    nbefore = ntoks[:start]
    while nbefore and nbefore[-1] in _PREFIX:  # احذف «يا/هاي/اوكي» قبل الاسم
        before.pop()
        nbefore.pop()
    after = toks[end:]
    rest = " ".join(before + after).lstrip(" ,،.!؟?").strip()
    return rest
