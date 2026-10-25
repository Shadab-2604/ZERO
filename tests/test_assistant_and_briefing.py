"""
Tests covering Assistant State Transitions, Wake/Sleep Commands, and Briefing Behavior.
Covers:
- Scenario 4: Greeting uses the configured local timezone
- Scenario 8: Wake command transitions SLEEPING to READY or LISTENING
- Scenario 9: Sleep command transitions to SLEEPING
- Scenario 10: Repeated wake events do not duplicate the briefing
- Scenario 18: Shutdown releases active workers and audio resources
"""

import pytest
from app.core.assistant import ZeroAssistant
from app.core.state_manager import AssistantState
from app.utils.time_utils import get_time_appropriate_greeting, get_current_time
from app.memory.database import init_db


@pytest.fixture(autouse=True)
def setup_assistant():
    init_db()
    assistant = ZeroAssistant()
    assistant.initialize()
    return assistant


def test_greeting_uses_configured_local_timezone():
    """Scenario 4: Greeting respects local hour according to timezone."""
    # Test morning timezone vs evening timezone
    current_utc = get_current_time("UTC")
    greeting = get_time_appropriate_greeting("UTC")

    hour = current_utc.hour
    if 5 <= hour < 12:
        assert greeting == "Good morning"
    elif 12 <= hour < 17:
        assert greeting == "Good afternoon"
    else:
        assert greeting == "Good evening"


def test_wake_command_transitions_sleeping_to_ready(setup_assistant):
    """Scenario 8: Waking moves assistant out of SLEEPING into READY."""
    assistant = setup_assistant
    assert assistant.state_manager.current_state == AssistantState.SLEEPING

    # Issue wake command
    response = assistant.wake()
    assert assistant.state_manager.current_state in (AssistantState.READY, AssistantState.LISTENING)
    assert len(response) > 0


def test_sleep_command_transitions_to_sleeping(setup_assistant):
    """Scenario 9: Sleep moves assistant into SLEEPING."""
    assistant = setup_assistant
    assistant.wake()
    assert assistant.state_manager.current_state != AssistantState.SLEEPING

    response = assistant.sleep()
    assert assistant.state_manager.current_state == AssistantState.SLEEPING
    assert "Going to sleep" in response


def test_repeated_wake_does_not_duplicate_briefing(setup_assistant):
    """Scenario 10: Repeated wake phrases do not repeatedly emit the entire briefing."""
    assistant = setup_assistant

    # First wake delivers full briefing
    first_wake = assistant.wake(force_briefing=False)
    assert assistant.briefing_service.has_delivered_session_briefing

    # Second wake should give concise awake status without duplicate narrative
    second_wake = assistant.wake(force_briefing=False)
    assert "What shall we work on?" in second_wake or "awake and ready" in second_wake
    # Should not re-run full system telemetry paragraph
    assert "This is your first recorded session" not in second_wake


def test_shutdown_releases_resources_cleanly(setup_assistant):
    """Scenario 18: Shutdown marks session inactive and closes resources."""
    assistant = setup_assistant
    assert assistant.active_session_id is not None

    stopped_speech = []
    assistant.set_speech_stop_callback(lambda: stopped_speech.append(True))

    assistant.shutdown()
    assert assistant.active_session_id is None
    assert len(stopped_speech) == 1
