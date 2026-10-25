"""
Zero AI — Integrated Desktop GUI Main Window (Obsidian Command).
Assembles the complete Stitch tactile intelligence desktop interface:
- 36px Custom Window Titlebar with live telemetry and native window control hooks.
- 64px Slim Navigation Rail with module switches and operator profile.
- Central Stacked Workspace:
  * Index 0: Command Center (Neural Inference, Ambient Orb, Tactical Actions, Live Audit)
  * Index 1: Live Voice Transcript & Code Intelligence (Dialogue Stream, Line-numbered Code, Execution)
  * Index 2: Knowledge Vault (Local Document Management, Semantic Indexing & RAG)
  * Index 3: System Control & Windows Automation (Bento Window Registry, Ambiguity Modal, Palette)
  * Index 4: Models & Intelligence Configuration (Ollama Models & Settings)
  * Index 5: System Telemetry & Hardware Diagnostics
- 40px Persistent Bottom Voice Dock with reactive audio equalizer, transcript ticker,
  and instant interruption [ESC] / force mic controls.
"""

import logging
import os
import psutil
from PySide6.QtCore import Qt, Signal, QObject, QTimer, QPoint
from PySide6.QtGui import QKeyEvent, QMouseEvent
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QStackedWidget,
    QLabel,
    QPushButton,
    QFrame,
    QMessageBox,
)

from app.config.settings import get_settings
from app.core.assistant import get_assistant
from app.core.state_manager import AssistantState
from app.voice.manager import VoiceManager
from app.memory.conversation_store import ConversationStore
from app.memory.activity_store import ActivityStore
from app.gui.theme import (
    DARK_THEME_QSS,
    CANVAS_BG,
    SURFACE_PANEL,
    CONTAINER_BG,
    CONTAINER_LOWEST,
    BORDER_SUBTLE,
    ACCENT_NEON,
    ACCENT_WARNING,
    ACCENT_CRITICAL,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_DIM,
)
from app.gui.widgets.sidebar import SidebarWidget
from app.gui.widgets.command_center import CommandCenterWidget
from app.gui.widgets.transcript_panel import TranscriptCodeWidget
from app.gui.widgets.system_control_panel import SystemControlWidget
from app.gui.widgets.footer_voice_bar import FooterVoiceBarWidget
from app.gui.widgets.knowledge_panel import KnowledgePanelWidget
from app.gui.widgets.settings_panel import SettingsPanelWidget
from app.gui.widgets.system_panel import SystemPanelWidget
from app.gui.widgets.briefing_panel import BriefingPanelWidget
from app.gui.widgets.history_panel import HistoryPanelWidget
from app.gui.widgets.info_panel import InfoPanelWidget
from app.gui.widgets.status_bar import StatusBarWidget

logger = logging.getLogger(__name__)


class StateSignalEmitter(QObject):
    """Bridge for receiving thread-safe state machine updates into Qt main loop."""
    state_changed = Signal(str, str)


