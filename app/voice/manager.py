"""
Voice subsystem manager coordinating speech recognition, synthesis, and wake listener.
"""

import logging
from typing import Callable, Any
from app.config.settings import get_settings
from app.voice.speech_synthesis import SpeechSynthesizer
from app.voice.speech_recognition import SpeechRecognizer
from app.voice.wake_listener import WakeWordListener

from app.voice.stream_listener import StreamingVoiceRecognizer

logger = logging.getLogger(__name__)


class VoiceManager:
    """Coordinates voice input/output pipelines, streaming recognition, and wake detection."""

    def __init__(
        self,
        on_wake_callback: Callable[[], None] | None = None,
        on_speech_recognized: Callable[[str], None] | None = None,
    ):
        self.synthesizer = SpeechSynthesizer()
        self.recognizer = SpeechRecognizer()
        self.streaming_listener: StreamingVoiceRecognizer | None = None
        self._on_wake = on_wake_callback
        self._on_speech_recognized = on_speech_recognized

        self.wake_listener = WakeWordListener(
            on_wake_detected=self._handle_wake_detected,
            is_speaking_check=lambda: self.synthesizer.is_speaking,
        )

        settings = get_settings()
        if settings.voice_enabled and settings.wake_word_enabled:
            self.wake_listener.start()

    @property
    def is_speaking(self) -> bool:
        """Check if assistant is actively speaking."""
        return self.synthesizer.is_speaking

    def _handle_wake_detected(self):
        """Dispatched when the wake phrase is validated."""
        if self._on_wake:
            self._on_wake()

    def speak(
        self,
        text: str,
        wait: bool = False,
        on_start: Callable[[], None] | None = None,
        on_end: Callable[[], None] | None = None,
        **kwargs,
    ) -> None:
        """Speak response text synchronously or asynchronously."""
        if not text or not text.strip():
            return
        if kwargs:
            self.synthesizer.speak(text, wait=wait, on_start=on_start, on_end=on_end, **kwargs)
        else:
            self.synthesizer.speak(text, wait=wait, on_start=on_start, on_end=on_end)

    def wait_until_done(self, timeout: float | None = 20.0) -> bool:
        """Wait until active speech completes playback."""
        return self.synthesizer.wait_until_done(timeout=timeout)

    def stop_speaking(self) -> None:
        """Interrupt and halt any active voice output."""
        self.synthesizer.stop()

    def create_streaming_listener(
        self,
        on_state_changed: Callable[[Any, str], None] | None = None,
        on_partial_transcript: Callable[[str], None] | None = None,
        on_final_transcript: Callable[[str], None] | None = None,
        on_error: Callable[[str], None] | None = None,
        silence_threshold_seconds: float = 1.8,
        continuation_window_seconds: float = 5.0,
    ) -> StreamingVoiceRecognizer:
        """
        Create and bind a streaming listener with automatic barge-in interruption.
        """
        def _handle_barge_in():
            logger.info("Barge-in callback invoked. Stopping TTS...")
            self.stop_speaking()

        self.streaming_listener = StreamingVoiceRecognizer(
            silence_threshold_seconds=silence_threshold_seconds,
            continuation_window_seconds=continuation_window_seconds,
            is_speaking_check=lambda: self.synthesizer.is_speaking,
            on_state_changed=on_state_changed,
            on_partial_transcript=on_partial_transcript,
            on_final_transcript=on_final_transcript,
            on_barge_in_interrupted=_handle_barge_in,
            on_error=on_error,
        )
        return self.streaming_listener

    def listen_once(self, timeout: float = 5.0, phrase_time_limit: float = 10.0) -> tuple[bool, str]:
        """Record and transcribe a single utterance synchronously."""
        if self.synthesizer.is_speaking:
            self.synthesizer.wait_until_done(timeout=5.0)
        return self.recognizer.listen_once(timeout=timeout, phrase_time_limit=phrase_time_limit)

    def trigger_push_to_talk(
        self,
        on_success: Callable[[str], None],
        on_error: Callable[[str], None] | None = None,
    ):
        """Begin one-shot voice recording for push-to-talk command."""
        self.stop_speaking()
        return self.recognizer.listen_once_async(on_success=on_success, on_error=on_error)

    def pause_wake_listener(self) -> None:
        """Pause wake listener to prevent microphone device contention."""
        self.wake_listener.set_muted(True)

    def resume_wake_listener(self) -> None:
        """Resume wake listener."""
        self.wake_listener.set_muted(False)

    def toggle_mute(self) -> bool:
        """Toggle microphone mute switch across wake and streaming listeners."""
        new_state = not self.wake_listener.is_muted
        self.wake_listener.set_muted(new_state)
        if self.streaming_listener:
            self.streaming_listener.set_muted(new_state)
        return new_state

    def shutdown(self) -> None:
        """Safely terminate all voice worker threads and hardware hooks."""
        logger.info("Shutting down VoiceManager...")
        if self.streaming_listener:
            self.streaming_listener.stop()
        self.wake_listener.stop()
        self.synthesizer.shutdown()
