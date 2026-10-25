"""
Real subsystem health monitoring for Zero AI.
Checks database connectivity, AI provider availability, voice devices, and host resources.
"""

import logging
from typing import Literal
import psutil
from sqlalchemy import text
from app.config.settings import get_settings
from app.memory.database import get_db_session

logger = logging.getLogger(__name__)


class HealthMonitor:
    """Subsystem health inspector."""

    @staticmethod
    def check_database() -> dict:
        """Check database connectivity and table readiness."""
        try:
            with get_db_session() as session:
                session.execute(text("SELECT 1"))
            return {"status": "healthy", "message": "SQLite database connected and responsive"}
        except Exception as e:
            logger.error("Database health check failed: %s", e)
            return {"status": "unhealthy", "message": str(e)}

    @staticmethod
    def check_ai_provider() -> dict:
        """Check configured AI provider readiness."""
        settings = get_settings()
        provider = settings.ai_provider.lower()

        if provider == "demo":
            return {
                "status": "healthy",
                "mode": "DEMO",
                "provider": "demo",
                "message": "Local Demo AI Provider ready (offline mode, no API key required)",
            }

        # Real cloud provider
        has_key = bool(settings.ai_api_key and settings.ai_api_key.strip())
        if not has_key:
            return {
                "status": "degraded",
                "mode": "OFFLINE",
                "provider": provider,
                "message": f"Provider '{provider}' configured but AI_API_KEY is missing. Operating with offline fallback.",
            }

        return {
            "status": "healthy",
            "mode": "ONLINE",
            "provider": provider,
            "message": f"Provider '{provider}' configured with API key. Model: {settings.ai_model or 'default'}",
        }

    _cached_voice_status: dict | None = None

    @classmethod
    def check_voice_subsystem(cls, force_refresh: bool = False) -> dict:
        """Check speech recognition and TTS engine status safely."""
        if cls._cached_voice_status and not force_refresh:
            return cls._cached_voice_status

        settings = get_settings()
        if not settings.voice_enabled:
            return {
                "status": "disabled",
                "message": "Voice subsystem disabled in settings",
                "speech_recognition": "disabled",
                "speech_synthesis": "disabled",
            }

        tts_ok = False
        try:
            import pyttsx3
            tts_ok = True
        except Exception as e:
            logger.debug("TTS health check issue: %s", e)

        sr_ok = False
        try:
            import speech_recognition as sr
            sr_ok = True
        except Exception as e:
            logger.debug("Microphone list issue: %s", e)

        result = {
            "status": "healthy" if (tts_ok and sr_ok) else "degraded",
            "message": "Voice engines available" if (tts_ok and sr_ok) else "Microphone or TTS engine partially available",
            "speech_recognition": "available" if sr_ok else "no_microphone_found",
            "speech_synthesis": "available" if tts_ok else "unavailable",
            "wake_word_enabled": settings.wake_word_enabled,
        }
        cls._cached_voice_status = result
        return result

    @staticmethod
    def check_system_resources() -> dict:
        """Fetch real host resource metrics."""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.05)
            ram = psutil.virtual_memory()
            disk = psutil.disk_usage(".")
            return {
                "cpu_usage_percent": cpu_percent,
                "ram_usage_percent": ram.percent,
                "ram_available_mb": round(ram.available / (1024 * 1024), 1),
                "disk_free_gb": round(disk.free / (1024 * 1024 * 1024), 2),
            }
        except Exception as e:
            logger.error("Error gathering host metrics: %s", e)
            return {
                "cpu_usage_percent": 0.0,
                "ram_usage_percent": 0.0,
                "ram_available_mb": 0.0,
                "disk_free_gb": 0.0,
            }

    @classmethod
    def get_full_health_report(cls) -> dict:
        """Produce comprehensive health report for API and GUI status bar."""
        db_health = cls.check_database()
        ai_health = cls.check_ai_provider()
        voice_health = cls.check_voice_subsystem()
        resources = cls.check_system_resources()

        overall_ok = (
            db_health["status"] == "healthy"
            and ai_health["status"] in ("healthy", "degraded")
        )

        return {
            "status": "healthy" if overall_ok else "unhealthy",
            "mode": ai_health.get("mode", "DEMO"),
            "database": db_health,
            "ai_provider": ai_health,
            "voice": voice_health,
            "resources": resources,
        }
