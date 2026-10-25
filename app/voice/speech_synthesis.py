"""
Zero AI — Speech Synthesis (TTS) Engine & Windows SAPI5 Subsystem.

Purpose:
Coordinates non-blocking text-to-speech generation using Windows SAPI5 via
`pyttsx3`. Runs inside an isolated single-threaded apartment (STA) COM worker
thread to prevent COM marshaling deadlocks and GUI freezing.

Responsibilities:
- Asynchronous FIFO speech queuing with start/completion callback synchronization.
- Markdown sanitization: strips code blocks, tables, and URLs from audio output,
  substituting a concise summary and pointing users to their Live Caption HUD.
- Low-latency barge-in speech interruption (`stop()`): immediately purges queued
  utterances and resets COM buffers.
- Automatic engine re-initialization and recovery upon unexpected audio driver drops.

Important Dependencies:
- `pyttsx3`: Cross-platform TTS wrapper (using SAPI5 on Windows).
- `pythoncom`: Windows Component Object Model (COM) apartment management.

Deliberately Does Not Handle:
- Microphone capture or speech recognition (handled strictly in `app.voice.stream_listener`).
- Natural language generation or prompt routing (handled strictly in `app.ai`).
"""

import logging
import queue
import re
import threading
import time
from typing import Callable
from app.config.settings import get_settings

logger = logging.getLogger(__name__)


