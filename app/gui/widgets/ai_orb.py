"""
Animated futuristic AI Orb widget for Zero AI.
Uses pure Qt vector painting (QPainter, gradients, rotations) with zero external image files.
Adapts smoothly to assistant states: SLEEPING, READY, LISTENING, THINKING, SPEAKING, ERROR.
"""

import math
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import (
    QPainter,
    QColor,
    QRadialGradient,
    QPen,
    QBrush,
    QPaintEvent,
)
from PySide6.QtWidgets import QWidget
from app.core.state_manager import AssistantState


class AIOrbWidget(QWidget):
    """Futuristic animated reactive core orb widget."""

    clicked = Signal()

    def __init__(self, parent=None, reduced_motion: bool = False):
        super().__init__(parent)
        self.setFixedSize(140, 140)
        self.setCursor(Qt.PointingHandCursor)

        self._state = AssistantState.SLEEPING
        self._reduced_motion = reduced_motion

        # Animation parameters
        self._angle = 0.0
        self._pulse_phase = 0.0
        self._audio_level = 0.0

        # Animation timer (30 FPS)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_animation)
        self._timer.start(33)

    def set_state(self, new_state: AssistantState) -> None:
        """Update orb state to adjust colors and animation speed."""
        self._state = new_state
        self.update()

    def set_audio_level(self, level: float) -> None:
        """Feed instantaneous audio reactive amplitude (0.0 to 1.0)."""
        self._audio_level = max(0.0, min(level, 1.0))
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def _update_animation(self):
        if self._reduced_motion:
            return

        # Speed depends on state
        if self._state == AssistantState.THINKING:
            self._angle = (self._angle + 6.0) % 360.0
            self._pulse_phase = (self._pulse_phase + 0.12) % (2 * math.pi)
        elif self._state == AssistantState.LISTENING:
            self._angle = (self._angle + 3.0) % 360.0
            self._pulse_phase = (self._pulse_phase + 0.15) % (2 * math.pi)
        elif self._state == AssistantState.SPEAKING:
            self._angle = (self._angle + 2.0) % 360.0
            self._pulse_phase = (self._pulse_phase + 0.08) % (2 * math.pi)
        elif self._state == AssistantState.READY:
            self._angle = (self._angle + 1.2) % 360.0
            self._pulse_phase = (self._pulse_phase + 0.05) % (2 * math.pi)
        elif self._state == AssistantState.ERROR:
            self._angle = (self._angle + 4.0) % 360.0
            self._pulse_phase = (self._pulse_phase + 0.10) % (2 * math.pi)
        else:  # SLEEPING
            self._angle = (self._angle + 0.3) % 360.0
            self._pulse_phase = (self._pulse_phase + 0.02) % (2 * math.pi)

        self.update()

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        width = self.width()
        height = self.height()
        center_x = width / 2.0
        center_y = height / 2.0

        # Base Palette depending on State
        if self._state == AssistantState.SLEEPING:
            accent = QColor(0, 160, 90, 80)
            glow_color = QColor(0, 255, 136, 30)
            core_color = QColor(10, 40, 25, 120)
            pulse_amp = 3.0
        elif self._state == AssistantState.LISTENING:
            accent = QColor(0, 255, 200, 240)
            glow_color = QColor(0, 255, 230, 160)
            core_color = QColor(0, 255, 180, 200)
            pulse_amp = 9.0
        elif self._state == AssistantState.THINKING:
            accent = QColor(0, 200, 255, 240)
            glow_color = QColor(0, 150, 255, 150)
            core_color = QColor(10, 50, 120, 220)
            pulse_amp = 6.0
        elif self._state == AssistantState.SPEAKING:
            accent = QColor(0, 255, 136, 255)
            glow_color = QColor(0, 255, 136, 180)
            core_color = QColor(0, 200, 100, 220)
            pulse_amp = 7.0 + self._audio_level * 10.0
        elif self._state == AssistantState.ERROR:
            accent = QColor(255, 71, 87, 240)
            glow_color = QColor(255, 50, 50, 140)
            core_color = QColor(80, 10, 15, 200)
            pulse_amp = 5.0
        else:  # READY
            accent = QColor(0, 255, 136, 220)
            glow_color = QColor(0, 255, 136, 100)
            core_color = QColor(0, 80, 45, 180)
            pulse_amp = 5.0

        pulse_offset = math.sin(self._pulse_phase) * pulse_amp
        base_radius = 42.0 + pulse_offset

        # 1. Outer Diffuse Glow
        radial = QRadialGradient(center_x, center_y, base_radius + 20)
        radial.setColorAt(0.0, glow_color)
        radial.setColorAt(0.7, QColor(glow_color.red(), glow_color.green(), glow_color.blue(), 25))
        radial.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(radial))
        painter.drawEllipse(
            center_x - (base_radius + 20),
            center_y - (base_radius + 20),
            (base_radius + 20) * 2,
            (base_radius + 20) * 2,
        )

        # 2. Central Core Sphere
        core_radial = QRadialGradient(center_x - 5, center_y - 5, base_radius)
        core_radial.setColorAt(0.0, QColor(255, 255, 255, 220 if self._state != AssistantState.SLEEPING else 60))
        core_radial.setColorAt(0.35, accent)
        core_radial.setColorAt(0.85, core_color)
        core_radial.setColorAt(1.0, QColor(5, 15, 10, 255))
        painter.setBrush(QBrush(core_radial))
        painter.drawEllipse(
            center_x - base_radius,
            center_y - base_radius,
            base_radius * 2,
            base_radius * 2,
        )

        # 3. Rotating Orbital Arcs & HUD Tech Rings
        painter.save()
        painter.translate(center_x, center_y)
        painter.rotate(self._angle)

        ring1_radius = base_radius + 8
        arc_pen = QPen(accent, 1.8)
        arc_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(arc_pen)
        painter.setBrush(Qt.NoBrush)

        # Draw segmented orbital arcs
        painter.drawArc(-ring1_radius, -ring1_radius, ring1_radius * 2, ring1_radius * 2, 0 * 16, 90 * 16)
        painter.drawArc(-ring1_radius, -ring1_radius, ring1_radius * 2, ring1_radius * 2, 140 * 16, 70 * 16)
        painter.drawArc(-ring1_radius, -ring1_radius, ring1_radius * 2, ring1_radius * 2, 240 * 16, 80 * 16)

        # Reverse inner ring
        painter.rotate(-self._angle * 2.2)
        ring2_radius = base_radius + 15
        dim_accent = QColor(accent.red(), accent.green(), accent.blue(), 100)
        ring2_pen = QPen(dim_accent, 1.2, Qt.DashLine)
        painter.setPen(ring2_pen)
        painter.drawArc(-ring2_radius, -ring2_radius, ring2_radius * 2, ring2_radius * 2, 30 * 16, 120 * 16)
        painter.drawArc(-ring2_radius, -ring2_radius, ring2_radius * 2, ring2_radius * 2, 200 * 16, 110 * 16)

        painter.restore()
