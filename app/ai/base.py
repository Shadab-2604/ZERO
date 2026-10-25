"""
Base interface and abstractions for Zero AI model providers.
"""

from abc import ABC, abstractmethod


class BaseAIProvider(ABC):
    """Abstract base class for all Zero AI model providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider name."""
        pass

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """True if the provider is fully configured and ready."""
        pass

    @abstractmethod
    def generate_response(
        self, messages: list[dict], system_prompt: str | None = None
    ) -> str:
        """
        Generate an assistant text response for a conversation thread.
        `messages` format: [{"role": "user"|"assistant"|"system", "content": "..."}]
        """
        pass

    @abstractmethod
    def generate_summary(self, text: str) -> str:
        """Generate a concise summary of the given text or activity record."""
        pass
