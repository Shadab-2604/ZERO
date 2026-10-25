"""
Bottom status bar displaying real subsystem telemetry and operating mode.
"""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QLabel,
    QFrame,
)
from app.system.health_monitor import HealthMonitor


class StatusBarWidget(QFrame):
    """Bottom telemetry bar reflecting real health of Zero subsystems."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("status_bar")
        self.setFixedHeight(34)
        self._init_ui()

        # Update telemetry every 4 seconds
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh_telemetry)
        self._timer.start(4000)
        self.refresh_telemetry()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 14, 0)
        layout.setSpacing(18)

        # Mode Indicator
        self.mode_label = QLabel("MODE: DEMO")
        self.mode_label.setStyleSheet("color: #00FF88; font-weight: bold; font-size: 11px;")
        layout.addWidget(self.mode_label)

        layout.addWidget(self._separator())

        # Backend API
        layout.addWidget(self._label("API:"))
        self.val_api = QLabel("CONNECTED")
        self.val_api.setProperty("class", "status-value-ok")
        layout.addWidget(self.val_api)

        layout.addWidget(self._separator())

        # Database
        layout.addWidget(self._label("DB:"))
        self.val_db = QLabel("CHECKING...")
        self.val_db.setProperty("class", "status-value-ok")
        layout.addWidget(self.val_db)

        layout.addWidget(self._separator())

        # AI Provider
        layout.addWidget(self._label("AI:"))
        self.val_ai = QLabel("DEMO")
        self.val_ai.setProperty("class", "status-value-ok")
        layout.addWidget(self.val_ai)

        layout.addWidget(self._separator())

        # Voice & Mic
        layout.addWidget(self._label("VOICE:"))
        self.val_voice = QLabel("STANDBY")
        self.val_voice.setProperty("class", "status-value-ok")
        layout.addWidget(self.val_voice)

        layout.addStretch()

        # Host resource summary
        self.val_resources = QLabel("CPU: 0% | RAM: 0%")
        self.val_resources.setStyleSheet("color: #6E7681; font-size: 11px;")
        layout.addWidget(self.val_resources)

    def _label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setProperty("class", "status-label")
        return lbl

    def _separator(self) -> QLabel:
        sep = QLabel("|")
        sep.setStyleSheet("color: #1A2421; font-weight: bold;")
        return sep

    def refresh_telemetry(self):
        """Fetch real subsystem health check results."""
        report = HealthMonitor.get_full_health_report()

        mode = report.get("mode", "DEMO")
        self.mode_label.setText(f"MODE: {mode}")
        if mode == "ONLINE":
            self.mode_label.setStyleSheet("color: #00FF88; font-weight: bold; font-size: 11px;")
        elif mode == "OFFLINE":
            self.mode_label.setStyleSheet("color: #FFB800; font-weight: bold; font-size: 11px;")
        else:
            self.mode_label.setStyleSheet("color: #00E5FF; font-weight: bold; font-size: 11px;")

        # Database
        db_stat = report.get("database", {}).get("status", "unhealthy")
        self.val_db.setText("ONLINE" if db_stat == "healthy" else "ERROR")
        self.val_db.setStyleSheet("color: #00FF88;" if db_stat == "healthy" else "color: #FF4757;")

        # AI
        ai_stat = report.get("ai_provider", {})
        ai_provider = ai_stat.get("provider", "demo").upper()
        self.val_ai.setText(ai_provider)

        # Voice
        voice_info = report.get("voice", {})
        if voice_info.get("status") == "healthy":
            self.val_voice.setText("ACTIVE")
            self.val_voice.setStyleSheet("color: #00FF88;")
        elif voice_info.get("status") == "disabled":
            self.val_voice.setText("DISABLED")
            self.val_voice.setStyleSheet("color: #8A8A8A;")
        else:
            self.val_voice.setText("STANDBY")
            self.val_voice.setStyleSheet("color: #FFB800;")

        # System Resources
        res = report.get("resources", {})
        cpu = res.get("cpu_usage_percent", 0.0)
        ram = res.get("ram_usage_percent", 0.0)
        self.val_resources.setText(f"CPU: {cpu}% | RAM: {ram}%")
