"""
Zero AI — Slim 64px Functional Navigation Rail (Obsidian Command).
Provides tactile navigation between Command Center, Transcript & Code,
Knowledge Vault, System Control, Models, Diagnostics, and Settings.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QButtonGroup,
    QSpacerItem,
    QSizePolicy,
    QFrame,
)
from app.gui.theme import (
    SURFACE_PANEL,
    BORDER_SUBTLE,
    ACCENT_NEON,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_DIM,
)


class SidebarWidget(QWidget):
    """
    Slim 64px Navigation Rail matching the Stitch / Obsidian Command design spec.
    """

    navigate = Signal(str)
    new_conversation_clicked = Signal()
    toggle_mic_clicked = Signal()
    command_palette_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(64)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 10, 0, 10)
        layout.setSpacing(6)

        # 1. Operator Avatar / Identity (SYS.ROOT 01)
        avatar_btn = QPushButton("SYS")
        avatar_btn.setFixedSize(38, 38)
        avatar_btn.setCursor(Qt.PointingHandCursor)
        avatar_btn.setToolTip("SYS.ROOT // Operator Profile (New Session)")
        avatar_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #0B0F0D;
                color: {ACCENT_NEON};
                border: 1px solid {BORDER_SUBTLE};
                border-radius: 4px;
                font-family: 'Consolas', 'JetBrains Mono', monospace;
                font-weight: bold;
                font-size: 11px;
            }}
            QPushButton:hover {{
                border: 1px solid {ACCENT_NEON};
                background-color: #151A18;
            }}
        """)
        avatar_btn.clicked.connect(self.new_conversation_clicked.emit)

        lbl_sys = QLabel("ROOT")
        lbl_sys.setAlignment(Qt.AlignCenter)
        lbl_sys.setStyleSheet(f"color: {ACCENT_NEON}; font-family: 'Consolas', monospace; font-size: 8px; font-weight: bold;")

        lbl_id = QLabel("01")
        lbl_id.setAlignment(Qt.AlignCenter)
        lbl_id.setStyleSheet(f"color: {TEXT_DIM}; font-family: 'Consolas', monospace; font-size: 8px;")

        avatar_container = QWidget()
        av_layout = QVBoxLayout(avatar_container)
        av_layout.setContentsMargins(0, 0, 0, 4)
        av_layout.setSpacing(2)
        av_layout.setAlignment(Qt.AlignCenter)
        av_layout.addWidget(avatar_btn, alignment=Qt.AlignCenter)
        av_layout.addWidget(lbl_sys)
        av_layout.addWidget(lbl_id)
        layout.addWidget(avatar_container)

        # Divider
        div1 = QFrame()
        div1.setFrameShape(QFrame.HLine)
        div1.setStyleSheet(f"background-color: {BORDER_SUBTLE}; max-height: 1px; margin: 4px 6px;")
        layout.addWidget(div1)

        # 2. Main Navigation Module Buttons
        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True)

        # 0: Command Center (Active by default)
        self.btn_command = self._create_nav_button("⚡\nCMD", "command", "Command Center (Core AI & Telemetry)", active=True)
        # 1: Live Voice Transcript & Code Intelligence
        self.btn_transcript = self._create_nav_button("💬\nCODE", "transcript", "Live Voice Transcript & Code Intelligence")
        # 2: Knowledge Vault
        self.btn_vault = self._create_nav_button("📚\nVAULT", "knowledge", "Knowledge Vault (Documents & Semantic RAG)")
        # 3: System Control & Automation
        self.btn_system_control = self._create_nav_button("🛡️\nSYS", "system_control", "System Control & Windows Automation")
        # 4: Models & Intelligence
        self.btn_models = self._create_nav_button("🧠\nMDL", "models", "Models & Local Ollama Intelligence")
        # 5: Diagnostics
        self.btn_diagnostics = self._create_nav_button("📊\nDIAG", "diagnostics", "Hardware Diagnostics & Latency Telemetry")

        layout.addWidget(self.btn_command)
        layout.addWidget(self.btn_transcript)
        layout.addWidget(self.btn_vault)
        layout.addWidget(self.btn_system_control)
        layout.addWidget(self.btn_models)
        layout.addWidget(self.btn_diagnostics)

        # Backward compatibility button references
        self.btn_assistant = self.btn_command
        self.btn_knowledge = self.btn_vault
        self.btn_system = self.btn_system_control
        self.btn_activity = self.btn_diagnostics
        self.btn_history = self._create_nav_button("HIST", "history", "Conversation History")
        self.btn_briefing = self._create_nav_button("BRIEF", "briefing", "Daily Briefing")

        layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # Divider
        div2 = QFrame()
        div2.setFrameShape(QFrame.HLine)
        div2.setStyleSheet(f"background-color: {BORDER_SUBTLE}; max-height: 1px; margin: 4px 6px;")
        layout.addWidget(div2)

        # 3. Bottom Actions: Mic toggle, Palette, Settings
        self.btn_mic = QPushButton("🎤")
        self.btn_mic.setFixedSize(48, 32)
        self.btn_mic.setCursor(Qt.PointingHandCursor)
        self.btn_mic.setToolTip("Mute / Unmute Microphone")
        self.btn_mic.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {TEXT_SECONDARY};
                border: 1px solid transparent;
                border-radius: 4px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: #151A18;
                color: {ACCENT_NEON};
                border: 1px solid {BORDER_SUBTLE};
            }}
        """)
        self.btn_mic.clicked.connect(self.toggle_mic_clicked.emit)

        self.btn_palette = QPushButton("⌨")
        self.btn_palette.setFixedSize(48, 32)
        self.btn_palette.setCursor(Qt.PointingHandCursor)
        self.btn_palette.setToolTip("Action Palette [Ctrl+K]")
        self.btn_palette.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {TEXT_SECONDARY};
                border: 1px solid transparent;
                border-radius: 4px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: #151A18;
                color: {ACCENT_NEON};
                border: 1px solid {BORDER_SUBTLE};
            }}
        """)
        self.btn_palette.clicked.connect(self.command_palette_requested.emit)

        self.btn_settings = QPushButton("⚙")
        self.btn_settings.setFixedSize(48, 32)
        self.btn_settings.setCursor(Qt.PointingHandCursor)
        self.btn_settings.setToolTip("System Settings & Configuration")
        self.btn_settings.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {TEXT_SECONDARY};
                border: 1px solid transparent;
                border-radius: 4px;
                font-size: 15px;
            }}
            QPushButton:hover {{
                background-color: #151A18;
                color: {ACCENT_NEON};
                border: 1px solid {BORDER_SUBTLE};
            }}
        """)
        self.btn_settings.clicked.connect(lambda: self.navigate.emit("settings"))

        layout.addWidget(self.btn_mic, alignment=Qt.AlignCenter)
        layout.addWidget(self.btn_palette, alignment=Qt.AlignCenter)
        layout.addWidget(self.btn_settings, alignment=Qt.AlignCenter)

    def _create_nav_button(self, label: str, view_id: str, tooltip: str, active: bool = False) -> QPushButton:
        btn = QPushButton(label)
        btn.setProperty("class", "rail-button")
        btn.setFixedSize(56, 44)
        btn.setCheckable(True)
        btn.setChecked(active)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setToolTip(tooltip)
        btn.clicked.connect(lambda: self.navigate.emit(view_id))
        self.button_group.addButton(btn)
        return btn

    def set_active_view(self, view_id: str) -> None:
        """Update active button state to match selected view."""
        mapping = {
            "command": self.btn_command,
            "assistant": self.btn_command,
            "briefing": self.btn_command,
            "activity": self.btn_command,
            "transcript": self.btn_transcript,
            "history": self.btn_transcript,
            "knowledge": self.btn_vault,
            "system_control": self.btn_system_control,
            "system": self.btn_system_control,
            "models": self.btn_models,
            "diagnostics": self.btn_diagnostics,
            "settings": self.btn_settings,
        }
        btn = mapping.get(view_id)
        if btn:
            btn.setChecked(True)

    def set_mic_muted(self, muted: bool) -> None:
        """Update mic button display state."""
        if muted:
            self.btn_mic.setText("🔇")
            self.btn_mic.setToolTip("Microphone Muted (Click to Unmute)")
            self.btn_mic.setStyleSheet("color: #FF4444; font-size: 14px;")
        else:
            self.btn_mic.setText("🎤")
            self.btn_mic.setToolTip("Microphone Active (Click to Mute)")
            self.btn_mic.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 14px;")
