"""
Zero AI Live Caption & Voice HUD Window.
Provides a modern, real-time desktop caption interface:
- State indicator badge: LISTENING, HEARING YOU, PROCESSING, SPEAKING, INTERRUPTED, ERROR.
- Real-time live caption box updating continuously as speech arrives.
- Full scrollable transcript history with syntax-highlighted code blocks, headings, and citations.
- Barge-in interrupt controls and manual microphone fallback.
"""

import html
import logging
import markdown
from PySide6.QtCore import Qt, Signal, Slot, QTimer
from PySide6.QtGui import QColor, QFont, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from app.core.state_manager import AssistantState

logger = logging.getLogger(__name__)


class LiveCaptionWindow(QMainWindow):
    """
    Dedicated real-time caption HUD for continuous voice interaction.
    Displays live partial speech, finalized turns, complete answers, and state transitions.
    """

    state_updated = Signal(str, str)
    partial_caption_updated = Signal(str)
    final_transcript_ready = Signal(str)
    assistant_reply_ready = Signal(str, str)
    error_occurred = Signal(str)

    def __init__(self, on_user_submit=None, on_stop_speaking=None, on_toggle_mute=None):
        super().__init__()
        self.setWindowTitle("ZERO AI — Live Captions & Voice HUD")
        self.resize(850, 680)
        self.setMinimumSize(600, 480)

        self._on_user_submit = on_user_submit
        self._on_stop_speaking = on_stop_speaking
        self._on_toggle_mute = on_toggle_mute

        self._is_muted = False
        self._current_state = AssistantState.LISTENING

        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        """Construct modern HUD layout with rich aesthetics."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0A0E17;
            }
            QWidget {
                color: #E2E8F0;
                font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
            }
        """)

        central = QWidget(self)
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(18, 18, 18, 18)
        root_layout.setSpacing(12)

        # 1. Header Bar: Title, Status Badge, State Subtitle
        header_bar = QHBoxLayout()
        header_bar.setSpacing(12)

        title_label = QLabel("ZERO AI")
        title_label.setStyleSheet("font-size: 20px; font-weight: 800; color: #00E5FF; letter-spacing: 1.5px;")
        header_bar.addWidget(title_label)

        sub_title = QLabel("LIVE CAPTIONS & VOICE HUD")
        sub_title.setStyleSheet("font-size: 11px; font-weight: 600; color: #64748B; letter-spacing: 1px;")
        header_bar.addWidget(sub_title)

        header_bar.addStretch()

        # State Pill Badge
        self.state_badge = QLabel("LISTENING")
        self.state_badge.setAlignment(Qt.AlignCenter)
        self.state_badge.setFixedHeight(28)
        self.state_badge.setStyleSheet("""
            background-color: #0F172A;
            color: #00E5FF;
            font-size: 12px;
            font-weight: 700;
            padding: 4px 14px;
            border-radius: 14px;
            border: 1px solid #00E5FF;
            letter-spacing: 0.8px;
        """)
        header_bar.addWidget(self.state_badge)
        root_layout.addLayout(header_bar)

        # 2. State Subtitle / Diagnostic Banner
        self.status_banner = QLabel("Microphone active — speak naturally anytime")
        self.status_banner.setStyleSheet("font-size: 12px; color: #94A3B8; margin-left: 2px;")
        root_layout.addWidget(self.status_banner)

        # 3. Real-Time Live Caption Area
        caption_box = QFrame()
        caption_box.setStyleSheet("""
            QFrame {
                background-color: #0F172A;
                border: 1px solid #1E293B;
                border-left: 4px solid #00E5FF;
                border-radius: 8px;
                padding: 10px 14px;
            }
        """)
        caption_layout = QVBoxLayout(caption_box)
        caption_layout.setContentsMargins(8, 8, 8, 8)
        caption_layout.setSpacing(4)

        caption_header = QLabel("LIVE SPEECH CAPTION")
        caption_header.setStyleSheet("font-size: 10px; font-weight: 700; color: #00E5FF; letter-spacing: 1px;")
        caption_layout.addWidget(caption_header)

        self.live_caption_text = QLabel("Listening...")
        self.live_caption_text.setWordWrap(True)
        self.live_caption_text.setStyleSheet("""
            font-size: 15px;
            font-weight: 500;
            color: #F8FAFC;
            min-height: 38px;
        """)
        caption_layout.addWidget(self.live_caption_text)
        root_layout.addWidget(caption_box)

        # 4. Scrollable Full Transcript History
        transcript_header = QLabel("CONVERSATION TRANSCRIPT")
        transcript_header.setStyleSheet("font-size: 11px; font-weight: 700; color: #64748B; letter-spacing: 1px; margin-top: 4px;")
        root_layout.addWidget(transcript_header)

        self.transcript_browser = QTextBrowser()
        self.transcript_browser.setOpenExternalLinks(True)
        self.transcript_browser.setStyleSheet("""
            QTextBrowser {
                background-color: #0B1120;
                border: 1px solid #1E293B;
                border-radius: 8px;
                padding: 14px;
                color: #CBD5E1;
                font-size: 13px;
                line-height: 1.5;
            }
            QScrollBar:vertical {
                background: #0B1120;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #1E293B;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #00E5FF;
            }
        """)
        root_layout.addWidget(self.transcript_browser, stretch=1)

        # 5. Bottom Control Bar (Input + Buttons)
        bottom_bar = QHBoxLayout()
        bottom_bar.setSpacing(8)

        # Text input fallback
        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("Type a question or command (or speak aloud)...")
        self.text_input.setStyleSheet("""
            QLineEdit {
                background-color: #0F172A;
                border: 1px solid #1E293B;
                border-radius: 6px;
                padding: 8px 12px;
                color: #F8FAFC;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #00E5FF;
            }
        """)
        self.text_input.returnPressed.connect(self._handle_manual_submit)
        bottom_bar.addWidget(self.text_input, stretch=1)

        # Send Button
        self.send_btn = QPushButton("Send")
        self.send_btn.setStyleSheet("""
            QPushButton {
                background-color: #00E5FF;
                color: #0A0E17;
                font-weight: 700;
                border: none;
                border-radius: 6px;
                padding: 8px 18px;
            }
            QPushButton:hover {
                background-color: #38BDF8;
            }
        """)
        self.send_btn.clicked.connect(self._handle_manual_submit)
        bottom_bar.addWidget(self.send_btn)

        # Mute Button
        self.mute_btn = QPushButton("🎤 Mute")
        self.mute_btn.setStyleSheet("""
            QPushButton {
                background-color: #1E293B;
                color: #94A3B8;
                font-weight: 600;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 8px 14px;
            }
            QPushButton:hover {
                color: #F8FAFC;
                border-color: #64748B;
            }
        """)
        self.mute_btn.clicked.connect(self._handle_toggle_mute)
        bottom_bar.addWidget(self.mute_btn)

        # Interrupt / Stop Speaking Button
        self.stop_btn = QPushButton("⏹ Stop")
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #1E293B;
                color: #EF4444;
                font-weight: 600;
                border: 1px solid #EF4444;
                border-radius: 6px;
                padding: 8px 14px;
            }
            QPushButton:hover {
                background-color: #EF4444;
                color: #FFFFFF;
            }
        """)
        self.stop_btn.clicked.connect(self._handle_stop_speaking)
        bottom_bar.addWidget(self.stop_btn)

        root_layout.addLayout(bottom_bar)

    def _connect_signals(self):
        """Bind Qt signals to slot methods for thread safety."""
        self.state_updated.connect(self.on_state_updated)
        self.partial_caption_updated.connect(self.on_partial_caption_updated)
        self.final_transcript_ready.connect(self.on_final_transcript_ready)
        self.assistant_reply_ready.connect(self.on_assistant_reply_ready)
        self.error_occurred.connect(self.on_error_occurred)

    # =========================================================================
    # Slot Implementations (Thread-Safe UI Updates)
    # =========================================================================

    @Slot(str, str)
    def on_state_updated(self, state_str: str, reason: str):
        """Update status badge color, text, and descriptive subtitle."""
        clean_state = state_str.upper()

        badge_styles = {
            "LISTENING": "background-color: #0F172A; color: #00E5FF; border: 1px solid #00E5FF;",
            "HEARING YOU": "background-color: #064E3B; color: #34D399; border: 1px solid #10B981;",
            "CAPTURING": "background-color: #064E3B; color: #34D399; border: 1px solid #10B981;",
            "PROCESSING": "background-color: #78350F; color: #FBBF24; border: 1px solid #F59E0B;",
            "THINKING": "background-color: #78350F; color: #FBBF24; border: 1px solid #F59E0B;",
            "SPEAKING": "background-color: #4C1D95; color: #C084FC; border: 1px solid #8B5CF6;",
            "INTERRUPTED": "background-color: #7F1D1D; color: #F87171; border: 1px solid #EF4444;",
            "ERROR": "background-color: #7F1D1D; color: #FCA5A5; border: 1px solid #DC2626;",
            "SLEEPING": "background-color: #1E293B; color: #94A3B8; border: 1px solid #475569;",
            "READY": "background-color: #0F172A; color: #38BDF8; border: 1px solid #38BDF8;",
        }

        style = badge_styles.get(clean_state, badge_styles["LISTENING"])
        self.state_badge.setText(clean_state)
        self.state_badge.setStyleSheet(f"""
            font-size: 12px;
            font-weight: 700;
            padding: 4px 14px;
            border-radius: 14px;
            letter-spacing: 0.8px;
            {style}
        """)

        # Update subtitle notice
        if clean_state in ("LISTENING", "READY"):
            self.status_banner.setText("Microphone active — speak naturally anytime")
            self.status_banner.setStyleSheet("font-size: 12px; color: #94A3B8;")
            self.live_caption_text.setText("Listening...")
            self.live_caption_text.setStyleSheet("font-size: 15px; font-weight: 500; color: #64748B;")
        elif clean_state in ("HEARING YOU", "CAPTURING"):
            self.status_banner.setText("Hearing speech stream — keep speaking...")
            self.status_banner.setStyleSheet("font-size: 12px; color: #34D399;")
            self.live_caption_text.setStyleSheet("font-size: 16px; font-weight: 600; color: #00E5FF;")
        elif clean_state in ("PROCESSING", "THINKING"):
            self.status_banner.setText("Processing with local AI model...")
            self.status_banner.setStyleSheet("font-size: 12px; color: #FBBF24;")
        elif clean_state == "SPEAKING":
            self.status_banner.setText("Speaking aloud — barge-in enabled (speak anytime to interrupt)")
            self.status_banner.setStyleSheet("font-size: 12px; color: #C084FC;")
        elif clean_state == "INTERRUPTED":
            self.status_banner.setText("Speech interrupted by user. Capturing your voice...")
            self.status_banner.setStyleSheet("font-size: 12px; color: #F87171;")
        elif clean_state == "ERROR":
            self.status_banner.setText(f"Notice: {reason}" if reason else "An error occurred.")
            self.status_banner.setStyleSheet("font-size: 12px; color: #EF4444;")

    @Slot(str)
    def on_partial_caption_updated(self, partial_text: str):
        """Update live speech caption as intermediate words arrive."""
        if partial_text:
            self.live_caption_text.setText(partial_text)
            self.live_caption_text.setStyleSheet("font-size: 16px; font-weight: 600; color: #00E5FF;")

    @Slot(str)
    def on_final_transcript_ready(self, final_text: str):
        """Render finalized user utterance in transcript history."""
        self.live_caption_text.setText(f"You: {final_text}")
        self.live_caption_text.setStyleSheet("font-size: 15px; font-weight: 600; color: #34D399;")
        self._append_message("user", final_text)

    @Slot(str, str)
    def on_assistant_reply_ready(self, reply_text: str, spoken_text: str):
        """Render complete assistant response with rich Markdown formatting."""
        self._append_message("assistant", reply_text)

    @Slot(str)
    def on_error_occurred(self, error_message: str):
        """Render error banner."""
        self.status_banner.setText(f"Error: {error_message}")
        self.status_banner.setStyleSheet("font-size: 12px; color: #EF4444;")

    # =========================================================================
    # Transcript Formatting & Appending
    # =========================================================================

    def _append_message(self, role: str, content: str):
        """Render message into HTML transcript browser."""
        if role == "user":
            html_block = f"""
            <div style="margin-top: 10px; margin-bottom: 8px;">
                <span style="color: #00E5FF; font-weight: bold; font-size: 12px;">YOU</span>
                <div style="background-color: #1E293B; border-radius: 6px; padding: 10px 14px; margin-top: 4px; color: #F8FAFC;">
                    {html.escape(content)}
                </div>
            </div>
            """
        else:
            # Render Markdown into HTML
            rendered_md = markdown.markdown(
                content,
                extensions=["fenced_code", "tables", "nl2br"],
            )
            html_block = f"""
            <div style="margin-top: 12px; margin-bottom: 14px;">
                <span style="color: #C084FC; font-weight: bold; font-size: 12px;">ZERO</span>
                <div style="background-color: #0F172A; border-left: 3px solid #8B5CF6; border-radius: 4px; padding: 12px 16px; margin-top: 4px; color: #E2E8F0;">
                    {rendered_md}
                </div>
            </div>
            """

        self.transcript_browser.append(html_block)
        # Scroll to bottom
        scrollbar = self.transcript_browser.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    # =========================================================================
    # User Interactions
    # =========================================================================

    def _handle_manual_submit(self):
        """Submit text from input box."""
        text = self.text_input.text().strip()
        if not text:
            return
        self.text_input.clear()
        self.on_final_transcript_ready(text)
        if self._on_user_submit:
            self._on_user_submit(text)

    def _handle_stop_speaking(self):
        """Interrupt active speech playback."""
        if self._on_stop_speaking:
            self._on_stop_speaking()
        self.on_state_updated("INTERRUPTED", "Stopped by user button")

    def _handle_toggle_mute(self):
        """Toggle microphone mute."""
        if self._on_toggle_mute:
            new_state = self._on_toggle_mute()
            self._is_muted = new_state
            if self._is_muted:
                self.mute_btn.setText("🔇 Unmute")
                self.mute_btn.setStyleSheet("background-color: #7F1D1D; color: #F87171; border: 1px solid #EF4444; border-radius: 6px; padding: 8px 14px;")
                self.status_banner.setText("Microphone MUTED. Tap Unmute or type a message.")
            else:
                self.mute_btn.setText("🎤 Mute")
                self.mute_btn.setStyleSheet("background-color: #1E293B; color: #94A3B8; border: 1px solid #334155; border-radius: 6px; padding: 8px 14px;")
                self.status_banner.setText("Microphone active — speak naturally anytime")
