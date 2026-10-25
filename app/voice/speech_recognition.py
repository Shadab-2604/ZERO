"""
Speech recognition (STT) interface for Zero AI.
Captures microphone audio synchronously or asynchronously without blocking the main GUI thread.
"""

import logging
import threading
from typing import Callable

logger = logging.getLogger(__name__)


class SpeechRecognizer:
    """Microphone speech-to-text listener with graceful error handling and synchronous/asynchronous recording."""

    def __init__(self):
        self._recognizer = None
        self._is_available = False
        self._init_recognizer()

    def _init_recognizer(self):
        try:
            import speech_recognition as sr
            self._recognizer = sr.Recognizer()
            self._recognizer.energy_threshold = 300
            self._recognizer.dynamic_energy_threshold = True
            # Verify microphone availability
            mics = sr.Microphone.list_microphone_names()
            self._is_available = len(mics) > 0
            logger.info("SpeechRecognizer initialized. Mics found: %d", len(mics))
        except Exception as e:
            logger.warning("Could not initialize SpeechRecognizer: %s", e)
            self._is_available = False

    @property
    def is_available(self) -> bool:
        return self._is_available

    def listen_once(
        self,
        timeout: float = 5.0,
        phrase_time_limit: float = 10.0,
    ) -> tuple[bool, str]:
        """
        Record and transcribe a single utterance synchronously.
        Returns (success: bool, text_or_error: str).
        """
        if not self._recognizer or not self._is_available:
            return False, "Speech recognition engine is unavailable."

        import speech_recognition as sr
        try:
            with sr.Microphone() as source:
                self._recognizer.adjust_for_ambient_noise(source, duration=0.3)
                audio = self._recognizer.listen(
                    source, timeout=timeout, phrase_time_limit=phrase_time_limit
                )
        except sr.WaitTimeoutError:
            return False, "TIMEOUT"
        except Exception as e:
            logger.error("Microphone hardware error: %s", e)
            return False, f"Microphone access error: {str(e)}"

        try:
            text = self._recognizer.recognize_google(audio)
            if text and text.strip():
                return True, text.strip()
            return False, "EMPTY"
        except sr.UnknownValueError:
            return False, "UNRECOGNIZED"
        except sr.RequestError as e:
            logger.error("Speech recognition service connection error: %s", e)
            return False, "Speech recognition service unavailable."
        except Exception as e:
            logger.error("Transcription error: %s", e)
            return False, f"Recognition error: {str(e)}"

    def listen_once_async(
        self,
        on_success: Callable[[str], None],
        on_error: Callable[[str], None] | None = None,
        timeout: float = 6.0,
        phrase_time_limit: float = 10.0,
    ) -> threading.Thread:
        """
        Record and transcribe a single utterance asynchronously in a daemon thread.
        """
        def _worker():
            success, result = self.listen_once(timeout=timeout, phrase_time_limit=phrase_time_limit)
            if success:
                on_success(result)
            else:
                if on_error:
                    if result == "TIMEOUT":
                        on_error("Listening timed out. No speech was detected.")
                    elif result == "UNRECOGNIZED":
                        on_error("Could not understand audio.")
                    else:
                        on_error(result)

        thread = threading.Thread(target=_worker, name="ZeroListenWorker", daemon=True)
        thread.start()
        return thread
