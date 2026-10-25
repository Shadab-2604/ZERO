"""
Automated unit tests for Zero AI Voice Interaction, Intent Routing, Speech Text Cleaning,
and Searchable Conversation History persistence.
"""

import pytest
from app.core.intent_router import IntentRouter, IntentType
from app.core.state_manager import StateManager, AssistantState
from app.voice.speech_synthesis import SpeechSynthesizer
from app.memory.conversation_store import ConversationStore
from app.core.assistant import get_assistant


def test_intent_routing_commands():
    """Verify built-in voice commands are mapped to correct intents."""
    # Wake & Sleep
    assert IntentRouter.match_intent("Zero, wake up")[0] == IntentType.WAKE
    assert IntentRouter.match_intent("wake up")[0] == IntentType.WAKE
    assert IntentRouter.match_intent("Zero, sleep")[0] == IntentType.SLEEP
    assert IntentRouter.match_intent("go to sleep")[0] == IntentType.SLEEP

    # Stop speaking & Repeat
    assert IntentRouter.match_intent("Zero, stop speaking")[0] == IntentType.STOP_SPEAKING
    assert IntentRouter.match_intent("shut up")[0] == IntentType.STOP_SPEAKING
    assert IntentRouter.match_intent("Zero, repeat that")[0] == IntentType.REPEAT
    assert IntentRouter.match_intent("say that again")[0] == IntentType.REPEAT

    # Knowledge commands
    assert IntentRouter.match_intent("Zero, search my knowledge for architecture")[0] == IntentType.SEARCH_KNOWLEDGE
    assert IntentRouter.match_intent("search my knowledge")[0] == IntentType.SEARCH_KNOWLEDGE
    assert IntentRouter.match_intent("Zero, rebuild knowledge")[0] == IntentType.REBUILD_KNOWLEDGE
    assert IntentRouter.match_intent("reindex knowledge")[0] == IntentType.REBUILD_KNOWLEDGE

    # Document generation
    assert IntentRouter.match_intent("Zero, create a report on progress")[0] == IntentType.GENERATE_DOCUMENT
    assert IntentRouter.match_intent("generate pdf document for meeting notes")[0] == IntentType.GENERATE_DOCUMENT
    assert IntentRouter.match_intent("export notes to pdf")[0] == IntentType.GENERATE_DOCUMENT


def test_speech_text_cleaning_code_omission():
    """Verify speech cleaner summarizes code blocks and cleans markdown symbols for natural TTS."""
    # Text with code block
    text_with_code = """Here is the implementation:
```python
def calculate_metrics(x, y):
    return x * 100 / (y + 1e-5)
```
Let me know if you need more details."""

    clean = SpeechSynthesizer.clean_text_for_speech(text_with_code)
    # Full syntax should NOT be in speech
    assert "def calculate_metrics" not in clean
    assert "1e-5" not in clean
    # Should contain polite summary
    assert "code implementation shown on screen" in clean
    assert "Here is the implementation" in clean
    assert "Let me know if you need more details" in clean


def test_speech_text_cleaning_markdown_and_artifacts():
    """Verify cleaner strips markdown markers, tables, and translates artifact tags."""
    text = "Status: **Active**. View artifact: [ARTIFACT_PDF:report.pdf]. Speed: `120ms`."
    clean = SpeechSynthesizer.clean_text_for_speech(text)
    assert "**" not in clean
    assert "`" not in clean
    assert "generated the PDF document" in clean


def test_state_manager_transitions():
    """Verify state transitions between SLEEPING, READY, LISTENING, THINKING, SPEAKING."""
    sm = StateManager(initial_state=AssistantState.SLEEPING)
    assert sm.current_state == AssistantState.SLEEPING

    sm.transition_to(AssistantState.READY, reason="Woken up")
    assert sm.current_state == AssistantState.READY

    sm.transition_to(AssistantState.LISTENING, reason="User speaking")
    assert sm.current_state == AssistantState.LISTENING

    sm.transition_to(AssistantState.THINKING, reason="Querying AI")
    assert sm.current_state == AssistantState.THINKING

    sm.transition_to(AssistantState.SPEAKING, reason="Playback active")
    assert sm.current_state == AssistantState.SPEAKING

    sm.transition_to(AssistantState.SLEEPING, reason="Command sleep")
    assert sm.current_state == AssistantState.SLEEPING


def test_conversation_history_persistence_and_search():
    """Verify creating, searching, and deleting conversations in SQLite."""
    # Create test conversation
    conv = ConversationStore.create_conversation(title="Quantum Computing Research")
    ConversationStore.add_message(
        conversation_id=conv.id,
        role="user",
        content="What is quantum superposition?",
    )
    ConversationStore.add_message(
        conversation_id=conv.id,
        role="assistant",
        content="Superposition allows qubits to exist in linear combinations of states.",
    )

    # Search conversation by title
    matches = ConversationStore.search_conversations("Quantum")
    assert any(c["id"] == conv.id for c in matches)

    # Search messages by content
    msg_matches = ConversationStore.search_messages("superposition")
    assert any(m["conversation_id"] == conv.id for m in msg_matches)

    # Clean up test conversation
    deleted = ConversationStore.delete_conversation(conv.id)
    assert deleted
    assert not any(c["id"] == conv.id for c in ConversationStore.list_conversations())


def test_repeat_intent_dispatch():
    """Verify repeat command returns previously stored assistant answer."""
    assistant = get_assistant()
    assistant.wake()

    # Process a normal input to establish last response
    resp1 = assistant.process_input("Hello Zero")
    first_reply = resp1["reply_text"]
    assert first_reply

    # Repeat that
    repeat_resp = assistant.process_input("Zero, repeat that")
    assert repeat_resp["intent"].upper() == "REPEAT"
    assert repeat_resp["reply_text"] == first_reply
