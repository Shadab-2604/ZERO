"""
Zero assistant state machine.
Supported states: STARTING, SLEEPING, READY, LISTENING, THINKING, SPEAKING, ERROR.
"""

from enum import Enum
import logging
import threading
from typing import Callable
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class AssistantState(str, Enum):
    STARTING = "STARTING"
    SLEEPING = "SLEEPING"
    READY = "READY"
    LISTENING = "LISTENING"
    HEARING_YOU = "HEARING YOU"
    CAPTURING = "CAPTURING"
    THINKING = "THINKING"
    PROCESSING = "PROCESSING"
    SPEAKING = "SPEAKING"
    INTERRUPTED = "INTERRUPTED"
    ERROR = "ERROR"


class StateManager:
    """Thread-safe manager for Zero assistant state transitions."""

    def __init__(self, initial_state: AssistantState = AssistantState.SLEEPING):
        self._current_state = initial_state
        self._previous_state = initial_state
        self._lock = threading.RLock()
        self._callbacks: list[Callable[[AssistantState, AssistantState], None]] = []
        self._last_transition_time = datetime.now(timezone.utc)

    @property
    def current_state(self) -> AssistantState:
        with self._lock:
            return self._current_state

    @property
    def previous_state(self) -> AssistantState:
        with self._lock:
            return self._previous_state

    @property
    def last_transition_time(self) -> datetime:
        with self._lock:
            return self._last_transition_time

    def register_callback(
        self, callback: Callable[[AssistantState, AssistantState], None]
    ) -> None:
        """Register a subscriber callback for state changes."""
        with self._lock:
            if callback not in self._callbacks:
                self._callbacks.append(callback)

    def unregister_callback(
        self, callback: Callable[[AssistantState, AssistantState], None]
    ) -> None:
        with self._lock:
            if callback in self._callbacks:
                self._callbacks.remove(callback)

    def transition_to(self, new_state: AssistantState, reason: str = "") -> bool:
        """
        Transition assistant to new state and notify registered listeners.
        """
        with self._lock:
            if self._current_state == new_state:
                return False

            old_state = self._current_state
            self._previous_state = old_state
            self._current_state = new_state
            self._last_transition_time = datetime.now(timezone.utc)

            logger.info(
                "Assistant state transition: %s -> %s (Reason: %s)",
                old_state.value,
                new_state.value,
                reason or "unspecified",
            )
            callbacks_copy = list(self._callbacks)

        # Notify callbacks outside lock to prevent deadlocks
        for cb in callbacks_copy:
            try:
                cb(old_state, new_state)
            except Exception as e:
                logger.error("Error executing state callback: %s", e)

        return True
