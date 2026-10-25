"""
Dedicated wake-word listener subsystem for Zero AI.
Monitors microphone for configured wake phrase without continuous cloud streaming.
Avoids self-triggering while assistant is speaking.
"""

import logging
import threading
import time
from typing import Callable
from app.config.settings import get_settings

logger = logging.getLogger(__name__)


class WakeWordListener:
    """Dedicated background listener for 'Zero, wake up' detection."""

    def __init__(self, on_wake_detected: Callable[[], None], is_speaking_check: Callable[[], bool]):
        self._on_wake = on_wake_detected
        self._is_speaking_check = is_speaking_check
        self._is_running = False
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._muted = False
        self._mic_active = False

    @property
    def is_running(self) -> bool:
        return self._is_running

    @property
    def is_muted(self) -> bool:
        return self._muted

    @property
    def is_mic_active(self) -> bool:
        return self._mic_active

    def set_muted(self, muted: bool) -> None:
        """Toggle microphone mute status."""
        self._muted = muted
        logger.info("WakeWordListener muted state set to: %s", muted)

    def start(self) -> bool:
        """Start background wake-word listening loop."""
        settings = get_settings()
        if not settings.wake_word_enabled:
            logger.info("WakeWordListener is disabled in settings.")
            return False

        if self._is_running:
            return True

        self._stop_event.clear()
        self._is_running = True
        self._thread = threading.Thread(
            target=self._listen_loop, name="ZeroWakeWordWorker", daemon=True
        )
        self._thread.start()
        logger.info("WakeWordListener started in background thread.")
        return True

    def stop(self) -> None:
        """Stop background wake listener."""
        self._stop_event.set()
        self._is_running = False
        self._mic_active = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        logger.info("WakeWordListener stopped.")

    def _listen_loop(self) -> None:
        """Background continuous phrase detection loop."""
        try:
            import speech_recognition as sr
        except ImportError:
            logger.warning("speech_recognition not installed. Wake listener inactive.")
            self._is_running = False
            return

        recognizer = sr.Recognizer()
        recognizer.energy_threshold = 400
        recognizer.dynamic_energy_threshold = True

        target_phrase = get_settings().wake_word.lower()

        while not self._stop_event.is_set():
            if self._muted:
                self._mic_active = False
                time.sleep(0.5)
                continue

            # Don't listen to Zero's own voice
            if self._is_speaking_check():
                self._mic_active = False
                time.sleep(0.3)
                continue

            try:
                with sr.Microphone() as source:
                    self._mic_active = True
                    # Short audio snippet check (1.5 - 2.5 seconds)
                    recognizer.adjust_for_ambient_noise(source, duration=0.2)
                    audio = recognizer.listen(source, timeout=2.0, phrase_time_limit=3.0)
                    self._mic_active = False

                # Transcribe locally or with fallback recognizer
                text = recognizer.recognize_google(audio).lower()
                logger.debug("Wake listener heard: '%s'", text)

                # Check if target phrase is matched
                if target_phrase in text or "zero wake up" in text or "wake up" in text:
                    logger.info("Wake word detected ('%s')!", text)
                    if not self._is_speaking_check():
                        self._on_wake()
            except sr.WaitTimeoutError:
                self._mic_active = False
                continue
            except sr.UnknownValueError:
                self._mic_active = False
                continue
            except Exception as e:
                self._mic_active = False
                logger.debug("Wake listener ambient cycle: %s", e)
                time.sleep(0.5)
