"""تنفيذ الأوامر على ويندوز (فتح/إغلاق البرامج، الصوت، الموسيقى، لقطة الشاشة، معلومات النظام...).

هذه الوحدة لا تعتمد على Qt ويمكن اختبارها لوحدها. تُنفَّذ الأوامر من خيط عامل واحد.
"""
from __future__ import annotations

import datetime as _dt
import logging
import os
import platform
import random
import shutil
import subprocess
import sys
import time
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote_plus

from . import apps
from .config import Config

log = logging.getLogger(__name__)
IS_WIN = sys.platform == "win32"
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

DANGEROUS = {"shutdown", "restart", "sleep"}
INFO_ACTIONS = {"time", "date", "system_info", "volume_up", "volume_down", "volume_set", "mute", "unmute", "screenshot"}

ACTION_HELP = {
    "open_app": '{"name": "اسم التطبيق بالإنجليزية مثل chrome/notepad/spotify"}',
    "close_app": '{"name": "اسم التطبيق"}',
    "open_website": '{"url": "https://..."} أو {"name": "youtube"}',
    "search_web": '{"query": "نص البحث", "site": null أو "youtube"}',
    "volume_set": '{"level": 0-100}',
    "volume_up": "{}", "volume_down": "{}", "mute": "{}", "unmute": "{}",
    "play_music": '{"query": "اسم الأغنية أو الفنان"}',
    "media": '{"cmd": "play_pause" | "next" | "prev"}',
    "screenshot": "{}",
    "system_info": '{"what": "all" | "cpu" | "ram" | "disk" | "battery"}',
    "time": "{}", "date": "{}", "lock": "{}",
    "shutdown": "{}", "restart": "{}", "sleep": "{}",
}
ACTION_NAMES = set(ACTION_HELP) | {"cancel_shutdown"}

_AR_MONTHS = ["كانون الثاني", "شباط", "آذار", "نيسان", "أيار", "حزيران", "تموز", "آب", "أيلول",
              "تشرين الأول", "تشرين الثاني", "كانون الأول"]
_AR_DAYS = ["الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"]


@dataclass
class Result:
    speak: str
    display: str = ""
    ok: bool = True


