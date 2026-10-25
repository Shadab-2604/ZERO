"""
Zero AI Streaming Voice Listener with Voice Activity Detection (VAD),
Utterance Continuation, Real-Time Live Partial Captions, and Barge-In Audio Interruption.

Key Requirements:
- Scenario A: Normal conversation (User speaks -> Live captions -> Finalized utterance -> Assistant answers).
- Scenario B: Pause and continue talking (Silence threshold 1.5-2.0s, continuation window up to 5.0s without premature send).
- Scenario C & D: Barge-in interruption during entire assistant speech output (User starts talking -> Instant TTS halt -> INTERRUPTED state -> Captures user speech -> Submits finalized utterance).
- Audio isolation: Discards speaker echo so assistant never transcribes its own voice.
"""

import logging
import math
import queue
import struct
import threading
import time
from typing import Callable

from app.core.state_manager import AssistantState

logger = logging.getLogger(__name__)

try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False
    logger.warning("PyAudio not available; streaming voice listener disabled.")

try:
    import speech_recognition as sr
    SR_AVAILABLE = True
except ImportError:
    SR_AVAILABLE = False
    logger.warning("speech_recognition not available.")


def calculate_rms(raw_pcm_bytes: bytes) -> float:
    """Calculate root-mean-square energy of 16-bit mono PCM audio."""
    if not raw_pcm_bytes:
        return 0.0
    count = len(raw_pcm_bytes) // 2
    if count == 0:
        return 0.0
    try:
        # Unpack short integers (h = 16-bit signed)
        shorts = struct.unpack(f"<{count}h", raw_pcm_bytes[:count * 2])
        sum_squares = sum(s * s for s in shorts)
        return math.sqrt(sum_squares / count)
    except Exception:
        return 0.0


