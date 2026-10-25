"""
Main interactive assistant chat panel featuring the animated AI orb,
conversation transcript, text input, microphone controls, and wake/sleep triggers.
"""

from datetime import datetime
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QScrollArea,
    QFrame,
    QSizePolicy,
)
from PySide6.QtGui import QGuiApplication, QFont
import re
import os
import sys
import markdown
from app.core.assistant import get_assistant
from app.core.state_manager import AssistantState
from app.gui.widgets.ai_orb import AIOrbWidget
from app.memory.conversation_store import ConversationStore
from app.utils.paths import get_exports_dir


class MessageBubble(QFrame):
    """Futuristic styled chat bubble for user and assistant messages with Markdown, code blocks, and PDF cards."""

    def __init__(self, role: str, content: str, timestamp_str: str = "", parent=None):
        super().__init__(parent)
        self.setProperty("class", "hud-card")
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(14, 10, 14, 10)
        self.layout.setSpacing(8)

        is_user = role.lower() == "user"

        # 1. Header Row
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        sender_label = QLabel("YOU" if is_user else "ZERO")
        sender_label.setStyleSheet(
            "color: #00FF88; font-weight: bold; font-size: 11px; letter-spacing: 1px;"
            if not is_user
            else "color: #58A6FF; font-weight: bold; font-size: 11px; letter-spacing: 1px;"
        )
        header_layout.addWidget(sender_label)

        if not timestamp_str:
            timestamp_str = datetime.now().strftime("%H:%M:%S")
        ts_label = QLabel(timestamp_str)
        ts_label.setStyleSheet("color: #6E7681; font-size: 10px;")
        header_layout.addWidget(ts_label)
        header_layout.addStretch()

        self.layout.addLayout(header_layout)

        # 2. Render content with code blocks, artifacts, and markdown
        self._render_content(content, is_user)

        # Style bubble border based on role
        if is_user:
            self.setStyleSheet(
                "QFrame { background-color: #0d161c; border: 1px solid #1f3747; border-radius: 8px; margin-left: 60px; }"
            )
        else:
            self.setStyleSheet(
                "QFrame { background-color: #09130e; border: 1px solid #143021; border-radius: 8px; margin-right: 60px; }"
            )

    def _render_content(self, raw_content: str, is_user: bool):
        """Parse raw content into text sections, code blocks, and PDF artifact cards."""
        # 1. Check for artifact PDF tokens: [ARTIFACT_PDF: filename | title]
        artifact_match = re.search(r"\[ARTIFACT_PDF:\s*([^\|\]]+)\s*\|\s*([^\]]+)\]", raw_content)
        content_to_parse = raw_content
        if artifact_match:
            pdf_filename = artifact_match.group(1).strip()
            pdf_title = artifact_match.group(2).strip()
            content_to_parse = raw_content.replace(artifact_match.group(0), "").strip()

            # Render PDF Artifact Action Card
            card = QFrame()
            card.setStyleSheet(
                "background-color: #0F1D14; border: 1px solid #00D06C; border-radius: 6px; padding: 10px;"
            )
            card_layout = QHBoxLayout(card)
            card_layout.setContentsMargins(12, 8, 12, 8)

            icon_lbl = QLabel("📄")
            icon_lbl.setStyleSheet("font-size: 18px;")
            card_layout.addWidget(icon_lbl)

            info_box = QVBoxLayout()
            title_lbl = QLabel(f"ARTIFACT: {pdf_title}")
            title_lbl.setStyleSheet("color: #00FF88; font-weight: bold; font-size: 12px; letter-spacing: 0.5px;")
            file_lbl = QLabel(f"File: exports/{pdf_filename}")
            file_lbl.setStyleSheet("color: #8A8A8A; font-size: 10px;")
            info_box.addWidget(title_lbl)
            info_box.addWidget(file_lbl)
            card_layout.addLayout(info_box)
            card_layout.addStretch()

            btn_open = QPushButton("Open PDF ↗")
            btn_open.setProperty("class", "btn-primary")
            btn_open.setCursor(Qt.PointingHandCursor)
            btn_open.clicked.connect(lambda: self._open_pdf(pdf_filename))
            card_layout.addWidget(btn_open)

            self.layout.addWidget(card)

        # 2. Split content by fenced code blocks (```lang ... ```)
        pattern = re.compile(r"```([a-zA-Z0-9_\-]*)\n(.*?)```", re.DOTALL)
        last_idx = 0

        for match in pattern.finditer(content_to_parse):
            pre_text = content_to_parse[last_idx:match.start()].strip()
            if pre_text:
                self._add_markdown_label(pre_text, is_user)

            lang = match.group(1).strip() or "CODE"
            code_body = match.group(2)
            self._add_code_block(lang, code_body)
            last_idx = match.end()

        post_text = content_to_parse[last_idx:].strip()
        if post_text:
            self._add_markdown_label(post_text, is_user)

    def _add_markdown_label(self, md_text: str, is_user: bool):
        """Render markdown text with styled HTML in QLabel."""
        html = markdown.markdown(
            md_text,
            extensions=["tables", "nl2br", "sane_lists"],
        )
        lbl = QLabel(html)
        lbl.setWordWrap(True)
        lbl.setTextFormat(Qt.RichText)
        lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lbl.setOpenExternalLinks(True)
        lbl.setStyleSheet(
            "color: #FFFFFF; font-size: 13px; line-height: 1.5;"
            if not is_user
            else "color: #E6EDF3; font-size: 13px; line-height: 1.5;"
        )
        self.layout.addWidget(lbl)

    def _add_code_block(self, language: str, code_content: str):
        """Add syntax-styled code box with copy button."""
        box = QFrame()
        box.setStyleSheet(
            "background-color: #0A0F14; border: 1px solid #1E293B; border-radius: 6px; margin: 4px 0px;"
        )
        box_layout = QVBoxLayout(box)
        box_layout.setContentsMargins(10, 8, 10, 8)
        box_layout.setSpacing(6)

        header_row = QHBoxLayout()
        lang_lbl = QLabel(language.upper())
        lang_lbl.setStyleSheet("color: #00FF88; font-size: 10px; font-weight: bold; letter-spacing: 1px;")
        header_row.addWidget(lang_lbl)
        header_row.addStretch()

        btn_copy = QPushButton("📋 Copy")
        btn_copy.setProperty("class", "btn-secondary")
        btn_copy.setFixedHeight(22)
        btn_copy.setCursor(Qt.PointingHandCursor)

        def _copy():
            QGuiApplication.clipboard().setText(code_content)
            btn_copy.setText("✓ Copied!")

        btn_copy.clicked.connect(_copy)
        header_row.addWidget(btn_copy)
        box_layout.addLayout(header_row)

        code_lbl = QLabel(code_content)
        code_lbl.setFont(QFont("Consolas", 10))
        code_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        code_lbl.setStyleSheet("color: #E2E8F0; background-color: transparent; padding: 4px; line-height: 1.4;")
        box_layout.addWidget(code_lbl)

        self.layout.addWidget(box)

    def _open_pdf(self, filename: str):
        """Open generated PDF file in default OS PDF viewer."""
        pdf_path = get_exports_dir() / filename
        if pdf_path.exists():
            if sys.platform == "win32":
                os.startfile(str(pdf_path))
            elif sys.platform == "darwin":
                import subprocess
                subprocess.run(["open", str(pdf_path)])
            else:
                import subprocess
                subprocess.run(["xdg-open", str(pdf_path)])