class MainWindow(QMainWindow):
    """
    Primary PySide6 Desktop GUI for Zero AI implementing Stitch Obsidian Command.
    """

    def __init__(self, voice_manager: VoiceManager | None = None):
        super().__init__()
        self.setWindowTitle("ZERO AI // PERSONAL SYSTEM ASSISTANT")
        self.resize(1280, 800)
        self.setMinimumSize(1024, 680)

        self._drag_pos = QPoint()
        self._mic_muted = False

        self.voice_manager = voice_manager or VoiceManager(
            on_wake_callback=self._handle_voice_wake,
            on_speech_recognized=self._handle_voice_query,
        )

        self.assistant = get_assistant()
        self.assistant.set_speech_stop_callback(self.voice_manager.stop_speaking)

        # Thread-safe state change bridge
        self.state_bridge = StateSignalEmitter()
        self.state_bridge.state_changed.connect(self._on_state_transition)
        self.assistant.state_manager.register_callback(
            lambda old, new: self.state_bridge.state_changed.emit(old.value, new.value)
        )

        self._init_ui()
        self._apply_theme()
        self._check_startup_greeting()

        # Telemetry timer for custom titlebar
        self._titlebar_timer = QTimer(self)
        self._titlebar_timer.timeout.connect(self._refresh_titlebar_telemetry)
        self._titlebar_timer.start(2000)
        self._refresh_titlebar_telemetry()

    def _init_ui(self):
        root = QWidget()
        root.setObjectName("root_container")
        self.setCentralWidget(root)

        main_vertical = QVBoxLayout(root)
        main_vertical.setContentsMargins(0, 0, 0, 0)
        main_vertical.setSpacing(0)

        # =====================================================================
        # 1. TOP CUSTOM WINDOW TITLEBAR (Fixed 36px)
        # =====================================================================
        self.title_bar = QFrame()
        self.title_bar.setObjectName("title_bar")
        self.title_bar.setFixedHeight(36)
        tb_layout = QHBoxLayout(self.title_bar)
        tb_layout.setContentsMargins(12, 0, 8, 0)
        tb_layout.setSpacing(10)

        # Titlebar Left: Identity & Model Chip
        lbl_app_icon = QLabel("⚡")
        lbl_app_icon.setStyleSheet(f"color: {ACCENT_NEON}; font-size: 13px;")
        tb_layout.addWidget(lbl_app_icon)

        lbl_app_title = QLabel("Z.E.R.O. v2.4 // LOCAL INTELLIGENCE")
        lbl_app_title.setStyleSheet(f"color: {ACCENT_NEON}; font-family: 'Consolas', monospace; font-weight: bold; font-size: 11px; letter-spacing: 1px;")
        tb_layout.addWidget(lbl_app_title)

        sep0 = QLabel("|")
        sep0.setStyleSheet(f"color: {BORDER_SUBTLE}; font-family: monospace;")
        tb_layout.addWidget(sep0)

        settings = get_settings()
        self.lbl_title_model = QLabel(f"{settings.ollama_model_chat} [LOCAL]")
        self.lbl_title_model.setStyleSheet(f"background-color: {CONTAINER_BG}; color: {ACCENT_NEON}; border: 1px solid {BORDER_SUBTLE}; border-radius: 3px; padding: 2px 6px; font-family: 'Consolas', monospace; font-size: 10px;")
        tb_layout.addWidget(self.lbl_title_model)

        self.lbl_title_online = QLabel("ONLINE: ZERO")
        self.lbl_title_online.setStyleSheet(f"color: {TEXT_SECONDARY}; font-family: 'Consolas', monospace; font-size: 10px;")
        tb_layout.addWidget(self.lbl_title_online)

        tb_layout.addStretch()

        # Titlebar Center: Hardware Telemetry
        self.lbl_title_cpu = QLabel("CPU: 18%")
        self.lbl_title_cpu.setStyleSheet(f"color: {ACCENT_NEON}; font-family: 'Consolas', monospace; font-size: 10px;")
        self.lbl_title_ram = QLabel("RAM: 16.2GB")
        self.lbl_title_ram.setStyleSheet(f"color: {TEXT_PRIMARY}; font-family: 'Consolas', monospace; font-size: 10px;")
        self.lbl_title_lat = QLabel("LATENCY: 12ms")
        self.lbl_title_lat.setStyleSheet(f"color: {ACCENT_NEON}; font-family: 'Consolas', monospace; font-size: 10px;")

        tb_layout.addWidget(self.lbl_title_cpu)
        tb_layout.addWidget(self.lbl_title_ram)
        tb_layout.addWidget(self.lbl_title_lat)

        tb_layout.addStretch()

        # Titlebar Right: Window Controls
        btn_min = QPushButton("—")
        btn_min.setProperty("class", "titlebar-btn")
        btn_min.setToolTip("Minimize Window")
        btn_min.clicked.connect(self.showMinimized)

        self.btn_max = QPushButton("□")
        self.btn_max.setProperty("class", "titlebar-btn")
        self.btn_max.setToolTip("Maximize / Restore Window")
        self.btn_max.clicked.connect(self._toggle_maximize)

        btn_close = QPushButton("✕")
        btn_close.setProperty("class", "titlebar-btn titlebar-btn-close")
        btn_close.setToolTip("Close Application")
        btn_close.clicked.connect(self.close)

        tb_layout.addWidget(btn_min)
        tb_layout.addWidget(self.btn_max)
        tb_layout.addWidget(btn_close)

        main_vertical.addWidget(self.title_bar)

        # =====================================================================
        # 2. MAIN BODY (Sidebar Rail + Stacked Workspace)
        # =====================================================================
        body_layout = QHBoxLayout()
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        # Left 64px Navigation Rail
        self.sidebar = SidebarWidget(self)
        self.sidebar.navigate.connect(self._handle_navigation)
        self.sidebar.new_conversation_clicked.connect(self._handle_new_conversation)
        self.sidebar.toggle_mic_clicked.connect(self._handle_toggle_mic)
        self.sidebar.command_palette_requested.connect(self._open_command_palette)
        body_layout.addWidget(self.sidebar)

        # Central Stacked Workspace
        self.stacked = QStackedWidget(self)

        # View 0: Command Center
        self.command_center = CommandCenterWidget(self)
        self.command_center.state_change_requested.connect(self._on_orb_state_change)
        self.command_center.switch_to_transcript_requested.connect(lambda: self._handle_navigation("transcript"))
        self.command_center.switch_to_system_control_requested.connect(lambda: self._handle_navigation("system_control"))

        # View 1: Live Voice Transcript & Code Intelligence
        self.transcript_widget = TranscriptCodeWidget(self)
        self.transcript_widget.ptt_requested.connect(self._handle_push_to_talk)
        self.transcript_widget.ai_response_generated.connect(self._handle_ai_response_generated)
        self.transcript_widget.speak_replay_requested.connect(self._handle_listen_again)

        # Compatibility reference for existing tests/controllers
        self.chat_panel = self.transcript_widget

        # View 2: Knowledge Vault
        self.knowledge_panel = KnowledgePanelWidget(self)

        # View 3: System Control & Windows Automation
        self.system_control = SystemControlWidget(self)

        # View 4: Settings & Models
        self.settings_panel = SettingsPanelWidget(self)
        self.settings_panel.settings_updated.connect(self._handle_settings_updated)

        # View 5: Diagnostics
        self.system_panel = SystemPanelWidget(self)

        # Historical compatibility views
        self.history_panel = HistoryPanelWidget(self)
        self.history_panel.conversation_selected.connect(self._handle_conversation_switched)
        self.briefing_panel = BriefingPanelWidget(self)
        self.info_panel = InfoPanelWidget(self)
        self.status_bar_widget = StatusBarWidget(self)

        self.stacked.addWidget(self.command_center)       # Index 0: Command Center
        self.stacked.addWidget(self.transcript_widget)     # Index 1: Transcript & Code
        self.stacked.addWidget(self.knowledge_panel)       # Index 2: Knowledge Vault
        self.stacked.addWidget(self.system_control)        # Index 3: System Control & Automation
        self.stacked.addWidget(self.settings_panel)        # Index 4: Settings & Models
        self.stacked.addWidget(self.system_panel)          # Index 5: Diagnostics

        body_layout.addWidget(self.stacked, stretch=1)
        main_vertical.addLayout(body_layout, stretch=1)

        # =====================================================================
        # 3. PERSISTENT FOOTER VOICE DOCK (Fixed 40px)
        # =====================================================================
        self.footer_voice_bar = FooterVoiceBarWidget(self)
        self.footer_voice_bar.interrupt_requested.connect(self._handle_interrupt)
        self.footer_voice_bar.force_mic_pressed.connect(self._handle_push_to_talk)
        self.footer_voice_bar.force_mic_released.connect(lambda: None)
        main_vertical.addWidget(self.footer_voice_bar)

    def _apply_theme(self):
        self.setStyleSheet(DARK_THEME_QSS)

    def _refresh_titlebar_telemetry(self):
        """Update live telemetry metrics on top titlebar."""
        try:
            cpu_pct = psutil.cpu_percent(interval=0.0)
            self.lbl_title_cpu.setText(f"CPU: {cpu_pct:.0f}%")

            mem = psutil.virtual_memory()
            used_gb = mem.used / (1024**3)
            self.lbl_title_ram.setText(f"RAM: {used_gb:.1f}GB")

            settings = get_settings()
            self.lbl_title_model.setText(f"{settings.ollama_model_chat} [LOCAL]")
        except Exception:
            pass

    def _toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
            self.btn_max.setText("□")
        else:
            self.showMaximized()
            self.btn_max.setText("❐")

    def _handle_navigation(self, view_id: str):
        mapping = {
            "command": 0,
            "assistant": 0,
            "briefing": 0,
            "activity": 0,
            "transcript": 1,
            "history": 1,
            "knowledge": 2,
            "vault": 2,
            "system_control": 3,
            "system": 3,
            "models": 4,
            "settings": 4,
            "diagnostics": 5,
        }
        idx = mapping.get(view_id, 0)
        self.stacked.setCurrentIndex(idx)
        self.sidebar.set_active_view(view_id)

        if idx == 0:
            self.command_center.refresh_telemetry()
            self.command_center.refresh_audit_log()
        elif idx == 1:
            self.transcript_widget.load_history()
        elif idx == 2:
            self.knowledge_panel.refresh_all()
        elif idx == 3:
            self.system_control.refresh_windows()
        elif idx == 5:
            self.system_panel.reload_diagnostics()

    def switch_view(self, view_id: str):
        """Public alias for navigation to a view by ID."""
        self._handle_navigation(view_id)

    def _handle_new_conversation(self):
        conv = ConversationStore.create_conversation("New Conversation")
        self.assistant.active_conversation_id = conv.id
        self._handle_navigation("transcript")
        self.transcript_widget.load_history()
        self.transcript_widget.add_message(
            "assistant",
            "Initialized a new conversation session. Systems are online and standing by.",
        )
        self.footer_voice_bar.set_ticker_text("Initialized new conversation session.")
        ActivityStore.record_activity("SESSION", f"Created conversation: {conv.id[:8]}")

    def _handle_conversation_switched(self, conv_id: str):
        self.assistant.active_conversation_id = conv_id
        self._handle_navigation("transcript")
        self.transcript_widget.load_history()

    def _handle_toggle_mic(self):
        self._mic_muted = not self._mic_muted
        self.sidebar.set_mic_muted(self._mic_muted)
        self.footer_voice_bar.set_mic_status(not self._mic_muted)
        status_str = "MUTED" if self._mic_muted else "ACTIVE"
        self.footer_voice_bar.set_ticker_text(f"Microphone status switched to {status_str}.")

    def _open_command_palette(self):
        self._handle_navigation("system_control")
        self.system_control.input_query.setFocus()

    def _on_state_transition(self, old_state_str: str, new_state_str: str):
        try:
            # Handle direct enum or uppercase match
            clean_str = new_state_str.strip().upper()
            if clean_str in ("IDLE", "STANDBY"):
                clean_str = "READY"
            new_state = AssistantState(clean_str)
        except Exception:
            new_state = AssistantState.READY

        self.command_center.update_assistant_state(new_state)
        self.footer_voice_bar.set_assistant_state(new_state)
        self.info_panel.set_assistant_state(new_state)

    def _on_orb_state_change(self, new_state: AssistantState):
        self.assistant.state_manager.transition_to(new_state, reason="Operator state selector")

    def _handle_wake(self):
        greeting_or_briefing = self.assistant.wake(force_briefing=False)
        self.transcript_widget.add_message("assistant", greeting_or_briefing)
        self.footer_voice_bar.set_ticker_text(greeting_or_briefing, prefix="ZERO:")

        settings = get_settings()
        if settings.voice_enabled and not self._mic_muted:
            self.voice_manager.speak(
                greeting_or_briefing,
                on_start=lambda: self.assistant.state_manager.transition_to(
                    AssistantState.SPEAKING, reason="Speaking greeting"
                ),
                on_end=lambda: self.assistant.state_manager.transition_to(
                    AssistantState.READY, reason="Greeting finished"
                ),
            )

    def _handle_sleep(self):
        msg = self.assistant.sleep()
        self.transcript_widget.add_message("assistant", msg)
        self.footer_voice_bar.set_ticker_text(msg, prefix="ZERO:")

    def _handle_voice_wake(self):
        self._handle_wake()

    def _handle_voice_query(self, text: str):
        if self._mic_muted:
            return
        self.footer_voice_bar.set_ticker_text(text, prefix="OPERATOR:")
        self.transcript_widget.text_input.setText(text)
        self.transcript_widget.send_message()

    def _handle_ai_response_generated(self, text: str):
        self.footer_voice_bar.set_ticker_text(text, prefix="ZERO:")
        settings = get_settings()
        if settings.voice_enabled and not self._mic_muted:
            self.voice_manager.speak(
                text,
                on_start=lambda: self.assistant.state_manager.transition_to(
                    AssistantState.SPEAKING, reason="Speaking response"
                ),
                on_end=lambda: self.assistant.state_manager.transition_to(
                    AssistantState.READY, reason="Speech output finished"
                ),
            )

    def _handle_listen_again(self, text: str):
        self.voice_manager.speak(
            text,
            on_start=lambda: self.assistant.state_manager.transition_to(
                AssistantState.SPEAKING, reason="Replaying speech"
            ),
            on_end=lambda: self.assistant.state_manager.transition_to(
                AssistantState.READY, reason="Replay finished"
            ),
        )

    def _handle_push_to_talk(self):
        if self._mic_muted:
            QMessageBox.information(self, "Mic Muted", "Microphone is muted. Unmute from the navigation rail to use voice.")
            return

        settings = get_settings()
        if not settings.voice_enabled:
            QMessageBox.information(
                self,
                "Voice Disabled",
                "Voice features are currently disabled in Settings.",
            )
            return

        self.assistant.state_manager.transition_to(
            AssistantState.LISTENING, reason="Push to talk active"
        )
        self.footer_voice_bar.set_ticker_text("Recording push-to-talk audio...")

        def _on_success(transcribed_text: str):
            self.assistant.state_manager.transition_to(
                AssistantState.READY, reason="PTT completed"
            )
            self.footer_voice_bar.set_ticker_text(transcribed_text, prefix="OPERATOR:")
            self.transcript_widget.text_input.setText(transcribed_text)
            self.transcript_widget.send_message()

        def _on_error(err_msg: str):
            self.assistant.state_manager.transition_to(
                AssistantState.READY, reason="PTT error"
            )
            self.transcript_widget.add_message("assistant", f"[VOICE NOTICE] {err_msg}")
            self.footer_voice_bar.set_ticker_text(f"Voice error: {err_msg}")

        self.voice_manager.trigger_push_to_talk(on_success=_on_success, on_error=_on_error)

    def _handle_interrupt(self):
        """Immediately stop speech playback and return assistant to ready state."""
        self.voice_manager.stop_speaking()
        self.assistant.stop_speaking()
        self.assistant.state_manager.transition_to(
            AssistantState.READY, reason="Operator speech interruption"
        )
        self.transcript_widget.add_message(
            "interrupt",
            "Speech output halted by operator via [ESC] interruption control.",
        )
        self.footer_voice_bar.set_ticker_text("Speech interrupted by operator.")
        ActivityStore.record_activity("INTERRUPT", "Halted active speech output")

    def _handle_settings_updated(self):
        settings = get_settings(reload=True)
        self.assistant.conversation_manager.reload_provider()
        self.status_bar_widget.refresh_telemetry()
        self.info_panel.refresh_data()
        self.command_center.refresh_telemetry()
        self._refresh_titlebar_telemetry()

    def _check_startup_greeting(self):
        settings = get_settings()
        if settings.briefing_on_startup:
            briefing = self.assistant.briefing_service.generate_briefing(force=False)
            self.transcript_widget.add_message("assistant", briefing["text"])
            self.footer_voice_bar.set_ticker_text(briefing["text"], prefix="ZERO:")

    def keyPressEvent(self, event: QKeyEvent):
        """Global keyboard shortcut handling."""
        # Esc -> Interruption
        if event.key() == Qt.Key_Escape:
            self._handle_interrupt()
            event.accept()
            return

        # Ctrl+K -> Action Palette / System Control
        if event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_K:
            self._open_command_palette()
            event.accept()
            return

        # Ctrl+F -> Search Dialogue History
        if event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_F:
            self._handle_navigation("transcript")
            self.transcript_widget.search_input.setFocus()
            self.transcript_widget.search_input.selectAll()
            event.accept()
            return

        # Win+Shift+Z -> Analyze Display
        if (
            (event.modifiers() & Qt.ShiftModifier)
            and event.key() == Qt.Key_Z
        ):
            self.command_center._handle_action_analyze_display()
            event.accept()
            return

        super().keyPressEvent(event)

    def closeEvent(self, event):
        """Clean shutdown when user closes window."""
        logger.info("Application close event triggered. Releasing subsystems...")
        self.assistant.shutdown()
        self.voice_manager.shutdown()
        event.accept()
