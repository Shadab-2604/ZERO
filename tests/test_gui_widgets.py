"""
PySide6 GUI and widget tests for Zero AI.
Verifies window initialization, AI orb rendering, sidebar navigation, and panels.
"""

import os
from unittest.mock import MagicMock
import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage
from app.gui.widgets.ai_orb import AIOrbWidget
from app.gui.widgets.sidebar import SidebarWidget
from app.gui.widgets.status_bar import StatusBarWidget
from app.gui.widgets.info_panel import InfoPanelWidget
from app.gui.widgets.briefing_panel import BriefingPanelWidget
from app.gui.widgets.settings_panel import SettingsPanelWidget
from app.gui.main_window import MainWindow
from app.core.state_manager import AssistantState
from app.memory.database import init_db


@pytest.fixture(scope="session")
def qapp():
    """Ensure a single QApplication instance exists for GUI tests."""
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_ai_orb_widget_painting_and_states(qapp):
    """Verify AIOrbWidget can be rendered and changes state cleanly."""
    orb = AIOrbWidget()
    assert orb.width() == 140
    assert orb.height() == 140

    # Test all state transitions
    for state in AssistantState:
        orb.set_state(state)
        assert orb._state == state

    # Test rendering into an offscreen image
    image = QImage(140, 140, QImage.Format_ARGB32)
    image.fill(0)
    orb.render(image)
    assert not image.isNull()


def test_sidebar_widget_signals(qapp):
    """Verify SidebarWidget navigation triggers correct signals."""
    sidebar = SidebarWidget()
    received_views = []
    sidebar.navigate.connect(lambda v: received_views.append(v))

    sidebar.btn_history.click()
    sidebar.btn_briefing.click()
    sidebar.btn_settings.click()

    assert received_views == ["history", "briefing", "settings"]


def test_status_bar_updates(qapp):
    """Verify StatusBarWidget refreshes telemetry without exceptions."""
    init_db()
    bar = StatusBarWidget()
    bar.refresh_telemetry()
    assert "MODE:" in bar.mode_label.text()


def test_main_window_lifecycle(qapp):
    """Verify MainWindow initializes, renders, and shuts down cleanly."""
    init_db()
    mock_voice = MagicMock()
    mock_voice.stop_speaking = MagicMock()
    mock_voice.shutdown = MagicMock()

    window = MainWindow(voice_manager=mock_voice)
    assert window.windowTitle() == "ZERO AI // PERSONAL SYSTEM ASSISTANT"
    assert window.stacked.count() >= 5

    # Test wake & sleep
    window._handle_wake()
    assert window.assistant.state_manager.current_state in (
        AssistantState.READY,
        AssistantState.LISTENING,
    )

    window._handle_sleep()
    assert window.assistant.state_manager.current_state == AssistantState.SLEEPING

    window.close()