class AIWorkerThread(QThread):
    """Background worker to query assistant off the GUI thread."""

    response_ready = Signal(dict)

    def __init__(self, user_text: str):
        super().__init__()
        self._user_text = user_text

    def run(self):
        assistant = get_assistant()
        result = assistant.process_input(self._user_text)
        self.response_ready.emit(result)


class ChatPanelWidget(QWidget):
    """Main assistant interaction view."""

    wake_requested = Signal()
    sleep_requested = Signal()
    ptt_requested = Signal()
    ai_response_generated = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: AIWorkerThread | None = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        # 1. Top HUD Header: Orb + State Details + Wake/Sleep Switch
        hud_header = QFrame()
        hud_header.setProperty("class", "hud-card")
        hud_layout = QHBoxLayout(hud_header)
        hud_layout.setContentsMargins(18, 12, 18, 12)
        hud_layout.setSpacing(20)

        # Reactive Orb
        self.orb = AIOrbWidget(self)
        self.orb.clicked.connect(self._toggle_wake_sleep)
        hud_layout.addWidget(self.orb)

        # Identity & State Text Box
        info_box = QVBoxLayout()
        info_box.setSpacing(4)

        title = QLabel("ZERO // DESKTOP CORE")
        title.setStyleSheet("color: #FFFFFF; font-size: 16px; font-weight: 800; letter-spacing: 2px;")
        info_box.addWidget(title)

        state_row = QHBoxLayout()
        state_tag = QLabel("SYSTEM STATE:")
        state_tag.setStyleSheet("color: #8A8A8A; font-size: 11px; font-weight: bold;")
        self.state_label = QLabel("SLEEPING")
        self.state_label.setStyleSheet("color: #00FF88; font-size: 12px; font-weight: bold; letter-spacing: 1px;")
        state_row.addWidget(state_tag)
        state_row.addWidget(self.state_label)
        state_row.addStretch()
        info_box.addLayout(state_row)

        self.activity_hint = QLabel("Tap orb or say 'Zero, wake up' to engage.")
        self.activity_hint.setStyleSheet("color: #6E7681; font-size: 11px; font-style: italic;")
        info_box.addWidget(self.activity_hint)

        hud_layout.addLayout(info_box)
        hud_layout.addStretch()

        # Wake / Sleep Button
        self.btn_wake_toggle = QPushButton("⚡  Wake Up")
        self.btn_wake_toggle.setProperty("class", "btn-primary")
        self.btn_wake_toggle.setFixedSize(130, 36)
        self.btn_wake_toggle.setCursor(Qt.PointingHandCursor)
        self.btn_wake_toggle.clicked.connect(self._toggle_wake_sleep)
        hud_layout.addWidget(self.btn_wake_toggle)

        layout.addWidget(hud_header)

        # 2. Scrollable Chat Transcript
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setObjectName("chat_scroll")

        self.chat_container = QWidget()
        self.chat_container.setObjectName("chat_container")
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setContentsMargins(10, 10, 10, 10)
        self.chat_layout.setSpacing(12)
        self.chat_layout.addStretch()

        self.scroll_area.setWidget(self.chat_container)
        layout.addWidget(self.scroll_area)

        # 3. Input Controls Bar
        input_bar = QFrame()
        input_bar.setProperty("class", "hud-card")
        ib_layout = QHBoxLayout(input_bar)
        ib_layout.setContentsMargins(12, 8, 12, 8)
        ib_layout.setSpacing(10)

        # Push to talk button
        self.btn_ptt = QPushButton("🎤  Voice")
        self.btn_ptt.setProperty("class", "btn-secondary")
        self.btn_ptt.setFixedSize(90, 36)
        self.btn_ptt.setCursor(Qt.PointingHandCursor)
        self.btn_ptt.clicked.connect(self.ptt_requested.emit)
        ib_layout.addWidget(self.btn_ptt)

        # Text input
        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("Enter command or query (e.g. 'give me today's briefing')...")
        self.text_input.setFixedHeight(36)
        self.text_input.returnPressed.connect(self.send_message)
        ib_layout.addWidget(self.text_input)

        # Send button
        self.btn_send = QPushButton("Send ➤")
        self.btn_send.setProperty("class", "btn-primary")
        self.btn_send.setFixedSize(90, 36)
        self.btn_send.setCursor(Qt.PointingHandCursor)
        self.btn_send.clicked.connect(self.send_message)
        ib_layout.addWidget(self.btn_send)

        layout.addWidget(input_bar)

        self.load_history()

    def update_assistant_state(self, state: AssistantState) -> None:
        """Update orb and visual state indicators."""
        self.orb.set_state(state)
        self.state_label.setText(state.value)

        if state == AssistantState.SLEEPING:
            self.state_label.setStyleSheet("color: #8A8A8A; font-size: 12px; font-weight: bold;")
            self.btn_wake_toggle.setText("⚡  Wake Up")
            self.activity_hint.setText("Assistant is sleeping. Click Wake or say 'Zero, wake up'.")
        elif state == AssistantState.READY:
            self.state_label.setStyleSheet("color: #00FF88; font-size: 12px; font-weight: bold;")
            self.btn_wake_toggle.setText("🌙  Sleep")
            self.activity_hint.setText("Zero is ready and standing by.")
        elif state == AssistantState.THINKING:
            self.state_label.setStyleSheet("color: #00E5FF; font-size: 12px; font-weight: bold;")
            self.activity_hint.setText("Processing query through neural provider...")
        elif state == AssistantState.LISTENING:
            self.state_label.setStyleSheet("color: #00FFC8; font-size: 12px; font-weight: bold;")
            self.activity_hint.setText("Listening to audio stream...")
        elif state == AssistantState.SPEAKING:
            self.state_label.setStyleSheet("color: #00FF88; font-size: 12px; font-weight: bold;")
            self.activity_hint.setText("Audio synthesis playback active.")
        elif state == AssistantState.ERROR:
            self.state_label.setStyleSheet("color: #FF4757; font-size: 12px; font-weight: bold;")
            self.activity_hint.setText("An issue occurred with the last operation.")

    def _toggle_wake_sleep(self):
        assistant = get_assistant()
        if assistant.state_manager.current_state == AssistantState.SLEEPING:
            self.wake_requested.emit()
        else:
            self.sleep_requested.emit()

    def add_message(self, role: str, content: str, timestamp_str: str = ""):
        """Add message bubble to scroll area and autoscroll to bottom."""
        bubble = MessageBubble(role=role, content=content, timestamp_str=timestamp_str)
        # Insert before stretch
        count = self.chat_layout.count()
        self.chat_layout.insertWidget(count - 1, bubble)

        # Scroll to bottom smoothly
        self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum() + 100
        )

    def send_message(self):
        """Submit text input to assistant in background."""
        text = self.text_input.text().strip()
        if not text:
            return

        self.text_input.clear()
        self.add_message("user", text)

        # Launch background AI worker
        self._worker = AIWorkerThread(text)
        self._worker.response_ready.connect(self._handle_ai_response)
        self._worker.start()

    def _handle_ai_response(self, result: dict):
        reply = result.get("reply_text", "")
        self.add_message("assistant", reply)
        self.ai_response_generated.emit(reply)

    def load_history(self):
        """Load messages from database for active conversation."""
        assistant = get_assistant()
        conv_id = assistant.active_conversation_id
        if not conv_id:
            return

        messages = ConversationStore.get_messages(conv_id, limit=50)
        for m in messages:
            ts = m["created_at"][11:19]
            self.add_message(m["role"], m["content"], timestamp_str=ts)
