"""
Zero AI — Live Voice Transcript & Code Intelligence (Obsidian Command).
Implements the dual-pane transcript and code intelligence workspace:
- Top Header: Activity filter tabs, search dialogue history (Ctrl+F), PDF export, clear buffer.
- Left Pane (7 cols): Dialogue transcript stream with operator input, assistant audio responses,
  Listen Again button, interruption cards, and tool execution logs.
- Right Pane (5 cols): Syntax-highlighted code container with line numbers, copy to clipboard,
  PDF summary, and safe supervised execution with confirmation dialog.
"""

from datetime import datetime
import os
import psutil
import re
import subprocess
import sys
from PySide6.QtCore import Qt, Signal, QThread, QTimer
from PySide6.QtGui import QGuiApplication, QFont, QTextCursor
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QPlainTextEdit,
    QScrollArea,
    QFrame,
    QFileDialog,
    QMessageBox,
    QButtonGroup,
)
import markdown

from app.config.settings import get_settings
from app.core.assistant import get_assistant
from app.core.state_manager import AssistantState
from app.gui.theme import (
    CANVAS_BG,
    SURFACE_PANEL,
    CONTAINER_BG,
    CONTAINER_LOWEST,
    CONTAINER_HIGH,
    BORDER_SUBTLE,
    ACCENT_NEON,
    ACCENT_WARNING,
    ACCENT_CRITICAL,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_DIM,
)
from app.memory.activity_store import ActivityStore
from app.memory.conversation_store import ConversationStore
from app.exports.pdf_generator import PDFGenerator


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


