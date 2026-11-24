"""نقطة التشغيل: python main.py [--minimized] [--no-mic]"""
from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler


def _setup_logging() -> None:
    from jarvis.config import log_file
    h = RotatingFileHandler(log_file(), maxBytes=500_000, backupCount=2, encoding="utf-8")
    h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logging.basicConfig(level=logging.INFO, handlers=[h])

    def hook(t, v, tb):
        logging.getLogger("jarvis").critical("uncaught", exc_info=(t, v, tb))
    sys.excepthook = hook


def main() -> int:
    _setup_logging()
    from PySide6.QtCore import Qt
    from PySide6.QtNetwork import QLocalServer, QLocalSocket
    from PySide6.QtWidgets import QApplication

    from jarvis import APP_NAME
    from jarvis.assistant import Assistant
    from jarvis.config import Config
    from jarvis.ui.main_window import MainWindow, app_icon
    from jarvis.ui.theme import apply_theme

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setQuitOnLastWindowClosed(False)
    app.setWindowIcon(app_icon())

    # نسخة واحدة فقط: إن كان جارفيس يعمل أصلاً، أظهره واخرج
    sock = QLocalSocket()
    sock.connectToServer(APP_NAME)
    if sock.waitForConnected(300):
        sock.write(b"show"); sock.flush(); sock.waitForBytesWritten(300)
        return 0
    server = QLocalServer()
    QLocalServer.removeServer(APP_NAME)
    server.listen(APP_NAME)

    apply_theme(app)
    cfg = Config.load()
    assistant = Assistant(cfg)
    win = MainWindow(cfg, assistant)
    server.newConnection.connect(lambda: (server.nextPendingConnection(), win.show_front()))

    minimized = "--minimized" in sys.argv or cfg.start_minimized
    if minimized and win.tray:
        win.hide()
    else:
        win.show()
    if "--no-mic" not in sys.argv:
        assistant.start_mic()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
