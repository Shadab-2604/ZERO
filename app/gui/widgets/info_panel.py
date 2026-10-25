"""
Right-side HUD information panel widget for Zero AI.
Displays live clock, system health, pending tasks, recent project activity, and last session summary.
"""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QScrollArea,
    QPushButton,
)
from app.config.settings import get_settings
from app.utils.time_utils import get_current_time
from app.memory.activity_store import ActivityStore
from app.system.health_monitor import HealthMonitor
from app.core.state_manager import AssistantState


class InfoPanelWidget(QWidget):
    """Collapsible right-side HUD information panel."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(280)
        self._init_ui()

        # Update clock and stats every second
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh_data)
        self._timer.start(1000)
        self.refresh_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 16, 14, 16)
        layout.setSpacing(12)

        # 1. Live Chrono & Clock Card
        clock_card = QFrame()
        clock_card.setProperty("class", "hud-card")
        c_layout = QVBoxLayout(clock_card)
        c_layout.setContentsMargins(14, 12, 14, 12)
        c_layout.setSpacing(2)

        self.lbl_time = QLabel("00:00:00")
        self.lbl_time.setStyleSheet("color: #00FF88; font-size: 20px; font-weight: bold; font-family: monospace;")
        self.lbl_date = QLabel("DAY, DATE")
        self.lbl_date.setStyleSheet("color: #FFFFFF; font-size: 11px;")
        self.lbl_tz = QLabel("TIMEZONE: UTC")
        self.lbl_tz.setStyleSheet("color: #6E7681; font-size: 10px;")

        c_layout.addWidget(self.lbl_time)
        c_layout.addWidget(self.lbl_date)
        c_layout.addWidget(self.lbl_tz)
        layout.addWidget(clock_card)

        # Scrollable content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        c_box = QVBoxLayout(content)
        c_box.setContentsMargins(0, 0, 6, 0)
        c_box.setSpacing(12)

        # 2. Assistant State Card
        state_card = QFrame()
        state_card.setProperty("class", "hud-card")
        s_layout = QVBoxLayout(state_card)
        s_layout.setContentsMargins(12, 10, 12, 10)
        s_layout.addWidget(self._section_title("OPERATIONAL STATE"))

        self.lbl_state = QLabel("SLEEPING")
        self.lbl_state.setStyleSheet("color: #00FF88; font-weight: bold; font-size: 13px;")
        s_layout.addWidget(self.lbl_state)
        c_box.addWidget(state_card)

        # 3. System Health Indicators Card
        health_card = QFrame()
        health_card.setProperty("class", "hud-card")
        h_layout = QVBoxLayout(health_card)
        h_layout.setContentsMargins(12, 10, 12, 10)
        h_layout.addWidget(self._section_title("SYSTEM TELEMETRY"))

        self.lbl_cpu = QLabel("CPU: 0%")
        self.lbl_ram = QLabel("RAM: 0%")
        self.lbl_db = QLabel("Database: ONLINE")
        self.lbl_ai = QLabel("AI: DEMO MODE")

        for lbl in (self.lbl_cpu, self.lbl_ram, self.lbl_db, self.lbl_ai):
            lbl.setStyleSheet("color: #8A8A8A; font-size: 11px;")
            h_layout.addWidget(lbl)
        c_box.addWidget(health_card)

        # 4. Pending Tasks Card
        tasks_card = QFrame()
        tasks_card.setProperty("class", "hud-card")
        t_layout = QVBoxLayout(tasks_card)
        t_layout.setContentsMargins(12, 10, 12, 10)
        t_layout.addWidget(self._section_title("PENDING OBJECTIVES"))

        self.tasks_list_layout = QVBoxLayout()
        t_layout.addLayout(self.tasks_list_layout)
        c_box.addWidget(tasks_card)

        # 5. Last Session Summary Card
        summary_card = QFrame()
        summary_card.setProperty("class", "hud-card")
        sum_layout = QVBoxLayout(summary_card)
        sum_layout.setContentsMargins(12, 10, 12, 10)
        sum_layout.addWidget(self._section_title("PREVIOUS SESSION"))

        self.lbl_summary = QLabel("No previous summary recorded.")
        self.lbl_summary.setWordWrap(True)
        self.lbl_summary.setStyleSheet("color: #8A8A8A; font-size: 11px; line-height: 1.3;")
        sum_layout.addWidget(self.lbl_summary)
        c_box.addWidget(summary_card)

        c_box.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

    def _section_title(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #00FF88; font-size: 10px; font-weight: bold; letter-spacing: 1px;")
        return lbl

    def set_assistant_state(self, state: AssistantState):
        self.lbl_state.setText(state.value)

    def refresh_data(self):
        """Update live clock, metrics, tasks, and summary."""
        settings = get_settings()
        now = get_current_time(settings.timezone)
        self.lbl_time.setText(now.strftime("%H:%M:%S"))
        self.lbl_date.setText(now.strftime("%A, %b %d, %Y"))
        self.lbl_tz.setText(f"TIMEZONE: {settings.timezone}")

        # Metrics
        health = HealthMonitor.get_full_health_report()
        res = health.get("resources", {})
        self.lbl_cpu.setText(f"CPU Load: {res.get('cpu_usage_percent', 0)}%")
        self.lbl_ram.setText(f"RAM Usage: {res.get('ram_usage_percent', 0)}%")
        db_stat = health.get("database", {}).get("status", "unhealthy")
        self.lbl_db.setText(f"Database: {db_stat.upper()}")
        mode = health.get("mode", "DEMO")
        self.lbl_ai.setText(f"AI Provider: {mode}")

        # Tasks
        tasks = ActivityStore.list_tasks(status="pending")
        while self.tasks_list_layout.count():
            item = self.tasks_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not tasks:
            no_t = QLabel("No active tasks.")
            no_t.setStyleSheet("color: #6E7681; font-size: 11px; font-style: italic;")
            self.tasks_list_layout.addWidget(no_t)
        else:
            for t in tasks[:4]:
                t_lbl = QLabel(f"• {t['title']}")
                t_lbl.setWordWrap(True)
                t_lbl.setStyleSheet("color: #E6EDF3; font-size: 11px;")
                self.tasks_list_layout.addWidget(t_lbl)

        # Summary
        summary = ActivityStore.get_latest_session_summary()
        if summary:
            self.lbl_summary.setText(summary["summary_text"])
            self.lbl_summary.setStyleSheet("color: #A0AEC0; font-size: 11px;")
        else:
            self.lbl_summary.setText("This is your first recorded session. History will appear here.")