class TranscriptItemCard(QFrame):
    """Render a single turn or event inside the dialogue stream."""

    listen_again_requested = Signal(str)

    def __init__(
        self,
        item_type: str,  # "user", "assistant", "interrupt", "tool"
        content: str,
        timestamp_str: str = "",
        metadata: dict | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.item_type = item_type
        self.content = content
        self.timestamp_str = timestamp_str or datetime.now().strftime("%H:%M:%S")
        self.metadata = metadata or {}

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        if self.item_type == "user":
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: {CONTAINER_BG};
                    border: 1px solid {BORDER_SUBTLE};
                    border-radius: 4px;
                }}
            """)
            hdr = QHBoxLayout()
            dot = QLabel("■")
            dot.setStyleSheet(f"color: {ACCENT_NEON}; font-size: 10px;")
            title = QLabel("OPERATOR [VOICE INPUT]")
            title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-family: 'Consolas', monospace; font-weight: bold; font-size: 11px;")
            ts = QLabel(self.timestamp_str)
            ts.setStyleSheet(f"color: {TEXT_DIM}; font-family: 'Consolas', monospace; font-size: 10px;")

            hdr.addWidget(dot)
            hdr.addWidget(title)
            hdr.addStretch()
            hdr.addWidget(ts)
            layout.addLayout(hdr)

            body = QLabel(self.content)
            body.setWordWrap(True)
            body.setTextInteractionFlags(Qt.TextSelectableByMouse)
            body.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 12px; padding-left: 6px; border-left: 2px solid {ACCENT_NEON};")
            layout.addWidget(body)

        elif self.item_type == "interrupt":
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: #1A0D0D;
                    border: 1px solid {ACCENT_CRITICAL};
                    border-radius: 4px;
                }}
            """)
            hdr = QHBoxLayout()
            tag = QLabel("[SPEECH INTERRUPTED BY OPERATOR]")
            tag.setStyleSheet(f"color: {ACCENT_CRITICAL}; font-family: 'Consolas', monospace; font-weight: bold; font-size: 10px;")
            ts = QLabel(self.timestamp_str)
            ts.setStyleSheet(f"color: {TEXT_DIM}; font-family: 'Consolas', monospace; font-size: 10px;")
            hdr.addWidget(tag)
            hdr.addStretch()
            hdr.addWidget(ts)
            layout.addLayout(hdr)

            body = QLabel(self.content)
            body.setWordWrap(True)
            body.setTextInteractionFlags(Qt.TextSelectableByMouse)
            body.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 12px; padding-left: 6px; border-left: 2px solid {ACCENT_CRITICAL};")
            layout.addWidget(body)

        elif self.item_type == "tool":
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: {CONTAINER_LOWEST};
                    border: 1px solid {BORDER_SUBTLE};
                    border-radius: 4px;
                }}
            """)
            hdr = QHBoxLayout()
            tag = QLabel("⚙  TOOL EXECUTION // RESULT")
            tag.setStyleSheet(f"color: {ACCENT_WARNING}; font-family: 'Consolas', monospace; font-weight: bold; font-size: 10px;")
            ts = QLabel(self.timestamp_str)
            ts.setStyleSheet(f"color: {TEXT_DIM}; font-family: 'Consolas', monospace; font-size: 10px;")
            hdr.addWidget(tag)
            hdr.addStretch()
            hdr.addWidget(ts)
            layout.addLayout(hdr)

            body = QLabel(self.content)
            body.setWordWrap(True)
            body.setTextInteractionFlags(Qt.TextSelectableByMouse)
            body.setStyleSheet(f"color: {TEXT_SECONDARY}; font-family: 'Consolas', monospace; font-size: 11px;")
            layout.addWidget(body)

        else:  # "assistant"
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: {CONTAINER_LOWEST};
                    border: 1px solid {BORDER_SUBTLE};
                    border-left: 2px solid {ACCENT_NEON};
                    border-radius: 4px;
                }}
            """)
            hdr = QHBoxLayout()
            model_tag = self.metadata.get("model", get_settings().ollama_model_chat)
            title = QLabel(f"Z.E.R.O. [{model_tag.upper()}]")
            title.setStyleSheet(f"color: {ACCENT_NEON}; font-family: 'Consolas', monospace; font-weight: bold; font-size: 11px;")

            chip = QLabel("SYNTH: OK")
            chip.setStyleSheet(f"""
                background-color: {CONTAINER_BG};
                color: {ACCENT_NEON};
                border: 1px solid {BORDER_SUBTLE};
                border-radius: 2px;
                padding: 1px 4px;
                font-family: 'Consolas', monospace;
                font-size: 9px;
            """)

            btn_listen = QPushButton("🔊 Listen Again")
            btn_listen.setCursor(Qt.PointingHandCursor)
            btn_listen.setToolTip("Replay speech synthesis for this response")
            btn_listen.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {TEXT_SECONDARY};
                    border: none;
                    font-size: 11px;
                }}
                QPushButton:hover {{
                    color: {ACCENT_NEON};
                }}
            """)
            btn_listen.clicked.connect(lambda: self.listen_again_requested.emit(self.content))

            ts = QLabel(self.timestamp_str)
            ts.setStyleSheet(f"color: {TEXT_DIM}; font-family: 'Consolas', monospace; font-size: 10px;")

            hdr.addWidget(title)
            hdr.addWidget(chip)
            hdr.addStretch()
            hdr.addWidget(btn_listen)
            hdr.addWidget(ts)
            layout.addLayout(hdr)

            # Markdown-rendered text
            html = markdown.markdown(self.content, extensions=["tables", "nl2br", "sane_lists"])
            body = QLabel(html)
            body.setWordWrap(True)
            body.setTextFormat(Qt.RichText)
            body.setTextInteractionFlags(Qt.TextSelectableByMouse)
            body.setOpenExternalLinks(True)
            body.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 12px; line-height: 1.4;")
            layout.addWidget(body)

            # Telemetry mini subpanel
            sub_metrics = QHBoxLayout()
            sub_metrics.setSpacing(6)

            m1 = QLabel("DAEMON: ONLINE")
            m1.setStyleSheet(f"background-color: {CONTAINER_BG}; color: {ACCENT_NEON}; border: 1px solid {BORDER_SUBTLE}; padding: 2px 6px; font-family: monospace; font-size: 9px;")
            m2 = QLabel(f"THREADS: {psutil.cpu_count(logical=True)} ACTIVE")
            m2.setStyleSheet(f"background-color: {CONTAINER_BG}; color: {TEXT_SECONDARY}; border: 1px solid {BORDER_SUBTLE}; padding: 2px 6px; font-family: monospace; font-size: 9px;")
            sub_metrics.addWidget(m1)
            sub_metrics.addWidget(m2)
            sub_metrics.addStretch()
            layout.addLayout(sub_metrics)


class TranscriptCodeWidget(QWidget):
    """
    Split view workspace implementing Stitch screen 2 (Obsidian Command).
    """

    ptt_requested = Signal()
    ai_response_generated = Signal(str)
    speak_replay_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("transcript_code_view")

        self._active_filter = "all"  # "all", "speech", "code", "tools"
        self._items: list[TranscriptItemCard] = []
        self._worker: AIWorkerThread | None = None
        self._current_code: str = ""
        self._current_code_filename: str = "script.py"

        self._init_ui()
        self.load_history()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # =====================================================================
        # TOP TOOLBAR: Filter Segmented Tabs, Search & Action Buttons
        # =====================================================================
        top_bar = QFrame()
        top_bar.setFixedHeight(42)
        top_bar.setStyleSheet(f"background-color: {CONTAINER_LOWEST}; border-bottom: 1px solid {BORDER_SUBTLE};")
        tb_layout = QHBoxLayout(top_bar)
        tb_layout.setContentsMargins(14, 0, 14, 0)
        tb_layout.setSpacing(12)

        # 1. Filter Tabs
        self.filter_group = QButtonGroup(self)
        self.filter_group.setExclusive(True)

        self.tab_all = self._create_filter_tab("All Activity", "all", active=True)
        self.tab_speech = self._create_filter_tab("Speech Only", "speech")
        self.tab_code = self._create_filter_tab("Code Outputs", "code")
        self.tab_tools = self._create_filter_tab("Tool Executions", "tools")

        tab_container = QWidget()
        tc_layout = QHBoxLayout(tab_container)
        tc_layout.setContentsMargins(0, 0, 0, 0)
        tc_layout.setSpacing(2)
        tc_layout.addWidget(self.tab_all)
        tc_layout.addWidget(self.tab_speech)
        tc_layout.addWidget(self.tab_code)
        tc_layout.addWidget(self.tab_tools)
        tb_layout.addWidget(tab_container)

        # 2. Search dialogue input (Ctrl+F)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Ctrl+F Search dialogue history...")
        self.search_input.setFixedWidth(260)
        self.search_input.setFixedHeight(28)
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {CONTAINER_BG};
                color: {TEXT_PRIMARY};
                border: 1px solid {BORDER_SUBTLE};
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
            }}
            QLineEdit:focus {{
                border: 1px solid {ACCENT_NEON};
            }}
        """)
        self.search_input.textChanged.connect(self._apply_search_filter)
        tb_layout.addWidget(self.search_input)

        tb_layout.addStretch()

        # 3. Action Buttons: Export to PDF & Clear Buffer
        self.btn_export_pdf = QPushButton("📄  Export Conversation to PDF")
        self.btn_export_pdf.setCursor(Qt.PointingHandCursor)
        self.btn_export_pdf.setProperty("class", "btn-secondary")
        self.btn_export_pdf.setFixedHeight(28)
        self.btn_export_pdf.clicked.connect(self._handle_export_conversation_pdf)
        tb_layout.addWidget(self.btn_export_pdf)

        self.btn_clear_buffer = QPushButton("🗑️  Clear Buffer")
        self.btn_clear_buffer.setCursor(Qt.PointingHandCursor)
        self.btn_clear_buffer.setProperty("class", "btn-secondary")
        self.btn_clear_buffer.setFixedHeight(28)
        self.btn_clear_buffer.clicked.connect(self._handle_clear_buffer)
        tb_layout.addWidget(self.btn_clear_buffer)

        main_layout.addWidget(top_bar)

        # =====================================================================
        # SPLIT VIEW: Left Dialogue Stream (7 cols) + Right Code Viewer (5 cols)
        # =====================================================================
        split_layout = QHBoxLayout()
        split_layout.setContentsMargins(0, 0, 0, 0)
        split_layout.setSpacing(0)

        # LEFT PANE: Transcript Stream
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(12, 10, 12, 10)
        left_layout.setSpacing(8)

        # Meta Header
        stream_meta = QHBoxLayout()
        self.lbl_session_meta = QLabel("SESSION_ID: #LOCAL-STREAM")
        self.lbl_session_meta.setStyleSheet(f"color: {TEXT_DIM}; font-family: 'Consolas', monospace; font-size: 10px;")
        lbl_ring = QLabel("BUFFER: PERSISTED SQLITE")
        lbl_ring.setStyleSheet(f"color: {TEXT_DIM}; font-family: 'Consolas', monospace; font-size: 10px;")
        stream_meta.addWidget(self.lbl_session_meta)
        stream_meta.addStretch()
        stream_meta.addWidget(lbl_ring)
        left_layout.addLayout(stream_meta)

        # Scroll Area for Transcript Cards
        self.transcript_scroll = QScrollArea()
        self.transcript_scroll.setWidgetResizable(True)
        self.transcript_scroll.setStyleSheet("background: transparent; border: none;")

        self.transcript_box = QWidget()
        self.transcript_box_layout = QVBoxLayout(self.transcript_box)
        self.transcript_box_layout.setContentsMargins(0, 0, 0, 0)
        self.transcript_box_layout.setSpacing(8)
        self.transcript_scroll.setWidget(self.transcript_box)
        left_layout.addWidget(self.transcript_scroll, stretch=1)

        # Bottom Prompt Input Dock
        input_dock = QFrame()
        input_dock.setFixedHeight(48)
        input_dock.setStyleSheet(f"background-color: {CONTAINER_BG}; border: 1px solid {BORDER_SUBTLE}; border-radius: 4px;")
        id_layout = QHBoxLayout(input_dock)
        id_layout.setContentsMargins(10, 4, 10, 4)
        id_layout.setSpacing(8)

        lbl_prompt = QLabel(">")
        lbl_prompt.setStyleSheet(f"color: {ACCENT_NEON}; font-family: 'Consolas', monospace; font-weight: bold; font-size: 14px;")
        id_layout.addWidget(lbl_prompt)

        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("Enter command or question for Z.E.R.O. ...")
        self.text_input.setStyleSheet("background: transparent; border: none; color: #F5F7F6; font-size: 13px;")
        self.text_input.returnPressed.connect(self.send_message)
        id_layout.addWidget(self.text_input, stretch=1)

        self.btn_ptt = QPushButton("🎤 Mic")
        self.btn_ptt.setCursor(Qt.PointingHandCursor)
        self.btn_ptt.setProperty("class", "btn-secondary")
        self.btn_ptt.setFixedHeight(30)
        self.btn_ptt.clicked.connect(self.ptt_requested.emit)
        id_layout.addWidget(self.btn_ptt)

        self.btn_send = QPushButton("Send")
        self.btn_send.setCursor(Qt.PointingHandCursor)
        self.btn_send.setProperty("class", "btn-primary")
        self.btn_send.setFixedHeight(30)
        self.btn_send.clicked.connect(self.send_message)
        id_layout.addWidget(self.btn_send)

        left_layout.addWidget(input_dock)

        split_layout.addWidget(left_container, stretch=7)

        # Pane Divider
        v_div = QFrame()
        v_div.setFrameShape(QFrame.VLine)
        v_div.setStyleSheet(f"background-color: {BORDER_SUBTLE}; max-width: 1px;")
        split_layout.addWidget(v_div)

        # RIGHT PANE: Code & Artifact Viewer
        right_container = QWidget()
        right_container.setStyleSheet(f"background-color: #080C0A;")
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(12, 10, 12, 10)
        right_layout.setSpacing(8)

        # Code Header Bar
        code_hdr = QHBoxLayout()
        code_hdr.setSpacing(8)

        self.lbl_code_title = QLabel("system_telemetry_watcher.py")
        self.lbl_code_title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-family: 'Consolas', monospace; font-weight: bold; font-size: 12px;")
        code_hdr.addWidget(self.lbl_code_title)

        self.lbl_code_lang = QLabel("PYTHON 3.12")
        self.lbl_code_lang.setStyleSheet(f"""
            background-color: {CONTAINER_BG};
            color: {TEXT_DIM};
            border: 1px solid {BORDER_SUBTLE};
            border-radius: 2px;
            padding: 2px 6px;
            font-family: 'Consolas', monospace;
            font-size: 9px;
        """)
        code_hdr.addWidget(self.lbl_code_lang)
        code_hdr.addStretch()

        self.btn_code_pdf = QPushButton("PDF Summary")
        self.btn_code_pdf.setCursor(Qt.PointingHandCursor)
        self.btn_code_pdf.setProperty("class", "btn-secondary")
        self.btn_code_pdf.setFixedHeight(26)
        self.btn_code_pdf.clicked.connect(self._handle_code_pdf_summary)
        code_hdr.addWidget(self.btn_code_pdf)

        self.btn_code_copy = QPushButton("Copy")
        self.btn_code_copy.setCursor(Qt.PointingHandCursor)
        self.btn_code_copy.setProperty("class", "btn-secondary")
        self.btn_code_copy.setFixedHeight(26)
        self.btn_code_copy.clicked.connect(self._handle_code_copy)
        code_hdr.addWidget(self.btn_code_copy)

        self.btn_code_exec = QPushButton("Execute")
        self.btn_code_exec.setCursor(Qt.PointingHandCursor)
        self.btn_code_exec.setProperty("class", "btn-primary")
        self.btn_code_exec.setFixedHeight(26)
        self.btn_code_exec.setToolTip("Safely execute generated Python code under operator supervision")
        self.btn_code_exec.clicked.connect(self._handle_code_execute)
        code_hdr.addWidget(self.btn_code_exec)

        right_layout.addLayout(code_hdr)

        # Line-Numbered Code Editor View
        self.code_editor = QPlainTextEdit()
        self.code_editor.setReadOnly(True)
        self.code_editor.setFont(QFont("Consolas", 10))
        self.code_editor.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {CONTAINER_LOWEST};
                color: #C0C8C4;
                border: 1px solid {BORDER_SUBTLE};
                border-radius: 4px;
                padding: 10px;
                line-height: 1.4;
            }}
        """)
        right_layout.addWidget(self.code_editor, stretch=1)

        # Set default sample code
        default_script = (
            "# Z.E.R.O. Telemetry Watcher Module\n"
            "import os\n"
            "import psutil\n\n"
            "def inspect_workstation_health():\n"
            "    cpu = psutil.cpu_percent(interval=0.1)\n"
            "    mem = psutil.virtual_memory()\n"
            "    print(f'[HOST HEALTH] CPU Load: {cpu}% | RAM Used: {mem.percent}%')\n"
            "    return {'cpu': cpu, 'mem_percent': mem.percent}\n\n"
            "if __name__ == '__main__':\n"
            "    inspect_workstation_health()\n"
        )
        self.set_code_content(default_script, "telemetry_watcher.py", "PYTHON 3.12")

        split_layout.addWidget(right_container, stretch=5)

        main_layout.addLayout(split_layout, stretch=1)

    def _create_filter_tab(self, label: str, filter_id: str, active: bool = False) -> QPushButton:
        btn = QPushButton(label)
        btn.setProperty("class", "filter-tab")
        btn.setCheckable(True)
        btn.setChecked(active)
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(lambda: self._set_active_filter(filter_id))
        self.filter_group.addButton(btn)
        return btn

    def _set_active_filter(self, filter_id: str):
        self._active_filter = filter_id
        self._filter_items()

    def _filter_items(self):
        query = self.search_input.text().strip().lower()

        for card in self._items:
            matches_filter = True
            if self._active_filter == "speech":
                matches_filter = card.item_type in ("user", "assistant")
            elif self._active_filter == "code":
                matches_filter = "```" in card.content or card.item_type == "tool"
            elif self._active_filter == "tools":
                matches_filter = card.item_type == "tool"

            matches_search = True
            if query:
                matches_search = (query in card.content.lower()) or (query in card.timestamp_str.lower())

            card.setVisible(matches_filter and matches_search)

    def _apply_search_filter(self):
        self._filter_items()

    def add_message(
        self,
        role: str,
        content: str,
        timestamp_str: str = "",
        metadata: dict | None = None,
    ):
        """Add a message card to the dialogue stream and inspect for generated code."""
        # Detect if this message contains code blocks
        code_match = re.search(r"```([a-zA-Z0-9_\-]*)\n(.*?)```", content, re.DOTALL)
        if code_match and role.lower() == "assistant":
            lang = code_match.group(1).strip() or "PYTHON"
            extracted_code = code_match.group(2)
            self.set_code_content(extracted_code, f"zero_output_{datetime.now().strftime('%H%M%S')}.py", lang.upper())

        item_type = role.lower()
        if "interrupted" in content.lower():
            item_type = "interrupt"
        elif "[tool" in content.lower() or "tool execution" in content.lower():
            item_type = "tool"

        card = TranscriptItemCard(item_type, content, timestamp_str, metadata)
        card.listen_again_requested.connect(self._handle_listen_again)
        self._items.append(card)
        self.transcript_box_layout.addWidget(card)

        # Smart scroll to bottom
        QTimer.singleShot(50, self._scroll_to_bottom)

    def _scroll_to_bottom(self):
        scrollbar = self.transcript_scroll.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def set_code_content(self, code: str, filename: str = "script.py", language: str = "PYTHON 3.12"):
        """Populate the right code viewer panel."""
        self._current_code = code
        self._current_code_filename = filename
        self.lbl_code_title.setText(filename)
        self.lbl_code_lang.setText(language)

        # Prefix with line numbers
        lines = code.splitlines()
        formatted_lines = [f"{i+1:3d} | {line}" for i, line in enumerate(lines)]
        self.code_editor.setPlainText("\n".join(formatted_lines))

    def send_message(self):
        """Send operator prompt to local AI assistant."""
        text = self.text_input.text().strip()
        if not text:
            return

        self.text_input.clear()
        self.add_message("user", text)

        self.btn_send.setEnabled(False)
        self.text_input.setEnabled(False)

        self._worker = AIWorkerThread(text)
        self._worker.response_ready.connect(self._on_ai_response_ready)
        self._worker.start()

    def _on_ai_response_ready(self, result: dict):
        self.btn_send.setEnabled(True)
        self.text_input.setEnabled(True)
        self.text_input.setFocus()

        ans_text = result.get("text", "")
        self.add_message("assistant", ans_text)
        self.ai_response_generated.emit(ans_text)

    def _handle_listen_again(self, text: str):
        """Replay or synthesize text aloud."""
        clean_text = re.sub(r"```.*?```", "", text, flags=re.DOTALL).strip()
        self.speak_replay_requested.emit(clean_text)

    def _handle_code_copy(self):
        """Copy active code to clipboard."""
        if not self._current_code:
            return
        QGuiApplication.clipboard().setText(self._current_code)
        self.btn_code_copy.setText("✓ Copied!")
        QTimer.singleShot(1500, lambda: self.btn_code_copy.setText("Copy"))

    def _handle_code_pdf_summary(self):
        """Export current code artifact to a PDF report."""
        if not self._current_code:
            QMessageBox.information(self, "No Code", "No code artifact is currently loaded.")
            return

        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Code Summary to PDF",
            os.path.join(os.getcwd(), f"{self._current_code_filename}.pdf"),
            "PDF Files (*.pdf)",
        )
        if not save_path:
            return

        try:
            body = (
                f"# Code Artifact: {self._current_code_filename}\n\n"
                f"**Language:** `{self.lbl_code_lang.text()}`  \n"
                f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"```python\n{self._current_code}\n```\n"
            )
            html = PDFGenerator.create_html_report(
                title=f"Code Intelligence // {self._current_code_filename}",
                body_markdown=body,
                subtitle="Verified Model Generated Output",
            )
            out_pdf = PDFGenerator.generate_pdf(html, filename=os.path.basename(save_path))
            QMessageBox.information(self, "Export Succeeded", f"Code PDF summary saved to:\n{out_pdf}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export code PDF: {str(e)}")

    def _handle_code_execute(self):
        """Safely execute Python code in bounded subprocess after user confirmation."""
        if not self._current_code:
            QMessageBox.information(self, "No Code", "No code snippet available to execute.")
            return

        preview = self._current_code[:300] + ("..." if len(self._current_code) > 300 else "")
        reply = QMessageBox.warning(
            self,
            "Supervised Code Execution Preview",
            "SECURITY CONFIRMATION REQUIRED:\n\n"
            "You are requesting to execute the generated code in an isolated local Python subprocess with a strict 5.0-second timeout.\n\n"
            f"Code Preview:\n-----------------------------\n{preview}\n-----------------------------\n\n"
            "Do you authorize execution of this script?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        try:
            res = subprocess.run(
                [sys.executable, "-c", self._current_code],
                capture_output=True,
                text=True,
                timeout=5.0,
            )
            output = res.stdout or res.stderr or "[Execution completed with no stdout output]"
            if len(output) > 4000:
                output = output[:4000] + "\n[Output truncated at 4000 bytes]"

            status_str = "SUCCESS" if res.returncode == 0 else f"EXIT CODE {res.returncode}"
            self.add_message(
                "tool",
                f"Execution of '{self._current_code_filename}' ({status_str}):\n{output}",
            )
            ActivityStore.record_activity(
                category="EXECUTE",
                description=f"Executed script {self._current_code_filename} ({status_str})",
            )
        except subprocess.TimeoutExpired:
            self.add_message("tool", f"Execution of '{self._current_code_filename}' timed out after 5.0 seconds.")
            QMessageBox.warning(self, "Execution Timeout", "Execution timed out after 5.0 seconds.")
        except Exception as e:
            self.add_message("tool", f"Execution failed: {str(e)}")
            QMessageBox.critical(self, "Execution Failure", f"Failed to run script: {str(e)}")

    def _handle_export_conversation_pdf(self):
        """Export current transcript buffer to verified PDF document."""
        if not self._items:
            QMessageBox.information(self, "Empty Transcript", "Conversation buffer is empty.")
            return

        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Conversation to PDF",
            os.path.join(os.getcwd(), f"zero_dialogue_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"),
            "PDF Files (*.pdf)",
        )
        if not save_path:
            return

        try:
            lines = [
                f"# Z.E.R.O. Conversation Transcript\n",
                f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ",
                f"**Session:** {self.lbl_session_meta.text()}\n",
                "--------------------------------------------------\n",
            ]
            for item in self._items:
                sender = "OPERATOR" if item.item_type == "user" else "Z.E.R.O."
                lines.append(f"### {sender} ({item.timestamp_str})\n\n{item.content}\n")

            md_content = "\n".join(lines)
            html = PDFGenerator.create_html_report(
                title="Z.E.R.O. Dialogue Transcript",
                body_markdown=md_content,
                subtitle="Complete Multi-Turn Voice & Text Record",
            )
            out_pdf = PDFGenerator.generate_pdf(html, filename=os.path.basename(save_path))
            QMessageBox.information(self, "Export Succeeded", f"Transcript PDF saved to:\n{out_pdf}")
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Failed to export transcript: {str(e)}")

    def _handle_clear_buffer(self):
        """Clear the visual conversation buffer with confirmation."""
        reply = QMessageBox.question(
            self,
            "Clear Visual Buffer",
            "Are you sure you want to clear the visible dialogue buffer?\n\n"
            "NOTE: This clears only the currently rendered screen view.\n"
            "Your persistent conversation history and Knowledge files remain safely stored in the database.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            while self.transcript_box_layout.count():
                item = self.transcript_box_layout.takeAt(0)
                w = item.widget()
                if w:
                    w.deleteLater()
            self._items.clear()

    def load_history(self):
        """Load messages from active conversation store."""
        assistant = get_assistant()
        conv_id = assistant.active_conversation_id
        if not conv_id:
            return

        self.lbl_session_meta.setText(f"SESSION_ID: #{conv_id[:8].upper()}")
        messages = ConversationStore.get_messages(conv_id, limit=50)

        for m in messages:
            role = m.get("role", "assistant") if isinstance(m, dict) else getattr(m, "role", "assistant")
            content = m.get("content", "") if isinstance(m, dict) else getattr(m, "content", "")
            ts = m.get("created_at", "") if isinstance(m, dict) else str(getattr(m, "created_at", ""))
            if "T" in ts:
                ts_part = ts.split("T")[1][:8]
            else:
                ts_part = ts[:8]
            self.add_message(role, content, ts_part)
