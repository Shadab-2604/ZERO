"""
Settings and configuration management panel for Zero AI.
Allows safe updates of providers, API base URLs, voice settings, briefings, knowledge settings, and data maintenance.
Includes live 'Test AI Connection', 'Test Microphone', 'Test Voice Output', and 'Reindex Knowledge' actions
with masked secrets and thread-safe execution.
"""

import logging
from PySide6.QtCore import Qt, Signal, QThread, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QComboBox,
    QCheckBox,
    QScrollArea,
    QFrame,
    QSlider,
    QSpinBox,
    QMessageBox,
)
from app.config.settings import get_settings
from app.memory.conversation_store import ConversationStore
from app.memory.activity_store import ActivityStore
from app.memory.database import backup_database
from app.ai.connection_tester import AIConnectionTester
from app.utils.paths import get_knowledge_dir
from app.knowledge.service import get_knowledge_service
from app.knowledge.parsers import DocumentParserFactory
from app.voice.speech_synthesis import SpeechSynthesizer

logger = logging.getLogger(__name__)


class ConnectionTestWorker(QThread):
    """Background worker for testing AI provider connection without freezing the GUI."""

    test_completed = Signal(dict)

    def __init__(self, api_base: str, api_key: str, preferred_model: str, update_env: bool = False):
        super().__init__()
        self.api_base = api_base
        self.api_key = api_key
        self.preferred_model = preferred_model
        self.update_env = update_env

    def run(self):
        tester = AIConnectionTester(
            api_base=self.api_base,
            api_key=self.api_key,
        )
        report = tester.run_full_diagnostic(
            preferred_model=self.preferred_model,
            update_env_on_success=self.update_env,
        )
        self.test_completed.emit(report.to_dict())


class MicTestWorker(QThread):
    """Background worker for testing audio input without blocking UI."""

    test_finished = Signal(bool, str)

    def __init__(self, device_index: int | None = None):
        super().__init__()
        self.device_index = device_index

    def run(self):
        try:
            import speech_recognition as sr
            r = sr.Recognizer()
            mic_kwargs = {}
            if self.device_index is not None and self.device_index >= 0:
                mic_kwargs["device_index"] = self.device_index

            with sr.Microphone(**mic_kwargs) as source:
                r.adjust_for_ambient_noise(source, duration=0.5)
                audio = r.record(source, duration=1.5)
                raw_len = len(audio.get_raw_data())
                if raw_len > 100:
                    self.test_finished.emit(True, f"Microphone working! Captured {raw_len} audio bytes.")
                else:
                    self.test_finished.emit(False, "Microphone returned silence or insufficient data.")
        except Exception as e:
            self.test_finished.emit(False, f"Microphone error: {e}")


class ReindexWorker(QThread):
    """Background worker for reindexing knowledge base."""

    reindex_finished = Signal(dict)

    def run(self):
        try:
            service = get_knowledge_service()
            stats = service.reindex_all_incremental()
            self.reindex_finished.emit(stats)
        except Exception as e:
            logger.error("Knowledge reindexing error: %s", e)
            self.reindex_finished.emit({"error": str(e)})