class SpeechSynthesizer:
    """
    Non-blocking text-to-speech engine with stop/interrupt support and completion tracking.
    
    Manages an isolated background thread initialized with `pythoncom.CoInitialize()`,
    guaranteeing safe Windows COM interop and preventing GUI thread starvation.
    """

    def __init__(self):
        self._queue: queue.Queue[tuple[str, Callable | None, Callable | None, threading.Event | None]] = queue.Queue()
        self._stop_event = threading.Event()
        self._worker_thread: threading.Thread | None = None
        self._is_speaking = False
        self._lock = threading.Lock()
        self._local_engine = None
        self._idle_event = threading.Event()
        self._idle_event.set()

    @property
    def is_speaking(self) -> bool:
        return self._is_speaking

    @staticmethod
    def clean_text_for_speech(text: str) -> str:
        """
        Prepare text for natural, pleasant speech synthesis:
        - For code-heavy answers, speaks: "I've placed the code in your captions. You can read and copy it there."
        - Does not read long code blocks character by character.
        - Speaks a concise explanation of the code alongside the caption notice.
        - Replaces markdown tables, links, and formatting.
        - Condenses lengthy answers for speech while leaving transcript intact.
        """
        if not text or not text.strip():
            return ""

        # Remove system notices and tags
        cleaned = text.replace("[DEMO MODE]", "").replace("[SYSTEM NOTICE]", "")
        cleaned = re.sub(r"\[ARTIFACT_PDF:[^\]]+\]", "I have generated the PDF document for download.", cleaned)

        # Check for code blocks
        has_code_blocks = bool(re.search(r"```[a-zA-Z0-9_\-]*\n.*?```", cleaned, flags=re.DOTALL))
        if has_code_blocks:
            # Extract explanation outside the code blocks
            explanation = re.sub(r"```[a-zA-Z0-9_\-]*\n.*?```", " ", cleaned, flags=re.DOTALL)
            explanation = re.sub(r"`([^`]+)`", r"\1", explanation)
            explanation = re.sub(r"https?://\S+", "the linked web address", explanation)
            explanation = re.sub(r"^#+\s*", "", explanation, flags=re.MULTILINE)
            explanation = re.sub(r"[*_~]{1,3}", "", explanation)
            explanation = re.sub(r"^\s*[-*•]\s+", "", explanation, flags=re.MULTILINE)
            explanation = re.sub(r"\|[^\n]+\|", " ", explanation)
            explanation = re.sub(r"\s+", " ", explanation).strip()

            caption_notice = "Here is the code implementation shown on screen. I've placed the code in your captions. You can read and copy it there."
            if explanation and len(explanation) > 10:
                sentences = re.split(r"(?<=[.!?])\s+", explanation)
                concise_summary = " ".join(sentences[:2]).strip()
                return f"{concise_summary} {caption_notice}"
            return caption_notice

        # Standard natural-language markdown cleaning
        cleaned = re.sub(r"`([^`]+)`", r"\1", cleaned)
        cleaned = re.sub(r"https?://\S+", "the linked web address", cleaned)
        cleaned = re.sub(r"^#+\s*", "", cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r"[*_~]{1,3}", "", cleaned)
        cleaned = re.sub(r"^\s*[-*•]\s+", "", cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r"\|[^\n]+\|", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        # For very long responses (>400 chars), speak primary content and summarize
        if len(cleaned) > 400:
            sentences = re.split(r"(?<=[.!?])\s+", cleaned)
            spoken_slice = " ".join(sentences[:3]).strip()
            if len(sentences) > 3:
                spoken_slice += " The complete details are displayed in your transcript."
            return spoken_slice

        return cleaned

    def start_worker(self):
        """Start background TTS dispatch worker."""
        if self._worker_thread and self._worker_thread.is_alive():
            return
        self._stop_event.clear()
        self._worker_thread = threading.Thread(
            target=self._run_loop, name="ZeroTTSWorker", daemon=True
        )
        self._worker_thread.start()

    def _init_local_engine(self):
        """Initialize or reset pyttsx3 engine within worker thread."""
        try:
            import pyttsx3
            settings = get_settings()
            self._local_engine = pyttsx3.init()
            self._local_engine.setProperty("rate", settings.tts_voice_rate)
            self._local_engine.setProperty("volume", settings.tts_voice_volume)
            logger.info("pyttsx3 engine initialized successfully.")
        except Exception as e:
            logger.warning("Local TTS engine init failed: %s", e)
            self._local_engine = None

    def _run_loop(self):
        """Worker loop processing TTS requests with Windows COM isolation."""
        try:
            import pythoncom
            pythoncom.CoInitialize()
        except Exception:
            pass

        self._init_local_engine()

        while not self._stop_event.is_set():
            try:
                item = self._queue.get(timeout=0.15)
            except queue.Empty:
                with self._lock:
                    if not self._is_speaking:
                        self._idle_event.set()
                continue

            text, on_start, on_end, done_evt = item
            if not text or not self._local_engine:
                if on_end:
                    try:
                        on_end()
                    except Exception:
                        pass
                if done_evt:
                    done_evt.set()
                continue

            with self._lock:
                self._is_speaking = True
                self._idle_event.clear()

            if on_start:
                try:
                    on_start()
                except Exception as e:
                    logger.error("Error in on_start callback: %s", e)

            try:
                clean_text = self.clean_text_for_speech(text)
                if clean_text:
                    self._local_engine.say(clean_text)
                    self._local_engine.runAndWait()
            except Exception as e:
                logger.error("TTS playback error: %s. Recovering engine...", e)
                try:
                    self._init_local_engine()
                except Exception:
                    pass
            finally:
                with self._lock:
                    self._is_speaking = False
                    if self._queue.empty():
                        self._idle_event.set()
                if on_end:
                    try:
                        on_end()
                    except Exception as e:
                        logger.error("Error in on_end callback: %s", e)
                if done_evt:
                    done_evt.set()

        try:
            import pythoncom
            pythoncom.CoUninitialize()
        except Exception:
            pass

    def speak(
        self,
        text: str,
        wait: bool = False,
        on_start: Callable[[], None] | None = None,
        on_end: Callable[[], None] | None = None,
        timeout: float | None = 30.0,
    ) -> None:
        """
        Enqueue text for speech synthesis.
        If wait=True, blocks until speech completes or timeout expires.
        """
        if not text or not text.strip():
            return

        if not self._worker_thread or not self._worker_thread.is_alive():
            self.start_worker()

        done_event = threading.Event() if wait else None
        self._queue.put((text, on_start, on_end, done_event))

        if wait and done_event:
            done_event.wait(timeout=timeout)

    def wait_until_done(self, timeout: float | None = 20.0) -> bool:
        """Wait until all queued speech finishes playback."""
        return self._idle_event.wait(timeout=timeout)

    def stop(self) -> None:
        """Clear queued speech and interrupt any active speech playback."""
        # Drain queue
        while not self._queue.empty():
            try:
                item = self._queue.get_nowait()
                if item and len(item) > 3 and item[3]:
                    item[3].set()
            except queue.Empty:
                break

        if self._local_engine:
            try:
                self._local_engine.stop()
            except Exception:
                pass

        with self._lock:
            self._is_speaking = False
            self._idle_event.set()
        logger.info("Speech playback halted and queue flushed.")

    def shutdown(self) -> None:
        """Safely terminate worker thread and release system resources."""
        self.stop()
        self._stop_event.set()
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=1.0)
