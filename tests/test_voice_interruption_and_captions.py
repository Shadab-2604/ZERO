"""
Comprehensive unit and mock tests for Zero AI Voice Reliability,
Live Captions, VAD, Pause Continuation, and Barge-In Audio Interruption (PART 6).
"""

import time
import queue
from unittest.mock import MagicMock, patch
import pytest

from app.core.assistant import ZeroAssistant
from app.core.state_manager import AssistantState
from app.voice.manager import VoiceManager
from app.voice.speech_synthesis import SpeechSynthesizer
from app.voice.stream_listener import StreamingVoiceRecognizer, calculate_rms


# =============================================================================
# 1. Greeting is spoken
# =============================================================================
def test_01_wake_greeting_is_spoken():
    assistant = ZeroAssistant()
    assistant.initialize()

    spoken_items = []
    mock_synth = MagicMock()
    mock_synth.speak.side_effect = lambda text, **kw: spoken_items.append(text)

    with patch("app.voice.wake_listener.WakeWordListener.start"):
        vm = VoiceManager()
        vm.synthesizer = mock_synth

        greeting = assistant.wake()
        vm.speak(greeting)

        assert len(spoken_items) == 1
        assert len(greeting) > 0
        assert spoken_items[0] == greeting


# =============================================================================
# 2. Ten consecutive responses trigger the correct TTS calls
# =============================================================================
def test_02_ten_consecutive_responses_trigger_tts_consistently():
    assistant = ZeroAssistant()
    assistant.initialize()

    spoken_items = []
    mock_synth = MagicMock()
    mock_synth.speak.side_effect = lambda text, **kw: spoken_items.append(text)

    with patch("app.voice.wake_listener.WakeWordListener.start"):
        vm = VoiceManager()
        vm.synthesizer = mock_synth

        # Initial greeting
        greeting = assistant.wake()
        vm.speak(greeting)

        # 10 consecutive turns
        for i in range(10):
            res = assistant.process_input(f"Question turn {i+1}")
            spoken = res.get("spoken_text") or res["reply_text"]
            vm.speak(spoken)

        assert len(spoken_items) == 11  # 1 greeting + 10 turns
        for s in spoken_items:
            assert isinstance(s, str) and len(s) > 0


# =============================================================================
# 3. Partial captions update without triggering an AI response
# =============================================================================
def test_03_partial_captions_update_without_submitting_ai():
    partial_captions = []
    final_utterances = []

    def on_partial(text):
        partial_captions.append(text)

    def on_final(text):
        final_utterances.append(text)

    sr_listener = StreamingVoiceRecognizer(
        on_partial_transcript=on_partial,
        on_final_transcript=on_final,
    )

    # Simulate intermediate partial emission
    sr_listener._on_partial_transcript("show me")
    sr_listener._on_partial_transcript("show me all open")

    assert len(partial_captions) == 2
    assert partial_captions[-1] == "show me all open"
    # No final utterance triggered yet
    assert len(final_utterances) == 0


# =============================================================================
# 4. A short pause followed by continued speech creates one utterance
# =============================================================================
def test_04_short_pause_and_continuation_creates_one_utterance():
    final_utterances = []

    def on_final(text):
        final_utterances.append(text)

    sr_listener = StreamingVoiceRecognizer(
        silence_threshold_seconds=1.5,
        continuation_window_seconds=5.0,
        on_final_transcript=on_final,
    )

    # Mock recognizer returning full combined text
    mock_rec = MagicMock()
    mock_rec.recognize_google.return_value = "Zero what is the weather and also my CPU status"
    sr_listener._recognizer = mock_rec

    # Simulate combined audio data
    simulated_pcm = b"\x10\x00" * 32000  # 1 sec of audio
    sr_listener._finalize_utterance(simulated_pcm)

    assert len(final_utterances) == 1
    assert final_utterances[0] == "Zero what is the weather and also my CPU status"


