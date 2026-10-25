"""
Regression tests for Continuous Hands-Free Voice Conversation, Repeated TTS, and Truthful Session Summaries.
"""

from unittest.mock import MagicMock, patch
import pytest
from app.core.assistant import ZeroAssistant, get_assistant
from app.core.briefing_service import BriefingService
from app.core.state_manager import AssistantState
from app.memory.activity_store import ActivityStore
from app.voice.speech_synthesis import SpeechSynthesizer
from app.voice.manager import VoiceManager


def test_speech_synthesizer_clean_text_formatting():
    """Verify clean_text_for_speech strips markdown and summarizes code/tables."""
    raw = (
        "## Header\n\n"
        "Here is the code:\n"
        "```python\ndef test():\n    return 42\n```\n"
        "Visit https://example.com for more info. **Important** notice.\n"
        "| Col1 | Col2 |\n|---|---|\n| A | B |\n"
    )
    cleaned = SpeechSynthesizer.clean_text_for_speech(raw)
    assert "```" not in cleaned
    assert "Here is the code implementation shown on screen." in cleaned
    assert "https://" not in cleaned
    assert "##" not in cleaned
    assert "**" not in cleaned


def test_five_consecutive_voice_turns_trigger_tts_consistently():
    """Verify that multiple consecutive conversation turns trigger speech on every turn."""
    assistant = ZeroAssistant()
    assistant.initialize()

    spoken_log = []
    mock_synth = MagicMock()

    def _mock_speak(text, wait=False, on_start=None, on_end=None):
        spoken_log.append(text)
        if on_start:
            on_start()
        if on_end:
            on_end()

    mock_synth.speak.side_effect = _mock_speak

    with patch("app.voice.wake_listener.WakeWordListener.start"):
        voice_manager = VoiceManager()
        voice_manager.synthesizer = mock_synth

        # Turn 0: Wake
        greeting = assistant.wake()
        voice_manager.speak(greeting)
        assert len(spoken_log) == 1
        assert "Zero is online" in spoken_log[0] or "ready" in spoken_log[0]

    # Turns 1 to 5: Consecutive queries
    queries = [
        "What is 10 + 20?",
        "What is 50 * 4?",
        "What is 18 percent of 450?",
        "Check my ping",
        "System status",
    ]

    for i, q in enumerate(queries, 1):
        res = assistant.process_input(q)
        reply = res.get("spoken_text") or res["reply_text"]
        voice_manager.speak(reply)
        assert len(spoken_log) == i + 1, f"Turn {i} failed to trigger TTS"
        assert len(spoken_log[-1].strip()) > 0, f"Turn {i} spoke empty text"


def test_empty_ai_response_does_not_trigger_tts():
    """Verify empty text is never sent to speech synthesis."""
    mock_engine = MagicMock()
    synth = SpeechSynthesizer()
    synth._local_engine = mock_engine

    synth.speak("")
    synth.speak("   ")

    # Queue should remain empty
    assert synth._queue.empty() is True


def test_tts_failure_does_not_crash_session():
    """Verify that an exception in speech synthesis is caught and does not crash assistant."""
    synth = SpeechSynthesizer()
    synth._local_engine = MagicMock()
    synth._local_engine.say.side_effect = RuntimeError("Simulated SAPI5 COM failure")

    # Should not raise exception
    synth.speak("Test speech recovery", wait=False)
    # Allow worker to process
    import time
    time.sleep(0.3)
    synth.shutdown()


def test_stop_speaking_halts_playback():
    """Verify stop_speaking interrupts playback and clears queue."""
    synth = SpeechSynthesizer()
    mock_engine = MagicMock()
    synth._local_engine = mock_engine

    # Patch start_worker to prevent background thread from re-initializing real pyttsx3
    with patch.object(synth, "start_worker"):
        synth.speak("Sentence one")
        synth.speak("Sentence two")

        synth.stop()
        assert synth.is_speaking is False
        assert synth._queue.empty() is True
        mock_engine.stop.assert_called()


def test_truthful_session_summary_without_hallucinations():
    """
    Verify that session summaries only contain verified executed actions
    and do not invent fake scan sequences or secret recipes.
    """
    assistant = ZeroAssistant()
    assistant.initialize()

    # 1. Ask a question (curiosity question, not an action)
    assistant.process_input("What is the secret recipe for XYZ pudding?")

    # 2. Execute an actual verified tool action
    assistant.process_input("System status")

    # 3. Shutdown assistant
    assistant.shutdown()

    # Verify latest session summary
    latest = ActivityStore.get_latest_session_summary()
    assert latest is not None
    summary_text = latest["summary_text"]

    # Must NOT invent secret recipe as an accomplished project task
    assert "recipe" not in summary_text.lower()
    assert "pudding" not in summary_text.lower()
    assert "scan sequence" not in summary_text.lower()


def test_briefing_uses_truthful_greeting_when_no_tasks_exist():
    """Verify briefing greets cleanly without inventing previous work when none exists."""
    briefing_service = BriefingService()

    # With clean/mocked records with no verified tasks
    with patch("app.memory.activity_store.ActivityStore.get_latest_session_summary", return_value=None), \
         patch("app.memory.activity_store.ActivityStore.get_recent_activities", return_value=[]), \
         patch("app.memory.activity_store.ActivityStore.list_tasks", return_value=[]):
        briefing = briefing_service.generate_briefing(force=True)
        assert briefing["delivered"] is True
        assert "This is your first recorded session" in briefing["text"] or "Welcome back" in briefing["text"]
        assert "secret recipe" not in briefing["text"].lower()


def test_summarize_previous_work_routes_cleanly():
    """Verify 'Zero, summarize my previous work' routes to SUMMARIZE_PREVIOUS and does not hallucinate."""
    from app.core.intent_router import IntentRouter, IntentType
    intent, _ = IntentRouter.match_intent("Zero, summarize my previous work")
    assert intent == IntentType.SUMMARIZE_PREVIOUS

    intent2, _ = IntentRouter.match_intent("what did we do earlier?")
    assert intent2 == IntentType.SUMMARIZE_PREVIOUS
