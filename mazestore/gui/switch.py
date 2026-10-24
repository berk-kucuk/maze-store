"""A small monochrome on/off switch."""
from __future__ import annotations

from PyQt6.QtCore import QPropertyAnimation, QRectF, QSize, Qt, pyqtProperty
from PyQt6.QtGui import QColor, QPainter, QPainterPath
from PyQt6.QtWidgets import QAbstractButton


class Switch(QAbstractButton):
    def __init__(self, checked: bool = False, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(checked)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(self.sizeHint())
        self._pos = 1.0 if checked else 0.0
        self._anim = QPropertyAnimation(self, b"knob", self)
        self._anim.setDuration(140)
        self.toggled.connect(self._animate)

    def sizeHint(self) -> QSize:
        return QSize(38, 22)

    def _get_knob(self) -> float:
        return self._pos

    def _set_knob(self, v: float) -> None:
        self._pos = v
        self.update()

    # Not `pos`: that would shadow QWidget.pos().
    knob = pyqtProperty(float, _get_knob, _set_knob)

    def _animate(self, on: bool) -> None:
        self._anim.stop()
        self._anim.setStartValue(self._pos)
        self._anim.setEndValue(1.0 if on else 0.0)
        self._anim.start()

    def paintEvent(self, _ev) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        track = QPainterPath()
        track.addRoundedRect(r, r.height() / 2, r.height() / 2)
        off, on = QColor(255, 255, 255, 22), QColor("#f2f2f4")
        mix = QColor(
            int(off.red() + (on.red() - off.red()) * self._pos),
            int(off.green() + (on.green() - off.green()) * self._pos),
            int(off.blue() + (on.blue() - off.blue()) * self._pos),
            int(off.alpha() + (on.alpha() - off.alpha()) * self._pos))
        p.fillPath(track, mix)
        border = QColor(255, 255, 255, int(40 * (1 - self._pos)))
        p.setPen(border)
        p.drawPath(track)
        d = r.height() - 6
        x = r.left() + 3 + (r.width() - d - 6) * self._pos
        knob = QColor("#000000") if self._pos > 0.5 else QColor("#bdbdc2")
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(knob)
        p.drawEllipse(QRectF(x, r.top() + 3, d, d))
        p.end()
