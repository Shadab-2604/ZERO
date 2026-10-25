"""
Zero AI — Persistent Footer Voice & Live Caption Dock (Obsidian Command).
Fixed 40px bottom bar with reactive audio equalizer bars, state indicator,
real-time transcript ticker, and operational interruption / force mic controls.
"""

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
)
from app.core.state_manager import AssistantState
from app.gui.theme import (
    BORDER_SUBTLE,
    ACCENT_NEON,
    ACCENT_WARNING,
    ACCENT_CRITICAL,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_DIM,
)


class FooterVoiceBarWidget(QWidget):
    """
    Persistent 40px voice dock displaying real-time audio telemetry,
    live transcript ticker, and interrupt controls.
    """

    interrupt_requested = Signal()
    force_mic_pressed = Signal()
    force_mic_released = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("footer_voice_bar")
        self.setFixedHeight(40)

        self._state = AssistantState.READY
        self._audio_level = 0.0
        self._bars: list[QFrame] = []
        self._tick = 0

        self._init_ui()

        # Animation timer for audio equalizer bars
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate_equalizer)
        self._timer.start(80)

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 14, 0)
        layout.setSpacing(12)

        # 1. Left: Reactive Audio Waveform Equalizer
        eq_container = QWidget()
        eq_layout = QHBoxLayout(eq_container)
        eq_layout.setContentsMargins(0, 0, 0, 0)
        eq_layout.setSpacing(2)

        for _ in range(10):
            bar = QFrame()
            bar.setFixedWidth(2)
            bar.setFixedHeight(6)
            bar.setStyleSheet(f"background-color: {TEXT_DIM}; border-radius: 1px;")
            self._bars.append(bar)
            eq_layout.addWidget(bar, alignment=Qt.AlignVCenter)

        layout.addWidget(eq_container)

        # State text
        self.lbl_state = QLabel("READY")
        self.lbl_state.setStyleSheet(f"color: {ACCENT_NEON}; font-family: 'Consolas', monospace; font-weight: bold; font-size: 11px;")
        layout.addWidget(self.lbl_state)

        sep1 = QLabel("|")
        sep1.setStyleSheet(f"color: {BORDER_SUBTLE}; font-family: monospace;")
        layout.addWidget(sep1)

        # Mic state
        self.lbl_mic = QLabel("MIC: ACTIVE (48kHz)")
        self.lbl_mic.setStyleSheet(f"color: {TEXT_SECONDARY}; font-family: 'Consolas', monospace; font-size: 10px;")
        layout.addWidget(self.lbl_mic)

        sep2 = QLabel("|")
        sep2.setStyleSheet(f"color: {BORDER_SUBTLE}; font-family: monospace;")
        layout.addWidget(sep2)

        # Latency
        self.lbl_latency = QLabel("0.02s LATENCY")
        self.lbl_latency.setStyleSheet(f"color: {ACCENT_NEON}; font-family: 'Consolas', monospace; font-size: 10px;")
        layout.addWidget(self.lbl_latency)

        # 2. Center: Live Speech Transcript Ticker
        self.lbl_ticker = QLabel('System initialized and ready for voice input or text commands.')
        self.lbl_ticker.setStyleSheet(f"color: {TEXT_PRIMARY}; font-family: 'Segoe UI', sans-serif; font-size: 11px;")
        self.lbl_ticker.setWordWrap(False)
        layout.addWidget(self.lbl_ticker, stretch=1)

        # 3. Right: Interrupt and Force Mic Controls
        self.btn_interrupt = QPushButton("INTERRUPT [ESC]")
        self.btn_interrupt.setCursor(Qt.PointingHandCursor)
        self.btn_interrupt.setToolTip("Interrupt active speech playback or AI inference")
        self.btn_interrupt.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {ACCENT_NEON};
                border: 1px solid {BORDER_SUBTLE};
                border-radius: 3px;
                padding: 3px 8px;
                font-family: 'Consolas', monospace;
                font-weight: bold;
                font-size: 10px;
            }}
            QPushButton:hover {{
                background-color: #271212;
                border: 1px solid {ACCENT_CRITICAL};
                color: {ACCENT_CRITICAL};
            }}
        """)
        self.btn_interrupt.clicked.connect(self.interrupt_requested.emit)
        layout.addWidget(self.btn_interrupt)

        self.btn_force_mic = QPushButton("HOLD [SPACE] FOR FORCE MIC")
        self.btn_force_mic.setCursor(Qt.PointingHandCursor)
        self.btn_force_mic.setToolTip("Hold Spacebar or Click & Hold to force push-to-talk recording")
        self.btn_force_mic.setStyleSheet(f"""
            QPushButton {{
                background-color: #151A18;
                color: {TEXT_SECONDARY};
                border: 1px solid {BORDER_SUBTLE};
                border-radius: 3px;
                padding: 3px 8px;
                font-family: 'Consolas', monospace;
                font-size: 10px;
            }}
            QPushButton:hover {{
                border: 1px solid {ACCENT_NEON};
                color: {ACCENT_NEON};
            }}
            QPushButton:pressed {{
                background-color: {ACCENT_NEON};
                color: #050505;
                font-weight: bold;
            }}
        """)
        self.btn_force_mic.pressed.connect(self.force_mic_pressed.emit)
        self.btn_force_mic.released.connect(self.force_mic_released.emit)
        layout.addWidget(self.btn_force_mic)

    def set_assistant_state(self, state: AssistantState) -> None:
        """Update display when assistant state changes."""
        self._state = state
        state_str = state.value.upper()
        self.lbl_state.setText(state_str)

        if state == AssistantState.SPEAKING:
            self.lbl_state.setStyleSheet(f"color: {ACCENT_NEON}; font-family: 'Consolas', monospace; font-weight: bold; font-size: 11px;")
        elif state == AssistantState.LISTENING:
            self.lbl_state.setStyleSheet(f"color: #00E479; font-family: 'Consolas', monospace; font-weight: bold; font-size: 11px;")
        elif state == AssistantState.THINKING:
            self.lbl_state.setStyleSheet(f"color: #00C8FF; font-family: 'Consolas', monospace; font-weight: bold; font-size: 11px;")
        elif state == AssistantState.ERROR:
            self.lbl_state.setStyleSheet(f"color: {ACCENT_CRITICAL}; font-family: 'Consolas', monospace; font-weight: bold; font-size: 11px;")
        elif state == AssistantState.SLEEPING:
            self.lbl_state.setStyleSheet(f"color: {TEXT_DIM}; font-family: 'Consolas', monospace; font-size: 11px;")
        else:
            self.lbl_state.setStyleSheet(f"color: {ACCENT_NEON}; font-family: 'Consolas', monospace; font-size: 11px;")

    def set_mic_status(self, active: bool, rate_hz: int = 48000) -> None:
        """Update mic status label."""
        if active:
            self.lbl_mic.setText(f"MIC: ACTIVE ({rate_hz // 1000}kHz)")
            self.lbl_mic.setStyleSheet(f"color: {TEXT_SECONDARY}; font-family: 'Consolas', monospace; font-size: 10px;")
        else:
            self.lbl_mic.setText("MIC: MUTED")
            self.lbl_mic.setStyleSheet(f"color: {ACCENT_CRITICAL}; font-family: 'Consolas', monospace; font-size: 10px;")

    def set_latency(self, latency_ms: float) -> None:
        """Update latency readout."""
        sec = latency_ms / 1000.0
        self.lbl_latency.setText(f"{sec:.2f}s LATENCY")

    def set_ticker_text(self, text: str, prefix: str = "") -> None:
        """Update center scrolling ticker with recent conversation text."""
        display = f"{prefix} \"{text}\"" if prefix else text
        if len(display) > 120:
            display = display[:117] + "..."
        self.lbl_ticker.setText(display)

    def _animate_equalizer(self):
        """Update equalizer bar heights based on current assistant state."""
        import math
        self._tick += 1

        is_active = self._state in (AssistantState.LISTENING, AssistantState.SPEAKING, AssistantState.THINKING)
        pattern_offsets = [0.0, 0.6, 1.2, 1.8, 2.4, 3.0, 3.6, 4.2, 4.8, 5.4]

        for i, bar in enumerate(self._bars):
            if is_active:
                phase = (self._tick * 0.4) + pattern_offsets[i]
                h = int(6 + (math.sin(phase) + 1.0) * 7)
                bar.setFixedHeight(max(4, min(20, h)))
                bar.setStyleSheet(f"background-color: {ACCENT_NEON}; border-radius: 1px;")
            else:
                bar.setFixedHeight(4)
                bar.setStyleSheet(f"background-color: {BORDER_SUBTLE}; border-radius: 1px;")
