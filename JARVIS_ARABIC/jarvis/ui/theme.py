"""الثيم الداكن (HUD) للتطبيق."""
from __future__ import annotations

from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication

BG = "#0A0614"
PANEL = "#120B22"
PANEL2 = "#1A1033"
BORDER = "#2E1F57"
CYAN = "#B388FF"
BLUE = "#7C4DFF"
AMBER = "#FF80AB"
RED = "#FF5252"
GREEN = "#00E676"
TEXT = "#EDE7FF"
DIM = "#8C7BB5"

FONT_FAMILY = "Segoe UI"

QSS = f"""
* {{ font-family: "{FONT_FAMILY}", "Tahoma", "Arial", "DejaVu Sans"; color: {TEXT}; }}
QWidget#root {{ background: {BG}; border: 1px solid {BORDER}; }}
QWidget#titlebar {{ background: {PANEL}; border-bottom: 1px solid {BORDER}; }}
QLabel#title {{ color: {CYAN}; font-size: 15px; font-weight: 700; }}
QLabel#subtitle {{ color: {DIM}; font-size: 11px; }}
QLabel#state {{ color: {CYAN}; font-size: 18px; font-weight: 600; }}
QLabel#hint {{ color: {DIM}; font-size: 13px; }}
QLabel#chip {{ color: {DIM}; font-size: 11px; background: {PANEL}; border: 1px solid {BORDER};
               border-radius: 9px; padding: 3px 10px; }}
QPushButton#tbtn {{ background: transparent; border: none; color: {DIM}; font-size: 15px; padding: 4px 11px; }}
QPushButton#tbtn:hover {{ color: {CYAN}; background: {PANEL2}; }}
QPushButton#close:hover {{ color: white; background: #C2185B; }}
QPushButton {{ background: {PANEL2}; border: 1px solid {BORDER}; border-radius: 6px; padding: 7px 16px; }}
QPushButton:hover {{ border-color: {CYAN}; color: {CYAN}; }}
QPushButton:pressed {{ background: {BORDER}; }}
QPushButton#primary {{ background: {BLUE}; border: none; color: white; font-weight: 600; }}
QPushButton#primary:hover {{ background: #9575FF; color: white; }}
QTextBrowser {{ background: {PANEL}; border: 1px solid {BORDER}; border-radius: 8px; padding: 6px;
               selection-background-color: {BLUE}; font-size: 14px; }}
QLineEdit, QSpinBox, QComboBox, QDoubleSpinBox {{ background: {PANEL}; border: 1px solid {BORDER};
               border-radius: 6px; padding: 7px 10px; selection-background-color: {BLUE}; min-height: 18px; }}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{ border-color: {CYAN}; }}
QComboBox QAbstractItemView {{ background: {PANEL}; border: 1px solid {BORDER}; selection-background-color: {BLUE}; }}
QGroupBox {{ border: 1px solid {BORDER}; border-radius: 8px; margin-top: 16px; padding: 14px 10px 8px 10px; }}
QGroupBox::title {{ subcontrol-origin: margin; subcontrol-position: top right; padding: 0 8px; color: {CYAN}; font-weight: 600; }}
QCheckBox {{ spacing: 8px; }}
QCheckBox::indicator {{ width: 18px; height: 18px; border: 1px solid {BORDER}; border-radius: 4px; background: {PANEL}; }}
QCheckBox::indicator:checked {{ background: {CYAN}; border-color: {CYAN}; }}
QSlider::groove:horizontal {{ height: 4px; background: {BORDER}; border-radius: 2px; }}
QSlider::handle:horizontal {{ background: {CYAN}; width: 14px; margin: -6px 0; border-radius: 7px; }}
QScrollBar:vertical {{ background: transparent; width: 9px; }}
QScrollBar::handle:vertical {{ background: {BORDER}; border-radius: 4px; min-height: 24px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QToolTip {{ background: {PANEL2}; color: {TEXT}; border: 1px solid {CYAN}; padding: 4px; }}
"""


def apply_theme(app: QApplication) -> None:
    app.setStyle("Fusion")
    pal = QPalette()
    pal.setColor(QPalette.Window, QColor(BG))
    pal.setColor(QPalette.WindowText, QColor(TEXT))
    pal.setColor(QPalette.Base, QColor(PANEL))
    pal.setColor(QPalette.AlternateBase, QColor(PANEL2))
    pal.setColor(QPalette.Text, QColor(TEXT))
    pal.setColor(QPalette.Button, QColor(PANEL2))
    pal.setColor(QPalette.ButtonText, QColor(TEXT))
    pal.setColor(QPalette.Highlight, QColor(BLUE))
    pal.setColor(QPalette.HighlightedText, QColor("white"))
    pal.setColor(QPalette.ToolTipBase, QColor(PANEL2))
    pal.setColor(QPalette.ToolTipText, QColor(TEXT))
    app.setPalette(pal)
    f = QFont(FONT_FAMILY, 10)
    app.setFont(f)
    app.setStyleSheet(QSS)
