"""
Deep System Status and Subsystem Diagnostics panel for Zero AI.
"""

import sys
import platform
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QFrame,
)
from app.system.health_monitor import HealthMonitor
from app.config.settings import get_settings
from app.utils.paths import get_data_dir


class SystemPanelWidget(QWidget):
    """Deep system diagnostic and telemetry view."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # Header
        header_layout = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("SYSTEM STATUS & DIAGNOSTICS")
        title.setStyleSheet("color: #FFFFFF; font-size: 16px; font-weight: bold; letter-spacing: 1.5px;")
        sub = QLabel("Real-time telemetry across core subsystems and hardware resources")
        sub.setStyleSheet("color: #00FF88; font-size: 11px;")
        title_box.addWidget(title)
        title_box.addWidget(sub)
        header_layout.addLayout(title_box)
        header_layout.addStretch()

        btn_refresh = QPushButton("⟳  Run Diagnostics")
        btn_refresh.setProperty("class", "btn-primary")
        btn_refresh.clicked.connect(self.reload_diagnostics)
        header_layout.addWidget(btn_refresh)
        layout.addLayout(header_layout)

        # Scroll
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        self.c_layout = QVBoxLayout(content)
        self.c_layout.setContentsMargins(0, 0, 10, 0)
        self.c_layout.setSpacing(14)

        scroll.setWidget(content)
        layout.addWidget(scroll)

        self.reload_diagnostics()

    def reload_diagnostics(self):
        """Re-run health checks and populate diagnostic cards."""
        while self.c_layout.count():
            item = self.c_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        settings = get_settings()
        health = HealthMonitor.get_full_health_report()
        res = health.get("resources", {})
        ai_info = health.get("ai_provider", {})
        db_info = health.get("database", {})
        voice_info = health.get("voice", {})

        # 1. Environment & Host
        card_env = self._create_card("HOST ENVIRONMENT & RUNTIME")
        self._add_row(card_env, "Operating System", f"{platform.system()} {platform.release()} ({platform.machine()})")
        self._add_row(card_env, "Python Interpreter", sys.version.split()[0])
        self._add_row(card_env, "Application Environment", settings.app_env.upper())
        self._add_row(card_env, "API Binding (Loopback)", f"http://{settings.app_host}:{settings.app_port}")
        self.c_layout.addWidget(card_env)

        # 2. Subsystems Health
        card_sub = self._create_card("SUBSYSTEM HEALTH CHECKS")
        self._add_row(card_sub, "Overall Status", health.get("status", "healthy").upper(), color="#00FF88")
        self._add_row(card_sub, "Operating Mode", health.get("mode", "DEMO"), color="#00E5FF")
        self._add_row(card_sub, "Database Connectivity", db_info.get("status", "healthy").upper())
        self._add_row(card_sub, "Database Path", str(get_data_dir() / "zero.db"))
        self._add_row(card_sub, "AI Provider Status", ai_info.get("message", "Ready"))
        self._add_row(card_sub, "Voice Subsystem", voice_info.get("message", "Ready"))
        self.c_layout.addWidget(card_sub)

        # 3. Hardware Resource Metrics
        card_res = self._create_card("HARDWARE RESOURCES")
        self._add_row(card_res, "CPU Load", f"{res.get('cpu_usage_percent', 0)}%")
        self._add_row(card_res, "RAM Utilization", f"{res.get('ram_usage_percent', 0)}% (Available: {res.get('ram_available_mb', 0)} MB)")
        self._add_row(card_res, "Primary Disk Free", f"{res.get('disk_free_gb', 0)} GB available")
        self.c_layout.addWidget(card_res)

        self.c_layout.addStretch()

    def _create_card(self, title: str) -> QFrame:
        card = QFrame()
        card.setProperty("class", "hud-card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(8)

        lbl = QLabel(title)
        lbl.setStyleSheet("color: #00FF88; font-size: 11px; font-weight: bold; letter-spacing: 1px;")
        layout.addWidget(lbl)
        return card

    def _add_row(self, card: QFrame, label: str, value: str, color: str = "#FFFFFF"):
        layout = card.layout()
        row = QHBoxLayout()
        lbl_k = QLabel(label + ":")
        lbl_k.setStyleSheet("color: #8A8A8A; font-size: 12px; font-weight: 500;")
        lbl_v = QLabel(value)
        lbl_v.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: bold;")
        lbl_v.setWordWrap(True)

        row.addWidget(lbl_k)
        row.addSpacing(10)
        row.addWidget(lbl_v)
        row.addStretch()
        layout.addLayout(row)