class SettingsPanelWidget(QWidget):
    """Configuration panel for Zero AI assistant."""

    settings_updated = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._test_worker: ConnectionTestWorker | None = None
        self._mic_worker: MicTestWorker | None = None
        self._reindex_worker: ReindexWorker | None = None
        self._synthesizer = SpeechSynthesizer()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # Header
        header = QLabel("SYSTEM CONFIGURATION & PREFERENCES")
        header.setStyleSheet("color: #FFFFFF; font-size: 16px; font-weight: bold; letter-spacing: 1.5px;")
        layout.addWidget(header)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 10, 0)
        content_layout.setSpacing(16)

        # -------------------------------------------------------------
        # 1. AI Provider Section
        # -------------------------------------------------------------
        ai_card = QFrame()
        ai_card.setProperty("class", "hud-card")
        ai_layout = QVBoxLayout(ai_card)
        ai_layout.setContentsMargins(18, 16, 18, 16)
        ai_layout.setSpacing(10)

        ai_header = QLabel("AI INTELLIGENCE PROVIDER")
        ai_header.setStyleSheet("color: #00FF88; font-size: 12px; font-weight: bold; letter-spacing: 1px;")
        ai_layout.addWidget(ai_header)

        # Provider Select
        p_row = QHBoxLayout()
        p_row.addWidget(QLabel("Active Provider:"))
        self.combo_provider = QComboBox()
        self.combo_provider.addItems(["demo", "openai", "gemini", "anthropic", "ollama"])
        p_row.addWidget(self.combo_provider)
        ai_layout.addLayout(p_row)

        # API Base URL
        b_row = QHBoxLayout()
        b_row.addWidget(QLabel("API Base URL:"))
        self.input_api_base = QLineEdit()
        self.input_api_base.setPlaceholderText("e.g. https://agent-router.net/aggregate/openai/v1")
        b_row.addWidget(self.input_api_base)
        ai_layout.addLayout(b_row)

        # Model Name
        m_row = QHBoxLayout()
        m_row.addWidget(QLabel("Model Name:"))
        self.input_model = QLineEdit()
        self.input_model.setPlaceholderText("e.g. gpt-4o-mini, gemini-1.5-flash, llama3")
        m_row.addWidget(self.input_model)
        ai_layout.addLayout(m_row)

        # API Key (Masked)
        k_row = QHBoxLayout()
        k_row.addWidget(QLabel("API Key:"))
        self.input_api_key = QLineEdit()
        self.input_api_key.setEchoMode(QLineEdit.Password)
        self.input_api_key.setPlaceholderText("Enter new API Key (stored securely in .env)")
        k_row.addWidget(self.input_api_key)
        ai_layout.addLayout(k_row)

        self.key_status_label = QLabel("Current Key Status: Not Configured")
        self.key_status_label.setStyleSheet("color: #8A8A8A; font-size: 11px;")
        ai_layout.addWidget(self.key_status_label)

        # Test AI Connection Action Button & Status
        test_row = QHBoxLayout()
        self.btn_test_connection = QPushButton("⚡  Test AI Connection")
        self.btn_test_connection.setProperty("class", "btn-secondary")
        self.btn_test_connection.setCursor(Qt.PointingHandCursor)
        self.btn_test_connection.clicked.connect(self._run_connection_test)
        test_row.addWidget(self.btn_test_connection)

        self.connection_status_label = QLabel("")
        self.connection_status_label.setStyleSheet("font-size: 11px;")
        test_row.addWidget(self.connection_status_label)
        test_row.addStretch()
        ai_layout.addLayout(test_row)

        content_layout.addWidget(ai_card)

        # -------------------------------------------------------------
        # 2. Voice Subsystem Section
        # -------------------------------------------------------------
        voice_card = QFrame()
        voice_card.setProperty("class", "hud-card")
        v_layout = QVBoxLayout(voice_card)
        v_layout.setContentsMargins(18, 16, 18, 16)
        v_layout.setSpacing(10)

        v_header = QLabel("VOICE & SPEECH CONTROLS")
        v_header.setStyleSheet("color: #00FF88; font-size: 12px; font-weight: bold; letter-spacing: 1px;")
        v_layout.addWidget(v_header)

        self.chk_voice = QCheckBox("Enable Voice Input & Synthesis (TTS/STT)")
        self.chk_wake_word = QCheckBox("Enable Background Wake-Word Detection ('Zero, wake up')")
        v_layout.addWidget(self.chk_voice)
        v_layout.addWidget(self.chk_wake_word)

        w_row = QHBoxLayout()
        w_row.addWidget(QLabel("Custom Wake Phrase:"))
        self.input_wake_phrase = QLineEdit()
        w_row.addWidget(self.input_wake_phrase)
        v_layout.addLayout(w_row)

        # Microphone Input Device Selection
        mic_row = QHBoxLayout()
        mic_row.addWidget(QLabel("Microphone Input Device:"))
        self.combo_input_device = QComboBox()
        self._populate_microphone_devices()
        mic_row.addWidget(self.combo_input_device)
        v_layout.addLayout(mic_row)

        # Speech-to-Text Engine Selection
        stt_row = QHBoxLayout()
        stt_row.addWidget(QLabel("Speech Recognition Engine:"))
        self.combo_stt_engine = QComboBox()
        self.combo_stt_engine.addItems(["Google Speech API (Online / Default)", "Sphinx / Offline"])
        stt_row.addWidget(self.combo_stt_engine)
        v_layout.addLayout(stt_row)

        # TTS Output Voice Selection
        tts_row = QHBoxLayout()
        tts_row.addWidget(QLabel("Output Voice:"))
        self.combo_output_voice = QComboBox()
        self._populate_tts_voices()
        tts_row.addWidget(self.combo_output_voice)
        v_layout.addLayout(tts_row)

        # Speech Rate & Volume Controls
        rate_vol_row = QHBoxLayout()
        rate_vol_row.addWidget(QLabel("Speech Rate (WPM):"))
        self.spin_speech_rate = QSpinBox()
        self.spin_speech_rate.setRange(80, 350)
        self.spin_speech_rate.setValue(180)
        self.spin_speech_rate.setStyleSheet("background-color: #0b1410; color: #FFFFFF; padding: 4px;")
        rate_vol_row.addWidget(self.spin_speech_rate)

        rate_vol_row.addSpacing(20)
        rate_vol_row.addWidget(QLabel("Volume (%):"))
        self.slider_speech_volume = QSlider(Qt.Horizontal)
        self.slider_speech_volume.setRange(0, 100)
        self.slider_speech_volume.setValue(90)
        self.lbl_volume_val = QLabel("90%")
        self.lbl_volume_val.setStyleSheet("color: #00FF88; font-weight: bold; min-width: 40px;")
        self.slider_speech_volume.valueChanged.connect(lambda v: self.lbl_volume_val.setText(f"{v}%"))
        rate_vol_row.addWidget(self.slider_speech_volume)
        rate_vol_row.addWidget(self.lbl_volume_val)
        v_layout.addLayout(rate_vol_row)

        # Test Voice & Microphone Buttons
        test_voice_row = QHBoxLayout()
        self.btn_test_mic = QPushButton("🎤  Test Microphone")
        self.btn_test_mic.setProperty("class", "btn-secondary")
        self.btn_test_mic.setCursor(Qt.PointingHandCursor)
        self.btn_test_mic.clicked.connect(self._test_microphone)
        test_voice_row.addWidget(self.btn_test_mic)

        self.btn_test_voice = QPushButton("🔊  Test Voice Output")
        self.btn_test_voice.setProperty("class", "btn-secondary")
        self.btn_test_voice.setCursor(Qt.PointingHandCursor)
        self.btn_test_voice.clicked.connect(self._test_voice_output)
        test_voice_row.addWidget(self.btn_test_voice)

        test_voice_row.addStretch()
        v_layout.addLayout(test_voice_row)

        self.voice_test_status = QLabel("")
        self.voice_test_status.setStyleSheet("font-size: 11px;")
        v_layout.addWidget(self.voice_test_status)

        content_layout.addWidget(voice_card)

        # -------------------------------------------------------------
        # 3. Knowledge Base Settings Section
        # -------------------------------------------------------------
        kb_card = QFrame()
        kb_card.setProperty("class", "hud-card")
        kb_layout = QVBoxLayout(kb_card)
        kb_layout.setContentsMargins(18, 16, 18, 16)
        kb_layout.setSpacing(10)

        kb_header = QLabel("KNOWLEDGE BASE & RAG SETTINGS")
        kb_header.setStyleSheet("color: #00FF88; font-size: 12px; font-weight: bold; letter-spacing: 1px;")
        kb_layout.addWidget(kb_header)

        # Directory Row
        dir_row = QHBoxLayout()
        dir_row.addWidget(QLabel("Knowledge Directory:"))
        self.lbl_kb_path = QLabel(str(get_knowledge_dir()))
        self.lbl_kb_path.setStyleSheet("color: #00E5FF; font-family: monospace; font-size: 11px;")
        dir_row.addWidget(self.lbl_kb_path)

        self.btn_open_kb_folder = QPushButton("📂  Open Folder")
        self.btn_open_kb_folder.setProperty("class", "btn-secondary")
        self.btn_open_kb_folder.setCursor(Qt.PointingHandCursor)
        self.btn_open_kb_folder.clicked.connect(self._open_knowledge_folder)
        dir_row.addWidget(self.btn_open_kb_folder)
        kb_layout.addLayout(dir_row)

        # Backend Engine
        backend_row = QHBoxLayout()
        backend_row.addWidget(QLabel("Index Backend:"))
        lbl_backend = QLabel("SQLite FTS5 + BM25 (High-Speed Local Full-Text Search)")
        lbl_backend.setStyleSheet("color: #00FF88; font-weight: 600;")
        backend_row.addWidget(lbl_backend)
        backend_row.addStretch()
        kb_layout.addLayout(backend_row)

        # Status & Stats
        self.lbl_kb_status = QLabel("Loading knowledge statistics...")
        self.lbl_kb_status.setStyleSheet("color: #8A8A8A; font-size: 11px;")
        kb_layout.addWidget(self.lbl_kb_status)

        # Supported Formats & OCR / Converter status
        formats_text = "Supported Formats: PDF, DOCX, PPTX, XLSX, CSV, JSON, Markdown, Code (25+ types)"
        lbl_formats = QLabel(formats_text)
        lbl_formats.setStyleSheet("color: #B0B0B0; font-size: 11px;")
        kb_layout.addWidget(lbl_formats)

        ocr_status = "Available" if DocumentParserFactory.is_ocr_available() else "Not Installed (Optional)"
        lo_status = "Available" if DocumentParserFactory.is_libreoffice_available() else "Not Installed (Optional)"
        lbl_addons = QLabel(f"OCR Subsystem: {ocr_status} | LibreOffice (.doc/.xls converter): {lo_status}")
        lbl_addons.setStyleSheet("color: #7A8880; font-size: 11px;")
        kb_layout.addWidget(lbl_addons)

        # Reindex Action Button
        reindex_row = QHBoxLayout()
        self.btn_reindex_kb = QPushButton("🔄  Reindex Knowledge Base")
        self.btn_reindex_kb.setProperty("class", "btn-secondary")
        self.btn_reindex_kb.setCursor(Qt.PointingHandCursor)
        self.btn_reindex_kb.clicked.connect(self._reindex_knowledge)
        reindex_row.addWidget(self.btn_reindex_kb)

        self.lbl_reindex_msg = QLabel("")
        self.lbl_reindex_msg.setStyleSheet("font-size: 11px;")
        reindex_row.addWidget(self.lbl_reindex_msg)
        reindex_row.addStretch()
        kb_layout.addLayout(reindex_row)

        content_layout.addWidget(kb_card)

        # -------------------------------------------------------------
        # 4. Briefing & Behavior
        # -------------------------------------------------------------
        b_card = QFrame()
        b_card.setProperty("class", "hud-card")
        b_layout = QVBoxLayout(b_card)
        b_layout.setContentsMargins(18, 16, 18, 16)
        b_layout.setSpacing(10)

        b_header = QLabel("BEHAVIOR & LOCALIZATION")
        b_header.setStyleSheet("color: #00FF88; font-size: 12px; font-weight: bold; letter-spacing: 1px;")
        b_layout.addWidget(b_header)

        self.chk_briefing_startup = QCheckBox("Deliver Briefing on Startup")
        self.chk_briefing_wake = QCheckBox("Deliver Briefing on Wake")
        self.chk_reduced_motion = QCheckBox("Enable Reduced Motion (Disable orb rotation & pulses)")
        b_layout.addWidget(self.chk_briefing_startup)
        b_layout.addWidget(self.chk_briefing_wake)
        b_layout.addWidget(self.chk_reduced_motion)

        tz_row = QHBoxLayout()
        tz_row.addWidget(QLabel("Timezone:"))
        self.input_timezone = QLineEdit()
        tz_row.addWidget(self.input_timezone)
        b_layout.addLayout(tz_row)

        content_layout.addWidget(b_card)

        # -------------------------------------------------------------
        # 5. Data Maintenance
        # -------------------------------------------------------------
        data_card = QFrame()
        data_card.setProperty("class", "hud-card")
        d_layout = QVBoxLayout(data_card)
        d_layout.setContentsMargins(18, 16, 18, 16)
        d_layout.setSpacing(10)

        d_header = QLabel("DATA RETENTION & MAINTENANCE")
        d_header.setStyleSheet("color: #00FF88; font-size: 12px; font-weight: bold; letter-spacing: 1px;")
        d_layout.addWidget(d_header)

        btn_row = QHBoxLayout()
        self.btn_clear_history = QPushButton("Clear Chat History")
        self.btn_clear_history.setProperty("class", "btn-secondary")
        self.btn_clear_history.clicked.connect(self._clear_history)

        self.btn_clear_activity = QPushButton("Clear Activity Logs")
        self.btn_clear_activity.setProperty("class", "btn-secondary")
        self.btn_clear_activity.clicked.connect(self._clear_activity)

        self.btn_backup = QPushButton("Backup Database")
        self.btn_backup.setProperty("class", "btn-secondary")
        self.btn_backup.clicked.connect(self._backup_db)

        btn_row.addWidget(self.btn_clear_history)
        btn_row.addWidget(self.btn_clear_activity)
        btn_row.addWidget(self.btn_backup)
        d_layout.addLayout(btn_row)

        content_layout.addWidget(data_card)

        # Save Button
        self.btn_save = QPushButton("Save & Apply Configuration")
        self.btn_save.setProperty("class", "btn-primary")
        self.btn_save.setFixedHeight(36)
        self.btn_save.clicked.connect(self._save_settings)
        content_layout.addWidget(self.btn_save)

        content_layout.addStretch()
        scroll.setWidget(content_widget)
        layout.addWidget(scroll)

        self.load_current_settings()
        self._refresh_knowledge_stats()

    def _populate_microphone_devices(self):
        """Populate available audio input devices."""
        self.combo_input_device.clear()
        self.combo_input_device.addItem("System Default Input", -1)
        try:
            import speech_recognition as sr
            mic_names = sr.Microphone.list_microphone_names()
            seen = set()
            for idx, name in enumerate(mic_names):
                # Filter out obvious duplicates or outputs
                if "output" in name.lower() or "speaker" in name.lower():
                    continue
                if name not in seen:
                    seen.add(name)
                    self.combo_input_device.addItem(f"{name} (#{idx})", idx)
        except Exception as e:
            logger.debug("Microphone listing notice: %s", e)

    def _populate_tts_voices(self):
        """Populate available pyttsx3 speech synthesis voices."""
        self.combo_output_voice.clear()
        self.combo_output_voice.addItem("System Default Voice", "")
        try:
            import pyttsx3
            eng = pyttsx3.init()
            voices = eng.getProperty("voices")
            for v in voices:
                display = getattr(v, "name", str(v.id))
                self.combo_output_voice.addItem(display, getattr(v, "id", display))
        except Exception as e:
            logger.debug("TTS voice listing notice: %s", e)

    def _refresh_knowledge_stats(self):
        try:
            service = get_knowledge_service()
            status = service.get_indexing_status()
            cnt = status.get("total_indexed_files", 0)
            chunks = status.get("total_chunks", 0)
            last_ts = status.get("last_index_time") or "Never"
            self.lbl_kb_status.setText(f"Indexed Documents: {cnt} | Total Chunks: {chunks} | Last Scan: {last_ts}")
        except Exception as e:
            self.lbl_kb_status.setText(f"Status check error: {e}")

    def load_current_settings(self):
        """Populate inputs from active settings."""
        settings = get_settings()
        idx = self.combo_provider.findText(settings.ai_provider)
        if idx >= 0:
            self.combo_provider.setCurrentIndex(idx)

        self.input_api_base.setText(settings.ai_api_base)
        self.input_model.setText(settings.ai_model)
        has_key = bool(settings.ai_api_key and settings.ai_api_key.strip())
        self.key_status_label.setText(
            "Current Key Status: Configured (••••••••)" if has_key else "Current Key Status: Not Configured (Using Demo)"
        )

        self.chk_voice.setChecked(settings.voice_enabled)
        self.chk_wake_word.setChecked(settings.wake_word_enabled)
        self.input_wake_phrase.setText(settings.wake_word)

        self.spin_speech_rate.setValue(settings.tts_voice_rate)
        vol_pct = int(settings.tts_voice_volume * 100)
        self.slider_speech_volume.setValue(vol_pct)
        self.lbl_volume_val.setText(f"{vol_pct}%")

        if settings.voice_input_device:
            d_idx = self.combo_input_device.findData(settings.voice_input_device)
            if d_idx >= 0:
                self.combo_input_device.setCurrentIndex(d_idx)

        self.chk_briefing_startup.setChecked(settings.briefing_on_startup)
        self.chk_briefing_wake.setChecked(settings.briefing_on_wake)
        self.chk_reduced_motion.setChecked(settings.reduced_motion)
        self.input_timezone.setText(settings.timezone)
        self.connection_status_label.setText("")

    def _open_knowledge_folder(self):
        kb_path = get_knowledge_dir()
        kb_path.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(kb_path)))

    def _reindex_knowledge(self):
        self.btn_reindex_kb.setEnabled(False)
        self.lbl_reindex_msg.setText("Scanning and indexing documents...")
        self.lbl_reindex_msg.setStyleSheet("color: #00E5FF; font-style: italic;")

        self._reindex_worker = ReindexWorker()
        self._reindex_worker.reindex_finished.connect(self._handle_reindex_finished)
        self._reindex_worker.start()

    def _handle_reindex_finished(self, stats: dict):
        self.btn_reindex_kb.setEnabled(True)
        if "error" in stats:
            self.lbl_reindex_msg.setText(f"✗ Reindex error: {stats['error']}")
            self.lbl_reindex_msg.setStyleSheet("color: #FF4757; font-weight: bold;")
        else:
            added = stats.get("added", 0)
            updated = stats.get("updated", 0)
            unchanged = stats.get("unchanged", 0)
            total = stats.get("total_files", 0)
            self.lbl_reindex_msg.setText(f"✓ Reindexed! Total: {total} (New: {added}, Updated: {updated}, Unchanged: {unchanged})")
            self.lbl_reindex_msg.setStyleSheet("color: #00FF88; font-weight: bold;")
            self._refresh_knowledge_stats()

    def _test_microphone(self):
        self.btn_test_mic.setEnabled(False)
        self.voice_test_status.setText("Testing microphone input (listening 1.5s)...")
        self.voice_test_status.setStyleSheet("color: #00E5FF; font-style: italic;")

        device_index = self.combo_input_device.currentData()
        self._mic_worker = MicTestWorker(device_index=device_index)
        self._mic_worker.test_finished.connect(self._handle_mic_test_finished)
        self._mic_worker.start()

    def _handle_mic_test_finished(self, success: bool, msg: str):
        self.btn_test_mic.setEnabled(True)
        if success:
            self.voice_test_status.setText(f"✓ {msg}")
            self.voice_test_status.setStyleSheet("color: #00FF88; font-weight: bold;")
        else:
            self.voice_test_status.setText(f"✗ {msg}")
            self.voice_test_status.setStyleSheet("color: #FF4757; font-weight: bold;")

    def _test_voice_output(self):
        rate = self.spin_speech_rate.value()
        vol = self.slider_speech_volume.value() / 100.0
        self.voice_test_status.setText("Playing voice test audio...")
        self.voice_test_status.setStyleSheet("color: #00E5FF; font-style: italic;")

        def _on_done():
            self.voice_test_status.setText("✓ Voice output test completed.")
            self.voice_test_status.setStyleSheet("color: #00FF88; font-weight: bold;")

        self._synthesizer.speak(
            "This is a voice output test from Zero AI assistant. Speech synthesis online.",
            on_end=_on_done,
        )

    def _run_connection_test(self):
        """Execute non-blocking AI connection test."""
        settings = get_settings()
        api_base = self.input_api_base.text().strip() or settings.ai_api_base or "https://agent-router.net/aggregate/openai/v1"
        entered_key = self.input_api_key.text().strip()
        api_key = entered_key if entered_key else settings.ai_api_key
        preferred_model = self.input_model.text().strip() or settings.ai_model

        if not api_key:
            self.connection_status_label.setText("⚠ Missing API key in field or .env")
            self.connection_status_label.setStyleSheet("color: #FFB800; font-weight: bold;")
            return

        self.btn_test_connection.setEnabled(False)
        self.connection_status_label.setText("Testing connection...")
        self.connection_status_label.setStyleSheet("color: #00E5FF; font-style: italic;")

        self._test_worker = ConnectionTestWorker(
            api_base=api_base,
            api_key=api_key,
            preferred_model=preferred_model,
            update_env=False,
        )
        self._test_worker.test_completed.connect(self._handle_test_result)
        self._test_worker.start()

    def _handle_test_result(self, result: dict):
        self.btn_test_connection.setEnabled(True)
        auth = result.get("authentication", {})
        verified = result.get("verified_models", [])
        selected = result.get("selected_model")

        if auth.get("success") and verified:
            self.connection_status_label.setText(f"✓ Verified: {selected}")
            self.connection_status_label.setStyleSheet("color: #00FF88; font-weight: bold;")
            if selected:
                self.input_model.setText(selected)
            QMessageBox.information(
                self,
                "Connection Successful",
                f"AI Provider connection verified successfully!\n\n"
                f"Models discovered: {result.get('models_discovered')}\n"
                f"Verified: {', '.join(verified)}\n"
                f"Selected Default: {selected}",
            )
        else:
            cat = auth.get("category", "ERROR")
            err_msg = result.get("error_report") or auth.get("message") or "Connection failed"
            self.connection_status_label.setText(f"✗ Failed ({cat})")
            self.connection_status_label.setStyleSheet("color: #FF4757; font-weight: bold;")
            QMessageBox.warning(
                self,
                "Connection Failed",
                f"AI Connection Test Failed ({cat}):\n\n{err_msg}\n\n"
                f"Suggested Action:\n{result.get('suggested_fix', 'Check your API key and base URL.')}",
            )

    def _save_settings(self):
        """Persist settings updates with input validation."""
        settings = get_settings()
        chosen_provider = self.combo_provider.currentText()
        new_key = self.input_api_key.text().strip()

        # Validation: If cloud provider chosen, require key either existing or entered
        if chosen_provider in ["openai", "gemini", "anthropic"]:
            effective_key = new_key or settings.ai_api_key
            if not effective_key:
                QMessageBox.warning(
                    self,
                    "Validation Error",
                    f"Provider '{chosen_provider}' requires an API Key. Please provide an API key or use 'demo' provider.",
                )
                return

        # Update in-memory settings
        settings.ai_provider = chosen_provider
        settings.ai_api_base = self.input_api_base.text().strip()
        settings.ai_model = self.input_model.text().strip()

        if new_key:
            settings.ai_api_key = new_key

        settings.voice_enabled = self.chk_voice.isChecked()
        settings.wake_word_enabled = self.chk_wake_word.isChecked()
        settings.wake_word = self.input_wake_phrase.text().strip() or "zero wake up"

        settings.tts_voice_rate = self.spin_speech_rate.value()
        settings.tts_voice_volume = round(self.slider_speech_volume.value() / 100.0, 2)
        settings.voice_input_device = str(self.combo_input_device.currentData() or "")
        settings.voice_output_voice = str(self.combo_output_voice.currentData() or "")

        settings.briefing_on_startup = self.chk_briefing_startup.isChecked()
        settings.briefing_on_wake = self.chk_briefing_wake.isChecked()
        settings.reduced_motion = self.chk_reduced_motion.isChecked()
        settings.timezone = self.input_timezone.text().strip() or "Asia/Kolkata"

        # Update .env safely
        updates = {
            "AI_PROVIDER": settings.ai_provider,
            "AI_API_BASE": settings.ai_api_base,
            "AI_MODEL": settings.ai_model,
            "VOICE_ENABLED": str(settings.voice_enabled).lower(),
            "WAKE_WORD_ENABLED": str(settings.wake_word_enabled).lower(),
            "WAKE_WORD": settings.wake_word,
            "TTS_VOICE_RATE": str(settings.tts_voice_rate),
            "TTS_VOICE_VOLUME": str(settings.tts_voice_volume),
            "VOICE_INPUT_DEVICE": settings.voice_input_device,
            "VOICE_OUTPUT_VOICE": settings.voice_output_voice,
            "BRIEFING_ON_STARTUP": str(settings.briefing_on_startup).lower(),
            "BRIEFING_ON_WAKE": str(settings.briefing_on_wake).lower(),
            "REDUCED_MOTION": str(settings.reduced_motion).lower(),
            "TIMEZONE": settings.timezone,
        }
        if new_key:
            updates["AI_API_KEY"] = new_key

        tester = AIConnectionTester()
        tester.safe_update_env(updates)

        # Log activity event
        ActivityStore.record_activity("settings", "Updated assistant preferences.")
        self.load_current_settings()
        self.input_api_key.clear()
        self.settings_updated.emit()

        QMessageBox.information(self, "Settings Saved", "Zero configuration updated successfully.")

    def _clear_history(self):
        reply = QMessageBox.question(
            self,
            "Clear History",
            "Are you sure you want to delete all stored conversation history?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            ConversationStore.clear_all_conversations()
            QMessageBox.information(self, "History Cleared", "Conversation history cleared.")

    def _clear_activity(self):
        reply = QMessageBox.question(
            self,
            "Clear Activities",
            "Are you sure you want to clear stored activity logs and session summaries?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            ActivityStore.clear_all_activities()
            QMessageBox.information(self, "Activity Cleared", "Activity records cleared.")

    def _backup_db(self):
        backup_path = backup_database()
        if backup_path:
            QMessageBox.information(
                self, "Backup Complete", f"Database backed up to:\n{backup_path.name}"
            )
        else:
            QMessageBox.warning(self, "Backup Failed", "Unable to create database backup.")
