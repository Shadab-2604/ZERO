"""
Searchable Conversation History Panel for Zero AI.
Enables browsing past conversation threads, searching messages by keyword,
resuming previous conversations, and safely deleting threads or clearing history.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QScrollArea,
    QFrame,
    QMessageBox,
)
from app.memory.conversation_store import ConversationStore
from app.core.assistant import get_assistant


class HistoryPanelWidget(QWidget):
    """Panel displaying searchable list of historical conversations."""

    conversation_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # 1. Header
        header_layout = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("CONVERSATION ARCHIVE & LOGS")
        title.setStyleSheet("color: #FFFFFF; font-size: 16px; font-weight: bold; letter-spacing: 1.5px;")
        sub = QLabel("Searchable local dialogue threads stored in SQLite")
        sub.setStyleSheet("color: #00FF88; font-size: 11px;")
        title_box.addWidget(title)
        title_box.addWidget(sub)
        header_layout.addLayout(title_box)
        header_layout.addStretch()

        btn_refresh = QPushButton("⟳  Refresh")
        btn_refresh.setProperty("class", "btn-secondary")
        btn_refresh.clicked.connect(self.reload_conversations)
        header_layout.addWidget(btn_refresh)

        btn_clear_all = QPushButton("🗑  Clear History")
        btn_clear_all.setStyleSheet(
            "background-color: #2D1418; color: #FF4757; border: 1px solid #7F1D1D; border-radius: 4px; padding: 6px 12px; font-weight: bold;"
        )
        btn_clear_all.setCursor(Qt.PointingHandCursor)
        btn_clear_all.clicked.connect(self._confirm_clear_all)
        header_layout.addWidget(btn_clear_all)

        layout.addLayout(header_layout)

        # 2. Search Bar
        search_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍  Search conversation history by keyword or title...")
        self.search_input.setFixedHeight(36)
        self.search_input.textChanged.connect(self._on_search_text_changed)
        search_row.addWidget(self.search_input)

        self.btn_clear_search = QPushButton("✕ Clear")
        self.btn_clear_search.setProperty("class", "btn-secondary")
        self.btn_clear_search.setFixedHeight(36)
        self.btn_clear_search.clicked.connect(lambda: self.search_input.clear())
        search_row.addWidget(self.btn_clear_search)

        layout.addLayout(search_row)

        # 3. Scroll area for conversation list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.conv_container = QWidget()
        self.conv_layout = QVBoxLayout(self.conv_container)
        self.conv_layout.setContentsMargins(0, 0, 10, 0)
        self.conv_layout.setSpacing(10)
        self.conv_layout.addStretch()

        scroll.setWidget(self.conv_container)
        layout.addWidget(scroll)

        self.reload_conversations()

    def _on_search_text_changed(self, text: str):
        self.reload_conversations(query=text.strip())

    def reload_conversations(self, query: str = ""):
        """Fetch and populate list of conversations matching optional query."""
        while self.conv_layout.count() > 1:
            item = self.conv_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if query:
            conversations = ConversationStore.search_conversations(query=query, limit=50)
        else:
            conversations = ConversationStore.list_conversations(limit=50)

        if not conversations:
            empty_lbl = QLabel(
                f"No conversations found matching '{query}'." if query else "No conversation history recorded yet."
            )
            empty_lbl.setStyleSheet("color: #8A8A8A; font-style: italic; padding: 24px;")
            self.conv_layout.insertWidget(0, empty_lbl)
            return

        for c in conversations:
            card = QFrame()
            card.setProperty("class", "hud-card")
            card_layout = QHBoxLayout(card)
            card_layout.setContentsMargins(16, 12, 16, 12)

            info_vbox = QVBoxLayout()
            c_title = QLabel(c["title"])
            c_title.setStyleSheet("color: #FFFFFF; font-size: 13px; font-weight: bold;")
            info_vbox.addWidget(c_title)

            ts_str = c["updated_at"][:19].replace("T", " ")
            c_meta = QLabel(f"ID: {c['id'][:8]}... | Updated: {ts_str}")
            c_meta.setStyleSheet("color: #6E7681; font-size: 11px;")
            info_vbox.addWidget(c_meta)

            card_layout.addLayout(info_vbox)
            card_layout.addStretch()

            btn_load = QPushButton("Open in Chat 💬")
            btn_load.setProperty("class", "btn-primary")
            btn_load.setCursor(Qt.PointingHandCursor)
            btn_load.clicked.connect(lambda _, cid=c["id"]: self._load_conversation(cid))
            card_layout.addWidget(btn_load)

            btn_delete = QPushButton("🗑 Delete")
            btn_delete.setProperty("class", "btn-secondary")
            btn_delete.setCursor(Qt.PointingHandCursor)
            btn_delete.clicked.connect(lambda _, cid=c["id"], t=c["title"]: self._confirm_delete(cid, t))
            card_layout.addWidget(btn_delete)

            count = self.conv_layout.count()
            self.conv_layout.insertWidget(count - 1, card)

    def _load_conversation(self, conv_id: str):
        assistant = get_assistant()
        assistant.active_conversation_id = conv_id
        self.conversation_selected.emit(conv_id)

    def _confirm_delete(self, conv_id: str, title: str):
        reply = QMessageBox.question(
            self,
            "Delete Conversation",
            f"Are you sure you want to delete conversation '{title}'?\nThis cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            ConversationStore.delete_conversation(conv_id)
            self.reload_conversations(query=self.search_input.text().strip())

    def _confirm_clear_all(self):
        reply = QMessageBox.warning(
            self,
            "Clear Entire History",
            "Are you sure you want to delete ALL conversation history?\nAll previous dialogue threads will be permanently erased.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            ConversationStore.clear_all_conversations()
            self.reload_conversations()