class StreamingVoiceRecognizer:
    """
    Real-time streaming audio listener with energy-based VAD,
    partial caption recognition, pause continuation, and barge-in interruption.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        chunk_size: int = 1024,
        silence_threshold_seconds: float = 1.8,
        continuation_window_seconds: float = 5.0,
        min_speech_duration_seconds: float = 0.35,
        is_speaking_check: Callable[[], bool] | None = None,
        on_state_changed: Callable[[AssistantState, str], None] | None = None,
        on_partial_transcript: Callable[[str], None] | None = None,
        on_final_transcript: Callable[[str], None] | None = None,
        on_barge_in_interrupted: Callable[[], None] | None = None,
        on_error: Callable[[str], None] | None = None,
    ):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.silence_threshold = silence_threshold_seconds
        self.continuation_window = continuation_window_seconds
        self.min_speech_duration = min_speech_duration_seconds

        self._is_speaking_check = is_speaking_check or (lambda: False)
        self._on_state_changed = on_state_changed
        self._on_partial_transcript = on_partial_transcript
        self._on_final_transcript = on_final_transcript
        self._on_barge_in_interrupted = on_barge_in_interrupted
        self._on_error = on_error

        self._recognizer = sr.Recognizer() if SR_AVAILABLE else None
        if self._recognizer:
            self._recognizer.energy_threshold = 300
            self._recognizer.dynamic_energy_threshold = False

        self._pyaudio_instance: pyaudio.PyAudio | None = None
        self._audio_stream = None

        self._stop_event = threading.Event()
        self._worker_thread: threading.Thread | None = None
        self._is_muted = False
        self._lock = threading.Lock()

        # Dynamic ambient noise energy tracker
        self._ambient_energy = 250.0

        # Partial recognition worker queue to avoid blocking audio stream
        self._partial_queue: queue.Queue[bytes] = queue.Queue(maxsize=2)
        self._partial_thread: threading.Thread | None = None

    @property
    def is_running(self) -> bool:
        return self._worker_thread is not None and self._worker_thread.is_alive()

    @property
    def is_muted(self) -> bool:
        return self._is_muted

    def set_muted(self, muted: bool) -> None:
        """Mute or unmute microphone audio capture."""
        with self._lock:
            self._is_muted = muted
            logger.info("Microphone muted state set to: %s", muted)

    def start(self) -> bool:
        """Start streaming listener background worker."""
        if not PYAUDIO_AVAILABLE or not SR_AVAILABLE:
            logger.warning("Streaming voice listener cannot start: dependencies unavailable.")
            if self._on_error:
                self._on_error("PyAudio or SpeechRecognition library is missing.")
            return False

        if self.is_running:
            return True

        self._stop_event.clear()
        self._partial_thread = threading.Thread(
            target=self._partial_recognition_worker,
            name="ZeroPartialASRWorker",
            daemon=True,
        )
        self._partial_thread.start()

        self._worker_thread = threading.Thread(
            target=self._streaming_loop,
            name="ZeroStreamAudioWorker",
            daemon=True,
        )
        self._worker_thread.start()
        logger.info("StreamingVoiceRecognizer started.")
        return True

    def stop(self) -> None:
        """Halt streaming listener and release audio hardware."""
        self._stop_event.set()
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=1.5)
        self._close_stream()
        logger.info("StreamingVoiceRecognizer stopped.")

    def _init_audio_stream(self) -> bool:
        """Open 16kHz 16-bit mono PCM microphone stream."""
        try:
            self._close_stream()
            self._pyaudio_instance = pyaudio.PyAudio()
            self._audio_stream = self._pyaudio_instance.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size,
            )
            return True
        except Exception as e:
            logger.error("Failed to open PyAudio input stream: %s", e)
            if self._on_error:
                self._on_error(f"Microphone access error: {str(e)}")
            return False

    def _close_stream(self) -> None:
        """Safely close active PyAudio stream."""
        if self._audio_stream:
            try:
                self._audio_stream.stop_stream()
                self._audio_stream.close()
            except Exception:
                pass
            self._audio_stream = None

        if self._pyaudio_instance:
            try:
                self._pyaudio_instance.terminate()
            except Exception:
                pass
            self._pyaudio_instance = None

    def _notify_state(self, state: AssistantState, reason: str = ""):
        if self._on_state_changed:
            try:
                self._on_state_changed(state, reason)
            except Exception as e:
                logger.error("Error in on_state_changed callback: %s", e)

    def _partial_recognition_worker(self):
        """Worker thread executing partial recognition on intermediate audio buffers."""
        while not self._stop_event.is_set():
            try:
                raw_audio = self._partial_queue.get(timeout=0.2)
            except queue.Empty:
                continue

            if not raw_audio or not self._recognizer:
                continue

            try:
                audio_data = sr.AudioData(raw_audio, self.sample_rate, 2)
                partial_text = self._recognizer.recognize_google(audio_data)
                if partial_text and self._on_partial_transcript:
                    self._on_partial_transcript(partial_text.strip())
            except (sr.UnknownValueError, sr.RequestError):
                pass
            except Exception as e:
                logger.debug("Partial recognition notice: %s", e)

    def _streaming_loop(self):
        """
        Main streaming audio loop:
        Monitors RMS energy, detects speech onset/offset, triggers barge-in,
        handles pause continuation, and finalizes utterances.
        """
        if not self._init_audio_stream():
            return

        self._notify_state(AssistantState.LISTENING, "Microphone ready")

        utterance_buffer = bytearray()
        speech_started_time = 0.0
        last_speech_time = 0.0
        in_speech = False
        consecutive_speech_frames = 0
        last_partial_time = 0.0

        bytes_per_frame = self.chunk_size * 2  # 16-bit mono = 2 bytes per sample
        chunk_duration = self.chunk_size / self.sample_rate  # ~0.064s for 1024 frames @ 16kHz

        while not self._stop_event.is_set():
            if self._is_muted:
                time.sleep(0.1)
                continue

            try:
                raw_chunk = self._audio_stream.read(self.chunk_size, exception_on_overflow=False)
            except Exception as e:
                logger.warning("Audio read error: %s. Attempting stream reconnect...", e)
                time.sleep(0.2)
                self._init_audio_stream()
                continue

            if not raw_chunk:
                time.sleep(0.01)
                continue

            energy = calculate_rms(raw_chunk)
            now = time.time()
            zero_is_speaking = self._is_speaking_check()

            # Dynamic speech threshold adaptation
            if not in_speech and not zero_is_speaking:
                self._ambient_energy = 0.95 * self._ambient_energy + 0.05 * energy

            speech_threshold = max(350.0, self._ambient_energy * 2.2)
            barge_in_threshold = max(550.0, self._ambient_energy * 3.2)

            # =================================================================
            # BARGE-IN INTERRUPTION HANDLING (Scenarios C & D)
            # =================================================================
            if zero_is_speaking:
                if energy >= barge_in_threshold:
                    consecutive_speech_frames += 1
                    if consecutive_speech_frames >= 2:  # Confirmed user speech over TTS
                        logger.info("Barge-in detected! Energy: %.1f > %.1f", energy, barge_in_threshold)
                        self._notify_state(AssistantState.INTERRUPTED, "User interrupted assistant")

                        if self._on_barge_in_interrupted:
                            try:
                                self._on_barge_in_interrupted()
                            except Exception as e:
                                logger.error("Error invoking on_barge_in_interrupted: %s", e)

                        # Wait briefly for speaker reverberation to dissipate
                        time.sleep(0.08)
                        # Discard speaker-bleed frames and start capturing user utterance cleanly
                        utterance_buffer.clear()
                        in_speech = True
                        speech_started_time = now
                        last_speech_time = now
                        consecutive_speech_frames = 0
                        last_partial_time = now

                        self._notify_state(AssistantState.HEARING_YOU, "Listening to user speech")
                        continue
                else:
                    consecutive_speech_frames = 0
                continue

            # =================================================================
            # NORMAL SPEECH DETECTION & CONTINUATION (Scenarios A & B)
            # =================================================================
            if not in_speech:
                if energy >= speech_threshold:
                    consecutive_speech_frames += 1
                    if consecutive_speech_frames >= 2:
                        # User began speaking
                        in_speech = True
                        speech_started_time = now
                        last_speech_time = now
                        consecutive_speech_frames = 0
                        utterance_buffer.clear()
                        utterance_buffer.extend(raw_chunk)
                        last_partial_time = now

                        self._notify_state(AssistantState.HEARING_YOU, "User speech detected")
                else:
                    consecutive_speech_frames = 0
            else:
                # Currently inside user utterance
                utterance_buffer.extend(raw_chunk)

                if energy >= speech_threshold:
                    # Speech ongoing
                    last_speech_time = now

                    # Periodically request partial transcript every ~0.65s
                    if (now - last_partial_time) >= 0.65 and len(utterance_buffer) >= (self.sample_rate * 2 * 0.7):
                        last_partial_time = now
                        # Snapshot current audio for partial recognition
                        try:
                            # Drop oldest if queue full
                            if self._partial_queue.full():
                                try:
                                    self._partial_queue.get_nowait()
                                except queue.Empty:
                                    pass
                            self._partial_queue.put_nowait(bytes(utterance_buffer))
                        except queue.Full:
                            pass
                else:
                    # Silence detected during utterance
                    silence_duration = now - last_speech_time
                    utterance_duration = now - speech_started_time

                    # Scenario B: Utterance continuation check
                    # If silence duration exceeds threshold, finalize utterance!
                    if silence_duration >= self.silence_threshold or utterance_duration >= 20.0:
                        total_speech_len = len(utterance_buffer) / (self.sample_rate * 2)
                        if total_speech_len >= self.min_speech_duration:
                            self._finalize_utterance(bytes(utterance_buffer))
                        else:
                            logger.debug("Discarded brief noise spike (duration: %.2fs)", total_speech_len)
                            self._notify_state(AssistantState.LISTENING, "Noise discarded")

                        # Reset state
                        in_speech = False
                        utterance_buffer.clear()
                        consecutive_speech_frames = 0

        self._close_stream()

    def _finalize_utterance(self, raw_audio: bytes):
        """Transcribe completed utterance and deliver finalized transcript."""
        if not raw_audio or not self._recognizer:
            self._notify_state(AssistantState.LISTENING, "Empty utterance")
            return

        self._notify_state(AssistantState.PROCESSING, "Finalizing transcription")

        try:
            audio_data = sr.AudioData(raw_audio, self.sample_rate, 2)
            final_text = self._recognizer.recognize_google(audio_data)

            if final_text and final_text.strip():
                clean_text = final_text.strip()
                logger.info("Utterance finalized: '%s'", clean_text)
                if self._on_final_transcript:
                    self._on_final_transcript(clean_text)
            else:
                self._notify_state(AssistantState.LISTENING, "Unrecognized audio")
        except sr.UnknownValueError:
            logger.debug("Speech unrecognized (silence or ambient noise).")
            self._notify_state(AssistantState.LISTENING, "Speech unrecognized")
        except sr.RequestError as e:
            logger.error("Speech recognition service connection error: %s", e)
            if self._on_error:
                self._on_error("Speech recognition service connection error.")
            self._notify_state(AssistantState.ERROR, "Speech service error")
        except Exception as e:
            logger.error("Final transcription error: %s", e)
            if self._on_error:
                self._on_error(f"Recognition error: {str(e)}")
            self._notify_state(AssistantState.ERROR, str(e))
