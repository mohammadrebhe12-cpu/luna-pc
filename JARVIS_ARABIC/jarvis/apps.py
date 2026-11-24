"""جداول التطبيقات والمواقع المعروفة (بأسمائها العربية والإنجليزية واللهجة الأردنية)."""
from __future__ import annotations


from .textutil import norm, strip_al

# key: (أسماء, أمر التشغيل لـ `start`, عمليات الإغلاق)
APPS: dict[str, dict] = {
    "chrome": {"names": ["chrome", "google chrome", "كروم", "جوجل كروم", "قوقل كروم", "المتصفح", "browser"],
               "launch": "chrome", "procs": ["chrome.exe"], "label": "كروم"},
    "edge": {"names": ["edge", "microsoft edge", "ايدج", "إيدج", "مايكروسوفت ايدج"],
             "launch": "msedge", "procs": ["msedge.exe"], "label": "إيدج"},
    "firefox": {"names": ["firefox", "فايرفوكس", "فيرفوكس", "فايرفكس"],
                "launch": "firefox", "procs": ["firefox.exe"], "label": "فايرفوكس"},
    "notepad": {"names": ["notepad", "نوت باد", "المفكره", "مفكرة", "الدفتر", "نوتباد"],
                "launch": "notepad", "procs": ["notepad.exe"], "label": "المفكرة"},
    "calculator": {"names": ["calculator", "calc", "الحاسبه", "حاسبه", "الالة الحاسبه", "كالكيوليتر", "الكالكوليتر"],
                   "launch": "calc", "procs": ["CalculatorApp.exe", "calc.exe", "Calculator.exe"], "label": "الحاسبة"},
    "explorer": {"names": ["file explorer", "explorer", "مستكشف الملفات", "الملفات", "مدير الملفات", "الاكسبلورر"],
                 "launch": "explorer", "procs": [], "label": "مستكشف الملفات"},
    "word": {"names": ["word", "microsoft word", "ورد", "الورد", "مايكروسوفت ورد"],
             "launch": "winword", "procs": ["WINWORD.EXE"], "label": "ورد"},
    "excel": {"names": ["excel", "اكسل", "إكسل", "الاكسل"],
              "launch": "excel", "procs": ["EXCEL.EXE"], "label": "إكسل"},
    "powerpoint": {"names": ["powerpoint", "power point", "باوربوينت", "باور بوينت", "بوربوينت"],
                   "launch": "powerpnt", "procs": ["POWERPNT.EXE"], "label": "باوربوينت"},
    "outlook": {"names": ["outlook", "اوتلوك", "أوتلوك"],
                "launch": "outlook", "procs": ["OUTLOOK.EXE"], "label": "أوتلوك"},
    "spotify": {"names": ["spotify", "سبوتيفاي", "سبوتفاي"],
                "launch": "spotify:", "procs": ["Spotify.exe"], "label": "سبوتيفاي"},
    "vscode": {"names": ["vs code", "vscode", "visual studio code", "فيجوال ستوديو كود", "في اس كود", "فيجوال ستديو كود"],
               "launch": "code", "procs": ["Code.exe"], "label": "فيجوال ستوديو كود"},
    "cmd": {"names": ["cmd", "command prompt", "سي ام دي", "سطر الاوامر", "موجه الاوامر", "الكمند"],
            "launch": "cmd", "procs": ["cmd.exe"], "label": "سطر الأوامر"},
    "powershell": {"names": ["powershell", "power shell", "باوركشل", "باور شل", "بوورشيل"],
                   "launch": "powershell", "procs": ["powershell.exe"], "label": "باورشل"},
    "terminal": {"names": ["terminal", "windows terminal", "التيرمنال", "الطرفيه"],
                 "launch": "wt", "procs": ["WindowsTerminal.exe"], "label": "التيرمنال"},
    "paint": {"names": ["paint", "mspaint", "الرسام", "رسام", "بينت", "الباينت"],
              "launch": "mspaint", "procs": ["mspaint.exe"], "label": "الرسام"},
    "taskmgr": {"names": ["task manager", "taskmgr", "مدير المهام", "ادارة المهام", "تاسك مانجر"],
                "launch": "taskmgr", "procs": ["Taskmgr.exe"], "label": "مدير المهام"},
    "settings": {"names": ["settings", "الاعدادات", "اعدادات ويندوز", "الإعدادات", "اعدادات"],
                 "launch": "ms-settings:", "procs": ["SystemSettings.exe"], "label": "الإعدادات"},
    "control": {"names": ["control panel", "لوحه التحكم", "كنترول بانل"],
                "launch": "control", "procs": [], "label": "لوحة التحكم"},
    "whatsapp": {"names": ["whatsapp", "واتساب", "واتس اب", "واتس", "الواتس", "الواتساب"],
                 "launch": "whatsapp:", "procs": ["WhatsApp.exe", "WhatsApp.Root.exe"], "label": "واتساب"},
    "telegram": {"names": ["telegram", "تلغرام", "تيليجرام", "تلجرام", "تليجرام"],
                 "launch": "telegram", "procs": ["Telegram.exe"], "label": "تلغرام"},
    "discord": {"names": ["discord", "ديسكورد", "ديسكورت"],
                "launch": "discord", "procs": ["Discord.exe"], "label": "ديسكورد"},
    "teams": {"names": ["teams", "microsoft teams", "تيمز"],
              "launch": "msteams:", "procs": ["ms-teams.exe", "Teams.exe"], "label": "تيمز"},
    "zoom": {"names": ["zoom", "زووم", "زوم"],
             "launch": "zoom", "procs": ["Zoom.exe"], "label": "زوم"},
    "vlc": {"names": ["vlc", "في ال سي", "فى ال سى", "في ال سي بلاير"],
            "launch": "vlc", "procs": ["vlc.exe"], "label": "VLC"},
    "snipping": {"names": ["snipping tool", "snip", "اداه القص", "القص"],
                 "launch": "snippingtool", "procs": ["SnippingTool.exe"], "label": "أداة القص"},
    "camera": {"names": ["camera", "الكاميرا", "كاميرا"],
               "launch": "microsoft.windows.camera:", "procs": ["WindowsCamera.exe"], "label": "الكاميرا"},
    "store": {"names": ["microsoft store", "store", "المتجر", "ستور"],
              "launch": "ms-windows-store:", "procs": ["WinStore.App.exe"], "label": "المتجر"},
}

