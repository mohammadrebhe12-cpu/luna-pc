"""نافذة الإعدادات."""
from __future__ import annotations

import threading

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout,
                               QLabel, QLineEdit, QPlainTextEdit, QPushButton, QScrollArea, QSlider, QSpinBox,
                               QVBoxLayout, QWidget)

from .. import autostart
from ..config import Config
from ..listener import list_input_devices
from ..llm import LLMClient
from ..tts import ARABIC_VOICES, ENGLISH_VOICES


class SettingsDialog(QDialog):
    saved = Signal()
    _llm_result = Signal(str)

    def __init__(self, cfg: Config, parent=None, test_voice=None):
        super().__init__(parent)
        self.cfg = cfg
        self._test_voice = test_voice
        self.setWindowTitle("الإعدادات — العمد PC")
        self.setLayoutDirection(Qt.RightToLeft)
        self.resize(560, 700)
        outer = QVBoxLayout(self)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QScrollArea.NoFrame)
        body = QWidget(); lay = QVBoxLayout(body)
        scroll.setWidget(body); outer.addWidget(scroll)

        # ---------- الصوت
        g = QGroupBox("صوت لونا"); f = QFormLayout(g)
        self.tts_on = QCheckBox("الرد بالصوت"); self.tts_on.setChecked(cfg.tts_enabled); f.addRow(self.tts_on)
        self.voice = QComboBox()
        for vid, label in ARABIC_VOICES:
            self.voice.addItem(label, vid)
        self._select(self.voice, cfg.voice)
        f.addRow("الصوت العربي", self.voice)
        self.en_voice = QComboBox()
        for vid, label in ENGLISH_VOICES:
            self.en_voice.addItem(label, vid)
        self._select(self.en_voice, cfg.english_voice)
        f.addRow("الصوت الإنجليزي", self.en_voice)
        self.rate = QSlider(Qt.Horizontal); self.rate.setRange(-40, 40); self.rate.setValue(cfg.tts_rate)
        f.addRow("السرعة", self.rate)
        self.pitch = QSlider(Qt.Horizontal); self.pitch.setRange(-30, 30); self.pitch.setValue(cfg.tts_pitch)
        f.addRow("طبقة الصوت", self.pitch)
        tb = QPushButton("تجربة الصوت"); tb.clicked.connect(self._try_voice); f.addRow(tb)
        lay.addWidget(g)

        # ---------- الاستماع
        g = QGroupBox("الاستماع"); f = QFormLayout(g)
        self.wake_on = QCheckBox("تفعيل كلمة التنبيه (يا لونا)"); self.wake_on.setChecked(cfg.wake_enabled)
        f.addRow(self.wake_on)
        self.wake_words = QLineEdit(", ".join(cfg.wake_words)); f.addRow("كلمات التنبيه", self.wake_words)
        self.timeout = QSpinBox(); self.timeout.setRange(0, 300); self.timeout.setSuffix(" ث")
        self.timeout.setValue(cfg.conversation_timeout)
        f.addRow("إبقاء المحادثة مفتوحة", self.timeout)
        self.model = QComboBox()
        for m, d in [("tiny", "tiny — الأسرع، دقة ضعيفة"), ("base", "base — سريع"),
                     ("small", "small — موصى به للعربية"), ("medium", "medium — الأدق، يحتاج جهاز قوي")]:
            self.model.addItem(d, m)
        self._select(self.model, cfg.stt_model)
        f.addRow("نموذج التعرف على الصوت", self.model)
        self.lang = QComboBox()
        for m, d in [("ar", "العربية"), ("en", "English"), ("auto", "تلقائي")]:
            self.lang.addItem(d, m)
        self._select(self.lang, cfg.stt_language)
        f.addRow("لغة الكلام", self.lang)
        self.mic = QComboBox(); self.mic.addItem("الافتراضي", "")
        for did, name in list_input_devices():
            self.mic.addItem(f"{did}: {name}", did)
        self._select(self.mic, cfg.mic_device)
        f.addRow("المايكروفون", self.mic)
        self.sens = QSlider(Qt.Horizontal); self.sens.setRange(15, 80); self.sens.setValue(int(cfg.vad_sensitivity * 10))
        f.addRow("عتبة الصوت (أعلى = أقل حساسية)", self.sens)
        lay.addWidget(g)

        # ---------- الذكاء الاصطناعي
        g = QGroupBox("الذكاء الاصطناعي (Ollama — مجاني ومحلي)"); f = QFormLayout(g)
        self.llm_on = QCheckBox("استخدام الذكاء الاصطناعي للمحادثة والأوامر المعقدة"); self.llm_on.setChecked(cfg.llm_enabled)
        f.addRow(self.llm_on)
        self.llm_url = QLineEdit(cfg.llm_url); f.addRow("العنوان", self.llm_url)
        self.llm_model = QComboBox(); self.llm_model.setEditable(True); self.llm_model.addItem(cfg.llm_model)
        self.llm_model.setCurrentText(cfg.llm_model)
        f.addRow("النموذج", self.llm_model)
        row = QHBoxLayout(); self.llm_check = QPushButton("فحص الاتصال"); self.llm_check.clicked.connect(self._check_llm)
        self.llm_status = QLabel(""); row.addWidget(self.llm_check); row.addWidget(self.llm_status, 1)
        f.addRow(row)
        self._llm_result.connect(self._on_llm_result)
        lay.addWidget(g)

        # ---------- النظام
        g = QGroupBox("النظام"); f = QFormLayout(g)
        self.autostart = QCheckBox("تشغيل لونا عند بدء ويندوز")
        self.autostart.setChecked(autostart.is_enabled() or cfg.autostart); f.addRow(self.autostart)
        self.minimized = QCheckBox("البدء مصغّرًا في شريط المهام"); self.minimized.setChecked(cfg.start_minimized); f.addRow(self.minimized)
        self.sounds = QCheckBox("المؤثرات الصوتية"); self.sounds.setChecked(cfg.sounds_enabled); f.addRow(self.sounds)
        self.greet = QCheckBox("ترحيب صوتي عند التشغيل"); self.greet.setChecked(cfg.greet_on_start); f.addRow(self.greet)
        self.honor = QLineEdit(cfg.honorific); f.addRow("لقب المستخدم", self.honor)
        row = QHBoxLayout(); self.music = QLineEdit(cfg.music_folder); b = QPushButton("استعراض…")
        b.clicked.connect(self._browse_music); row.addWidget(self.music, 1); row.addWidget(b)
        f.addRow("مجلد الموسيقى", row)
        self.custom = QPlainTextEdit(); self.custom.setFixedHeight(80)
        self.custom.setPlainText("\n".join(f"{k} = {v}" for k, v in cfg.custom_apps.items()))
        self.custom.setPlaceholderText('اسم = مسار البرنامج\nمثال: الالعاب = C:\\Games\\game.exe')
        f.addRow("برامج مخصصة (سطر لكل برنامج)", self.custom)
        lay.addWidget(g)
        lay.addStretch(1)

        btns = QHBoxLayout()
        ok = QPushButton("حفظ"); ok.setObjectName("primary"); ok.clicked.connect(self._save)
        cancel = QPushButton("إلغاء"); cancel.clicked.connect(self.reject)
        btns.addStretch(1); btns.addWidget(cancel); btns.addWidget(ok)
        outer.addLayout(btns)

    # ------------------------------------------------------------ مساعدات
    @staticmethod
    def _select(combo: QComboBox, value) -> None:
        i = combo.findData(value)
        if i >= 0:
            combo.setCurrentIndex(i)

    def _browse_music(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "اختر مجلد الموسيقى", self.music.text())
        if d:
            self.music.setText(d)

    def _try_voice(self) -> None:
        self._apply_to(self.cfg)
        if self._test_voice:
            self._test_voice("مرحباً، أنا لونا. هذا صوتي الجديد.")

    def _check_llm(self) -> None:
        self.llm_status.setText("جاري الفحص…")
        url = self.llm_url.text().strip()

        def work():
            c = Config(); c.llm_url = url
            self._llm_result.emit("\n".join(LLMClient(c).models()))
        threading.Thread(target=work, daemon=True).start()

    def _on_llm_result(self, models: str) -> None:
        if not models:
            self.llm_status.setText("❌ غير متصل — شغّل Ollama وثبّت نموذجًا")
            return
        names = models.split("\n")
        cur = self.llm_model.currentText()
        self.llm_model.clear(); self.llm_model.addItems(names)
        self.llm_model.setCurrentText(cur if cur in names else names[0])
        self.llm_status.setText(f"✅ متصل — {len(names)} نموذج")

    def _apply_to(self, c: Config) -> None:
        c.tts_enabled = self.tts_on.isChecked()
        c.voice = self.voice.currentData()
        c.english_voice = self.en_voice.currentData()
        c.tts_rate = self.rate.value()
        c.tts_pitch = self.pitch.value()

    def _save(self) -> None:
        c = self.cfg
        self._apply_to(c)
        c.wake_enabled = self.wake_on.isChecked()
        words = [w.strip() for w in self.wake_words.text().replace("،", ",").split(",") if w.strip()]
        c.wake_words = words or ["لونا", "luna"]
        c.conversation_timeout = self.timeout.value()
        c.stt_model = self.model.currentData()
        c.stt_language = self.lang.currentData()
        c.mic_device = self.mic.currentData() or ""
        c.vad_sensitivity = self.sens.value() / 10.0
        c.llm_enabled = self.llm_on.isChecked()
        c.llm_url = self.llm_url.text().strip() or "http://localhost:11434"
        c.llm_model = self.llm_model.currentText().strip() or "qwen2.5:3b"
        c.start_minimized = self.minimized.isChecked()
        c.sounds_enabled = self.sounds.isChecked()
        c.greet_on_start = self.greet.isChecked()
        c.honorific = self.honor.text().strip() or "سيدي"
        c.music_folder = self.music.text().strip()
        apps = {}
        for line in self.custom.toPlainText().splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                if k.strip() and v.strip():
                    apps[k.strip()] = v.strip().strip('"')
        c.custom_apps = apps
        want = self.autostart.isChecked()
        if autostart.set_enabled(want) or want == c.autostart:
            c.autostart = want
        c.save()
        self.saved.emit()
        self.accept()
