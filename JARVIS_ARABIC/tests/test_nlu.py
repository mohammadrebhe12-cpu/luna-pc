import pytest

from jarvis import nlu
from jarvis.textutil import extract_number, norm


def P(text, custom=None):
    r = nlu.parse(text, custom)
    return (r.name, r.args) if r else None


def test_norm():
    assert norm("أَفْتَحْ الكُروم!") == "افتح الكروم"
    assert norm("الصوت ٥٠") == "الصوت 50"
    assert norm("youtube.com.") == "youtube.com"


@pytest.mark.parametrize("text,key", [
    ("افتح الكروم", "chrome"), ("يا جارفيس افتحلي كروم", "chrome"), ("شغللي المفكرة", "notepad"),
    ("بدي افتح الحاسبة", "calculator"), ("open chrome", "chrome"), ("launch notepad", "notepad"),
    ("افتح إكسل", "excel"), ("افتح تطبيق واتساب", "whatsapp"), ("شغل سبوتيفاي", "spotify"),
    ("افتح الإعدادات", "settings"), ("لو سمحت افتح مدير المهام", "taskmgr"),
])
def test_open_app(text, key):
    name, args = P(text)
    assert name == "open_app" and args["key"] == key


@pytest.mark.parametrize("text,key", [
    ("سكر الكروم", "chrome"), ("سكرلي المفكرة", "notepad"), ("اغلق الحاسبة", "calculator"),
    ("اقفل الكروم", "chrome"), ("close chrome", "chrome"), ("طفي سبوتيفاي", "spotify"),
])
def test_close_app(text, key):
    name, args = P(text)
    assert name == "close_app" and args["key"] == key


@pytest.mark.parametrize("text,site", [
    ("افتح يوتيوب", "youtube"), ("افتحلي الفيسبوك", "facebook"), ("open github", "github"),
    ("افتح واتساب ويب", "whatsapp_web"), ("افتح جيميل", "gmail"),
])
def test_open_site(text, site):
    name, args = P(text)
    assert name == "open_website" and args["key"] == site


def test_open_domain_and_unknown():
    assert P("افتح موقع example.com") == ("open_website", {"url": "https://example.com"})
    assert P("افتح موقع الجامعة")[0] == "open_website"
    n, a = P("افتح فوتوشوب")
    assert n == "open_app" and a["name"] == "فوتوشوب"


@pytest.mark.parametrize("text,name,extra", [
    ("ارفع الصوت", "volume_up", {}), ("علي الصوت شوي", "volume_up", {"step": 5}),
    ("وطي الصوت", "volume_down", {}), ("نزل الصوت كتير", "volume_down", {"step": 25}),
    ("volume up", "volume_up", {}), ("turn the volume down", "volume_down", {}),
    ("اكتم الصوت", "mute", {}), ("كتم", "mute", {}), ("mute", "mute", {}),
    ("فك الكتم", "unmute", {}), ("unmute", "unmute", {}),
    ("خلي الصوت 30", "volume_set", {"level": 30}), ("الصوت على خمسين", "volume_set", {"level": 50}),
    ("set volume to 70", "volume_set", {"level": 70}), ("اضبط الصوت ٤٠", "volume_set", {"level": 40}),
])
def test_volume(text, name, extra):
    n, a = P(text)
    assert n == name
    for k, v in extra.items():
        assert a[k] == v


@pytest.mark.parametrize("text,name,args", [
    ("خذ سكرين شوت", "screenshot", {}), ("take a screenshot", "screenshot", {}), ("صور الشاشة", "screenshot", {}),
    ("كم الساعة", "time", {}), ("what time is it", "time", {}), ("شو التاريخ اليوم", "date", {}),
    ("معلومات النظام", "system_info", {"what": "all"}), ("كم نسبة البطارية", "system_info", {"what": "battery"}),
    ("كم استهلاك المعالج", "system_info", {"what": "cpu"}), ("كم الرام المستخدم", "system_info", {"what": "ram"}),
    ("قفل الشاشة", "lock", {}), ("lock screen", "lock", {}), ("اقفل الجهاز", "lock", {}),
    ("طفي الجهاز", "shutdown", {}), ("اطفي الكمبيوتر", "shutdown", {}), ("shutdown the computer", "shutdown", {}),
    ("اعادة تشغيل الجهاز", "restart", {}), ("restart", "restart", {}),
    ("الغي الاطفاء", "cancel_shutdown", {}),
    ("وقف الأغنية", "media", {"cmd": "play_pause"}), ("الأغنية التالية", "media", {"cmd": "next"}),
    ("pause", "media", {"cmd": "play_pause"}), ("previous song", "media", {"cmd": "prev"}),
])
def test_misc(text, name, args):
    n, a = P(text)
    assert n == name
    for k, v in args.items():
        assert a[k] == v


@pytest.mark.parametrize("text,q", [
    ("شغل أغنية عمرو دياب", "عمرو دياب"), ("شغللي فيروز", "فيروز"), ("play shape of you", "shape of you"),
    ("شغل موسيقى هادية", "موسيقي هاديه"),
])
def test_play_music(text, q):
    n, a = P(text)
    assert n == "play_music" and norm(a["query"]) == norm(q)


def test_play_music_empty():
    assert P("شغل موسيقى") == ("play_music", {"query": ""})


def test_search():
    assert P("ابحث عن طقس عمان") == ("search_web", {"query": "طقس عمان", "site": None})
    assert P("search for python tutorials") == ("search_web", {"query": "python tutorials", "site": None})
    n, a = P("ابحث في يوتيوب عن وصفة كنافة")
    assert n == "search_web" and a["site"] == "youtube" and a["query"] == "وصفه كنافه"


@pytest.mark.parametrize("text,name", [
    ("اسكت", "ctl_stop_speaking"), ("شكراً", "ctl_thanks"), ("من أنت", "ctl_who"), ("مرحبا", "ctl_greet"),
    ("كيفك", "ctl_how_are_you"), ("مع السلامة", "ctl_end_conversation"), ("اغلق جارفيس", "ctl_exit"),
    ("شو بتقدر تعمل", "ctl_help"), ("thank you", "ctl_thanks"), ("hello", "ctl_greet"),
])
def test_control(text, name):
    assert P(text)[0] == name


def test_custom_apps():
    custom = {"الالعاب": r"C:\Games\game.exe"}
    n, a = P("افتح الالعاب", custom)
    assert n == "open_app" and a["path"].endswith("game.exe")
    n, a = P("سكر الالعاب", custom)
    assert n == "close_app" and a["process"] == "game.exe"


def test_not_understood_goes_to_llm():
    assert P("اشرح لي نظرية النسبية بشكل مبسط") is None
    assert P("what is the capital of France") is None
    assert P("كيف أطبخ المنسف") is None


def test_extract_number():
    assert extract_number("الصوت 45") == 45
    assert extract_number("الصوت على ستين") == 60
    assert extract_number("بدون رقم") is None


def test_wake_name_stripped_from_command():
    assert P("يا لونا افتح كروم")[0] == "open_app"
    assert P("luna volume up")[0] == "volume_up"
