"""
Centralized settings management for Zero AI using Pydantic Settings.
Never prints or exposes secrets in serialized outputs or logs.
"""

from typing import Literal
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from app.utils.paths import get_project_root


class Settings(BaseSettings):
    """Zero AI application settings loaded from environment and .env file."""

    model_config = SettingsConfigDict(
        env_file=get_project_root() / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Core Application
    app_name: str = Field(default="Zero", alias="APP_NAME")
    app_env: Literal["development", "production", "testing"] = Field(
        default="development", alias="APP_ENV"
    )
    app_host: str = Field(default="127.0.0.1", alias="APP_HOST")
    app_port: int = Field(default=8765, alias="APP_PORT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # AI Provider
    ai_provider: str = Field(default="demo", alias="AI_PROVIDER")
    ai_api_key: str = Field(default="", alias="AI_API_KEY")
    ai_model: str = Field(default="", alias="AI_MODEL")
    ai_api_base: str = Field(default="", alias="AI_API_BASE")
    ai_timeout: float = Field(default=30.0, alias="AI_TIMEOUT")

    # Local AI & Routing (Ollama)
    zero_mode: str = Field(default="local_only", alias="ZERO_MODE")
    local_chat_model: str = Field(default="llama3.2", alias="LOCAL_CHAT_MODEL")
    local_code_model: str = Field(default="qwen2.5-coder:3b", alias="LOCAL_CODE_MODEL")
    external_ai_enabled: bool = Field(default=False, alias="EXTERNAL_AI_ENABLED")
    web_search_enabled: bool = Field(default=False, alias="WEB_SEARCH_ENABLED")

    # Voice Subsystem
    voice_enabled: bool = Field(default=False, alias="VOICE_ENABLED")
    voice_provider: str = Field(default="local", alias="VOICE_PROVIDER")
    voice_input_device: str = Field(default="", alias="VOICE_INPUT_DEVICE")
    voice_output_voice: str = Field(default="", alias="VOICE_OUTPUT_VOICE")
    voice_stt_engine: str = Field(default="google", alias="VOICE_STT_ENGINE")
    wake_word_enabled: bool = Field(default=False, alias="WAKE_WORD_ENABLED")
    wake_word: str = Field(default="zero wake up", alias="WAKE_WORD")
    tts_voice_rate: int = Field(default=180, alias="TTS_VOICE_RATE")
    tts_voice_volume: float = Field(default=0.9, alias="TTS_VOICE_VOLUME")

    # Knowledge Base
    knowledge_backend: str = Field(default="sqlite_fts5", alias="KNOWLEDGE_BACKEND")

    # Persistence
    database_url: str = Field(
        default="sqlite:///./data/zero.db", alias="DATABASE_URL"
    )
    timezone: str = Field(default="Asia/Kolkata", alias="TIMEZONE")

    # Briefing & Interaction
    briefing_enabled: bool = Field(default=True, alias="BRIEFING_ENABLED")
    briefing_on_startup: bool = Field(default=True, alias="BRIEFING_ON_STARTUP")
    briefing_on_wake: bool = Field(default=True, alias="BRIEFING_ON_WAKE")
    greeting_style: str = Field(default="jarvis", alias="GREETING_STYLE")

    # GUI
    reduced_motion: bool = Field(default=False, alias="REDUCED_MOTION")
    gui_theme: str = Field(default="jarvis_dark", alias="GUI_THEME")

    def get_public_dict(self) -> dict:
        """
        Return safe dictionary of non-secret settings for API and UI display.
        API keys and sensitive tokens are completely masked.
        """
        has_key = bool(self.ai_api_key and len(self.ai_api_key.strip()) > 0)
        masked_key = "configured (••••••••)" if has_key else "not configured"
        return {
            "app_name": self.app_name,
            "app_env": self.app_env,
            "app_host": self.app_host,
            "app_port": self.app_port,
            "log_level": self.log_level,
            "ai_provider": self.ai_provider,
            "ai_api_key_status": masked_key,
            "ai_model": self.ai_model or ("demo-built-in" if self.ai_provider == "demo" else "default"),
            "ai_api_base": self.ai_api_base or "default",
            "ai_timeout": self.ai_timeout,
            "zero_mode": self.zero_mode,
            "local_chat_model": self.local_chat_model,
            "local_code_model": self.local_code_model,
            "external_ai_enabled": self.external_ai_enabled,
            "web_search_enabled": self.web_search_enabled,
            "voice_enabled": self.voice_enabled,
            "voice_provider": self.voice_provider,
            "voice_input_device": self.voice_input_device,
            "voice_output_voice": self.voice_output_voice,
            "voice_stt_engine": self.voice_stt_engine,
            "wake_word_enabled": self.wake_word_enabled,
            "wake_word": self.wake_word,
            "tts_voice_rate": self.tts_voice_rate,
            "tts_voice_volume": self.tts_voice_volume,
            "knowledge_backend": self.knowledge_backend,
            "timezone": self.timezone,
            "briefing_enabled": self.briefing_enabled,
            "briefing_on_startup": self.briefing_on_startup,
            "briefing_on_wake": self.briefing_on_wake,
            "greeting_style": self.greeting_style,
            "reduced_motion": self.reduced_motion,
            "gui_theme": self.gui_theme,
        }

    @property
    def ollama_model_chat(self) -> str:
        """Alias property returning active local chat model."""
        return self.local_chat_model or self.ai_model or "llama3.2"


# Global singleton instance
_settings_instance: Settings | None = None


def get_settings(reload: bool = False) -> Settings:
    """Retrieve or reload cached settings singleton."""
    global _settings_instance
    if _settings_instance is None or reload:
        _settings_instance = Settings()
    return _settings_instance
