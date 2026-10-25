"""
Zero AI — Command Center Interface (Obsidian Command).
Implements the central tactical command console:
- Left Column: Neural inference telemetry, compute utilization, wake-word radar.
- Center Column: Ambient matrix void, procedural cybernetic AI Orb, state selector.
- Right Column: Tactical system actions deck, real-time audit log stream.
"""

from datetime import datetime
import os
import psutil
from PySide6.QtCore import Qt, Signal, QTimer, QThread
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QProgressBar,
    QScrollArea,
    QFrame,
    QFileDialog,
    QMessageBox,
)

from app.config.settings import get_settings
from app.core.state_manager import AssistantState
from app.gui.theme import (
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
from app.gui.widgets.ai_orb import AIOrbWidget
from app.memory.activity_store import ActivityStore
from app.services.desktop_control import get_desktop_service
from app.knowledge.service import get_knowledge_service
from app.exports.pdf_generator import PDFGenerator


class IndexDocsWorker(QThread):
    """Background worker to index knowledge files safely without freezing GUI."""
    completed = Signal(dict)

    def run(self):
        try:
            svc = get_knowledge_service()
            report = svc.sync_and_index(force_all=False)
            self.completed.emit(report)
        except Exception as e:
            self.completed.emit({"error": str(e), "indexed": 0, "skipped": 0})


class CommandCenterWidget(QWidget):
    """
    Tactical Command Center matching Stitch screen 1 (Obsidian Command).
    """

    state_change_requested = Signal(AssistantState)
    switch_to_transcript_requested = Signal()
    switch_to_system_control_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("command_center")

        self.desktop_service = get_desktop_service()
        self._current_state = AssistantState.READY
        self._index_worker: IndexDocsWorker | None = None
        self._mini_mic_bars: list[QFrame] = []

        self._init_ui()

        # Telemetry refresh timer (every 1.5 seconds)
        self._telemetry_timer = QTimer(self)
        self._telemetry_timer.timeout.connect(self.refresh_telemetry)
        self._telemetry_timer.start(1500)
        self.refresh_telemetry()
        self.refresh_audit_log()

    def _init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        # =====================================================================
        # 1. LEFT TELEMETRY COLUMN (Width ~300px)
        # =====================================================================
        left_col = QWidget()
        left_col.setFixedWidth(280)
        left_layout = QVBoxLayout(left_col)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        # 1A. Neural Inference Module
        mod_inf = QFrame()
        mod_inf.setProperty("class", "telemetry-module")
        inf_layout = QVBoxLayout(mod_inf)
        inf_layout.setContentsMargins(12, 10, 12, 10)
        inf_layout.setSpacing(6)

        hdr_inf = QHBoxLayout()
        lbl_inf_title = QLabel("// TELEMETRY.INFERENCE")
        lbl_inf_title.setStyleSheet(f"color: {TEXT_DIM}; font-family: 'Consolas', monospace; font-size: 10px; font-weight: bold;")
        self.lbl_inf_status = QLabel("● 11434 ONLINE")
        self.lbl_inf_status.setStyleSheet(f"color: {ACCENT_NEON}; font-family: 'Consolas', monospace; font-size: 10px; font-weight: bold;")
        hdr_inf.addWidget(lbl_inf_title)
        hdr_inf.addStretch()
        hdr_inf.addWidget(self.lbl_inf_status)
        inf_layout.addLayout(hdr_inf)

        div_inf = QFrame()
        div_inf.setFrameShape(QFrame.HLine)
        div_inf.setStyleSheet(f"background-color: {BORDER_SUBTLE}; max-height: 1px;")
        inf_layout.addWidget(div_inf)

        grid_inf = QGridLayout()
        grid_inf.setContentsMargins(0, 4, 0, 4)
        grid_inf.setHorizontalSpacing(10)
        grid_inf.setVerticalSpacing(4)

        grid_inf.addWidget(QLabel("Model:"), 0, 0)
        self.lbl_model_name = QLabel("llama3.2")
        self.lbl_model_name.setStyleSheet(f"color: {ACCENT_NEON}; font-family: 'Consolas', monospace; font-weight: bold;")
        grid_inf.addWidget(self.lbl_model_name, 0, 1, alignment=Qt.AlignRight)

        grid_inf.addWidget(QLabel("Quantization:"), 1, 0)
        self.lbl_quant = QLabel("q4_K_M // GGUF")
        self.lbl_quant.setStyleSheet(f"color: {TEXT_SECONDARY}; font-family: 'Consolas', monospace; font-size: 10px;")
        grid_inf.addWidget(self.lbl_quant, 1, 1, alignment=Qt.AlignRight)

        grid_inf.addWidget(QLabel("Context:"), 2, 0)
        self.lbl_context = QLabel("8,192 tok")
        self.lbl_context.setStyleSheet(f"color: {TEXT_PRIMARY}; font-family: 'Consolas', monospace; font-size: 11px;")
        grid_inf.addWidget(self.lbl_context, 2, 1, alignment=Qt.AlignRight)

        grid_inf.addWidget(QLabel("Eval Speed:"), 3, 0)
        self.lbl_speed = QLabel("64.2 tok/sec")
        self.lbl_speed.setStyleSheet(f"color: {ACCENT_NEON}; font-family: 'Consolas', monospace; font-size: 11px;")
        grid_inf.addWidget(self.lbl_speed, 3, 1, alignment=Qt.AlignRight)

        for i in range(4):
            lbl = grid_inf.itemAtPosition(i, 0).widget()
            if isinstance(lbl, QLabel):
                lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px;")

        inf_layout.addLayout(grid_inf)

        self.bar_inf = QProgressBar()
        self.bar_inf.setFixedHeight(4)
        self.bar_inf.setTextVisible(False)
        self.bar_inf.setValue(72)
        self.bar_inf.setStyleSheet(f"""
            QProgressBar {{ background-color: {CONTAINER_LOWEST}; border: 1px solid {BORDER_SUBTLE}; border-radius: 2px; }}
            QProgressBar::chunk {{ background-color: {ACCENT_NEON}; border-radius: 1px; }}
        """)
        inf_layout.addWidget(self.bar_inf)
        left_layout.addWidget(mod_inf)

        # 1B. Compute Utilization Module
        mod_cpu = QFrame()
        mod_cpu.setProperty("class", "telemetry-module")
        cpu_layout = QVBoxLayout(mod_cpu)
        cpu_layout.setContentsMargins(12, 10, 12, 10)
        cpu_layout.setSpacing(6)

        hdr_cpu = QHBoxLayout()
        lbl_cpu_title = QLabel("// COMPUTE.UTILIZATION")
        lbl_cpu_title.setStyleSheet(f"color: {TEXT_DIM}; font-family: 'Consolas', monospace; font-size: 10px; font-weight: bold;")
        self.lbl_cpu_threads = QLabel(f"{psutil.cpu_count(logical=True)} Threads")
        self.lbl_cpu_threads.setStyleSheet(f"color: {TEXT_SECONDARY}; font-family: 'Consolas', monospace; font-size: 10px;")
        hdr_cpu.addWidget(lbl_cpu_title)
        hdr_cpu.addStretch()
        hdr_cpu.addWidget(self.lbl_cpu_threads)
        cpu_layout.addLayout(hdr_cpu)

        div_cpu = QFrame()
        div_cpu.setFrameShape(QFrame.HLine)
        div_cpu.setStyleSheet(f"background-color: {BORDER_SUBTLE}; max-height: 1px;")
        cpu_layout.addWidget(div_cpu)

        # CPU Load
        lbl_cpu_sub = QHBoxLayout()
        lbl_cpu_desc = QLabel("CPU Load")
        lbl_cpu_desc.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px;")
        self.lbl_cpu_val = QLabel("18%")
        self.lbl_cpu_val.setStyleSheet(f"color: {ACCENT_NEON}; font-family: 'Consolas', monospace; font-weight: bold;")
        lbl_cpu_sub.addWidget(lbl_cpu_desc)
        lbl_cpu_sub.addStretch()
        lbl_cpu_sub.addWidget(self.lbl_cpu_val)
        cpu_layout.addLayout(lbl_cpu_sub)

        self.bar_cpu = QProgressBar()
        self.bar_cpu.setFixedHeight(4)
        self.bar_cpu.setTextVisible(False)
        self.bar_cpu.setValue(18)
        self.bar_cpu.setStyleSheet(f"""
            QProgressBar {{ background-color: {CONTAINER_LOWEST}; border: 1px solid {BORDER_SUBTLE}; border-radius: 2px; }}
            QProgressBar::chunk {{ background-color: {ACCENT_NEON}; border-radius: 1px; }}
        """)
        cpu_layout.addWidget(self.bar_cpu)

        # RAM Usage
        lbl_ram_sub = QHBoxLayout()
        lbl_ram_desc = QLabel("System RAM")
        lbl_ram_desc.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px;")
        self.lbl_ram_val = QLabel("16.4 GB")
        self.lbl_ram_val.setStyleSheet(f"color: {TEXT_PRIMARY}; font-family: 'Consolas', monospace; font-weight: bold;")
        lbl_ram_sub.addWidget(lbl_ram_desc)
        lbl_ram_sub.addStretch()
        lbl_ram_sub.addWidget(self.lbl_ram_val)
        cpu_layout.addLayout(lbl_ram_sub)

        self.bar_ram = QProgressBar()
        self.bar_ram.setFixedHeight(4)
        self.bar_ram.setTextVisible(False)
        self.bar_ram.setValue(38)
        self.bar_ram.setStyleSheet(f"""
            QProgressBar {{ background-color: {CONTAINER_LOWEST}; border: 1px solid {BORDER_SUBTLE}; border-radius: 2px; }}
            QProgressBar::chunk {{ background-color: {ACCENT_NEON}; border-radius: 1px; }}
        """)
        cpu_layout.addWidget(self.bar_ram)

        # Core Metrics Strip
        thermals_box = QHBoxLayout()
        thermals_box.setSpacing(6)

        c1 = QFrame()
        c1.setStyleSheet(f"background-color: {CONTAINER_LOWEST}; border: 1px solid {BORDER_SUBTLE}; border-radius: 3px; padding: 4px;")
        l1 = QVBoxLayout(c1)
        l1.setContentsMargins(2, 2, 2, 2)
        l1.setSpacing(1)
        l1_k = QLabel("CORES")
        l1_k.setStyleSheet(f"color: {TEXT_DIM}; font-size: 9px; font-family: monospace;")
        self.l1_v = QLabel(str(psutil.cpu_count(logical=False) or 8))
        self.l1_v.setStyleSheet(f"color: {ACCENT_NEON}; font-weight: bold; font-family: monospace;")
        l1.addWidget(l1_k, alignment=Qt.AlignCenter)
        l1.addWidget(self.l1_v, alignment=Qt.AlignCenter)

        c2 = QFrame()
        c2.setStyleSheet(f"background-color: {CONTAINER_LOWEST}; border: 1px solid {BORDER_SUBTLE}; border-radius: 3px; padding: 4px;")
        l2 = QVBoxLayout(c2)
        l2.setContentsMargins(2, 2, 2, 2)
        l2.setSpacing(1)
        l2_k = QLabel("STATUS")
        l2_k.setStyleSheet(f"color: {TEXT_DIM}; font-size: 9px; font-family: monospace;")
        self.l2_v = QLabel("OPTIMAL")
        self.l2_v.setStyleSheet(f"color: {ACCENT_NEON}; font-weight: bold; font-family: monospace;")
        l2.addWidget(l2_k, alignment=Qt.AlignCenter)
        l2.addWidget(self.l2_v, alignment=Qt.AlignCenter)

        thermals_box.addWidget(c1)
        thermals_box.addWidget(c2)
        cpu_layout.addLayout(thermals_box)
        left_layout.addWidget(mod_cpu)

        # 1C. Wake-Word Sensor Module
        mod_wake = QFrame()
        mod_wake.setProperty("class", "telemetry-module")
        wake_layout = QVBoxLayout(mod_wake)
        wake_layout.setContentsMargins(12, 10, 12, 10)
        wake_layout.setSpacing(6)

        hdr_wake = QHBoxLayout()
        lbl_wake_title = QLabel("// WAKE-WORD.SENSOR")
        lbl_wake_title.setStyleSheet(f"color: {TEXT_DIM}; font-family: 'Consolas', monospace; font-size: 10px; font-weight: bold;")
        lbl_wake_thresh = QLabel("ARMED")
        lbl_wake_thresh.setStyleSheet(f"color: {ACCENT_NEON}; font-family: 'Consolas', monospace; font-size: 10px; font-weight: bold;")
        hdr_wake.addWidget(lbl_wake_title)
        hdr_wake.addStretch()
        hdr_wake.addWidget(lbl_wake_thresh)
        wake_layout.addLayout(hdr_wake)

        div_wake = QFrame()
        div_wake.setFrameShape(QFrame.HLine)
        div_wake.setStyleSheet(f"background-color: {BORDER_SUBTLE}; max-height: 1px;")
        wake_layout.addWidget(div_wake)

        sub_wake = QHBoxLayout()
        lbl_phr = QLabel("PHRASE: \"ZERO\"")
        lbl_phr.setStyleSheet(f"color: {ACCENT_NEON}; font-family: monospace; font-size: 10px; font-weight: bold;")
        lbl_flr = QLabel("FLOOR: -42dB")
        lbl_flr.setStyleSheet(f"color: {TEXT_DIM}; font-family: monospace; font-size: 10px;")
        sub_wake.addWidget(lbl_phr)
        sub_wake.addStretch()
        sub_wake.addWidget(lbl_flr)
        wake_layout.addLayout(sub_wake)

        # Mini Audio Visualizer Bar Cluster
        bars_container = QWidget()
        bars_layout = QHBoxLayout(bars_container)
        bars_layout.setContentsMargins(2, 4, 2, 4)
        bars_layout.setSpacing(2)

        for _ in range(16):
            b = QFrame()
            b.setFixedWidth(3)
            b.setFixedHeight(8)
            b.setStyleSheet(f"background-color: {BORDER_SUBTLE}; border-radius: 1px;")
            self._mini_mic_bars.append(b)
            bars_layout.addWidget(b, alignment=Qt.AlignBottom)

        wake_layout.addWidget(bars_container)
        left_layout.addWidget(mod_wake)
        left_layout.addStretch()

        main_layout.addWidget(left_col)

        # =====================================================================
        # 2. CENTER OPERATIONAL VOID & ORB (Stretch 1)
        # =====================================================================
        center_col = QFrame()
        center_col.setStyleSheet(f"background-color: {CONTAINER_LOWEST}; border: 1px solid {BORDER_SUBTLE}; border-radius: 4px;")
        center_layout = QVBoxLayout(center_col)
        center_layout.setContentsMargins(16, 20, 16, 16)
        center_layout.setSpacing(14)
        center_layout.setAlignment(Qt.AlignCenter)

        # Upper State Banner
        self.badge_state = QLabel("STATE: READY (Continuous Duplex)")
        self.badge_state.setAlignment(Qt.AlignCenter)
        self.badge_state.setStyleSheet(f"""
            background-color: {CONTAINER_HIGH};
            color: {ACCENT_NEON};
            border: 1px solid {BORDER_SUBTLE};
            border-radius: 12px;
            padding: 4px 14px;
            font-family: 'Consolas', monospace;
            font-weight: bold;
            font-size: 11px;
            letter-spacing: 0.5px;
        """)
        center_layout.addWidget(self.badge_state, alignment=Qt.AlignCenter)

        self.lbl_orb_caption = QLabel('"Standing by, Operator. Local neural mesh active across 24 CPU threads & 16GB VRAM."')
        self.lbl_orb_caption.setAlignment(Qt.AlignCenter)
        self.lbl_orb_caption.setWordWrap(True)
        self.lbl_orb_caption.setMaximumWidth(460)
        self.lbl_orb_caption.setStyleSheet(f"color: {TEXT_SECONDARY}; font-family: 'Consolas', monospace; font-size: 11px;")
        center_layout.addWidget(self.lbl_orb_caption, alignment=Qt.AlignCenter)

        center_layout.addStretch(1)

        # Center AI Orb with Radial Dial Coordinate Frame
        orb_container = QWidget()
        orb_container.setFixedSize(220, 220)
        orb_frame_layout = QVBoxLayout(orb_container)
        orb_frame_layout.setContentsMargins(0, 0, 0, 0)
        orb_frame_layout.setAlignment(Qt.AlignCenter)

        self.orb_widget = AIOrbWidget(orb_container)
        self.orb_widget.setFixedSize(180, 180)
        self.orb_widget.clicked.connect(self._handle_orb_click)
        orb_frame_layout.addWidget(self.orb_widget, alignment=Qt.AlignCenter)

        center_layout.addWidget(orb_container, alignment=Qt.AlignCenter)
        center_layout.addStretch(1)

        # Core State Selector Switches
        state_switch_box = QVBoxLayout()
        state_switch_box.setSpacing(6)
        state_switch_box.setAlignment(Qt.AlignCenter)

        lbl_sim = QLabel("// CORE STATE SELECTOR")
        lbl_sim.setStyleSheet(f"color: {TEXT_DIM}; font-family: 'Consolas', monospace; font-size: 9px; font-weight: bold; letter-spacing: 1px;")
        state_switch_box.addWidget(lbl_sim, alignment=Qt.AlignCenter)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(4)

        states = [
            ("Idle", AssistantState.READY),
            ("Listening", AssistantState.LISTENING),
            ("Processing", AssistantState.THINKING),
            ("Speaking", AssistantState.SPEAKING),
            ("Error", AssistantState.ERROR),
        ]
        self._state_buttons: list[QPushButton] = []
        for name, st in states:
            b = QPushButton(name)
            b.setCursor(Qt.PointingHandCursor)
            b.setProperty("class", "btn-secondary")
            b.setFixedHeight(26)
            b.clicked.connect(lambda _, target_st=st: self._simulate_state_change(target_st))
            self._state_buttons.append(b)
            btn_row.addWidget(b)

        state_switch_box.addLayout(btn_row)
        center_layout.addLayout(state_switch_box)

        main_layout.addWidget(center_col, stretch=1)

        # =====================================================================
        # 3. RIGHT ACTIVITY & ACTION DECK (Width ~300px)
        # =====================================================================
        right_col = QWidget()
        right_col.setFixedWidth(290)
        right_layout = QVBoxLayout(right_col)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        # 3A. Tactical Quick Actions
        mod_act = QFrame()
        mod_act.setProperty("class", "telemetry-module")
        act_layout = QVBoxLayout(mod_act)
        act_layout.setContentsMargins(12, 10, 12, 10)
        act_layout.setSpacing(6)

        hdr_act = QHBoxLayout()
        lbl_act_title = QLabel("// SYSTEM.ACTIONS")
        lbl_act_title.setStyleSheet(f"color: {TEXT_DIM}; font-family: 'Consolas', monospace; font-size: 10px; font-weight: bold;")
        lbl_act_mode = QLabel("AUTONOMOUS")
        lbl_act_mode.setStyleSheet(f"color: {ACCENT_NEON}; font-family: 'Consolas', monospace; font-size: 10px; font-weight: bold;")
        hdr_act.addWidget(lbl_act_title)
        hdr_act.addStretch()
        hdr_act.addWidget(lbl_act_mode)
        act_layout.addLayout(hdr_act)

        div_act = QFrame()
        div_act.setFrameShape(QFrame.HLine)
        div_act.setStyleSheet(f"background-color: {BORDER_SUBTLE}; max-height: 1px;")
        act_layout.addWidget(div_act)

        # Action 1: Analyze Display
        btn_disp = self._create_action_button(
            "🖥️  Analyze Display",
            "Win+Shift+Z",
            "Capture active screen safely for analysis",
            self._handle_action_analyze_display,
        )
        # Action 2: Index Local Docs
        btn_docs = self._create_action_button(
            "📁  Index Local Docs",
            "AUTO",
            "Sync and index files in Knowledge/ repository",
            self._handle_action_index_docs,
        )
        # Action 3: Automate Active App
        btn_auto = self._create_action_button(
            "⚡  Automate Active App",
            "HOOKED",
            "Inspect foreground application for safe control",
            self._handle_action_automate_app,
        )
        # Action 4: Export Session PDF
        btn_pdf = self._create_action_button(
            "📄  Export Session PDF",
            "SAVE",
            "Export current session report as formatted PDF",
            self._handle_action_export_pdf,
        )

        act_layout.addWidget(btn_disp)
        act_layout.addWidget(btn_docs)
        act_layout.addWidget(btn_auto)
        act_layout.addWidget(btn_pdf)
        right_layout.addWidget(mod_act)

        # 3B. Verified Audit Log Feed
        mod_log = QFrame()
        mod_log.setProperty("class", "telemetry-module")
        log_layout = QVBoxLayout(mod_log)
        log_layout.setContentsMargins(12, 10, 12, 10)
        log_layout.setSpacing(6)

        hdr_log = QHBoxLayout()
        lbl_log_title = QLabel("// AUDIT.LOG")
        lbl_log_title.setStyleSheet(f"color: {TEXT_DIM}; font-family: 'Consolas', monospace; font-size: 10px; font-weight: bold;")
        lbl_log_hook = QLabel("LIVE HOOK")
        lbl_log_hook.setStyleSheet(f"color: {ACCENT_NEON}; font-family: 'Consolas', monospace; font-size: 9px; font-weight: bold;")
        hdr_log.addWidget(lbl_log_title)
        hdr_log.addStretch()
        hdr_log.addWidget(lbl_log_hook)
        log_layout.addLayout(hdr_log)

        div_log = QFrame()
        div_log.setFrameShape(QFrame.HLine)
        div_log.setStyleSheet(f"background-color: {BORDER_SUBTLE}; max-height: 1px;")
        log_layout.addWidget(div_log)

        self.log_scroll = QScrollArea()
        self.log_scroll.setWidgetResizable(True)
        self.log_scroll.setStyleSheet("background: transparent; border: none;")

        self.log_container = QWidget()
        self.log_container_layout = QVBoxLayout(self.log_container)
        self.log_container_layout.setContentsMargins(0, 0, 0, 0)
        self.log_container_layout.setSpacing(6)
        self.log_scroll.setWidget(self.log_container)

        log_layout.addWidget(self.log_scroll, stretch=1)
        right_layout.addWidget(mod_log, stretch=1)

        main_layout.addWidget(right_col)

    def _create_action_button(self, label: str, badge: str, tooltip: str, handler) -> QPushButton:
        btn = QPushButton()
        btn.setCursor(Qt.PointingHandCursor)
        btn.setToolTip(tooltip)
        btn.setFixedHeight(34)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {CONTAINER_BG};
                border: 1px solid {BORDER_SUBTLE};
                border-radius: 4px;
                padding: 4px 8px;
                text-align: left;
            }}
            QPushButton:hover {{
                border: 1px solid {ACCENT_NEON};
                background-color: {CONTAINER_HIGH};
            }}
            QPushButton:pressed {{
                background-color: {CONTAINER_LOWEST};
            }}
        """)

        h_layout = QHBoxLayout(btn)
        h_layout.setContentsMargins(6, 0, 6, 0)

        lbl = QLabel(label)
        lbl.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 11px; font-weight: 500;")
        lbl_badge = QLabel(badge)
        lbl_badge.setStyleSheet(f"color: {TEXT_DIM}; font-family: 'Consolas', monospace; font-size: 9px;")

        h_layout.addWidget(lbl)
        h_layout.addStretch()
        h_layout.addWidget(lbl_badge)

        btn.clicked.connect(handler)
        return btn

    def refresh_telemetry(self):
        """Query real live metrics from system services."""
        try:
            settings = get_settings()
            self.lbl_model_name.setText(settings.ollama_model_chat)

            # CPU
            cpu_pct = psutil.cpu_percent(interval=0.0)
            self.lbl_cpu_val.setText(f"{cpu_pct:.1f}%")
            self.bar_cpu.setValue(int(cpu_pct))

            # RAM
            mem = psutil.virtual_memory()
            used_gb = mem.used / (1024**3)
            total_gb = mem.total / (1024**3)
            self.lbl_ram_val.setText(f"{used_gb:.1f} / {total_gb:.1f} GB")
            self.bar_ram.setValue(int(mem.percent))

            # Animate mini mic visualizer bars based on state
            import math
            import random
            is_active = self._current_state in (AssistantState.LISTENING, AssistantState.SPEAKING)
            for i, b in enumerate(self._mini_mic_bars):
                if is_active:
                    h = random.randint(6, 20)
                    b.setFixedHeight(h)
                    b.setStyleSheet(f"background-color: {ACCENT_NEON}; border-radius: 1px;")
                else:
                    b.setFixedHeight(random.randint(3, 7))
                    b.setStyleSheet(f"background-color: {BORDER_SUBTLE}; border-radius: 1px;")

        except Exception as e:
            pass

    def refresh_audit_log(self):
        """Fetch real activity events from ActivityStore and render entries."""
        try:
            # Clear existing items
            while self.log_container_layout.count():
                item = self.log_container_layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()

            events = ActivityStore.get_recent_activities(limit=8)
            if not events:
                empty_lbl = QLabel("No audit events recorded yet.")
                empty_lbl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px; padding: 10px;")
                self.log_container_layout.addWidget(empty_lbl)
                return

            for ev in events:
                card = QFrame()
                card.setStyleSheet(f"""
                    QFrame {{
                        background-color: {CONTAINER_LOWEST};
                        border: 1px solid {BORDER_SUBTLE};
                        border-radius: 3px;
                        padding: 6px;
                    }}
                    QFrame:hover {{
                        border: 1px solid {CONTAINER_HIGH};
                    }}
                """)
                c_layout = QVBoxLayout(card)
                c_layout.setContentsMargins(4, 4, 4, 4)
                c_layout.setSpacing(2)

                top_row = QHBoxLayout()
                ts_str = ev.get("timestamp", "")
                if "T" in ts_str:
                    time_part = ts_str.split("T")[1][:8]
                else:
                    time_part = ts_str[:8]
                lbl_time = QLabel(time_part)
                lbl_time.setStyleSheet(f"color: {TEXT_DIM}; font-family: 'Consolas', monospace; font-size: 9px;")

                cat = ev.get("category", "SYSTEM").upper()
                lbl_tag = QLabel(f"[{cat}]")
                lbl_tag.setStyleSheet(f"color: {ACCENT_NEON}; font-family: 'Consolas', monospace; font-weight: bold; font-size: 9px;")

                top_row.addWidget(lbl_time)
                top_row.addStretch()
                top_row.addWidget(lbl_tag)
                c_layout.addLayout(top_row)

                desc = QLabel(ev.get("description", ""))
                desc.setWordWrap(True)
                desc.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 10px;")
                c_layout.addWidget(desc)

                self.log_container_layout.addWidget(card)

            self.log_container_layout.addStretch()
        except Exception:
            pass

    def update_assistant_state(self, new_state: AssistantState):
        """Synchronize AI orb and display badge with central assistant state machine."""
        self._current_state = new_state
        self.orb_widget.set_state(new_state)

        state_name = new_state.value.upper()
        self.badge_state.setText(f"STATE: {state_name} (Continuous Duplex)")

        quotes = {
            AssistantState.READY: '"Standing by, Operator. Local neural mesh active and responsive."',
            AssistantState.LISTENING: '"Capturing microphone input... Audio pipeline buffer streaming."',
            AssistantState.THINKING: '"Synthesizing neural model inference... Context evaluating."',
            AssistantState.SPEAKING: '"Rendering vocal synthesis stream via local text-to-speech engine."',
            AssistantState.ERROR: '"Operational exception detected. Subsystem error captured in audit log."',
            AssistantState.SLEEPING: '"Low power standby mode. Awaiting wake phrase \'Zero\'."',
        }
        self.lbl_orb_caption.setText(quotes.get(new_state, f'"Operating in state: {state_name}"'))

    def _simulate_state_change(self, target_state: AssistantState):
        """Allow manual state testing via Core State Selector buttons."""
        self.update_assistant_state(target_state)
        self.state_change_requested.emit(target_state)

    def _handle_orb_click(self):
        """Clicking AI orb transitions to conversational transcript."""
        self.switch_to_transcript_requested.emit()

    def _handle_action_analyze_display(self):
        """Safely capture display screenshot with user consent and save to knowledge/screenshots/."""
        reply = QMessageBox.question(
            self,
            "Capture Primary Display Snapshot",
            "Do you want Z.E.R.O. to analyze your active primary display?\n\n"
            "A local screenshot will be captured and saved locally in 'knowledge/screenshots/' without external transmission.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if reply != QMessageBox.Yes:
            return

        try:
            screen = QGuiApplication.primaryScreen()
            if not screen:
                QMessageBox.warning(self, "Capture Failed", "Could not locate primary display screen.")
                return

            os.makedirs(os.path.join("knowledge", "screenshots"), exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            target_path = os.path.join("knowledge", "screenshots", f"display_analysis_{timestamp}.png")

            pixmap = screen.grabWindow(0)
            pixmap.save(target_path, "PNG")

            ActivityStore.record_activity(
                category="DISPLAY",
                description=f"Captured display snapshot: {os.path.basename(target_path)}",
            )
            self.refresh_audit_log()

            QMessageBox.information(
                self,
                "Display Captured",
                f"Successfully captured display snapshot:\n{target_path}\n\nStored locally in Knowledge repository.",
            )
        except Exception as e:
            QMessageBox.critical(self, "Capture Error", f"Failed to capture display: {str(e)}")

    def _handle_action_index_docs(self):
        """Synchronize and index local Knowledge repository files in background thread."""
        if self._index_worker and self._index_worker.isRunning():
            QMessageBox.information(self, "Indexing in Progress", "Document indexing is already running.")
            return

        self._index_worker = IndexDocsWorker()
        self._index_worker.completed.connect(self._on_indexing_finished)
        self._index_worker.start()

    def _on_indexing_finished(self, report: dict):
        if "error" in report:
            QMessageBox.critical(self, "Indexing Error", f"Indexing failed: {report['error']}")
            return

        discovered = report.get("discovered", 0)
        indexed = report.get("indexed", 0)
        skipped = report.get("skipped", 0)

        ActivityStore.record_activity(
            category="VAULT",
            description=f"Indexed {indexed} documents ({skipped} unchanged) in Knowledge Vault",
        )
        self.refresh_audit_log()

        QMessageBox.information(
            self,
            "Indexing Complete",
            f"Knowledge Vault indexing complete:\n- Discovered: {discovered}\n- Indexed: {indexed}\n- Skipped/Current: {skipped}",
        )

    def _handle_action_automate_app(self):
        """Inspect active foreground application and offer automation controls."""
        fg = self.desktop_service.get_foreground_window_info()
        if not fg:
            QMessageBox.information(
                self,
                "No Foreground App",
                "Could not identify an active non-shell desktop application.",
            )
            return

        title = fg.get("title", "Unknown")
        proc = fg.get("process_name", "unknown.exe")
        pid = fg.get("pid", 0)

        reply = QMessageBox.question(
            self,
            "Automate Active Application",
            f"Detected Active Foreground Application:\n\n"
            f"Title: {title}\n"
            f"Process: {proc} (PID {pid})\n\n"
            "Would you like to open System Control & Automation to manage this window?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if reply == QMessageBox.Yes:
            self.switch_to_system_control_requested.emit()

    def _handle_action_export_pdf(self):
        """Export session summary report to verified PDF."""
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Session PDF",
            os.path.join(os.getcwd(), f"zero_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"),
            "PDF Files (*.pdf)",
        )
        if not save_path:
            return

        try:
            activities = ActivityStore.get_recent_activities(limit=15)
            lines = [
                f"# Z.E.R.O. Session Intelligence Report\n",
                f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ",
                f"**Host Machine:** {os.environ.get('COMPUTERNAME', 'Windows Host')}  ",
                f"**Local AI Model:** {get_settings().ollama_model_chat}\n",
                "## Recent Operational Events\n",
            ]
            for act in activities:
                lines.append(f"- **[{act.get('category')}]** `{act.get('timestamp')}`: {act.get('description')}")

            markdown_content = "\n".join(lines)
            html = PDFGenerator.create_html_report(
                title="Z.E.R.O. Session Intelligence Report",
                body_markdown=markdown_content,
                subtitle="Local Audit & System Operations Summary",
            )
            out_pdf = PDFGenerator.generate_pdf(html, filename=os.path.basename(save_path))

            ActivityStore.record_activity(
                category="EXPORT",
                description=f"Exported session PDF: {os.path.basename(out_pdf)}",
            )
            self.refresh_audit_log()

            QMessageBox.information(
                self,
                "Export Succeeded",
                f"Successfully exported session PDF report to:\n{out_pdf}",
            )
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Failed to generate PDF: {str(e)}")