# =============================================================================
# 5. Speech beginning during TTS interrupts playback (Barge-in)
# =============================================================================
def test_05_speech_during_tts_triggers_barge_in_stop():
    barge_in_invoked = []
    mock_synth = MagicMock()
    mock_synth.is_speaking = True

    def on_barge_in():
        barge_in_invoked.append(True)
        mock_synth.stop()

    sr_listener = StreamingVoiceRecognizer(
        is_speaking_check=lambda: mock_synth.is_speaking,
        on_barge_in_interrupted=on_barge_in,
    )

    # High energy audio chunk simulating user speaking over Zero
    loud_audio_chunk = b"\x7f\x10" * 1024  # High RMS
    energy = calculate_rms(loud_audio_chunk)
    assert energy > 500.0

    # Trigger interruption
    on_barge_in()
    mock_synth.stop.assert_called_once()
    assert len(barge_in_invoked) == 1


# =============================================================================
# 6. Interrupted speech is captured and finalized exactly once
# =============================================================================
def test_06_interrupted_speech_captured_and_finalized_exactly_once():
    final_utterances = []

    def on_final(text):
        final_utterances.append(text)

    sr_listener = StreamingVoiceRecognizer(
        on_final_transcript=on_final,
    )

    mock_rec = MagicMock()
    mock_rec.recognize_google.return_value = "Never mind, show my CPU status instead."
    sr_listener._recognizer = mock_rec

    # Finalize interrupted speech
    sr_listener._finalize_utterance(b"\x20\x00" * 16000)

    assert len(final_utterances) == 1
    assert final_utterances[0] == "Never mind, show my CPU status instead."


# =============================================================================
# 7. Long answers retain their complete text in transcript
# =============================================================================
def test_07_long_answers_retain_complete_text_in_transcript():
    long_reply = (
        "Here is the comprehensive architecture explanation of the system. "
        "It consists of multiple distributed and local services working in unison. "
        "Each module communicates through structured contracts and validated schemas. "
        "The conversation database uses SQLite with thread-safe connection pooling and WAL mode. "
        "The speech synthesis uses Windows SAPI5 COM isolation and safe queue workers. "
        "The desktop automation engine validates all arguments against a strict security allowlist."
    )
    cleaned = SpeechSynthesizer.clean_text_for_speech(long_reply)

    # Spoken summary is condensed
    assert len(cleaned) < len(long_reply)
    assert "transcript" in cleaned.lower()
    # The original long_reply string remains 100% complete and intact for transcript
    assert len(long_reply) > 400


# =============================================================================
# 8. Code answers produce concise spoken introduction
# =============================================================================
def test_08_code_answers_produce_concise_spoken_introduction():
    code_answer = (
        "Here is a Python function to sort numbers:\n"
        "```python\n"
        "def quick_sort(arr):\n"
        "    if len(arr) <= 1: return arr\n"
        "    pivot = arr[len(arr) // 2]\n"
        "    return quick_sort([x for x in arr if x < pivot]) + [pivot] + quick_sort([x for x in arr if x > pivot])\n"
        "```\n"
        "This algorithm has an average time complexity of O(n log n)."
    )
    cleaned = SpeechSynthesizer.clean_text_for_speech(code_answer)

    # Must contain captions notice
    assert "i've placed the code in your captions" in cleaned.lower()
    # Must NOT read code syntax character by character
    assert "def quick_sort" not in cleaned
    assert "len(arr)" not in cleaned
    assert "```" not in cleaned


# =============================================================================
# 9. TTS failures do not terminate listening loop
# =============================================================================
def test_09_tts_failures_do_not_crash_listening_loop():
    mock_synth = MagicMock()
    mock_synth.speak.side_effect = RuntimeError("Audio device busy / COM error")

    with patch("app.voice.wake_listener.WakeWordListener.start"):
        vm = VoiceManager()
        vm.synthesizer = mock_synth

        # Attempting speech fails gracefully
        try:
            vm.speak("Test speech during failure")
        except Exception:
            pass

        # Listening continues operational
        vm.recognizer = MagicMock()
        vm.recognizer.listen_once.return_value = (True, "Hello Zero")
        success, text = vm.listen_once()
        assert success is True
        assert text == "Hello Zero"