class Actions:
    def __init__(self, cfg: Config):
        self.cfg = cfg

    # ------------------------------------------------------------ مساعدات
    @staticmethod
    def t(lang: str, ar: str, en: str) -> str:
        return ar if lang == "ar" else en

    def run(self, name: str, args: dict | None, lang: str = "ar") -> Result:
        args = args or {}
        fn = getattr(self, "a_" + name, None)
        if name not in ACTION_NAMES or fn is None:
            return Result(self.t(lang, "ما عندي هالأمر.", "I don't have that command."), ok=False)
        try:
            return fn(args, lang)
        except Exception as e:  # لا نترك أي خطأ يوقف المساعد
            log.exception("action %s failed", name)
            return Result(self.t(lang, "صار خطأ أثناء التنفيذ.", "Something went wrong while executing."),
                          display=f"{name}: {e}", ok=False)

    def _win_only(self, lang: str) -> Result:
        return Result(self.t(lang, "هذا الأمر يعمل على ويندوز فقط.", "That command only works on Windows."), ok=False)

    def _start(self, target: str) -> None:
        subprocess.Popen(["cmd", "/c", "start", "", target], creationflags=NO_WINDOW,
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # ------------------------------------------------------------ التطبيقات
    @staticmethod
    def _app_exists(launch: str) -> bool:
        if ":" in launch:  # بروتوكول مثل ms-settings:
            return True
        if shutil.which(launch):
            return True
        if IS_WIN:
            import winreg
            exe = launch if launch.lower().endswith(".exe") else launch + ".exe"
            for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
                try:
                    winreg.CloseKey(winreg.OpenKey(
                        hive, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths" + "\\" + exe))
                    return True
                except OSError:
                    continue
        return False

    @staticmethod
    def _start_menu_lookup(name: str) -> str | None:
        """بحث تقريبي في اختصارات قائمة ابدأ."""
        import difflib
        roots = [os.environ.get("ProgramData", ""), os.environ.get("APPDATA", "")]
        found: dict[str, str] = {}
        for r in roots:
            base = Path(r) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
            if base.exists():
                for p in base.rglob("*.lnk"):
                    found.setdefault(p.stem.lower(), str(p))
        q = name.lower().strip()
        for k, v in found.items():
            if q and q in k:
                return v
        m = difflib.get_close_matches(q, list(found), n=1, cutoff=0.6)
        return found[m[0]] if m else None

    def a_open_app(self, args: dict, lang: str) -> Result:
        if not IS_WIN:
            return self._win_only(lang)
        name = (args.get("name") or "").strip()
        label = name
        path = args.get("path")
        key = args.get("key") or (apps.find_app(name) if name else None)
        if path:
            self._start(path)
            return Result(self.t(lang, f"تمام، فتحت {name}.", f"Opening {name}."))
        if key and key in apps.APPS:
            spec = apps.APPS[key]
            label = spec["label"]
            if self._app_exists(spec["launch"]):
                self._start(spec["launch"])
                return Result(self.t(lang, f"تمام، فتحت {label}.", f"Opening {name or label}."))
        # لم يُعرف التطبيق: جرّب قائمة ابدأ، ثم الموقع
        lnk = self._start_menu_lookup(name) if name else None
        if lnk:
            os.startfile(lnk)  # type: ignore[attr-defined]
            return Result(self.t(lang, f"تمام، فتحت {name}.", f"Opening {name}."))
        if name and shutil.which(name):
            self._start(name)
            return Result(self.t(lang, f"تمام، فتحت {name}.", f"Opening {name}."))
        site = apps.find_site(name) if name else None
        if site:
            return self.a_open_website({"key": site}, lang)
        return Result(self.t(lang, f"ما لقيت برنامج اسمه {name}. بتقدر تضيفه من الإعدادات.",
                             f"I couldn't find an app called {name}. You can add it in Settings."), ok=False)

    def a_close_app(self, args: dict, lang: str) -> Result:
        if not IS_WIN:
            return self._win_only(lang)
        key = args.get("key") or apps.find_app(args.get("name") or "")
        name = args.get("name") or ""
        procs: list[str] = []
        if args.get("process"):
            procs = [args["process"]]
        elif key and key in apps.APPS:
            procs = list(apps.APPS[key]["procs"])
            name = apps.APPS[key]["label"]
            if key == "explorer" or not procs:
                return Result(self.t(lang, f"ما بنصح أسكّر {name} لأنه ممكن يوقف سطح المكتب.",
                                     f"I'd rather not close {name}; it may break the desktop."), ok=False)
        elif name and name.isascii():
            procs = [name if name.lower().endswith(".exe") else name + ".exe"]
        if not procs:
            return Result(self.t(lang, f"ما عرفت أي برنامج بدك أسكّر: {name}.", f"I don't know which program '{name}' is."), ok=False)
        closed = False
        for p in procs:
            r = subprocess.run(["taskkill", "/IM", p, "/F", "/T"], capture_output=True, timeout=15,
                               creationflags=NO_WINDOW)
            closed = closed or r.returncode == 0
        if closed:
            return Result(self.t(lang, f"تمام، سكّرت {name}.", f"Closed {name}."))
        return Result(self.t(lang, f"{name} مش شغّال أصلاً.", f"{name} isn't running."), ok=False)

    # ------------------------------------------------------------ المواقع والبحث
    def a_open_website(self, args: dict, lang: str) -> Result:
        url = args.get("url")
        label = args.get("name") or ""
        key = args.get("key") or (apps.find_site(label) if label else None)
        if key and key in apps.SITES:
            url, label = apps.SITES[key]["url"], apps.SITES[key]["label"]
        if not url:
            n = label.strip().lower().replace(" ", "")
            if n.isascii() and n:
                url = n if "." in n else f"{n}.com"
                url = "https://" + url.removeprefix("https://").removeprefix("http://")
            else:
                return self.a_search_web({"query": label}, lang)
        if not url.startswith("http"):
            url = "https://" + url
        webbrowser.open(url)
        return Result(self.t(lang, f"تمام، فتحت {label or url}.", f"Opening {label or url}."))

    def a_search_web(self, args: dict, lang: str) -> Result:
        q = (args.get("query") or "").strip()
        if not q:
            return Result(self.t(lang, "عن شو بدك أبحث؟", "What should I search for?"), ok=False)
        if args.get("site") == "youtube":
            webbrowser.open("https://www.youtube.com/results?search_query=" + quote_plus(q))
        else:
            webbrowser.open("https://www.google.com/search?q=" + quote_plus(q))
        return Result(self.t(lang, f"بحثت عن {q}.", f"Searching for {q}."))

    # ------------------------------------------------------------ الصوت
    @staticmethod
    def _endpoint():
        if not IS_WIN:
            return None
        try:
            try:
                import comtypes
                comtypes.CoInitialize()
            except Exception:
                pass
            from pycaw.pycaw import AudioUtilities
            dev = AudioUtilities.GetSpeakers()
            ev = getattr(dev, "EndpointVolume", None)
            if ev is not None:
                return ev
            from ctypes import POINTER, cast
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import IAudioEndpointVolume
            iface = dev.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            return cast(iface, POINTER(IAudioEndpointVolume))
        except Exception as e:
            log.warning("pycaw unavailable: %s", e)
            return None

    @staticmethod
    def _key(vk: int, times: int = 1) -> None:
        import ctypes
        u = ctypes.windll.user32  # type: ignore[attr-defined]
        for _ in range(times):
            u.keybd_event(vk, 0, 0, 0)
            u.keybd_event(vk, 0, 2, 0)
            time.sleep(0.02)

    def _vol_msg(self, lang: str, level: int | None) -> Result:
        if level is None:
            return Result(self.t(lang, "تمام.", "Done."))
        return Result(self.t(lang, f"الصوت الآن {level} بالمئة.", f"Volume is now {level} percent."))

    def _change_volume(self, delta: int, lang: str) -> Result:
        if not IS_WIN:
            return self._win_only(lang)
        ep = self._endpoint()
        if ep is not None:
            cur = int(round(ep.GetMasterVolumeLevelScalar() * 100))
            new = max(0, min(100, cur + delta))
            ep.SetMasterVolumeLevelScalar(new / 100.0, None)
            if new > 0 and ep.GetMute():
                ep.SetMute(0, None)
            return self._vol_msg(lang, new)
        self._key(0xAF if delta > 0 else 0xAE, max(1, abs(delta) // 2))  # كل ضغطة ≈ 2%
        return self._vol_msg(lang, None)

    def a_volume_up(self, args, lang):
        return self._change_volume(+int(args.get("step", 10)), lang)

    def a_volume_down(self, args, lang):
        return self._change_volume(-int(args.get("step", 10)), lang)

    def a_volume_set(self, args, lang):
        if not IS_WIN:
            return self._win_only(lang)
        level = max(0, min(100, int(args.get("level", 50))))
        ep = self._endpoint()
        if ep is not None:
            ep.SetMasterVolumeLevelScalar(level / 100.0, None)
            if level > 0 and ep.GetMute():
                ep.SetMute(0, None)
            return self._vol_msg(lang, level)
        self._key(0xAE, 50)  # إلى الصفر
        self._key(0xAF, level // 2)
        return self._vol_msg(lang, level)

    def a_mute(self, args, lang):
        if not IS_WIN:
            return self._win_only(lang)
        ep = self._endpoint()
        if ep is not None:
            ep.SetMute(1, None)
        else:
            self._key(0xAD)
        return Result(self.t(lang, "كتمت الصوت.", "Muted."))

    def a_unmute(self, args, lang):
        if not IS_WIN:
            return self._win_only(lang)
        ep = self._endpoint()
        if ep is not None:
            ep.SetMute(0, None)
        else:
            self._key(0xAD)
        return Result(self.t(lang, "رجّعت الصوت.", "Unmuted."))

    # ------------------------------------------------------------ الموسيقى
    def _first_youtube_url(self, query: str) -> str | None:
        try:
            import yt_dlp  # اختياري ومجاني
            opts = {"quiet": True, "no_warnings": True, "extract_flat": True, "skip_download": True,
                    "socket_timeout": 8}
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(f"ytsearch1:{query}", download=False)
            ent = (info or {}).get("entries") or []
            if ent and ent[0].get("id"):
                return "https://www.youtube.com/watch?v=" + ent[0]["id"]
        except Exception as e:
            log.info("yt-dlp search failed: %s", e)
        return None

    def a_play_music(self, args: dict, lang: str) -> Result:
        q = (args.get("query") or "").strip()
        folder = Path(self.cfg.music_folder) if self.cfg.music_folder else None
        exts = {".mp3", ".wav", ".flac", ".m4a", ".ogg", ".wma"}
        if not q and folder and folder.is_dir():
            files = [p for p in folder.rglob("*") if p.suffix.lower() in exts]
            if files:
                f = random.choice(files)
                if IS_WIN:
                    os.startfile(str(f))  # type: ignore[attr-defined]
                else:
                    webbrowser.open(f.as_uri())
                return Result(self.t(lang, f"شغّلت {f.stem}.", f"Playing {f.stem}."))
        if not q:
            q = "أغاني عربية مشهورة" if lang == "ar" else "popular music mix"
        url = self._first_youtube_url(q)
        if url:
            webbrowser.open(url)
            return Result(self.t(lang, f"تمام، بشغّل {q} على يوتيوب.", f"Playing {q} on YouTube."))
        webbrowser.open("https://www.youtube.com/results?search_query=" + quote_plus(q))
        return Result(self.t(lang, f"فتحت نتائج {q} على يوتيوب.", f"Opened YouTube results for {q}."))

    def a_media(self, args: dict, lang: str) -> Result:
        if not IS_WIN:
            return self._win_only(lang)
        cmd = args.get("cmd", "play_pause")
        vk = {"play_pause": 0xB3, "next": 0xB0, "prev": 0xB1, "stop": 0xB2}.get(cmd, 0xB3)
        self._key(vk)
        msg = {"play_pause": ("تمام.", "Done."), "next": ("الأغنية التالية.", "Next track."),
               "prev": ("الأغنية السابقة.", "Previous track."), "stop": ("أوقفت التشغيل.", "Stopped.")}.get(cmd, ("تمام.", "Done."))
        return Result(self.t(lang, *msg))

    # ------------------------------------------------------------ لقطة الشاشة
    def a_screenshot(self, args: dict, lang: str) -> Result:
        pics = Path.home() / "Pictures" / "JARVIS"
        pics.mkdir(parents=True, exist_ok=True)
        path = pics / ("screenshot_" + _dt.datetime.now().strftime("%Y%m%d_%H%M%S") + ".png")
        try:
            import mss
            import mss.tools
            with mss.mss() as sct:
                img = sct.grab(sct.monitors[0])
                mss.tools.to_png(img.rgb, img.size, output=str(path))
        except Exception as e1:
            try:
                from PIL import ImageGrab
                ImageGrab.grab(all_screens=True).save(path)
            except Exception as e2:
                log.warning("screenshot failed: %s / %s", e1, e2)
                return Result(self.t(lang, "ما قدرت آخذ لقطة الشاشة.", "I couldn't take the screenshot."),
                              display=f"{e1}", ok=False)
        return Result(self.t(lang, "أخذت لقطة الشاشة وحفظتها في مجلد الصور.", "Screenshot saved to your Pictures folder."),
                      display=str(path))

    # ------------------------------------------------------------ معلومات النظام
    @staticmethod
    def _uptime() -> str:
        import psutil
        secs = int(time.time() - psutil.boot_time())
        h, m = secs // 3600, (secs % 3600) // 60
        return f"{h}:{m:02d}"

    def a_system_info(self, args: dict, lang: str) -> Result:
        import psutil
        what = args.get("what", "all")
        ar = lang == "ar"
        cpu = psutil.cpu_percent(interval=0.6)
        vm = psutil.virtual_memory()
        anchor = os.environ.get("SystemDrive", "C:") + "\\" if IS_WIN else "/"
        du = shutil.disk_usage(anchor)
        batt = None
        try:
            batt = psutil.sensors_battery()
        except Exception:
            pass
        gb = 1024 ** 3
        parts_speak, parts_disp = [], []
        if what in ("all", "cpu"):
            parts_speak.append(f"المعالج {cpu:.0f} بالمئة" if ar else f"CPU at {cpu:.0f} percent")
            parts_disp.append(f"CPU: {cpu:.0f}% ({psutil.cpu_count(logical=True)} threads)")
        if what in ("all", "ram"):
            parts_speak.append(f"الذاكرة {vm.percent:.0f} بالمئة من {vm.total / gb:.0f} جيجا" if ar
                               else f"memory {vm.percent:.0f} percent of {vm.total / gb:.0f} gigabytes")
            parts_disp.append(f"RAM: {vm.used / gb:.1f}/{vm.total / gb:.1f} GB ({vm.percent:.0f}%)")
        if what in ("all", "disk"):
            parts_speak.append(f"المتبقي على القرص {du.free / gb:.0f} جيجا" if ar else f"{du.free / gb:.0f} gigabytes free on disk")
            parts_disp.append(f"Disk: {du.free / gb:.0f} GB free of {du.total / gb:.0f} GB")
        if what in ("all", "battery"):
            if batt:
                plug = (" وموصول بالشاحن" if ar else ", plugged in") if batt.power_plugged else ""
                parts_speak.append(f"البطارية {batt.percent:.0f} بالمئة{plug}" if ar else f"battery {batt.percent:.0f} percent{plug}")
                parts_disp.append(f"Battery: {batt.percent:.0f}% {'(charging)' if batt.power_plugged else ''}")
            elif what == "battery":
                parts_speak.append("هذا الجهاز ما فيه بطارية" if ar else "this device has no battery")
        if what == "all":
            parts_disp.append(f"OS: {platform.platform()}")
            parts_disp.append(f"Uptime: {self._uptime()} h")
        speak = ("، ".join(parts_speak) + ".") if ar else (", ".join(parts_speak).capitalize() + ".")
        return Result(speak, "\n".join(parts_disp))

    # ------------------------------------------------------------ الوقت والتاريخ
    def a_time(self, args, lang):
        now = _dt.datetime.now()
        h12 = now.hour % 12 or 12
        if lang == "ar":
            period = "صباحاً" if now.hour < 12 else "مساءً"
            return Result(f"الساعة الآن {h12} و{now.minute} دقيقة {period}." if now.minute else f"الساعة الآن {h12} {period}.",
                          now.strftime("%H:%M"))
        return Result(now.strftime("It's %I:%M %p."), now.strftime("%H:%M"))

    def a_date(self, args, lang):
        now = _dt.datetime.now()
        if lang == "ar":
            return Result(f"اليوم {_AR_DAYS[now.weekday()]}، {now.day} {_AR_MONTHS[now.month - 1]} {now.year}.",
                          now.strftime("%Y-%m-%d"))
        return Result(now.strftime("Today is %A, %B %d, %Y."), now.strftime("%Y-%m-%d"))

    # ------------------------------------------------------------ الطاقة
    def a_lock(self, args, lang):
        if not IS_WIN:
            return self._win_only(lang)
        import ctypes
        ctypes.windll.user32.LockWorkStation()  # type: ignore[attr-defined]
        return Result(self.t(lang, "قفلت الشاشة.", "Locked."))

    def a_shutdown(self, args, lang):
        if not IS_WIN:
            return self._win_only(lang)
        subprocess.Popen(["shutdown", "/s", "/t", "15"], creationflags=NO_WINDOW)
        return Result(self.t(lang, "تمام، الجهاز رح ينطفي بعد 15 ثانية. قل «ألغِ الإطفاء» للتراجع.",
                             "Shutting down in 15 seconds. Say 'cancel shutdown' to abort."))

    def a_restart(self, args, lang):
        if not IS_WIN:
            return self._win_only(lang)
        subprocess.Popen(["shutdown", "/r", "/t", "15"], creationflags=NO_WINDOW)
        return Result(self.t(lang, "تمام، رح أعيد التشغيل بعد 15 ثانية. قل «ألغِ الإطفاء» للتراجع.",
                             "Restarting in 15 seconds. Say 'cancel shutdown' to abort."))

    def a_sleep(self, args, lang):
        if not IS_WIN:
            return self._win_only(lang)
        subprocess.Popen(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"], creationflags=NO_WINDOW)
        return Result(self.t(lang, "تصبح على خير.", "Going to sleep."))

    def a_cancel_shutdown(self, args, lang):
        if not IS_WIN:
            return self._win_only(lang)
        r = subprocess.run(["shutdown", "/a"], capture_output=True, creationflags=NO_WINDOW)
        if r.returncode == 0:
            return Result(self.t(lang, "ألغيت الإطفاء.", "Shutdown cancelled."))
        return Result(self.t(lang, "ما في عملية إطفاء جارية.", "No shutdown in progress."), ok=False)
