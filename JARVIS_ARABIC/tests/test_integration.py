import time

import pytest
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

from jarvis.actions import Actions, Result
from jarvis.assistant import Assistant
from jarvis.config import Config
from jarvis.llm import LLMReply


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


class FakeTTS(QObject):
    started = Signal(); finished = Signal(); failed = Signal(str)
    def __init__(self): super().__init__(); self.said = []
    def speak(self, t):
        self.said.append(t); self.started.emit(); self.finished.emit()
    def stop(self): pass


class FakeActions(Actions):
    def __init__(self, cfg): super().__init__(cfg); self.calls = []
    def run(self, name, args=None, lang="ar"):
        self.calls.append((name, args)); return Result("تم " + name)


class FakeLLM:
    def __init__(self, ok=True): self.ok = ok; self.last = None
    def available(self, force=False): return self.ok
    def chat(self, hist, text):
        self.last = text
        return LLMReply("أكيد", "open_app", {"name": "chrome"}) if "كروم" in text else LLMReply("الجواب هو أربعة")


def pump(app, cond, timeout=3):
    end = time.time() + timeout
    while time.time() < end and not cond():
        app.processEvents(); time.sleep(0.01)
    app.processEvents()


def make(app, llm_ok=True):
    cfg = Config(); cfg.tts_enabled = True
    a = Assistant(cfg, tts=FakeTTS(), llm=FakeLLM(llm_ok), actions=FakeActions(cfg))
    msgs = []; a.message.connect(lambda r, t: msgs.append((r, t)))
    return a, msgs


def test_wake_flow_and_conversation(app):
    a, msgs = make(app)
    a.on_transcript("افتح كروم")                      # بدون كلمة تنبيه: يُتجاهل
    assert msgs == []
    a.on_transcript("يا لونا")                       # تنبيه فقط
    assert a.tts.said[-1].startswith("نعم") and a.in_conversation()
    a.on_transcript("افتح كروم")                       # داخل نافذة المحادثة بدون كلمة تنبيه
    pump(app, lambda: a.actions.calls)
    assert a.actions.calls[-1][0] == "open_app"
    assert ("user", "افتح كروم") in msgs
    pump(app, lambda: not a._busy)
    a.conv_until = 0
    a.on_transcript("لونا ارفع الصوت")
    pump(app, lambda: len(a.actions.calls) == 2)
    assert a.actions.calls[-1][0] == "volume_up"
    assert a.state == "idle"


def test_llm_path_and_action(app):
    a, msgs = make(app)
    a.cfg.wake_enabled = False
    a.handle_text("كم اثنين زائد اثنين؟")
    pump(app, lambda: any(r == "jarvis" for r, _ in msgs))
    assert msgs[-1] == ("jarvis", "الجواب هو أربعة")
    a.handle_text("بدي تفتحلي المتصفح كروم بسرعة")
    pump(app, lambda: a.actions.calls)
    assert a.actions.calls[-1][0] == "open_app"


def test_llm_unavailable_fallback(app):
    a, msgs = make(app, llm_ok=False)
    a.handle_text("اشرح لي الفيزياء")
    pump(app, lambda: any(r == "jarvis" for r, _ in msgs))
    assert "Ollama" in msgs[-1][1]


def test_confirmation_for_shutdown(app):
    a, msgs = make(app)
    a.handle_text("طفي الجهاز")
    pump(app, lambda: a.pending is not None)
    assert not a.actions.calls and "متأكد" in a.tts.said[-1]
    a.handle_text("لا")
    pump(app, lambda: a.state == "idle")
    assert not a.actions.calls
    a.handle_text("طفي الجهاز"); pump(app, lambda: a.pending is not None)
    a.handle_text("نعم")
    pump(app, lambda: a.actions.calls)
    assert a.actions.calls[-1][0] == "shutdown"


def test_exit_and_end_conversation(app):
    a, _ = make(app)
    q = []; a.quit_requested.connect(lambda: q.append(1))
    a.handle_text("مع السلامة"); pump(app, lambda: not a._busy)
    assert not a.in_conversation()
    a.handle_text("اغلق جارفيس"); pump(app, lambda: q)
    assert q
