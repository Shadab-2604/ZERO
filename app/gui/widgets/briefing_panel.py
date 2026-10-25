"""
Dedicated Daily Briefing and Project Activity panel for Zero AI.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QFrame,
    QLineEdit,
)
from app.core.assistant import get_assistant
from app.memory.activity_store import ActivityStore
from app.utils.time_utils import get_current_time
from app.config.settings import get_settings


class BriefingPanelWidget(QWidget):
    """Panel displaying comprehensive daily briefings, project activity, and tasks."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # Header with Refresh
        header_layout = QHBoxLayout()
        title_box = QVBoxLayout()
        title_label = QLabel("MISSION BRIEFING & PROJECT ACTIVITY")
        title_label.setStyleSheet("color: #FFFFFF; font-size: 16px; font-weight: bold; letter-spacing: 1.5px;")
        self.timestamp_label = QLabel("")
        self.timestamp_label.setStyleSheet("color: #00FF88; font-size: 11px;")
        title_box.addWidget(title_label)
        title_box.addWidget(self.timestamp_label)

        header_layout.addLayout(title_box)
        header_layout.addStretch()

        self.btn_refresh = QPushButton("⟳  Regenerate Briefing")
        self.btn_refresh.setProperty("class", "btn-primary")
        self.btn_refresh.clicked.connect(self.reload_data)
        header_layout.addWidget(self.btn_refresh)

        layout.addLayout(header_layout)

        # Scroll Area for Content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 10, 0)
        content_layout.setSpacing(16)

        # 1. Briefing Card
        briefing_card = QFrame()
        briefing_card.setProperty("class", "hud-card")
        bc_layout = QVBoxLayout(briefing_card)
        bc_layout.setContentsMargins(18, 16, 18, 16)
        bc_layout.setSpacing(10)

        bc_header = QLabel("COMMAND BRIEFING NARRATIVE")
        bc_header.setStyleSheet("color: #00FF88; font-size: 12px; font-weight: bold; letter-spacing: 1px;")
        bc_layout.addWidget(bc_header)

        self.briefing_text = QLabel("Loading briefing telemetry...")
        self.briefing_text.setWordWrap(True)
        self.briefing_text.setStyleSheet("color: #E6EDF3; font-size: 13px; line-height: 1.5;")
        bc_layout.addWidget(self.briefing_text)
        content_layout.addWidget(briefing_card)

        # 2. Tasks & Action Items Card
        tasks_card = QFrame()
        tasks_card.setProperty("class", "hud-card")
        tc_layout = QVBoxLayout(tasks_card)
        tc_layout.setContentsMargins(18, 16, 18, 16)
        tc_layout.setSpacing(10)

        tc_header = QLabel("PENDING TASKS & WORK OBJECTIVES")
        tc_header.setStyleSheet("color: #00FF88; font-size: 12px; font-weight: bold; letter-spacing: 1px;")
        tc_layout.addWidget(tc_header)

        self.tasks_container = QVBoxLayout()
        tc_layout.addLayout(self.tasks_container)

        # Add Task Row
        add_task_layout = QHBoxLayout()
        self.task_input = QLineEdit()
        self.task_input.setPlaceholderText("Enter a new task or objective...")
        self.btn_add_task = QPushButton("＋ Add Task")
        self.btn_add_task.setProperty("class", "btn-secondary")
        self.btn_add_task.clicked.connect(self._add_task)
        self.task_input.returnPressed.connect(self._add_task)

        add_task_layout.addWidget(self.task_input)
        add_task_layout.addWidget(self.btn_add_task)
        tc_layout.addLayout(add_task_layout)

        content_layout.addWidget(tasks_card)

        # 3. Recent Activity Log Card
        activity_card = QFrame()
        activity_card.setProperty("class", "hud-card")
        ac_layout = QVBoxLayout(activity_card)
        ac_layout.setContentsMargins(18, 16, 18, 16)
        ac_layout.setSpacing(10)

        ac_header = QLabel("AUDIT & ACTIVITY LOG (LAST 10 EVENTS)")
        ac_header.setStyleSheet("color: #00FF88; font-size: 12px; font-weight: bold; letter-spacing: 1px;")
        ac_layout.addWidget(ac_header)

        self.activity_container = QVBoxLayout()
        ac_layout.addLayout(self.activity_container)

        content_layout.addWidget(activity_card)
        content_layout.addStretch()

        scroll.setWidget(content_widget)
        layout.addWidget(scroll)

        self.reload_data()

    def reload_data(self):
        """Fetch and populate current briefing, task list, and activity log."""
        settings = get_settings()
        now = get_current_time(settings.timezone)
        self.timestamp_label.setText(f"TIMEZONE: {settings.timezone}  |  {now.strftime('%A, %B %d, %Y - %I:%M:%S %p')}")

        assistant = get_assistant()
        briefing = assistant.briefing_service.generate_briefing(force=True)
        self.briefing_text.setText(briefing["text"])

        # Populate tasks
        # Clear existing
        while self.tasks_container.count():
            item = self.tasks_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        tasks = ActivityStore.list_tasks(status="pending")
        if not tasks:
            empty_lbl = QLabel("No pending tasks recorded. Create a new task below.")
            empty_lbl.setStyleSheet("color: #8A8A8A; font-style: italic;")
            self.tasks_container.addWidget(empty_lbl)
        else:
            for t in tasks[:10]:
                row = QHBoxLayout()
                task_title = QLabel(f"•  {t['title']}")
                task_title.setStyleSheet("color: #FFFFFF; font-size: 13px;")
                row.addWidget(task_title)
                row.addStretch()

                btn_done = QPushButton("Mark Complete")
                btn_done.setProperty("class", "btn-secondary")
                btn_done.setFixedSize(110, 26)
                btn_done.clicked.connect(lambda _, tid=t["id"]: self._complete_task(tid))
                row.addWidget(btn_done)

                row_widget = QWidget()
                row_widget.setLayout(row)
                self.tasks_container.addWidget(row_widget)

        # Populate activity log
        while self.activity_container.count():
            item = self.activity_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        activities = ActivityStore.get_recent_activities(limit=10)
        if not activities:
            no_act = QLabel("No activity events logged yet.")
            no_act.setStyleSheet("color: #8A8A8A; font-style: italic;")
            self.activity_container.addWidget(no_act)
        else:
            for a in activities:
                ts = a["timestamp"][:19].replace("T", " ")
                act_lbl = QLabel(f"[{ts}] [{a['category'].upper()}] {a['description']}")
                act_lbl.setStyleSheet("color: #A0AEC0; font-family: monospace; font-size: 11px;")
                self.activity_container.addWidget(act_lbl)

    def _add_task(self):
        text = self.task_input.text().strip()
        if not text:
            return
        ActivityStore.add_task(title=text)
        self.task_input.clear()
        self.reload_data()

    def _complete_task(self, task_id: str):
        ActivityStore.update_task_status(task_id, "completed")
        self.reload_data()
