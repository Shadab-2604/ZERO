"""
Zero AI — Finite State Machine & Operational Lifecycle Manager.

Purpose:
Maintains thread-safe assistant state transitions, tracks historical state
provenance, and dispatches change events to registered UI, audio, and API observers.

Responsibilities:
- Enforcing valid states across the assistant lifecycle:
  `STARTING`, `SLEEPING`, `READY`, `LISTENING`, `HEARING_YOU`, `PROCESSING`, `SPEAKING`, `INTERRUPTED`, `ERROR`.
- Providing re-entrant thread safety (`threading.RLock`) for concurrent state queries from GUI, audio worker threads, and REST API handlers.
- Dispatching asynchronous state callbacks outside the critical section to prevent re-entrant deadlocks with Qt signals or audio locks.

Deliberately Does Not Handle:
- Audio hardware streaming or microphone muting (delegated to `app.voice`).
- Natural language intent classification (delegated to `app.core.intent_router`).
"""

from enum import Enum
import logging
import threading
from typing import Callable
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class AssistantState(str, Enum):
    """
    Enumeration of all valid operational states for the Zero AI assistant.
    Inherits from str to allow direct JSON serialization and string comparisons.
    """
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
    """
    Thread-safe finite state machine orchestrator for Zero AI.
    
    Attributes:
        _current_state: Currently active AssistantState.
        _previous_state: State immediately preceding the active state.
        _lock: Reentrant lock guaranteeing atomic state transitions.
        _callbacks: Registered observer functions invoked on transition.
        _last_transition_time: UTC timestamp of the most recent transition.
    """

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
