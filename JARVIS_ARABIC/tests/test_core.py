import json
import threading
import wave
from http.server import BaseHTTPRequestHandler, HTTPServer

import numpy as np
import pytest

from jarvis import actions as A
from jarvis import wake
from jarvis.config import Config, sounds_dir
from jarvis.llm import LLMClient, parse_llm_output
from jarvis.sounds import ensure_sounds
from jarvis.stt import is_hallucination
from jarvis.vad import FRAME, SAMPLE_RATE, VadSegmenter


# ---------------------------------------------------------------- wake word
@pytest.mark.parametrize("text,rest", [
    ("يا جارفيس افتح كروم", "افتح كروم"),
    ("جارفيس", ""),
    ("يا جارفس، كم الساعة؟", "كم الساعة؟"),
    ("hey Jarvis open notepad", "open notepad"),
    ("اوكي جار فيس ارفع الصوت", "ارفع الصوت"),
    ("افتح كروم يا جارفيس", "افتح كروم"),
    ("جارفيز شغل اغنية", "شغل اغنية"),
])
def test_wake_found(text, rest):
    ok, r = wake.extract(text, ["جارفيس", "jarvis"])
    assert ok and r == rest


@pytest.mark.parametrize("text,rest", [
    ("يا لونا افتح كروم", "افتح كروم"), ("لونه كم الساعة", "كم الساعة"), ("hey Luna open notepad", "open notepad"),
    ("لونا", ""), ("ارفع الصوت يا لونا", "ارفع الصوت"),
])
def test_luna_wake(text, rest):
    assert wake.extract(text, ["لونا", "luna"]) == (True, rest)
    assert wake.extract("افتح كروم لنا", ["لونا", "luna"])[0] is False


@pytest.mark.parametrize("text", ["افتح كروم", "شو الاخبار اليوم", "جاري البحث عن الملف", "the service is down"])
def test_wake_not_found(text):
    assert wake.extract(text, ["جارفيس", "jarvis"])[0] is False


