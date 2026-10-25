"""
Main desktop window for Zero AI assistant.
Combines futuristic JARVIS sidebar, stacked view panels, interactive HUD info panel,
and live status bar with asynchronous subsystem event dispatching.
"""

import logging
from PySide6.QtCore import Qt, Signal, QObject
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QStackedWidget,
    QMessageBox,
)
from app.config.settings import get_settings
from app.core.assistant import get_assistant
from app.core.state_manager import AssistantState
from app.voice.manager import VoiceManager
from app.memory.conversation_store import ConversationStore
from app.gui.theme import DARK_THEME_QSS
from app.gui.widgets.sidebar import SidebarWidget
from app.gui.widgets.chat_panel import ChatPanelWidget
from app.gui.widgets.briefing_panel import BriefingPanelWidget
from app.gui.widgets.history_panel import HistoryPanelWidget
from app.gui.widgets.knowledge_panel import KnowledgePanelWidget
from app.gui.widgets.system_panel import SystemPanelWidget
from app.gui.widgets.settings_panel import SettingsPanelWidget
from app.gui.widgets.info_panel import InfoPanelWidget
from app.gui.widgets.status_bar import StatusBarWidget

logger = logging.getLogger(__name__)


class StateSignalEmitter(QObject):
    """Bridge for receiving thread-safe state machine updates into Qt main loop."""
    state_changed = Signal(str, str)