SITES: dict[str, dict] = {
    "youtube": {"names": ["youtube", "يوتيوب", "اليوتيوب", "يوتوب"], "url": "https://www.youtube.com", "label": "يوتيوب"},
    "google": {"names": ["google", "جوجل", "قوقل", "غوغل"], "url": "https://www.google.com", "label": "جوجل"},
    "facebook": {"names": ["facebook", "فيسبوك", "فيس بوك", "الفيس", "فيس"], "url": "https://www.facebook.com", "label": "فيسبوك"},
    "instagram": {"names": ["instagram", "انستغرام", "انستجرام", "انستا", "الانستا"], "url": "https://www.instagram.com", "label": "إنستغرام"},
    "twitter": {"names": ["twitter", "تويتر", "x", "اكس"], "url": "https://x.com", "label": "إكس"},
    "gmail": {"names": ["gmail", "جيميل", "الايميل", "البريد", "ايميل"], "url": "https://mail.google.com", "label": "جيميل"},
    "github": {"names": ["github", "جيت هاب", "جيتهب", "قيت هاب"], "url": "https://github.com", "label": "جيت هاب"},
    "whatsapp_web": {"names": ["whatsapp web", "واتساب ويب", "واتس اب ويب"], "url": "https://web.whatsapp.com", "label": "واتساب ويب"},
    "chatgpt": {"names": ["chatgpt", "شات جي بي تي", "تشات جي بي تي"], "url": "https://chatgpt.com", "label": "شات جي بي تي"},
    "claude": {"names": ["claude", "كلود"], "url": "https://claude.ai", "label": "كلود"},
    "linkedin": {"names": ["linkedin", "لينكدان", "لينكد ان"], "url": "https://www.linkedin.com", "label": "لينكدإن"},
    "netflix": {"names": ["netflix", "نتفلكس", "نتفليكس"], "url": "https://www.netflix.com", "label": "نتفلكس"},
    "maps": {"names": ["google maps", "maps", "الخرائط", "خرائط جوجل", "خريطه"], "url": "https://maps.google.com", "label": "الخرائط"},
    "wikipedia": {"names": ["wikipedia", "ويكيبيديا", "ويكبيديا"], "url": "https://ar.wikipedia.org", "label": "ويكيبيديا"},
    "translate": {"names": ["google translate", "translate", "المترجم", "ترجمه جوجل"], "url": "https://translate.google.com", "label": "المترجم"},
    "tiktok": {"names": ["tiktok", "تيك توك", "تيكتوك"], "url": "https://www.tiktok.com", "label": "تيك توك"},
    "reddit": {"names": ["reddit", "ريديت"], "url": "https://www.reddit.com", "label": "ريديت"},
    "amazon": {"names": ["amazon", "امازون", "أمازون"], "url": "https://www.amazon.com", "label": "أمازون"},
    "aljazeera": {"names": ["الجزيره", "aljazeera", "al jazeera"], "url": "https://www.aljazeera.net", "label": "الجزيرة"},
}


def _tokens(s: str) -> list[str]:
    return [strip_al(t) for t in norm(s).split()]


def _build(table: dict) -> list[tuple[list[str], str]]:
    out = []
    for key, spec in table.items():
        for n in spec["names"]:
            out.append((_tokens(n), key))
    out.sort(key=lambda x: -len(" ".join(x[0])))
    return out


_APP_INDEX = _build(APPS)
_SITE_INDEX = _build(SITES)


def _match(text: str, index: list[tuple[list[str], str]]) -> str | None:
    toks = _tokens(text)
    if not toks:
        return None
    best, best_len = None, 0
    for alias, key in index:
        n = len(alias)
        if not n or n > len(toks):
            continue
        for i in range(len(toks) - n + 1):
            if toks[i:i + n] == alias:
                length = len(" ".join(alias))
                if length > best_len:
                    best, best_len = key, length
                break
    return best


def find_app(text: str) -> str | None:
    return _match(text, _APP_INDEX)


def find_site(text: str) -> str | None:
    return _match(text, _SITE_INDEX)


def find_custom(text: str, custom: dict | None) -> tuple[str, str] | None:
    """مطابقة التطبيقات المخصصة من الإعدادات. يرجع (الاسم, المسار)."""
    if not custom:
        return None
    toks = _tokens(text)
    best = None
    for name, path in custom.items():
        alias = _tokens(name)
        n = len(alias)
        if not n or n > len(toks):
            continue
        for i in range(len(toks) - n + 1):
            if toks[i:i + n] == alias and (best is None or n > best[2]):
                best = (name, path, n)
                break
    return (best[0], best[1]) if best else None


def process_name_from_path(path: str) -> str:
    return path.strip('"').replace("\\", "/").rsplit("/", 1)[-1]