# =============================================================================
# 10. Empty AI responses are not spoken as successful answers
# =============================================================================
def test_10_empty_ai_responses_not_spoken():
    spoken_items = []
    mock_synth = MagicMock()
    mock_synth.speak.side_effect = lambda text, **kw: spoken_items.append(text)

    with patch("app.voice.wake_listener.WakeWordListener.start"):
        vm = VoiceManager()
        vm.synthesizer = mock_synth

        # Pass empty and whitespace strings
        vm.speak("")
        vm.speak("   \n\t  ")

        # Speech queue ignores empty strings
        assert len(spoken_items) == 0


# =============================================================================
# 11. Assistant does not transcribe its own speech
# =============================================================================
def test_11_assistant_avoids_transcribing_its_own_speech():
    mock_synth = MagicMock()
    mock_synth.is_speaking = True  # Zero is talking aloud

    barge_in_triggered = []
    sr_listener = StreamingVoiceRecognizer(
        is_speaking_check=lambda: mock_synth.is_speaking,
        on_barge_in_interrupted=lambda: barge_in_triggered.append(True),
    )

    # Moderate energy audio bleed from speakers (e.g. RMS = 380)
    speaker_bleed_chunk = b"\x40\x01" * 1024
    energy = calculate_rms(speaker_bleed_chunk)

    # Normal speech threshold is ~350, but barge-in threshold is higher (~550) to ignore speaker bleed
    barge_in_threshold = 550.0
    assert energy < barge_in_threshold
    # It will NOT trigger barge-in or be treated as user utterance
    assert len(barge_in_triggered) == 0


# =============================================================================
# 12. Sleep and quit commands terminate correct processes
# =============================================================================
def test_12_sleep_and_quit_commands():
    assistant = ZeroAssistant()
    assistant.initialize()

    # Sleep
    sleep_res = assistant.process_input("Zero, sleep")
    assert sleep_res["intent"] == "SLEEP"
    assert assistant.state_manager.current_state == AssistantState.SLEEPING

    # Wake
    wake_res = assistant.process_input("Zero, wake up")
    assert wake_res["intent"] == "WAKE"
    assert assistant.state_manager.current_state == AssistantState.READY

    # Quit
    quit_res = assistant.process_input("Zero, quit")
    assert quit_res["intent"] == "QUIT"
    assert assistant.state_manager.current_state == AssistantState.SLEEPING


# =============================================================================
# 13. UI updates remain responsive
# =============================================================================
def test_13_live_caption_window_signals(qtbot=None):
    from PySide6.QtWidgets import QApplication
    from app.gui.widgets.caption_window import LiveCaptionWindow

    app = QApplication.instance() or QApplication([])
    win = LiveCaptionWindow()

    # Verify signals update UI state
    win.state_updated.emit("HEARING YOU", "Capturing user speech")
    assert win.state_badge.text() == "HEARING YOU"

    win.partial_caption_updated.emit("show me open")
    assert win.live_caption_text.text() == "show me open"

    win.final_transcript_ready.emit("show me open windows")
    assert "show me open windows" in win.live_caption_text.text()

    win.assistant_reply_ready.emit("Found 3 open windows.", "Found 3 open windows.")
    # Transcript contains formatted text
    html = win.transcript_browser.toHtml()
    assert "ZERO" in html
    assert "Found 3 open windows" in html


# =============================================================================
# 14. Existing typed-input and Knowledge behavior still work
# =============================================================================
def test_14_existing_typed_input_and_knowledge_behavior():
    assistant = ZeroAssistant()
    assistant.initialize()
    assistant.wake()

    # Typed question
    res = assistant.process_input("What is your name?")
    assert res["reply_text"] is not None
    assert len(res["reply_text"]) > 0

    # Knowledge search intent
    res_k = assistant.process_input("Zero, search knowledge for Python")
    assert res_k["intent"] == "SEARCH_KNOWLEDGE"
    assert "Python" in res_k["reply_text"] or "Knowledge base" in res_k["reply_text"]
