"""النافذة الرئيسية (HUD داكن) وأيقونة شريط المهام."""
from __future__ import annotations

import html

import psutil
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QLabel, QLineEdit, QMenu, QPushButton, QSizeGrip,
                               QSystemTrayIcon, QTextBrowser, QVBoxLayout, QWidget)

from .. import APP_TITLE, BRAND_AR, BRAND_LATIN, __version__
from ..assistant import Assistant
from ..config import Config, resource_path
from ..sounds import SoundFx
from ..textutil import is_arabic
from .orb import STATE_COLORS, MicButton, OrbWidget
from .settings_dialog import SettingsDialog

ROLE_STYLE = {
    "user": ("#7C4DFF", "أنت"),
    "jarvis": ("#B388FF", "لونا"),
    "system": ("#FF80AB", "النظام"),
}


def app_icon() -> QIcon:
    p = resource_path("assets/icon.png")
    if p.exists():
        return QIcon(str(p))
    pm = QPixmap(64, 64); pm.fill(Qt.transparent)
    q = QPainter(pm); q.setRenderHint(QPainter.Antialiasing)
    q.setPen(QColor("#B388FF")); q.drawEllipse(6, 6, 52, 52); q.end()
    return QIcon(pm)


class TitleBar(QWidget):
    def __init__(self, win: "MainWindow"):
        super().__init__()
        self.win = win
        self.setObjectName("titlebar")
        self.setFixedHeight(42)
        lay = QHBoxLayout(self); lay.setContentsMargins(14, 0, 4, 0)
        t = QLabel(f"{BRAND_LATIN}  |  {BRAND_AR}"); t.setObjectName("title")
        s = QLabel(f"مساعد صوتي  ·  v{__version__}"); s.setObjectName("subtitle")
        lay.addWidget(t); lay.addWidget(s); lay.addStretch(1)
        for text, tip, slot, name in [("؟", "ماذا أستطيع أن أفعل؟", win.show_help, "tbtn"),
                                      ("⚙", "الإعدادات", win.open_settings, "tbtn"),
                                      ("—", "تصغير", win.showMinimized, "tbtn"),
                                      ("✕", "إخفاء إلى شريط المهام", win.close, "close")]:
            b = QPushButton(text); b.setObjectName("tbtn"); b.setToolTip(tip); b.clicked.connect(slot)
            if name == "close":
                b.setObjectName("tbtn"); b.setProperty("class", "close")
                b.setStyleSheet("QPushButton:hover { background:#C2185B; color:white; }")
            lay.addWidget(b)

    def mousePressEvent(self, e):  # noqa: N802
        if e.button() == Qt.LeftButton and self.win.windowHandle():
            self.win.windowHandle().startSystemMove()

    def mouseDoubleClickEvent(self, e):  # noqa: N802
        self.win.showNormal() if self.win.isMaximized() else self.win.showMaximized()


