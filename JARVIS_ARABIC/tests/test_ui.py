import os, time
from PySide6.QtWidgets import QApplication
from tests.test_integration import FakeTTS, FakeActions, FakeLLM, pump
from jarvis.assistant import Assistant
from jarvis.config import Config
from jarvis.ui.main_window import MainWindow
from jarvis.ui.settings_dialog import SettingsDialog
from jarvis.ui.theme import apply_theme


def test_window_and_settings(tmp_path):
    app = QApplication.instance() or QApplication([])
    apply_theme(app)
    cfg = Config()
    a = Assistant(cfg, tts=FakeTTS(), llm=FakeLLM(), actions=FakeActions(cfg))
    w = MainWindow(cfg, a); w.show()
    a.handle_text("كم الساعة"); pump(app, lambda: not a._busy)
    a.handle_text("ما هي عاصمة فرنسا؟"); pump(app, lambda: not a._busy)
    a.message.emit("user", "open chrome please"); a.message.emit("system", "تم حفظ الإعدادات.")
    w.orb.set_state("listening"); w.orb.set_level(0.5); w.mic_btn.setChecked(True)
    for _ in range(25): app.processEvents(); time.sleep(0.03)
    out = os.environ.get("SHOT", str(tmp_path / "w.png"))
    assert w.grab().save(out)
    d = SettingsDialog(cfg); d.show(); app.processEvents()
    d.grab().save(out.replace(".png", "_settings.png"))
    d._save()
    assert Config.load().voice == cfg.voice
    for st in ("idle", "loading", "thinking", "speaking"):
        w.orb.set_state(st); app.processEvents()
