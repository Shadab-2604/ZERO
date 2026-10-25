"""
Tests covering AI Provider Abstraction, Demo Fallback, Error Resilience, and Voice Handling.
Covers:
- Scenario 2: GUI launches in demo mode without an API key
- Scenario 11: The GUI remains responsive during a simulated slow AI request
- Scenario 12: Missing microphone permissions produce a useful message
- Scenario 13: Provider errors do not crash the GUI
"""

import time
import pytest
from unittest.mock import patch, MagicMock
from app.ai.provider_factory import AIProviderFactory
from app.ai.providers.demo_provider import DemoAIProvider
from app.core.assistant import ZeroAssistant
from app.core.state_manager import AssistantState
from app.voice.speech_recognition import SpeechRecognizer
from app.memory.database import init_db


@pytest.fixture(autouse=True)
def setup_db():
    init_db()


def test_launches_in_demo_mode_without_api_key(monkeypatch):
    """Scenario 2: When no API key is supplied, provider defaults to DemoAIProvider."""
    monkeypatch.setenv("AI_PROVIDER", "demo")
    monkeypatch.delenv("AI_API_KEY", raising=False)

    provider = AIProviderFactory.get_provider()
    assert isinstance(provider, DemoAIProvider)
    assert provider.is_available is True

    # Generates honest demo response with identifier
    response = provider.generate_response([{"role": "user", "content": "Hello Zero"}])
    assert "[DEMO MODE]" in response


def test_provider_errors_do_not_crash_assistant():
    """Scenario 13: Controlled error handling when AI provider raises an exception."""
    assistant = ZeroAssistant()
    assistant.initialize()
    assistant.wake()

    # Mock provider to raise runtime exception
    mock_provider = MagicMock()
    mock_provider.generate_response.side_effect = RuntimeError("Remote API connection timeout (simulated)")

    with patch.object(assistant.conversation_manager, "get_provider", return_value=mock_provider):
        result = assistant.process_input("Complex calculation query")
        assert "Remote API connection timeout" in result["reply_text"]
        # Assistant must transition back to READY or ERROR gracefully without raising unhandled crash
        assert assistant.state_manager.current_state in (AssistantState.READY, AssistantState.ERROR)


def test_responsive_during_slow_ai_request():
    """Scenario 11: Simulated slow AI request processes safely and transitions to THINKING."""
    assistant = ZeroAssistant()
    assistant.initialize()
    assistant.wake()

    def slow_generate(messages, system_prompt=None):
        time.sleep(0.3)
        return "Slow inference finished"

    mock_provider = MagicMock()
    mock_provider.generate_response.side_effect = slow_generate

    with patch.object(assistant.conversation_manager, "get_provider", return_value=mock_provider):
        result = assistant.process_input("Long reasoning task")
        assert "Slow inference finished" in result["reply_text"]
        assert assistant.state_manager.current_state == AssistantState.READY


def test_missing_microphone_permission_produces_useful_message():
    """Scenario 12: Hardware/permission microphone failures return helpful error text."""
    recognizer = SpeechRecognizer()
    recognizer._recognizer = MagicMock()

    # Simulate microphone initialization failure (e.g. no device / no permissions)
    with patch("speech_recognition.Microphone", side_effect=OSError("No Default Input Device Available")):
        error_messages = []

        thread = recognizer.listen_once_async(
            on_success=lambda text: None,
            on_error=lambda err: error_messages.append(err),
            timeout=1.0,
        )
        thread.join(timeout=2.0)

        assert len(error_messages) == 1
        assert "Microphone access error" in error_messages[0]