class MainWindow(QWidget):
    def __init__(self, cfg: Config, assistant: Assistant):
        super().__init__()
        self.cfg = cfg
        self.assistant = assistant
        self.fx = SoundFx(cfg)
        self._tray_hint_shown = False
        self.setObjectName("root")
        self.setWindowTitle(APP_TITLE)
        self.setWindowIcon(app_icon())
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.resize(1040, 640)
        self.setMinimumSize(820, 540)

        root = QVBoxLayout(self); root.setContentsMargins(1, 1, 1, 1); root.setSpacing(0)
        root.addWidget(TitleBar(self))
        body = QHBoxLayout(); body.setContentsMargins(18, 14, 18, 8); body.setSpacing(18)
        root.addLayout(body, 1)

        # ---------- يسار: الكرة
        left = QVBoxLayout(); left.setSpacing(6)
        self.orb = OrbWidget(); left.addWidget(self.orb, 1)
        self.state_lbl = QLabel("المايك مغلق"); self.state_lbl.setObjectName("state"); self.state_lbl.setAlignment(Qt.AlignCenter)
        self.hint_lbl = QLabel("اضغط على المايك للبدء"); self.hint_lbl.setObjectName("hint"); self.hint_lbl.setAlignment(Qt.AlignCenter)
        self.hint_lbl.setWordWrap(True)
        left.addWidget(self.state_lbl); left.addWidget(self.hint_lbl)
        row = QHBoxLayout(); row.addStretch(1)
        self.mic_btn = MicButton(); self.mic_btn.setToolTip("تشغيل / إيقاف المايك")
        self.mic_btn.clicked.connect(self.assistant.toggle_mic)
        row.addWidget(self.mic_btn)
        self.stop_btn = QPushButton("■ إيقاف الكلام"); self.stop_btn.clicked.connect(self.assistant.stop_speaking)
        row.addSpacing(14); row.addWidget(self.stop_btn); row.addStretch(1)
        left.addLayout(row)
        body.addLayout(left, 5)

        # ---------- يمين: المحادثة
        right = QVBoxLayout(); right.setSpacing(8)
        chips = QHBoxLayout()
        self.cpu_chip = QLabel("CPU --%"); self.cpu_chip.setObjectName("chip")
        self.ram_chip = QLabel("RAM --%"); self.ram_chip.setObjectName("chip")
        self.ai_chip = QLabel(""); self.ai_chip.setObjectName("chip")
        chips.addWidget(self.cpu_chip); chips.addWidget(self.ram_chip); chips.addWidget(self.ai_chip); chips.addStretch(1)
        right.addLayout(chips)
        self.chat = QTextBrowser(); self.chat.setOpenExternalLinks(False)
        right.addWidget(self.chat, 1)
        inp = QHBoxLayout()
        self.input = QLineEdit(); self.input.setPlaceholderText("اكتب أمرًا أو سؤالًا… (أو تكلم بعد تشغيل المايك)")
        self.input.returnPressed.connect(self._send)
        send = QPushButton("إرسال"); send.setObjectName("primary"); send.clicked.connect(self._send)
        inp.addWidget(self.input, 1); inp.addWidget(send)
        right.addLayout(inp)
        body.addLayout(right, 6)

        foot = QHBoxLayout(); foot.setContentsMargins(0, 0, 4, 2); foot.addStretch(1)
        foot.addWidget(QSizeGrip(self)); root.addLayout(foot)

        # ---------- ربط الإشارات
        a = self.assistant
        a.state_changed.connect(self._on_state)
        a.message.connect(self.add_message)
        a.level.connect(self.orb.set_level)
        a.status_text.connect(self._on_status_text)
        a.mic_changed.connect(self._on_mic)
        a.sound.connect(self.fx.play)
        a.quit_requested.connect(self.quit_app)

        self._stat_timer = QTimer(self); self._stat_timer.timeout.connect(self._update_stats); self._stat_timer.start(2000)
        self._hint_timer = QTimer(self); self._hint_timer.timeout.connect(self._update_hint); self._hint_timer.start(700)
        psutil.cpu_percent(None)
        self._update_stats()
        self._build_tray()
        self.add_message("jarvis", "مرحباً. اضغط على زر المايك وقل «يا لونا» أو اكتب أمرك هنا. اضغط «؟» لمعرفة ما أستطيع فعله.")

    # ------------------------------------------------------------ شريط المهام
    def _build_tray(self) -> None:
        self.tray = None
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self.tray = QSystemTrayIcon(app_icon(), self)
        self.tray.setToolTip(APP_TITLE)
        m = QMenu()
        act_show = QAction("إظهار العمد PC", self); act_show.triggered.connect(self.show_front)
        self.act_mic = QAction("تشغيل/إيقاف المايك", self); self.act_mic.triggered.connect(self.assistant.toggle_mic)
        act_set = QAction("الإعدادات", self); act_set.triggered.connect(self.open_settings)
        act_quit = QAction("خروج", self); act_quit.triggered.connect(self.quit_app)
        for x in (act_show, self.act_mic, act_set): m.addAction(x)
        m.addSeparator(); m.addAction(act_quit)
        self.tray.setContextMenu(m)
        self.tray.activated.connect(lambda r: self.show_front() if r in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick) else None)
        self.tray.show()

    def show_front(self) -> None:
        self.showNormal(); self.raise_(); self.activateWindow()

    def closeEvent(self, e) -> None:  # noqa: N802
        if self.tray and self.tray.isVisible():
            e.ignore(); self.hide()
            if not self._tray_hint_shown:
                self._tray_hint_shown = True
                self.tray.showMessage(APP_TITLE, "ما زالت لونا تعمل في الخلفية. للخروج استخدم أيقونة شريط المهام.",
                                      QSystemTrayIcon.Information, 4000)
        else:
            self.quit_app(); e.accept()

    def quit_app(self) -> None:
        self.assistant.shutdown()
        if self.tray:
            self.tray.hide()
        QApplication.instance().quit()

    # ------------------------------------------------------------ تفاعل
    def _send(self) -> None:
        t = self.input.text().strip()
        if t:
            self.input.clear()
            self.assistant.handle_text(t)

    def show_help(self) -> None:
        self.assistant.handle_text("شو بتقدر تعمل")

    def open_settings(self) -> None:
        old = (self.cfg.stt_model, self.cfg.mic_device, self.cfg.stt_language)
        dlg = SettingsDialog(self.cfg, self, test_voice=lambda s: self.assistant.tts.speak(s))
        dlg.saved.connect(lambda: self._after_settings(old))
        dlg.exec()

    def _after_settings(self, old) -> None:
        if old != (self.cfg.stt_model, self.cfg.mic_device, self.cfg.stt_language) and self.assistant.mic_on:
            self.assistant.restart_mic()
        self._update_hint()
        self.add_message("system", "تم حفظ الإعدادات.")

    # ------------------------------------------------------------ تحديث العرض
    LABELS = {"idle": "المايك مغلق", "loading": "جاري التحميل…", "listening": "أستمع…",
              "thinking": "أفكر…", "speaking": "أتحدث…"}

    def _on_state(self, s: str) -> None:
        self.orb.set_state(s)
        self.state_lbl.setText(self.LABELS.get(s, s))
        self.state_lbl.setStyleSheet(f"color: {STATE_COLORS.get(s, '#B388FF')};")
        self._update_hint()

    def _on_status_text(self, text: str) -> None:
        if text:
            self.hint_lbl.setText(text)
        else:
            self._update_hint()

    def _on_mic(self, on: bool) -> None:
        self.mic_btn.setChecked(on)
        if not on:
            self.orb.set_level(0.0)
        self._update_hint()

    def _update_hint(self) -> None:
        a = self.assistant
        if self.assistant.state == "loading":
            return
        if not a.mic_on:
            self.hint_lbl.setText("اضغط على المايك للبدء")
        elif a.state in ("thinking", "speaking"):
            self.hint_lbl.setText("")
        elif self.cfg.wake_enabled and not a.in_conversation():
            self.hint_lbl.setText("قل «يا لونا» ثم أمرك")
        else:
            self.hint_lbl.setText("أنا أسمعك، تفضّل")

    def _update_stats(self) -> None:
        self.cpu_chip.setText(f"CPU {psutil.cpu_percent(None):.0f}%")
        self.ram_chip.setText(f"RAM {psutil.virtual_memory().percent:.0f}%")
        if self.cfg.llm_enabled:
            ok = self.assistant.llm.available()
            self.ai_chip.setText("AI: Ollama ✔" if ok else "AI: Ollama ✖ (غير متصل)")
        else:
            self.ai_chip.setText("AI: متوقف")

    def add_message(self, role: str, text: str) -> None:
        color, name = ROLE_STYLE.get(role, ROLE_STYLE["system"])
        rtl = is_arabic(text)
        body = html.escape(text).replace("\n", "<br>")
        direction = "rtl" if rtl else "ltr"
        align = "right" if rtl else "left"
        cell = (f'<table width="100%" cellspacing="0" cellpadding="0" style="margin-bottom:9px"><tr>'
                f'<td width="3" bgcolor="{color}"></td>'
                f'<td bgcolor="#1A1033" dir="{direction}" align="{align}" style="padding:7px 10px">'
                f'<span style="color:{color}; font-size:11px; font-weight:600">{name}</span><br>'
                f'<span style="color:#F3EEFF; font-size:14px">{body}</span></td></tr></table>')
        self.chat.append(cell)
        sb = self.chat.verticalScrollBar(); sb.setValue(sb.maximum())
