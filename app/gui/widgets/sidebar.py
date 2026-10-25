"""
Sidebar navigation widget for Zero AI desktop interface.
Provides links to Chat, History, Daily Briefing, Project Activity, System Status, and Settings.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QButtonGroup,
    QSpacerItem,
    QSizePolicy,
    QFrame,
)


class SidebarWidget(QWidget):
    """Futuristic navigation sidebar for Zero AI."""

    # Navigation signal emitting view name
    navigate = Signal(str)
    new_conversation_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(230)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 20, 16, 16)
        layout.setSpacing(10)

        # Brand Header
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)

        # Pulsing online status indicator dot
        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet("color: #00FF88; font-size: 14px;")
        header_layout.addWidget(self.status_dot)

        brand_label = QLabel("ZERO AI")
        brand_label.setStyleSheet(
            "color: #FFFFFF; font-size: 18px; font-weight: 800; letter-spacing: 2px;"
        )
        header_layout.addWidget(brand_label)
        header_layout.addStretch()

        layout.addLayout(header_layout)

        sub_label = QLabel("JARVIS CORE v1.0")
        sub_label.setStyleSheet("color: #00FF88; font-size: 10px; font-weight: 600; letter-spacing: 1.5px; padding-left: 20px;")
        layout.addWidget(sub_label)

        # Divider
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet("background-color: #14221a; max-height: 1px; margin-top: 10px; margin-bottom: 10px;")
        layout.addWidget(divider)

        # New Conversation Action Button
        self.btn_new_chat = QPushButton("＋  New Conversation")
        self.btn_new_chat.setProperty("class", "btn-primary")
        self.btn_new_chat.setCursor(Qt.PointingHandCursor)
        self.btn_new_chat.clicked.connect(self.new_conversation_clicked.emit)
        layout.addWidget(self.btn_new_chat)

        layout.addSpacing(10)

        # Navigation Buttons Group
        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True)

        self.btn_assistant = self._create_nav_button("⚡  Assistant Core", "assistant", active=True)
        self.btn_history = self._create_nav_button("💬  Conversation History", "history")
        self.btn_knowledge = self._create_nav_button("📚  Knowledge Base", "knowledge")
        self.btn_briefing = self._create_nav_button("📋  Daily Briefing", "briefing")
        self.btn_activity = self._create_nav_button("📊  Project Activity", "activity")
        self.btn_system = self._create_nav_button("🛡️  System Status", "system")
        self.btn_settings = self._create_nav_button("⚙️  Settings", "settings")

        layout.addWidget(self.btn_assistant)
        layout.addWidget(self.btn_history)
        layout.addWidget(self.btn_knowledge)
        layout.addWidget(self.btn_briefing)
        layout.addWidget(self.btn_activity)
        layout.addWidget(self.btn_system)

        layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

        layout.addWidget(self.btn_settings)

    def _create_nav_button(self, label: str, view_id: str, active: bool = False) -> QPushButton:
        btn = QPushButton(label)
        btn.setProperty("class", "nav-button")
        btn.setCheckable(True)
        btn.setChecked(active)
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(lambda: self.navigate.emit(view_id))
        self.button_group.addButton(btn)
        return btn

    def set_active_view(self, view_id: str) -> None:
        """Update button selection state to match active view."""
        mapping = {
            "assistant": self.btn_assistant,
            "history": self.btn_history,
            "knowledge": self.btn_knowledge,
            "briefing": self.btn_briefing,
            "activity": self.btn_activity,
            "system": self.btn_system,
            "settings": self.btn_settings,
        }
        btn = mapping.get(view_id)
        if btn:
            btn.setChecked(True)
