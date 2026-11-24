"""الكرة المتحركة (HUD) وزر المايك — مرسومة بالكامل بـ QPainter."""
from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (QBrush, QColor, QPainter, QPainterPath, QPen, QPolygonF, QRadialGradient)
from PySide6.QtWidgets import QAbstractButton, QWidget

STATE_COLORS = {
    "idle": "#6A5799",
    "loading": "#D1B3FF",
    "listening": "#B388FF",
    "thinking": "#FF80AB",
    "speaking": "#8C6CFF",
}


def _lerp(a: QColor, b: QColor, t: float) -> QColor:
    return QColor(int(a.red() + (b.red() - a.red()) * t), int(a.green() + (b.green() - a.green()) * t),
                  int(a.blue() + (b.blue() - a.blue()) * t))


class OrbWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(280, 280)
        self._state = "idle"
        self._t = 0.0
        self._level = 0.0
        self._target_level = 0.0
        self._energy = 0.15
        self._color = QColor(STATE_COLORS["idle"])
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(33)

    def set_state(self, state: str) -> None:
        self._state = state if state in STATE_COLORS else "idle"

    def set_level(self, v: float) -> None:
        self._target_level = max(0.0, min(1.0, v))

    def _tick(self) -> None:
        if not self.isVisible():
            return
        self._t += 0.033
        self._level += (self._target_level - self._level) * 0.35
        s = self._state
        if s == "listening":
            tgt = 0.35 + self._level * 1.1
        elif s == "speaking":
            tgt = 0.65 + 0.3 * abs(math.sin(self._t * 7.3)) * (0.6 + 0.4 * math.sin(self._t * 2.1))
        elif s == "thinking":
            tgt = 0.75
        elif s == "loading":
            tgt = 0.45 + 0.15 * math.sin(self._t * 3)
        else:
            tgt = 0.15
        self._energy += (tgt - self._energy) * 0.18
        self._color = _lerp(self._color, QColor(STATE_COLORS[s]), 0.12)
        self.update()

    def paintEvent(self, _e) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        R = min(w, h) / 2 * 0.86
        t, en, col = self._t, self._energy, self._color
        s = self._state

        # --- توهج الخلفية
        g = QRadialGradient(cx, cy, R * 1.25)
        c0 = QColor(col); c0.setAlphaF(min(0.55, 0.10 + 0.28 * en))
        c1 = QColor(col); c1.setAlpha(0)
        g.setColorAt(0.0, c0); g.setColorAt(1.0, c1)
        p.setPen(Qt.NoPen); p.setBrush(QBrush(g))
        p.drawEllipse(QPointF(cx, cy), R * 1.25, R * 1.25)

        # --- حلقة التدريج (ticks)
        p.save(); p.translate(cx, cy); p.rotate(t * 6)
        for i in range(72):
            major = i % 6 == 0
            a = QColor(col); a.setAlphaF(0.75 if major else 0.35)
            p.setPen(QPen(a, 2 if major else 1))
            r1, r2 = R, R - (10 if major else 5)
            ang = math.radians(i * 5)
            p.drawLine(QPointF(r1 * math.cos(ang), r1 * math.sin(ang)), QPointF(r2 * math.cos(ang), r2 * math.sin(ang)))
        p.restore()

        # --- حلقة منقّطة
        p.save(); p.translate(cx, cy); p.rotate(-t * 14)
        pen = QPen(QColor(col.red(), col.green(), col.blue(), 110), 2, Qt.CustomDashLine)
        pen.setDashPattern([1.0, 5.0]); pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen); p.setBrush(Qt.NoBrush)
        p.drawEllipse(QPointF(0, 0), R * 0.88, R * 0.88)
        p.restore()

        # --- أقواس دوّارة
        speed = 260 if s == "thinking" else 55
        for i, (rad, span, wd, sp) in enumerate([(0.79, 75, 4, 1.0), (0.73, 50, 3, -1.6), (0.67, 110, 2, 0.7)]):
            p.save(); p.translate(cx, cy); p.rotate(t * speed * sp + i * 70)
            a = QColor(col); a.setAlphaF(0.85 - i * 0.18)
            pen = QPen(a, wd); pen.setCapStyle(Qt.RoundCap)
            p.setPen(pen)
            rr = R * rad
            p.drawArc(QRectF(-rr, -rr, 2 * rr, 2 * rr), 0, int(span * 16))
            p.drawArc(QRectF(-rr, -rr, 2 * rr, 2 * rr), 180 * 16, int(span * 16))
            p.restore()

        # --- موجات تتمدّد (الاستماع)
        if s in ("listening", "speaking"):
            for i in range(3):
                ph = (t * 0.7 + i / 3) % 1.0
                rr = R * (0.42 + 0.30 * ph)
                a = QColor(col); a.setAlphaF(max(0.0, (1 - ph) * 0.40 * min(1.0, en + 0.2)))
                p.setPen(QPen(a, 2)); p.setBrush(Qt.NoBrush)
                p.drawEllipse(QPointF(cx, cy), rr, rr)

        # --- حلقة الموجة الصوتية
        pts = QPolygonF()
        n = 120
        base = R * 0.52
        amp = R * (0.012 + 0.075 * en)
        for i in range(n + 1):
            th = 2 * math.pi * i / n
            wob = (math.sin(th * 5 + t * 4.0) * 0.6 + math.sin(th * 9 - t * 6.5) * 0.4)
            if s == "thinking":
                wob = math.sin(th * 3 + t * 9)
            r = base + amp * wob
            pts.append(QPointF(cx + r * math.cos(th), cy + r * math.sin(th)))
        a = QColor(col); a.setAlpha(230)
        p.setPen(QPen(a, 2.2)); p.setBrush(Qt.NoBrush)
        p.drawPolyline(pts)

        # --- النواة
        pulse = 1 + 0.04 * math.sin(t * 2.2) + 0.12 * self._level
        cr = R * 0.34 * pulse
        g2 = QRadialGradient(cx, cy, cr)
        core = QColor(255, 255, 255, 240)
        mid = QColor(col); mid.setAlpha(230)
        edge = QColor(col); edge.setAlpha(0)
        g2.setColorAt(0.0, core); g2.setColorAt(0.35, mid); g2.setColorAt(1.0, edge)
        p.setPen(Qt.NoPen); p.setBrush(QBrush(g2))
        p.drawEllipse(QPointF(cx, cy), cr, cr)
        ring = QColor(col); ring.setAlpha(200)
        p.setPen(QPen(ring, 2)); p.setBrush(Qt.NoBrush)
        p.drawEllipse(QPointF(cx, cy), R * 0.215, R * 0.215)
        p.end()


