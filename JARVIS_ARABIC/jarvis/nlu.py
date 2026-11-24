"""فهم الأوامر بالقواعد (سريع وبدون إنترنت) للعربية الفصحى واللهجة الأردنية/الشامية والإنجليزية.

ما لا تفهمه القواعد يُحوَّل إلى النموذج اللغوي (Ollama) إن كان متاحًا.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import apps
from .textutil import detect_lang, extract_number, norm, strip_al


@dataclass
class Intent:
    name: str
    args: dict = field(default_factory=dict)
    lang: str = "ar"
    raw: str = ""


def _N(items):
    return [norm(x) for x in items]


def has(t: str, phrases) -> bool:
    """هل يحتوي النص الموحّد على إحدى العبارات (كلمات كاملة)؟"""
    for p in phrases:
        if re.search(r"(?<!\w)" + re.escape(p) + r"(?!\w)", t):
            return True
    return False


def has_prefix(t: str, phrases) -> bool:
    for p in phrases:
        if t == p or t.startswith(p + " "):
            return True
    return False


# ------------------------------------------------------------------ كلمات مساعدة
_FILLER_PHRASES = _N([
    "لو سمحت", "من فضلك", "من فضلك", "بليز", "please", "ممكن", "بدي منك", "بدي", "الرجاء", "رجاء",
    "يا جارفيس", "جارفيس", "hey jarvis", "jarvis", "يا لونا", "لونا", "hey luna", "luna", "اوكي", "okay", "طيب", "يلا", "هلا جارفيس",
    "can you", "could you", "would you", "i want you to", "i want to", "i need you to",
])
_FILLER_RE = re.compile(r"(?<!\w)(?:" + "|".join(sorted(map(re.escape, _FILLER_PHRASES), key=len, reverse=True)) + r")(?!\w)")

OPEN_VERBS = _N(["افتح", "افتحلي", "افتحي", "فتح", "شغل", "شغللي", "شغلي", "اطلق", "روح على", "وديني على",
                 "open", "launch", "start", "run", "load"])
CLOSE_VERBS = _N(["سكر", "سكرلي", "سكري", "اغلق", "اغلقي", "اقفل", "اقفللي", "اقفلي", "طفي", "اطفي", "اطفيلي",
                  "انهي", "اقتل", "close", "kill", "quit", "exit", "terminate", "stop"])
PLAY_VERBS = _N(["شغل", "شغللي", "شغلي", "شغلني", "اسمعني", "سمعني", "اسمع", "play", "put on", "بدي اسمع"])
MUSIC_NOUNS = _N(["اغنيه", "اغنية", "اغاني", "الاغنيه", "مقطع", "فيديو", "song", "songs", "track", "video",
                  "لي", "لنا", "شي", "اشي", "ايشي", "اي", "any", "some", "a", "the"])
GENERIC_MUSIC = set(_N(["موسيقى", "الموسيقى", "music", "اغاني", "songs"]))
APP_NOUNS = _N(["برنامج", "تطبيق", "موقع", "الموقع", "البرنامج", "التطبيق", "ال", "لي", "app", "application",
                "program", "website", "site", "the", "my", "لنا", "على", "الى", "إلى"])

DEVICE_WORDS = _N(["الجهاز", "الكمبيوتر", "اللابتوب", "الحاسوب", "الحاسب", "ويندوز", "computer", "pc", "laptop",
                   "windows"])
SCREEN_WORDS = _N(["الشاشه", "screen"])
SOUND_WORDS = _N(["الصوت", "صوت", "volume", "السماعه", "السماعات", "الساوند", "sound"])


def strip_fillers(t: str) -> str:
    t = _FILLER_RE.sub(" ", t)
    return re.sub(r"\s+", " ", t).strip()


def _split_verb(t: str, verbs) -> tuple[str, str] | None:
    """إن بدأ النص بفعل من القائمة يرجع (الفعل, الباقي)."""
    for v in sorted(verbs, key=len, reverse=True):
        if t == v:
            return v, ""
        if t.startswith(v + " "):
            return v, t[len(v) + 1:].strip()
    return None


def _clean_object(obj: str, extra=()) -> str:
    drop = set(APP_NOUNS) | set(extra)
    toks = [w for w in obj.split() if w not in drop and strip_al(w) not in drop]
    return " ".join(toks).strip()


# ------------------------------------------------------------------ القواعد
_STOP_EXACT = set(_N(["اسكت", "بس", "كفايه", "كفى", "ستوب", "stop", "silence", "be quiet", "اخرس", "وقف", "وقفي"]))
_END_CONV = _N(["مع السلامه", "باي باي", "goodbye", "good bye", "وقف المحادثه", "انهي المحادثه", "روح نام",
                "انتهت المحادثه", "go to sleep"])
_END_EXACT = set(_N(["باي", "bye", "خلص", "سلام", "انتهينا", "نام", "تصبح على خير"]))
_EXIT_APP = _N(["اغلق جارفيس", "سكر جارفيس", "اطفي جارفيس", "اقفل جارفيس", "اخرج من جارفيس", "اخرج من البرنامج",
                "سكر البرنامج", "اغلاق البرنامج", "اغلق البرنامج", "close jarvis", "exit jarvis", "quit jarvis",
                "shut down jarvis", "اغلق التطبيق نفسك"])
_THANKS = _N(["شكرا", "يعطيك العافيه", "مشكور", "thanks", "thank you", "تسلم", "يسلمو", "الله يعطيك العافيه"])
_WHO = _N(["من انت", "مين انت", "شو اسمك", "ايش اسمك", "شو انت", "what is your name", "who are you", "what's your name"])
_HELP = _N(["شو بتقدر تعمل", "شو بتعمل", "ايش بتقدر", "شو الاوامر", "شو بتقدر", "ماذا تستطيع", "what can you do",
            "help", "مساعده", "الاوامر", "اعطني الاوامر"])
_GREET_START = _N(["مرحبا", "مرحبتين", "هلا", "اهلا", "السلام عليكم", "سلام عليكم", "صباح الخير", "مساء الخير",
                   "هاي", "hello", "hi", "hey", "good morning", "good evening", "good afternoon", "يا هلا"])
_HOW_ARE_YOU = _N(["كيفك", "كيف حالك", "شلونك", "شو اخبارك", "كيف الحال", "كيف حالك اليوم", "how are you",
                   "شو الاخبار", "اخبارك"])


def _rule_control(t: str, lang: str) -> Intent | None:
    if t in _STOP_EXACT:
        return Intent("ctl_stop_speaking", {}, lang)
    if has(t, _EXIT_APP):
        return Intent("ctl_exit", {}, lang)
    if has(t, _END_CONV) or t in _END_EXACT:
        return Intent("ctl_end_conversation", {}, lang)
    if has(t, _WHO):
        return Intent("ctl_who", {}, lang)
    if has(t, _HELP) and len(t.split()) <= 5:
        return Intent("ctl_help", {}, lang)
    if len(t.split()) <= 4 and has(t, _THANKS):
        return Intent("ctl_thanks", {}, lang)
    if len(t.split()) <= 4 and has(t, _HOW_ARE_YOU):
        return Intent("ctl_how_are_you", {}, lang)
    if len(t.split()) <= 3 and has_prefix(t, _GREET_START):
        return Intent("ctl_greet", {}, lang)
    return None


_SHUTDOWN_VERBS = _N(["طفي", "اطفي", "اطفيلي", "اطفئ", "اغلق", "سكر", "اقفل", "shutdown", "shut down",
                      "turn off", "power off", "اغلاق"])
_LOCK_VERBS = _N(["قفل", "اقفل", "اقفللي", "lock"])
_RESTART = _N(["اعاده تشغيل", "اعد تشغيل", "اعادة تشغيل", "ريستارت", "restart", "reboot", "ريبوت"])
_SLEEP = _N(["نيم الجهاز", "وضع السكون", "sleep mode", "سكون", "نيمه"])
_CANCEL_SHUT = _N(["الغي الاطفاء", "الغ الاطفاء", "الغاء الاطفاء", "cancel shutdown", "الغي الاغلاق", "الغ الاغلاق"])


def _rule_power(t: str, lang: str) -> Intent | None:
    if has(t, _CANCEL_SHUT):
        return Intent("cancel_shutdown", {}, lang)
    dev = has(t, DEVICE_WORDS)
    scr = has(t, SCREEN_WORDS)
    if scr and not dev and (_split_verb(t, _LOCK_VERBS) or _split_verb(t, _SHUTDOWN_VERBS)):
        return Intent("lock", {}, lang)  # «طفي/اقفل الشاشة» = قفل الشاشة
    if has(t, _RESTART) and (dev or len(t.split()) <= 3):
        return Intent("restart", {}, lang)
    if has(t, _SLEEP) or (t in ("sleep", "نام الجهاز")):
        return Intent("sleep", {}, lang)
    if has(t, ["lock screen", "lock computer", "lock pc", "lock"]) and len(t.split()) <= 4:
        return Intent("lock", {}, lang)
    if dev:
        sv = _split_verb(t, _LOCK_VERBS)
        if sv and sv[0] in ("قفل", "lock", "اقفل", "اقفللي"):
            # «اقفل الشاشة» = قفل الشاشة ، «اقفل الجهاز/الكمبيوتر» = قفل أيضًا (آمن)
            return Intent("lock", {}, lang)
        sv = _split_verb(t, _SHUTDOWN_VERBS)
        if sv or has(t, ["shutdown", "shut down", "turn off", "power off"]):
            return Intent("shutdown", {}, lang)
    return None


_UP_VERBS = _N(["ارفع", "علي", "زيد", "زود", "اعلي", "رفع", "increase", "raise", "up", "louder", "higher", "turn up", "اعلى"])
_DOWN_VERBS = _N(["وطي", "نزل", "خفض", "قلل", "خفف", "واطي", "lower", "decrease", "down", "quieter", "reduce",
                  "turn down", "وطيلي", "نزلي"])


def _rule_volume(t: str, lang: str) -> Intent | None:
    soundy = has(t, SOUND_WORDS)
    if has(t, _N(["فك الكتم", "الغ الكتم", "الغاء الكتم", "unmute", "رجع الصوت", "شغل الصوت", "ارجع الصوت"])):
        return Intent("unmute", {}, lang)
    if has(t, _N(["كتم", "اكتم", "كتمه", "mute", "اكتمه"])):
        return Intent("mute", {}, lang)
    if not soundy:
        if has(t, ["louder", "turn it up"]):
            return Intent("volume_up", {"step": 10}, lang)
        if has(t, ["quieter", "turn it down"]):
            return Intent("volume_down", {"step": 10}, lang)
        return None
    n = extract_number(t)
    if n is not None:
        return Intent("volume_set", {"level": max(0, min(100, n))}, lang)
    if has(t, _N(["اعلى صوت", "اقصى", "اخر شي", "maximum", "max", "full"])):
        return Intent("volume_set", {"level": 100}, lang)
    step = 10
    if has(t, _N(["شوي", "شويه", "slightly", "a bit", "little"])):
        step = 5
    elif has(t, _N(["كتير", "كثير", "كثيرا", "a lot", "much"])):
        step = 25
    words = set(t.split())
    if words & set(_DOWN_VERBS):
        return Intent("volume_down", {"step": step}, lang)
    if words & set(_UP_VERBS) or has(t, ["turn up"]):
        return Intent("volume_up", {"step": step}, lang)
    return None


_PAUSE = _N(["وقف الاغنيه", "وقف الموسيقى", "وقف مؤقتا", "ايقاف مؤقت", "pause", "وقف الاغاني", "اوقف الموسيقى",
             "اوقف الاغنيه", "وقف الفيديو", "pause music", "stop music", "stop the music", "وقف الموسيقي", "اوقف الموسيقي"])
_RESUME = _N(["كمل الاغنيه", "كمل الموسيقى", "resume", "continue playing", "كمل التشغيل", "استمر", "كمل الموسيقي",
              "كمل الفيديو"])
_NEXT = _N(["الاغنيه التاليه", "الاغنيه الجايه", "next song", "next track", "skip song", "skip track", "skip",
            "غير الاغنيه", "بدل الاغنيه", "التالي", "التاليه", "next"])
_PREV = _N(["الاغنيه السابقه", "الاغنيه اللي قبل", "previous song", "previous track", "previous", "prev song", "السابقه", "السابق"])


def _rule_media(t: str, lang: str) -> Intent | None:
    if has(t, _PAUSE) or t == "وقف الموسيقى":
        return Intent("media", {"cmd": "play_pause"}, lang)
    if has(t, _RESUME) or t in ("play", "كمل"):
        return Intent("media", {"cmd": "play_pause"}, lang)
    if has(t, _NEXT) and len(t.split()) <= 4:
        return Intent("media", {"cmd": "next"}, lang)
    if has(t, _PREV) and len(t.split()) <= 4:
        return Intent("media", {"cmd": "prev"}, lang)
    return None


_SHOT = _N(["سكرين شوت", "سكرينشوت", "screenshot", "screen shot", "لقطه شاشه", "لقطه للشاشه", "صور الشاشه",
            "صوره للشاشه", "صوره شاشه", "التقط الشاشه", "capture screen", "لقطه الشاشه", "خذ لقطه", "سكرين",
            "صوري الشاشه", "snapshot"])
_BATTERY = _N(["البطاريه", "نسبه الشحن", "battery", "كم الشحن", "الشحن"])
_SYSINFO = _N(["معلومات النظام", "معلومات الجهاز", "مواصفات الجهاز", "حاله الجهاز", "حاله النظام", "system info",
               "system status", "pc status", "حاله الكمبيوتر", "computer status", "specs", "مواصفات الكمبيوتر",
               "معلومات الكمبيوتر", "معلومات الحاسوب"])
_TIME = _N(["كم الساعه", "الساعه كم", "شو الوقت", "كم الوقت", "what time", "time is it", "current time",
            "الوقت الان", "الساعه الان", "شو الساعه", "what's the time", "الوقت هسا", "كم صارت الساعه", "الساعه هسا"])
_DATE = _N(["شو التاريخ", "تاريخ اليوم", "اي يوم اليوم", "شو اليوم", "what date", "today's date", "what day",
            "date today", "كم التاريخ", "التاريخ", "what is the date", "what's the date", "اي يوم"])


def _rule_info(t: str, lang: str) -> Intent | None:
    if has(t, _SHOT):
        return Intent("screenshot", {}, lang)
    if has(t, _BATTERY):
        return Intent("system_info", {"what": "battery"}, lang)
    if has(t, _SYSINFO):
        return Intent("system_info", {"what": "all"}, lang)
    if has(t, _N(["المعالج", "cpu", "السي بي يو", "البروسيسور", "استهلاك المعالج"])) and has(t, _N(["كم", "شو", "استهلاك", "نسبه", "usage", "how"])):
        return Intent("system_info", {"what": "cpu"}, lang)
    if has(t, _N(["الرام", "ram", "الذاكره", "memory"])) and has(t, _N(["كم", "شو", "استهلاك", "نسبه", "usage", "how"])):
        return Intent("system_info", {"what": "ram"}, lang)
    if has(t, _N(["القرص", "disk", "المساحه", "storage", "التخزين", "الهارد"])) and has(t, _N(["كم", "شو", "فاضي", "free", "how", "متبقي", "باقي"])):
        return Intent("system_info", {"what": "disk"}, lang)
    if has(t, _TIME):
        return Intent("time", {}, lang)
    if has(t, _DATE):
        return Intent("date", {}, lang)
    return None


_SEARCH_VERBS = _N(["ابحث عن", "ابحثلي عن", "ابحث لي عن", "دور على", "دورلي على", "دور لي على", "بحث عن", "فتش على",
                    "search for", "search", "look up", "google", "جوجل", "قوقل", "ابحث"])


def _rule_search(t: str, lang: str) -> Intent | None:
    sv = _split_verb(t, _SEARCH_VERBS)
    if not sv:
        return None
    q = sv[1]
    site = None
    m = re.match(r"^(?:في|ب|on|in|at)\s+(\S+)\s+(?:عن|for|about)?\s*(.*)$", q)
    if m and apps.find_site(m.group(1)) == "youtube":
        site, q = "youtube", m.group(2)
    elif re.match(r"^(?:على|في)\s+(?:يوتيوب|youtube)\b", q):
        site = "youtube"
        q = re.sub(r"^(?:على|في)\s+(?:يوتيوب|youtube)\s*(?:عن|for)?\s*", "", q)
    q = re.sub(r"^(?:عن|for|about)\s+", "", q).strip()
    if not q:
        return None
    return Intent("search_web", {"query": q, "site": site}, lang)


_DOMAIN_RE = re.compile(r"\b([a-z0-9][a-z0-9-]*(?:\.[a-z0-9-]+)*\.(?:com|net|org|io|jo|co|app|dev|edu|gov|info|me|tv|ai))\b")


def _rule_launch(t: str, lang: str, raw: str, custom: dict | None) -> Intent | None:
    # -------- تشغيل موسيقى / فتح تطبيق
    sv = _split_verb(t, OPEN_VERBS + PLAY_VERBS)
    if sv:
        verb, obj_raw = sv
        obj = _clean_object(obj_raw)
        is_play = verb in PLAY_VERBS
        if not obj:
            if is_play:
                return Intent("play_music", {"query": ""}, lang)
            return None
        # مطابقة التطبيقات المخصصة
        c = apps.find_custom(obj, custom)
        if c:
            return Intent("open_app", {"name": c[0], "path": c[1]}, lang)
        wants_site = has(obj_raw, _N(["موقع", "ويب", "website", "web", "site"]))
        app_key = apps.find_app(obj)
        site_key = apps.find_site(obj)
        # «واتساب ويب» تتغلب على «واتساب»
        if site_key == "whatsapp_web":
            return Intent("open_website", {"key": site_key}, lang)
        if app_key and not (wants_site and site_key):
            return Intent("open_app", {"key": app_key, "name": apps.APPS[app_key]["label"]}, lang)
        if site_key:
            return Intent("open_website", {"key": site_key}, lang)
        m = _DOMAIN_RE.search(raw.lower())
        if m:
            return Intent("open_website", {"url": "https://" + m.group(1)}, lang)
        if is_play:
            q = _clean_object(obj, MUSIC_NOUNS)
            if q in GENERIC_MUSIC:
                q = ""
            return Intent("play_music", {"query": q}, lang)
        if wants_site:
            return Intent("open_website", {"name": obj}, lang)
        return Intent("open_app", {"name": obj}, lang)
    # «بدي اسمع X» «سمعني X» تُعالج في PLAY_VERBS أعلاه
    # -------- إغلاق تطبيق
    sv = _split_verb(t, CLOSE_VERBS)
    if sv:
        verb, obj_raw = sv
        obj = _clean_object(obj_raw)
        if not obj:
            return None
        c = apps.find_custom(obj, custom)
        if c:
            return Intent("close_app", {"name": c[0], "process": apps.process_name_from_path(c[1])}, lang)
        key = apps.find_app(obj)
        if key:
            return Intent("close_app", {"key": key, "name": apps.APPS[key]["label"]}, lang)
        if apps.find_site(obj):
            return Intent("close_app", {"key": "chrome", "name": "المتصفح"}, lang)
        return Intent("close_app", {"name": obj}, lang)
    return None


def parse(text: str, custom_apps: dict | None = None) -> Intent | None:
    """يحوّل جملة المستخدم إلى Intent أو None إن لم تُفهم."""
    raw = text or ""
    lang = detect_lang(raw)
    t0 = norm(raw)
    if not t0:
        return None
    if has(t0, _EXIT_APP):
        return Intent("ctl_exit", {}, lang, raw)
    t = strip_fillers(t0) or t0
    for rule in (_rule_control, _rule_power, _rule_volume, _rule_media, _rule_info, _rule_search):
        r = rule(t, lang)
        if r:
            r.raw = raw
            return r
    r = _rule_launch(t, lang, raw, custom_apps)
    if r:
        r.raw = raw
    return r


# ------------------------------------------------------------------ ردود جاهزة للأوامر الحوارية
def canned_reply(name: str, lang: str, honorific: str = "سيدي", hour: int | None = None) -> str:
    ar = lang == "ar"
    if name == "ctl_greet":
        if hour is None:
            import datetime
            hour = datetime.datetime.now().hour
        if ar:
            part = "صباح الخير" if hour < 12 else ("مساء الخير" if hour < 19 else "مساء النور")
            return f"{part} {honorific}، كيف بقدر أساعدك؟"
        part = "Good morning" if hour < 12 else ("Good afternoon" if hour < 18 else "Good evening")
        return f"{part}, sir. How may I assist you?"
    if name == "ctl_how_are_you":
        return (f"تمام الحمدلله {honorific}، جاهزة لخدمتك. شو بتحب أعمل؟" if ar
                else "All systems operational, sir. What can I do for you?")
    if name == "ctl_thanks":
        return f"العفو {honorific}، هذا واجبي." if ar else "You're welcome, sir."
    if name == "ctl_who":
        return ("أنا لونا، مساعدتك الصوتية العربية المجانية. بقدر أفتح البرامج والمواقع، وأتحكم بالصوت والموسيقى، وآخذ لقطة شاشة، وأجاوبك على أسئلتك."
                if ar else "I'm Luna, your free voice assistant. I can launch apps, control volume and music, take screenshots, and chat.")
    if name == "ctl_help":
        return ("بقدر أعمل هذا: افتح أو سكّر أي برنامج، افتح المواقع، ابحث في جوجل أو يوتيوب، "
                "ارفع أو نزّل الصوت أو أكتمه، شغّل أغنية، خذ لقطة شاشة، أخبرك بالوقت والتاريخ ومعلومات الجهاز، "
                "وأقفل أو أطفي الجهاز. وإذا كان Ollama شغال بقدر أحكي معك وأفهم الأوامر المعقدة."
                if ar else
                "I can open and close apps and sites, search Google or YouTube, control volume and media, play songs, "
                "take screenshots, tell the time and system status, and lock or shut down the PC. With Ollama running I can also chat.")
    if name == "ctl_end_conversation":
        return f"تمام {honorific}، بانتظار ندائك." if ar else "Very well, sir. Call me when you need me."
    if name == "ctl_exit":
        return "إلى اللقاء." if ar else "Goodbye."
    if name == "ctl_stop_speaking":
        return ""
    return ""