class MainWindow(QMainWindow):
    """Primary PySide6 Desktop GUI for Zero AI."""

    def __init__(self, voice_manager: VoiceManager | None = None):
        super().__init__()
        self.setWindowTitle("ZERO AI // PERSONAL SYSTEM ASSISTANT")
        self.resize(1200, 780)
        self.setMinimumSize(960, 640)

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

    def _init_ui(self):
        root = QWidget()
        root.setObjectName("root_container")
        self.setCentralWidget(root)

        main_vertical = QVBoxLayout(root)
        main_vertical.setContentsMargins(0, 0, 0, 0)
        main_vertical.setSpacing(0)

        # Main Body (Sidebar + Stacked Views + Right Info Panel)
        body_layout = QHBoxLayout()
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        # 1. Left Navigation Sidebar
        self.sidebar = SidebarWidget(self)
        self.sidebar.navigate.connect(self._handle_navigation)
        self.sidebar.new_conversation_clicked.connect(self._handle_new_conversation)
        body_layout.addWidget(self.sidebar)

        # 2. Central Stacked Views
        self.stacked = QStackedWidget(self)
        self.chat_panel = ChatPanelWidget(self)
        self.chat_panel.wake_requested.connect(self._handle_wake)
        self.chat_panel.sleep_requested.connect(self._handle_sleep)
        self.chat_panel.ptt_requested.connect(self._handle_push_to_talk)
        self.chat_panel.ai_response_generated.connect(self._handle_ai_response_generated)

        self.history_panel = HistoryPanelWidget(self)
        self.history_panel.conversation_selected.connect(self._handle_conversation_switched)

        self.knowledge_panel = KnowledgePanelWidget(self)
        self.briefing_panel = BriefingPanelWidget(self)
        self.system_panel = SystemPanelWidget(self)
        self.settings_panel = SettingsPanelWidget(self)
        self.settings_panel.settings_updated.connect(self._handle_settings_updated)

        self.stacked.addWidget(self.chat_panel)       # Index 0: assistant
        self.stacked.addWidget(self.history_panel)    # Index 1: history
        self.stacked.addWidget(self.knowledge_panel)  # Index 2: knowledge
        self.stacked.addWidget(self.briefing_panel)   # Index 3: briefing / activity
        self.stacked.addWidget(self.system_panel)     # Index 4: system
        self.stacked.addWidget(self.settings_panel)   # Index 5: settings

        body_layout.addWidget(self.stacked, stretch=1)

        # 3. Right Info Panel
        self.info_panel = InfoPanelWidget(self)
        body_layout.addWidget(self.info_panel)

        main_vertical.addLayout(body_layout, stretch=1)

        # 4. Bottom Status Bar
        self.status_bar_widget = StatusBarWidget(self)
        main_vertical.addWidget(self.status_bar_widget)

    def _apply_theme(self):
        self.setStyleSheet(DARK_THEME_QSS)

    def _handle_navigation(self, view_id: str):
        mapping = {
            "assistant": 0,
            "history": 1,
            "knowledge": 2,
            "briefing": 3,
            "activity": 3,  # Briefing panel contains comprehensive activity logs
            "system": 4,
            "settings": 5,
        }
        idx = mapping.get(view_id, 0)
        self.stacked.setCurrentIndex(idx)
        if idx == 1:
            self.history_panel.reload_conversations()
        elif idx == 2:
            self.knowledge_panel.refresh_all()
        elif idx == 3:
            self.briefing_panel.reload_data()
        elif idx == 4:
            self.system_panel.reload_diagnostics()

    def _handle_new_conversation(self):
        conv = ConversationStore.create_conversation("New Conversation")
        self.assistant.active_conversation_id = conv.id
        self.stacked.setCurrentIndex(0)
        self.sidebar.set_active_view("assistant")
        self.chat_panel.load_history()
        self.chat_panel.add_message(
            "assistant",
            "Initialized a new conversation thread. Systems are online and standing by.",
        )

    def _handle_conversation_switched(self, conv_id: str):
        self.stacked.setCurrentIndex(0)
        self.sidebar.set_active_view("assistant")
        self.chat_panel.load_history()

    def _on_state_transition(self, old_state_str: str, new_state_str: str):
        new_state = AssistantState(new_state_str)
        self.chat_panel.update_assistant_state(new_state)
        self.info_panel.set_assistant_state(new_state)

    def _handle_wake(self):
        """Wake up assistant via button or command."""
        greeting_or_briefing = self.assistant.wake(force_briefing=False)
        self.chat_panel.add_message("assistant", greeting_or_briefing)
        settings = get_settings()
        if settings.voice_enabled:
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
        """Put assistant into sleep mode."""
        msg = self.assistant.sleep()
        self.chat_panel.add_message("assistant", msg)

    def _handle_voice_wake(self):
        """Triggered from background wake listener."""
        self._handle_wake()

    def _handle_voice_query(self, text: str):
        self.chat_panel.text_input.setText(text)
        self.chat_panel.send_message()

    def _handle_ai_response_generated(self, text: str):
        """Speak the assistant answer aloud if voice is enabled."""
        settings = get_settings()
        if settings.voice_enabled:
            self.voice_manager.speak(
                text,
                on_start=lambda: self.assistant.state_manager.transition_to(
                    AssistantState.SPEAKING, reason="Speaking response"
                ),
                on_end=lambda: self.assistant.state_manager.transition_to(
                    AssistantState.READY, reason="Speech output finished"
                ),
            )

    def _handle_push_to_talk(self):
        """One-shot push to talk recording."""
        settings = get_settings()
        if not settings.voice_enabled:
            QMessageBox.information(
                self,
                "Voice Disabled",
                "Voice features are currently disabled in Settings. Enable Voice Input to use the microphone.",
            )
            return

        self.assistant.state_manager.transition_to(
            AssistantState.LISTENING, reason="Push to talk active"
        )

        def _on_success(transcribed_text: str):
            self.assistant.state_manager.transition_to(
                AssistantState.READY, reason="PTT completed"
            )
            self.chat_panel.text_input.setText(transcribed_text)
            self.chat_panel.send_message()

        def _on_error(err_msg: str):
            self.assistant.state_manager.transition_to(
                AssistantState.READY, reason="PTT error"
            )
            self.chat_panel.add_message("assistant", f"[VOICE NOTICE] {err_msg}")

        self.voice_manager.trigger_push_to_talk(on_success=_on_success, on_error=_on_error)

    def _handle_settings_updated(self):
        settings = get_settings(reload=True)
        self.assistant.conversation_manager.reload_provider()
        self.status_bar_widget.refresh_telemetry()
        self.info_panel.refresh_data()

    def _check_startup_greeting(self):
        settings = get_settings()
        if settings.briefing_on_startup:
            # Deliver startup greeting into transcript
            briefing = self.assistant.briefing_service.generate_briefing(force=False)
            self.chat_panel.add_message("assistant", briefing["text"])

    def closeEvent(self, event):
        """Clean shutdown when user closes window."""
        logger.info("Application close event triggered. Releasing subsystems...")
        self.assistant.shutdown()
        self.voice_manager.shutdown()
        event.accept()