class MicButton(QAbstractButton):
    """زر المايك الدائري (مرسوم)، قابل للتبديل."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedSize(86, 86)
        self.setCursor(Qt.PointingHandCursor)
        self._t = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(50)

    def _tick(self) -> None:
        self._t += 0.05
        if self.isChecked():
            self.update()

    def paintEvent(self, _e) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        on = self.isChecked()
        col = QColor("#B388FF") if on else QColor("#5E4F85")
        cx, cy = self.width() / 2, self.height() / 2
        if on:
            glow = QRadialGradient(cx, cy, 43)
            c0 = QColor(col); c0.setAlphaF(0.30 + 0.12 * math.sin(self._t * 4))
            c1 = QColor(col); c1.setAlpha(0)
            glow.setColorAt(0.55, c0); glow.setColorAt(1, c1)
            p.setPen(Qt.NoPen); p.setBrush(QBrush(glow))
            p.drawEllipse(QPointF(cx, cy), 43, 43)
        p.setPen(QPen(col, 2.5)); p.setBrush(QColor(18, 11, 34))
        p.drawEllipse(QPointF(cx, cy), 31, 31)
        # أيقونة المايك
        p.setPen(QPen(col, 2.4)); p.setBrush(Qt.NoBrush)
        body = QPainterPath(); body.addRoundedRect(QRectF(cx - 6, cy - 17, 12, 21), 6, 6)
        p.drawPath(body)
        p.drawArc(QRectF(cx - 12, cy - 11, 24, 22), 200 * 16, 140 * 16)
        p.drawLine(QPointF(cx, cy + 11), QPointF(cx, cy + 18))
        p.drawLine(QPointF(cx - 6, cy + 18), QPointF(cx + 6, cy + 18))
        if not on:
            p.setPen(QPen(QColor("#FF5252"), 3)); p.drawLine(QPointF(cx - 15, cy + 15), QPointF(cx + 15, cy - 16))
        p.end()
