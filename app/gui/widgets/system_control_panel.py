"""
Zero AI — System Control & Automation Panel (Obsidian Command).
Implements the third Stitch screen:
- Top Header: Live window and host telemetry chips (Detected windows, controlled apps, host load).
- Security Notice: Controlled Automation banner (Ring-3 safe isolation).
- Left Section (8 cols): Managed Window Registry bento-grid with real live window data
  from DesktopControlService, providing FOCUS, MINIMIZE, MAXIMIZE, RESTORE, CLOSE,
  SEND TO BG, and TILE LEFT operations.
- Bottom Event Stream: Real-time Win32 automation interop event log.
- Right Section (4 cols): Contextual Ambiguity Resolution modal & Allowlisted Command Palette (Ctrl+K).
"""

from datetime import datetime
import psutil
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QScrollArea,
    QFrame,
    QMessageBox,
)

from app.gui.theme import (
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
from app.services.desktop_control import get_desktop_service
from app.memory.activity_store import ActivityStore


class WindowCardWidget(QFrame):
    """Bento-grid card representing a single managed application window."""

    action_triggered = Signal(str, int, str)  # action_name, hwnd, title

    def __init__(self, win_data: dict, parent=None):
        super().__init__(parent)
        self.win_data = win_data
        self.hwnd = win_data.get("hwnd", 0)
        self.title = win_data.get("title", "")
        self.pid = win_data.get("pid", 0)
        self.proc_name = win_data.get("process_name", "")
        self.is_focused = win_data.get("is_focused", False)
        self.is_minimized = win_data.get("is_minimized", False)
        self.is_maximized = win_data.get("is_maximized", False)
        self.mem_mb = win_data.get("memory_mb", 0.0)

        self._init_ui()

    def _init_ui(self):
        border_col = ACCENT_NEON if self.is_focused else BORDER_SUBTLE
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {CONTAINER_BG};
                border: 1px solid {border_col};
                border-radius: 4px;
                padding: 4px;
            }}
            QFrame:hover {{
                border: 1px solid {ACCENT_NEON};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        # 1. Header row
        hdr = QHBoxLayout()
        hdr.setSpacing(6)

        dot = QLabel("●" if self.is_focused else "○")
        dot.setStyleSheet(f"color: {ACCENT_NEON if self.is_focused else TEXT_DIM}; font-size: 10px;")
        hdr.addWidget(dot)

        app_name = self.proc_name.replace(".exe", "").capitalize() or "Application"
        lbl_app = QLabel(app_name)
        lbl_app.setStyleSheet(f"color: {TEXT_PRIMARY}; font-family: 'Consolas', monospace; font-weight: bold; font-size: 11px;")
        hdr.addWidget(lbl_app)

        lbl_pid = QLabel(f"PID: {self.pid}")
        lbl_pid.setStyleSheet(f"color: {TEXT_DIM}; font-family: 'Consolas', monospace; font-size: 9px;")
        hdr.addWidget(lbl_pid)
        hdr.addStretch()

        badge_text = "FOCUSED" if self.is_focused else ("MINIMIZED" if self.is_minimized else "ACTIVE")
        badge_color = ACCENT_NEON if self.is_focused else (ACCENT_WARNING if self.is_minimized else TEXT_SECONDARY)
        lbl_badge = QLabel(badge_text)
        lbl_badge.setStyleSheet(f"""
            background-color: {CONTAINER_HIGH};
            color: {badge_color};
            border: 1px solid {BORDER_SUBTLE};
            border-radius: 2px;
            padding: 1px 4px;
            font-family: 'Consolas', monospace;
            font-size: 9px;
            font-weight: bold;
        """)
        hdr.addWidget(lbl_badge)
        layout.addLayout(hdr)

        # 2. Window Title bar
        lbl_title = QLabel(f"> {self.title}")
        lbl_title.setToolTip(self.title)
        lbl_title.setStyleSheet(f"""
            background-color: {CONTAINER_LOWEST};
            color: {TEXT_PRIMARY};
            border: 1px solid {BORDER_SUBTLE};
            border-radius: 2px;
            padding: 4px 6px;
            font-family: 'Consolas', monospace;
            font-size: 10px;
        """)
        lbl_title.setWordWrap(False)
        layout.addWidget(lbl_title)

        # 3. Telemetry line
        telem_row = QHBoxLayout()
        lbl_res = QLabel(f"RESOURCE: ~{self.mem_mb} MB RAM")
        lbl_res.setStyleSheet(f"color: {TEXT_SECONDARY}; font-family: 'Consolas', monospace; font-size: 9px;")
        telem_row.addWidget(lbl_res)
        telem_row.addStretch()
        layout.addLayout(telem_row)

        # 4. Action Buttons Grid
        btn_grid = QGridLayout()
        btn_grid.setContentsMargins(0, 4, 0, 0)
        btn_grid.setSpacing(4)

        b_focus = self._create_card_btn("FOCUS", "btn-primary", lambda: self.action_triggered.emit("focus", self.hwnd, self.title))
        b_min = self._create_card_btn("MIN", "btn-secondary", lambda: self.action_triggered.emit("minimize", self.hwnd, self.title))
        b_max = self._create_card_btn("MAX", "btn-secondary", lambda: self.action_triggered.emit("maximize", self.hwnd, self.title))
        b_tile = self._create_card_btn("TILE L", "btn-secondary", lambda: self.action_triggered.emit("tile_left", self.hwnd, self.title))
        b_bg = self._create_card_btn("SEND BG", "btn-secondary", lambda: self.action_triggered.emit("send_to_bg", self.hwnd, self.title))
        b_close = self._create_card_btn("CLOSE", "btn-danger", lambda: self.action_triggered.emit("close", self.hwnd, self.title))

        btn_grid.addWidget(b_focus, 0, 0)
        btn_grid.addWidget(b_min, 0, 1)
        btn_grid.addWidget(b_max, 0, 2)
        btn_grid.addWidget(b_tile, 1, 0)
        btn_grid.addWidget(b_bg, 1, 1)
        btn_grid.addWidget(b_close, 1, 2)

        layout.addLayout(btn_grid)

    def _create_card_btn(self, text: str, css_class: str, handler) -> QPushButton:
        btn = QPushButton(text)
        btn.setProperty("class", css_class)
        btn.setFixedHeight(22)
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(handler)
        return btn


class SystemControlWidget(QWidget):
    """
    Managed Window Registry and Windows Automation Workspace.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("system_control_view")

        self.desktop_service = get_desktop_service()
        self._cards: list[WindowCardWidget] = []
        self._candidates: list[dict] = []
        self._selected_candidate: dict | None = None
        self._event_logs: list[str] = []

        self._init_ui()

        # Telemetry refresh timer
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self.refresh_windows)
        self._refresh_timer.start(2500)
        self.refresh_windows()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # =====================================================================
        # TOP TELEMETRY CHIPS HEADER
        # =====================================================================
        hdr_bar = QFrame()
        hdr_bar.setFixedHeight(40)
        hdr_bar.setStyleSheet(f"background-color: {CONTAINER_LOWEST}; border-bottom: 1px solid {BORDER_SUBTLE};")
        hdr_layout = QHBoxLayout(hdr_bar)
        hdr_layout.setContentsMargins(14, 0, 14, 0)
        hdr_layout.setSpacing(10)

        self.chip_detected = self._create_chip("DETECTED WINDOWS:", "0 Active", ACCENT_NEON)
        self.chip_controlled = self._create_chip("CONTROLLED APPS:", "0 Registered", ACCENT_NEON)
        self.chip_load = self._create_chip("HOST LOAD:", "CPU 0% / RAM 0%", TEXT_PRIMARY)
        self.chip_sec = self._create_chip("API INTEROP:", "Win32 & UIAutomation v4", ACCENT_WARNING)

        hdr_layout.addWidget(self.chip_detected)
        hdr_layout.addWidget(self.chip_controlled)
        hdr_layout.addWidget(self.chip_load)
        hdr_layout.addWidget(self.chip_sec)
        hdr_layout.addStretch()

        btn_refresh = QPushButton("↻ Refresh")
        btn_refresh.setCursor(Qt.PointingHandCursor)
        btn_refresh.setProperty("class", "btn-secondary")
        btn_refresh.setFixedHeight(24)
        btn_refresh.clicked.connect(self.refresh_windows)
        hdr_layout.addWidget(btn_refresh)

        main_layout.addWidget(hdr_bar)

        # =====================================================================
        # SAFETY NOTICE BANNER
        # =====================================================================
        safety_banner = QFrame()
        safety_banner.setFixedHeight(28)
        safety_banner.setStyleSheet(f"background-color: #0F1411; border-bottom: 1px solid {BORDER_SUBTLE};")
        sb_layout = QHBoxLayout(safety_banner)
        sb_layout.setContentsMargins(14, 0, 14, 0)

        lbl_safe_text = QLabel("🛡️ Controlled Automation Active: Windows UIAutomation & Win32 API. Destructive file operations restricted.")
        lbl_safe_text.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 10px;")
        sb_layout.addWidget(lbl_safe_text)
        sb_layout.addStretch()

        lbl_ring = QLabel("SECURITY LEVEL: RING-3 AGENT [ISOLATION: SECURE]")
        lbl_ring.setStyleSheet(f"color: {ACCENT_NEON}; font-family: 'Consolas', monospace; font-size: 10px; font-weight: bold;")
        sb_layout.addWidget(lbl_ring)

        main_layout.addWidget(safety_banner)

        # =====================================================================
        # DUAL WORKSPACE: Left 8 cols (Registry Grid) + Right 4 cols (Ambiguity/Palette)
        # =====================================================================
        split_layout = QHBoxLayout()
        split_layout.setContentsMargins(0, 0, 0, 0)
        split_layout.setSpacing(0)

        # LEFT PANE: 8 Columns Window Registry
        left_box = QWidget()
        left_layout = QVBoxLayout(left_box)
        left_layout.setContentsMargins(14, 12, 14, 12)
        left_layout.setSpacing(10)

        # Section Title
        reg_hdr = QHBoxLayout()
        lbl_reg = QLabel("MANAGED WINDOW REGISTRY")
        lbl_reg.setStyleSheet(f"color: {TEXT_PRIMARY}; font-family: 'Consolas', monospace; font-weight: bold; font-size: 12px;")
        lbl_dock = QLabel("// UI.AUTOMATION.DOCK")
        lbl_dock.setStyleSheet(f"color: {TEXT_DIM}; font-family: 'Consolas', monospace; font-size: 10px;")
        reg_hdr.addWidget(lbl_reg)
        reg_hdr.addWidget(lbl_dock)
        reg_hdr.addStretch()
        left_layout.addLayout(reg_hdr)

        # Bento Grid Scroll Area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("background: transparent; border: none;")

        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setSpacing(10)
        self.scroll_area.setWidget(self.grid_container)

        left_layout.addWidget(self.scroll_area, stretch=1)

        # Bottom Event Stream
        evt_frame = QFrame()
        evt_frame.setFixedHeight(68)
        evt_frame.setStyleSheet(f"background-color: {CONTAINER_LOWEST}; border: 1px solid {BORDER_SUBTLE}; border-radius: 4px; padding: 4px;")
        ef_layout = QVBoxLayout(evt_frame)
        ef_layout.setContentsMargins(8, 4, 8, 4)
        ef_layout.setSpacing(2)

        lbl_ef_title = QLabel("// EVENT STREAM: Win32 Automation Interop")
        lbl_ef_title.setStyleSheet(f"color: {ACCENT_NEON}; font-family: 'Consolas', monospace; font-weight: bold; font-size: 9px;")
        ef_layout.addWidget(lbl_ef_title)

        self.lbl_evt1 = QLabel("14:00:00 [READY] Win32 desktop interop initialized cleanly.")
        self.lbl_evt1.setStyleSheet(f"color: {TEXT_SECONDARY}; font-family: 'Consolas', monospace; font-size: 10px;")
        self.lbl_evt2 = QLabel("14:00:00 [DISCOVERY] Enumerated interactive desktop windows.")
        self.lbl_evt2.setStyleSheet(f"color: {TEXT_DIM}; font-family: 'Consolas', monospace; font-size: 10px;")
        ef_layout.addWidget(self.lbl_evt1)
        ef_layout.addWidget(self.lbl_evt2)

        left_layout.addWidget(evt_frame)

        split_layout.addWidget(left_box, stretch=8)

        # Vertical Divider
        div_v = QFrame()
        div_v.setFrameShape(QFrame.VLine)
        div_v.setStyleSheet(f"background-color: {BORDER_SUBTLE}; max-width: 1px;")
        split_layout.addWidget(div_v)

        # RIGHT PANE: 4 Columns Ambiguity Resolution & Action Palette
        right_box = QWidget()
        right_box.setStyleSheet(f"background-color: {CONTAINER_LOWEST};")
        right_layout = QVBoxLayout(right_box)
        right_layout.setContentsMargins(14, 12, 14, 12)
        right_layout.setSpacing(10)

        # Header
        amb_hdr = QHBoxLayout()
        lbl_amb_title = QLabel("Target Ambiguity Resolution")
        lbl_amb_title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-family: 'Consolas', monospace; font-weight: bold; font-size: 11px;")
        self.badge_amb_status = QLabel("AWAITING TARGET")
        self.badge_amb_status.setStyleSheet(f"background-color: {CONTAINER_HIGH}; color: {ACCENT_WARNING}; border: 1px solid {BORDER_SUBTLE}; border-radius: 2px; padding: 2px 4px; font-family: monospace; font-size: 9px;")
        amb_hdr.addWidget(lbl_amb_title)
        amb_hdr.addStretch()
        amb_hdr.addWidget(self.badge_amb_status)
        right_layout.addLayout(amb_hdr)

        # Query / Command Input (Ctrl+K)
        lbl_q_desc = QLabel("// ACTION PALETTE / TARGET FILTER [Ctrl+K]")
        lbl_q_desc.setStyleSheet(f"color: {TEXT_DIM}; font-family: 'Consolas', monospace; font-size: 9px;")
        right_layout.addWidget(lbl_q_desc)

        self.input_query = QLineEdit()
        self.input_query.setPlaceholderText("Filter target (e.g. 'code', 'terminal', 'chrome')...")
        self.input_query.setFixedHeight(28)
        self.input_query.setStyleSheet(f"""
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
        self.input_query.textChanged.connect(self._handle_target_filter_changed)
        self.input_query.returnPressed.connect(self._handle_confirm_selected_candidate)
        right_layout.addWidget(self.input_query)

        # Discovered Candidates List Box
        lbl_cand = QLabel("DISCOVERED CANDIDATES:")
        lbl_cand.setStyleSheet(f"color: {TEXT_DIM}; font-family: 'Consolas', monospace; font-size: 9px; font-weight: bold;")
        right_layout.addWidget(lbl_cand)

        self.candidates_scroll = QScrollArea()
        self.candidates_scroll.setWidgetResizable(True)
        self.candidates_scroll.setStyleSheet("background: transparent; border: none;")

        self.candidates_box = QWidget()
        self.candidates_layout = QVBoxLayout(self.candidates_box)
        self.candidates_layout.setContentsMargins(0, 0, 0, 0)
        self.candidates_layout.setSpacing(6)
        self.candidates_scroll.setWidget(self.candidates_box)
        right_layout.addWidget(self.candidates_scroll, stretch=1)

        # Instruction confirmation box
        self.confirm_box = QFrame()
        self.confirm_box.setStyleSheet(f"background-color: {CONTAINER_BG}; border: 1px solid {BORDER_SUBTLE}; border-left: 2px solid {ACCENT_NEON}; border-radius: 3px; padding: 6px;")
        cb_layout = QVBoxLayout(self.confirm_box)
        cb_layout.setContentsMargins(6, 6, 6, 6)
        cb_layout.setSpacing(4)
        lbl_cb_title = QLabel("// AGENT INSTRUCTION CONFIRMATION")
        lbl_cb_title.setStyleSheet(f"color: {ACCENT_NEON}; font-family: 'Consolas', monospace; font-size: 9px; font-weight: bold;")
        self.lbl_cb_text = QLabel("Select a candidate above to verify and execute action.")
        self.lbl_cb_text.setWordWrap(True)
        self.lbl_cb_text.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 11px;")
        cb_layout.addWidget(lbl_cb_title)
        cb_layout.addWidget(self.lbl_cb_text)
        right_layout.addWidget(self.confirm_box)

        # Action Buttons: Confirm & Focus / Cancel
        btn_box = QVBoxLayout()
        btn_box.setSpacing(6)

        self.btn_confirm_focus = QPushButton("✓  Confirm & Focus Target [Enter]")
        self.btn_confirm_focus.setCursor(Qt.PointingHandCursor)
        self.btn_confirm_focus.setProperty("class", "btn-primary")
        self.btn_confirm_focus.setFixedHeight(32)
        self.btn_confirm_focus.clicked.connect(self._handle_confirm_selected_candidate)

        self.btn_cancel_amb = QPushButton("✕  Cancel [Esc]")
        self.btn_cancel_amb.setCursor(Qt.PointingHandCursor)
        self.btn_cancel_amb.setProperty("class", "btn-secondary")
        self.btn_cancel_amb.setFixedHeight(28)
        self.btn_cancel_amb.clicked.connect(self._clear_ambiguity)

        btn_box.addWidget(self.btn_confirm_focus)
        btn_box.addWidget(self.btn_cancel_amb)
        right_layout.addLayout(btn_box)

        split_layout.addWidget(right_box, stretch=4)

        main_layout.addLayout(split_layout, stretch=1)

    def _create_chip(self, key: str, val: str, val_col: str) -> QFrame:
        chip = QFrame()
        chip.setStyleSheet(f"background-color: {CONTAINER_BG}; border: 1px solid {BORDER_SUBTLE}; border-radius: 3px; padding: 2px 6px;")
        l = QHBoxLayout(chip)
        l.setContentsMargins(4, 2, 4, 2)
        l.setSpacing(4)
        k_lbl = QLabel(key)
        k_lbl.setStyleSheet(f"color: {TEXT_DIM}; font-family: 'Consolas', monospace; font-size: 10px;")
        v_lbl = QLabel(val)
        v_lbl.setObjectName("val")
        v_lbl.setStyleSheet(f"color: {val_col}; font-family: 'Consolas', monospace; font-weight: bold; font-size: 10px;")
        l.addWidget(k_lbl)
        l.addWidget(v_lbl)
        return chip

    def refresh_windows(self):
        """Query real desktop application windows and populate bento grid."""
        try:
            windows = self.desktop_service.list_windows()
            running_apps = self.desktop_service.list_running_applications()

            # Update header telemetry chips
            v_det = self.chip_detected.findChild(QLabel, "val")
            if v_det:
                v_det.setText(f"{len(windows)} Active")

            v_ctrl = self.chip_controlled.findChild(QLabel, "val")
            if v_ctrl:
                v_ctrl.setText(f"{len(running_apps)} Registered")

            cpu_pct = psutil.cpu_percent(interval=0.0)
            mem_pct = psutil.virtual_memory().percent
            v_load = self.chip_load.findChild(QLabel, "val")
            if v_load:
                v_load.setText(f"CPU {cpu_pct:.0f}% / RAM {mem_pct:.0f}%")

            # Clear existing cards
            while self.grid_layout.count():
                item = self.grid_layout.takeAt(0)
                w = item.widget()
                if w:
                    w.deleteLater()
            self._cards.clear()

            # Render 2x2 Bento Grid or N-items
            display_wins = windows[:8]  # Render top active windows
            for i, w in enumerate(display_wins):
                card = WindowCardWidget(w)
                card.action_triggered.connect(self._handle_card_action)
                row = i // 2
                col = i % 2
                self.grid_layout.addWidget(card, row, col)
                self._cards.append(card)

            if not display_wins:
                empty = QLabel("No active application windows detected.")
                empty.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px; padding: 20px;")
                self.grid_layout.addWidget(empty, 0, 0)

        except Exception as e:
            self._log_event(f"[ERROR] Window discovery error: {str(e)}")

    def _handle_card_action(self, action: str, hwnd: int, title: str):
        """Execute allowlisted window operation and verify outcome."""
        res = {"success": False, "message": "Unknown action"}
        if action == "focus":
            res = self.desktop_service.focus_window(hwnd)
        elif action == "minimize":
            res = self.desktop_service.minimize_window(hwnd)
        elif action == "maximize":
            res = self.desktop_service.maximize_window(hwnd)
        elif action == "restore":
            res = self.desktop_service.restore_window(hwnd)
        elif action == "tile_left":
            res = self.desktop_service.tile_window_left(hwnd)
        elif action == "send_to_bg":
            res = self.desktop_service.send_to_background(hwnd)
        elif action == "close":
            # Confirm if prompt detected or verify
            reply = QMessageBox.question(
                self,
                "Confirm Window Close",
                f"Send graceful WM_CLOSE to '{title}' (HWND {hwnd})?\n\n"
                "Applications with unsaved changes will display their standard save prompt. Zero will not force-kill the process.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                res = self.desktop_service.request_close_window(hwnd)
            else:
                return

        msg = res.get("message", "")
        self._log_event(f"[{action.upper()}] HWND 0x{hwnd:08X}: {msg}")
        ActivityStore.record_activity(
            category="SYS_CONTROL",
            description=f"Action '{action}' on '{title[:30]}': {msg}",
        )
        QTimer.singleShot(300, self.refresh_windows)

    def _handle_target_filter_changed(self, text: str):
        """Filter discovered candidate targets matching natural-language query."""
        clean_text = text.strip()
        if not clean_text:
            self._clear_ambiguity()
            return

        target, candidates = self.desktop_service.find_window(clean_text)
        self._candidates = candidates

        # Clear candidates layout
        while self.candidates_layout.count():
            item = self.candidates_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        if not candidates:
            self.badge_amb_status.setText("0 MATCHES")
            self.badge_amb_status.setStyleSheet(f"background-color: {CONTAINER_HIGH}; color: {TEXT_DIM}; border: 1px solid {BORDER_SUBTLE}; padding: 2px 4px; font-family: monospace; font-size: 9px;")
            lbl = QLabel(f"No active windows matching '{clean_text}'.")
            lbl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px;")
            self.candidates_layout.addWidget(lbl)
            self.lbl_cb_text.setText("No candidates available for confirmation.")
            self._selected_candidate = None
            return

        self.badge_amb_status.setText(f"{len(candidates)} CANDIDATE{'S' if len(candidates) > 1 else ''}")
        self.badge_amb_status.setStyleSheet(f"background-color: {CONTAINER_HIGH}; color: {ACCENT_NEON}; border: 1px solid {BORDER_SUBTLE}; padding: 2px 4px; font-family: monospace; font-size: 9px;")

        for i, cand in enumerate(candidates):
            card = QFrame()
            is_rec = (i == 0)
            card.setStyleSheet(f"""
                QFrame {{
                    background-color: {CONTAINER_BG};
                    border: 1px solid {ACCENT_NEON if is_rec else BORDER_SUBTLE};
                    border-radius: 4px;
                    padding: 6px;
                }}
                QFrame:hover {{
                    border: 1px solid {ACCENT_NEON};
                }}
            """)
            c_layout = QVBoxLayout(card)
            c_layout.setContentsMargins(6, 4, 6, 4)
            c_layout.setSpacing(2)

            h = QHBoxLayout()
            lbl_title = QLabel(f"{cand.get('process_name', '')} (PID {cand.get('pid', 0)})")
            lbl_title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-family: 'Consolas', monospace; font-weight: bold; font-size: 10px;")
            h.addWidget(lbl_title)
            h.addStretch()
            if is_rec:
                rec_tag = QLabel("RECOMMENDED")
                rec_tag.setStyleSheet(f"color: {ACCENT_NEON}; font-family: 'Consolas', monospace; font-size: 8px; font-weight: bold;")
                h.addWidget(rec_tag)
            c_layout.addLayout(h)

            lbl_w_title = QLabel(cand.get("title", ""))
            lbl_w_title.setWordWrap(False)
            lbl_w_title.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 10px;")
            c_layout.addWidget(lbl_w_title)

            # Click selection
            card.mousePressEvent = lambda _, c=cand: self._select_candidate(c)
            self.candidates_layout.addWidget(card)

        # Select first candidate by default
        self._select_candidate(candidates[0])

    def _select_candidate(self, cand: dict):
        self._selected_candidate = cand
        title = cand.get("title", "")
        pid = cand.get("pid", 0)
        hwnd = cand.get("hwnd", 0)
        self.lbl_cb_text.setText(f"Z.E.R.O. requests permission to Focus and bring to foreground:\n'{title}' (PID {pid}, HWND 0x{hwnd:08X})")

    def _handle_confirm_selected_candidate(self):
        if not self._selected_candidate:
            return
        hwnd = self._selected_candidate.get("hwnd", 0)
        title = self._selected_candidate.get("title", "")
        self._handle_card_action("focus", hwnd, title)

    def _clear_ambiguity(self):
        self.input_query.clear()
        self.badge_amb_status.setText("AWAITING TARGET")
        self.badge_amb_status.setStyleSheet(f"background-color: {CONTAINER_HIGH}; color: {ACCENT_WARNING}; border: 1px solid {BORDER_SUBTLE}; padding: 2px 4px; font-family: monospace; font-size: 9px;")
        while self.candidates_layout.count():
            item = self.candidates_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self._candidates.clear()
        self._selected_candidate = None
        self.lbl_cb_text.setText("Select a candidate above to verify and execute action.")

    def _log_event(self, text: str):
        now_str = datetime.now().strftime("%H:%M:%S")
        line = f"{now_str} {text}"
        self.lbl_evt2.setText(self.lbl_evt1.text())
        self.lbl_evt1.setText(line)