# ---------------------------------------------------------------- VAD
def _tone(sec, amp=0.15, freq=220):
    t = np.arange(int(sec * SAMPLE_RATE)) / SAMPLE_RATE
    return (amp * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def _feed(seg, sig):
    outs = []
    for i in range(0, len(sig) - FRAME + 1, FRAME):
        o = seg.feed(sig[i:i + FRAME])
        if o is not None:
            outs.append(o)
    return outs


def test_vad_detects_speech_between_silences():
    rng = np.random.default_rng(0)
    noise = lambda s: (rng.normal(0, 0.002, int(s * SAMPLE_RATE))).astype(np.float32)
    sig = np.concatenate([noise(1.0), _tone(1.2) + noise(1.2), noise(1.5)])
    outs = _feed(VadSegmenter(), sig)
    assert len(outs) == 1
    assert 1.2 <= len(outs[0]) / SAMPLE_RATE <= 2.6


def test_vad_ignores_noise_and_clicks():
    rng = np.random.default_rng(1)
    sig = (rng.normal(0, 0.003, 4 * SAMPLE_RATE)).astype(np.float32)
    sig[8000:8000 + 300] += 0.3  # نقرة قصيرة
    assert _feed(VadSegmenter(), sig) == []


def test_vad_two_utterances():
    sil = np.zeros(int(1.2 * SAMPLE_RATE), dtype=np.float32)
    sig = np.concatenate([sil, _tone(0.8), sil, _tone(0.8, freq=330), sil])
    assert len(_feed(VadSegmenter(), sig)) == 2


# ---------------------------------------------------------------- stt filter
def test_hallucination_filter():
    assert is_hallucination("ترجمة نانسي قنقر")
    assert is_hallucination("Thanks for watching!")
    assert is_hallucination("")
    assert not is_hallucination("افتح الكروم")


# ---------------------------------------------------------------- config
def test_config_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    c = Config()
    c.voice = "ar-JO-SanaNeural"; c.tts_rate = 12; c.custom_apps = {"x": "y"}; c.wake_words = ["جارفيس"]
    c.save()
    c2 = Config.load()
    assert (c2.voice, c2.tts_rate, c2.custom_apps, c2.wake_words) == ("ar-JO-SanaNeural", 12, {"x": "y"}, ["جارفيس"])
    (tmp_path / "config.json").write_text("{broken", encoding="utf-8")
    assert Config.load().voice == Config().voice
    (tmp_path / "config.json").write_text(json.dumps({"tts_rate": "7", "bogus": 1, "wake_enabled": 0}), encoding="utf-8")
    c3 = Config.load()
    assert c3.tts_rate == 7 and c3.wake_enabled is False


# ---------------------------------------------------------------- sounds
def test_sounds_generated(tmp_path):
    paths = ensure_sounds(tmp_path)
    assert {"boot", "wake", "done", "error", "off"} <= set(paths)
    for p in paths.values():
        with wave.open(str(p)) as w:
            assert w.getnframes() > 2000 and w.getframerate() == 22050


# ---------------------------------------------------------------- LLM parsing + fake Ollama
def test_parse_llm_output():
    r = parse_llm_output('{"reply":"تمام","action":"open_app","args":{"name":"chrome"}}')
    assert (r.reply, r.action, r.args) == ("تمام", "open_app", {"name": "chrome"})
    assert parse_llm_output('بعض النص {"reply":"x","action":"hack_pc","args":{}} نهاية').action is None
    assert parse_llm_output("مجرد نص بدون JSON").reply == "مجرد نص بدون JSON"
    assert parse_llm_output('{"reply":"hi","action":null,"args":null}').args == {}


class _Ollama(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        body = json.dumps({"models": [{"name": "qwen2.5:3b"}]}).encode()
        self.send_response(200); self.end_headers(); self.wfile.write(body)

    def do_POST(self):
        n = int(self.headers["Content-Length"]); req = json.loads(self.rfile.read(n))
        _Ollama.last = req
        content = json.dumps({"reply": "أكيد، بفتحلك الكروم", "action": "open_app", "args": {"name": "chrome"}}, ensure_ascii=False)
        body = json.dumps({"message": {"role": "assistant", "content": content}}).encode()
        self.send_response(200); self.end_headers(); self.wfile.write(body)


@pytest.fixture
def ollama():
    srv = HTTPServer(("127.0.0.1", 0), _Ollama)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()


def test_llm_client(ollama):
    cfg = Config(); cfg.llm_url = ollama; cfg.llm_model = "qwen2.5:3b"
    c = LLMClient(cfg)
    assert c.available(force=True)
    r = c.chat([], "افتح كروم لو سمحت")
    assert r.action == "open_app" and r.args["name"] == "chrome"
    msgs = _Ollama.last["messages"]
    assert msgs[0]["role"] == "system" and "JSON" in msgs[0]["content"] and msgs[-1]["content"].startswith("افتح")
    assert _Ollama.last["format"] == "json"


def test_llm_unavailable():
    cfg = Config(); cfg.llm_url = "http://127.0.0.1:1"
    assert LLMClient(cfg).available(force=True) is False


# ---------------------------------------------------------------- actions
@pytest.fixture
def acts():
    return A.Actions(Config())


def test_time_date_ar_en(acts):
    r = acts.run("time", {}, "ar"); assert "الساعة" in r.speak
    r = acts.run("date", {}, "ar"); assert "اليوم" in r.speak
    assert acts.run("time", {}, "en").speak.startswith("It's")


def test_system_info(acts):
    r = acts.run("system_info", {"what": "all"}, "ar")
    assert r.ok and "المعالج" in r.speak and "RAM" in r.display
    assert acts.run("system_info", {"what": "cpu"}, "en").speak.lower().startswith("cpu")


def test_search_and_website(acts, monkeypatch):
    opened = []
    monkeypatch.setattr(A.webbrowser, "open", lambda u: opened.append(u) or True)
    acts.run("search_web", {"query": "طقس عمان"}, "ar")
    acts.run("search_web", {"query": "كنافة", "site": "youtube"}, "ar")
    acts.run("open_website", {"key": "github"}, "ar")
    acts.run("open_website", {"name": "example"}, "en")
    assert opened[0].startswith("https://www.google.com/search?q=%D8%B7")
    assert "youtube.com/results" in opened[1]
    assert opened[2] == "https://github.com" and opened[3] == "https://example.com"


def test_play_music_fallback_and_local(acts, monkeypatch, tmp_path):
    opened = []
    monkeypatch.setattr(A.webbrowser, "open", lambda u: opened.append(u) or True)
    monkeypatch.setattr(acts, "_first_youtube_url", lambda q: "https://www.youtube.com/watch?v=abc")
    r = acts.run("play_music", {"query": "فيروز"}, "ar")
    assert opened[-1].endswith("watch?v=abc") and r.ok
    monkeypatch.setattr(acts, "_first_youtube_url", lambda q: None)
    acts.run("play_music", {"query": "فيروز"}, "ar")
    assert "results?search_query" in opened[-1]
    (tmp_path / "a.mp3").write_bytes(b"x")
    acts.cfg.music_folder = str(tmp_path)
    r = acts.run("play_music", {"query": ""}, "ar")
    assert "a" in r.speak and opened[-1].startswith("file://")


def test_screenshot(acts, monkeypatch, tmp_path):
    monkeypatch.setattr(A.Path, "home", classmethod(lambda cls: tmp_path))

    class FakeImg:
        rgb = bytes(10 * 10 * 3); size = (10, 10)

    class FakeMss:
        monitors = [{}]
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def grab(self, m): return FakeImg()

    import mss
    monkeypatch.setattr(mss, "mss", lambda: FakeMss())
    r = acts.run("screenshot", {}, "ar")
    assert r.ok and r.display.endswith(".png")
    from pathlib import Path
    assert Path(r.display).stat().st_size > 50


def test_windows_only_guard_on_linux(acts):
    if A.IS_WIN:
        pytest.skip("windows")
    for name in ("open_app", "close_app", "volume_up", "mute", "lock", "shutdown", "media"):
        r = acts.run(name, {"key": "chrome", "name": "x"}, "ar")
        assert not r.ok and "ويندوز" in r.speak


def test_unknown_action(acts):
    assert acts.run("format_c", {}, "en").ok is False


def test_windows_paths_simulated(acts, monkeypatch):
    """نحاكي ويندوز: نتأكد من منطق الأوامر وسطر الاستدعاء (taskkill / start / shutdown)."""
    monkeypatch.setattr(A, "IS_WIN", True)
    calls = []

    class P:
        returncode = 0

    monkeypatch.setattr(A.subprocess, "run", lambda cmd, **k: calls.append(cmd) or P())
    monkeypatch.setattr(A.subprocess, "Popen", lambda cmd, **k: calls.append(cmd) or P())
    monkeypatch.setattr(A.Actions, "_app_exists", staticmethod(lambda l: True))
    r = acts.run("open_app", {"key": "chrome"}, "ar")
    assert r.ok and calls[-1][:4] == ["cmd", "/c", "start", ""] and calls[-1][4] == "chrome"
    r = acts.run("close_app", {"key": "calculator"}, "ar")
    assert r.ok and ["taskkill", "/IM", "CalculatorApp.exe", "/F", "/T"] in calls
    r = acts.run("close_app", {"key": "explorer"}, "ar")
    assert not r.ok  # حماية سطح المكتب
    acts.run("shutdown", {}, "ar")
    assert calls[-1][:3] == ["shutdown", "/s", "/t"]
    # الصوت عبر مفاتيح الوسائط عند غياب pycaw
    monkeypatch.setattr(A.Actions, "_endpoint", staticmethod(lambda: None))
    keys = []
    monkeypatch.setattr(A.Actions, "_key", staticmethod(lambda vk, times=1: keys.append((vk, times))))
    acts.run("volume_up", {"step": 10}, "ar"); acts.run("volume_down", {"step": 10}, "ar"); acts.run("mute", {}, "ar")
    assert keys == [(0xAF, 5), (0xAE, 5), (0xAD, 1)]
    # الصوت عبر pycaw وهمي
    class EP:
        v = 0.4; m = 0
        def GetMasterVolumeLevelScalar(self): return self.v
        def SetMasterVolumeLevelScalar(self, x, _): self.v = x
        def GetMute(self): return self.m
        def SetMute(self, x, _): self.m = x
    ep = EP()
    monkeypatch.setattr(A.Actions, "_endpoint", staticmethod(lambda: ep))
    assert "50" in acts.run("volume_up", {"step": 10}, "ar").speak
    assert "30" in acts.run("volume_down", {"step": 20}, "ar").speak
    assert abs(ep.v - 0.3) < 1e-9
    acts.run("volume_set", {"level": 80}, "ar"); assert abs(ep.v - 0.8) < 1e-9
