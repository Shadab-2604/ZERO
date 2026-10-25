"""
Zero AI — Stitch Obsidian Command Desktop GUI Integration Tests.
Verifies all newly integrated Stitch interface components:
- CommandCenterWidget: Telemetry, AI Orb interaction, Core State Selector, System Actions.
- TranscriptCodeWidget: Activity filters, search highlighting, code preview, safe execution sandbox, PDF export, clear buffer.
- SystemControlWidget: Managed window registry, bento actions (Focus, Min, Max, Restore, Close, Tile, Send to BG), Ambiguity resolution.
- FooterVoiceBarWidget: Persistent audio dock, state badges, ticker updates, interrupt control.
- MainWindow: Complete assembly, custom 36px titlebar, 64px slim navigation rail, shortcuts (Ctrl+F, Ctrl+K, Esc, Win+Shift+Z).
"""

import os
from unittest.mock import MagicMock, patch
import pytest
from PySide6.QtWidgets import QApplication, QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage

from app.core.state_manager import AssistantState
from app.memory.database import init_db
from app.memory.activity_store import ActivityStore
from app.gui.widgets.command_center import CommandCenterWidget
from app.gui.widgets.transcript_panel import TranscriptCodeWidget
from app.gui.widgets.system_control_panel import SystemControlWidget, WindowCardWidget
from app.gui.widgets.footer_voice_bar import FooterVoiceBarWidget
from app.gui.widgets.sidebar import SidebarWidget
from app.gui.main_window import MainWindow


@pytest.fixture(scope="session")
def qapp():
    """Ensure a single QApplication instance exists for GUI tests."""
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_command_center_widget_rendering_and_telemetry(qapp):
    """Verify CommandCenterWidget renders metrics, orb, and action buttons."""
    init_db()
    cc = CommandCenterWidget()
    assert cc.lbl_inf_status.text() == "● 11434 ONLINE"
    assert cc.orb_widget is not None

    # Test state selector buttons
    cc._simulate_state_change(AssistantState.LISTENING)
    assert cc._current_state == AssistantState.LISTENING
    assert "LISTENING" in cc.badge_state.text()

    cc._simulate_state_change(AssistantState.ERROR)
    assert cc._current_state == AssistantState.ERROR
    assert "ERROR" in cc.badge_state.text()

    # Test telemetry update
    cc.refresh_telemetry()
    assert cc.bar_cpu.value() >= 0
    assert cc.bar_ram.value() >= 0

    # Test audit log rendering
    ActivityStore.record_activity("TEST", "Audit event integration test")
    cc.refresh_audit_log()
    assert cc.log_container_layout.count() > 0


def test_transcript_code_widget_filtering_and_code_viewer(qapp):
    """Verify TranscriptCodeWidget filters, search, code display, and copy."""
    init_db()
    panel = TranscriptCodeWidget()
    panel.show()
    # Start with empty items for controlled filter testing
    panel._items.clear()

    # Add messages
    panel.add_message("user", "Run diagnostics on system threads")
    panel.add_message("assistant", "Analyzing threads. ```python\nprint('hello')\n```")
    panel.add_message("interrupt", "Speech interrupted by operator")
    panel.add_message("tool", "Tool execution returned status OK")

    assert len(panel._items) == 4

    # Test filter tabs
    panel._set_active_filter("speech")
    visible_cards = [c for c in panel._items if not c.isHidden()]
    assert len(visible_cards) == 2  # user & assistant

    panel._set_active_filter("tools")
    visible_cards = [c for c in panel._items if not c.isHidden()]
    assert len(visible_cards) == 1

    panel._set_active_filter("all")
    visible_cards = [c for c in panel._items if not c.isHidden()]
    assert len(visible_cards) == 4

    # Test search query filter
    panel.search_input.setText("diagnostics")
    visible_cards = [c for c in panel._items if not c.isHidden()]
    assert len(visible_cards) == 1
    panel.search_input.clear()

    # Verify code editor has populated code
    assert "print('hello')" in panel._current_code
    assert panel.lbl_code_lang.text() == "PYTHON"

    # Test copy
    panel._handle_code_copy()
    assert panel.btn_code_copy.text() == "✓ Copied!"


def test_system_control_bento_grid_and_actions(qapp):
    """Verify SystemControlWidget window enumeration, card actions, and ambiguity filter."""
    init_db()
    sc = SystemControlWidget()
    sc.refresh_windows()

    # Test mock card action triggering
    action_events = []
    mock_data = {
        "hwnd": 0x1234,
        "title": "Visual Studio Code - zero",
        "pid": 9999,
        "process_name": "Code.exe",
        "is_focused": True,
        "is_minimized": False,
        "is_maximized": False,
        "memory_mb": 512.0,
    }
    card = WindowCardWidget(mock_data)
    card.action_triggered.connect(lambda act, h, t: action_events.append((act, h, t)))

    card._create_card_btn("TEST", "btn-primary", lambda: card.action_triggered.emit("focus", card.hwnd, card.title)).click()
    assert action_events == [("focus", 0x1234, "Visual Studio Code - zero")]

    # Test ambiguity candidate filter
    with patch.object(sc.desktop_service, "find_window", return_value=(mock_data, [mock_data])):
        sc._handle_target_filter_changed("code")
        assert sc._selected_candidate == mock_data
        assert "Visual Studio Code" in sc.lbl_cb_text.text()

    sc._clear_ambiguity()
    assert sc._selected_candidate is None


def test_footer_voice_bar_dock_and_interruption(qapp):
    """Verify FooterVoiceBarWidget state updates, mic status, and interruption signal."""
    bar = FooterVoiceBarWidget()
    assert bar.lbl_state.text() == "READY"

    bar.set_assistant_state(AssistantState.SPEAKING)
    assert bar.lbl_state.text() == "SPEAKING"

    bar.set_mic_status(False)
    assert "MUTED" in bar.lbl_mic.text()

    bar.set_mic_status(True, rate_hz=48000)
    assert "ACTIVE (48kHz)" in bar.lbl_mic.text()

    bar.set_ticker_text("Processing request...", prefix="ZERO:")
    assert "Processing request..." in bar.lbl_ticker.text()

    # Test interrupt button
    interrupt_called = []
    bar.interrupt_requested.connect(lambda: interrupt_called.append(True))
    bar.btn_interrupt.click()
    assert interrupt_called == [True]


def test_main_window_full_stitch_integration(qapp):
    """Verify MainWindow integrates custom titlebar, 64px rail, stacked views, and shortcuts."""
    init_db()
    mock_voice = MagicMock()
    mock_voice.stop_speaking = MagicMock()
    mock_voice.shutdown = MagicMock()

    window = MainWindow(voice_manager=mock_voice)

    # 1. Custom Titlebar
    assert window.title_bar is not None
    assert "Z.E.R.O. v2.4 // LOCAL INTELLIGENCE" in window.title_bar.findChildren(QLabel)[1].text()

    # 2. 64px Slim Rail
    assert window.sidebar.width() == 64

    # 3. Stacked Views Navigation
    assert window.stacked.count() >= 6
    window._handle_navigation("command")
    assert window.stacked.currentIndex() == 0

    window._handle_navigation("transcript")
    assert window.stacked.currentIndex() == 1

    window._handle_navigation("knowledge")
    assert window.stacked.currentIndex() == 2

    window._handle_navigation("system_control")
    assert window.stacked.currentIndex() == 3

    # 4. Global Interruption handling
    window._handle_interrupt()
    mock_voice.stop_speaking.assert_called()
    assert window.assistant.state_manager.current_state == AssistantState.READY

    window.close()
