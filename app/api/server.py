"""
FastAPI local API server configuration and background runner.
Bound to 127.0.0.1 by default for desktop security.
"""

import logging
import threading
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from app.config.settings import get_settings
from app.api.routes.health import router as health_router
from app.api.routes.assistant import router as assistant_router
from app.api.routes.briefing import router as briefing_router
from app.api.routes.settings import router as settings_router
from app.api.routes.knowledge import router as knowledge_router
from app.api.routes.artifacts import router as artifacts_router
from app.api.routes.conversations import router as conversations_router

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Zero AI Desktop API",
        version="0.1.0",
        description="Local REST API for Zero personal assistant subsystems",
        docs_url="/docs",
        redoc_url=None,
    )

    # Local loopback security: restrict CORS to localhost
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1", "http://localhost"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        # Redact raw internal errors in responses
        logger.error("API error handling %s: %s", request.url.path, exc)
        return JSONResponse(
            status_code=500,
            content={"error": "An internal server error occurred.", "path": request.url.path},
        )

    @app.get("/")
    def root():
        """Root endpoint displaying Zero status and navigation."""
        settings = get_settings()
        return {
            "name": "Zero AI Desktop Assistant",
            "status": "ONLINE",
            "zero_mode": settings.zero_mode,
            "ai_provider": settings.ai_provider,
            "chat_model": settings.local_chat_model,
            "code_model": settings.local_code_model,
            "voice_enabled": settings.voice_enabled,
            "endpoints": {
                "health": "/health",
                "docs": "/docs",
                "settings": "/api/settings/public",
                "knowledge": "/api/knowledge/status",
                "conversations": "/api/conversations",
            },
        }

    # Register Routers
    app.include_router(health_router)
    app.include_router(assistant_router)
    app.include_router(briefing_router)
    app.include_router(settings_router)
    app.include_router(knowledge_router)
    app.include_router(artifacts_router)
    app.include_router(conversations_router)

    return app


class APIServerManager:
    """Manages the background Uvicorn server lifecycle."""

    def __init__(self):
        self._server: uvicorn.Server | None = None
        self._thread: threading.Thread | None = None

    def start_background(self, host: str = "127.0.0.1", port: int = 8765) -> None:
        """Start API server in a separate background daemon thread."""
        app = create_app()
        config = uvicorn.Config(
            app=app,
            host=host,
            port=port,
            log_level="warning",
            loop="asyncio",
        )
        self._server = uvicorn.Server(config)

        def _serve():
            logger.info("Starting local API server on http://%s:%d", host, port)
            try:
                self._server.run()
            except Exception as e:
                logger.error("Uvicorn server encountered an error: %s", e)

        self._thread = threading.Thread(target=_serve, name="ZeroAPIServerThread", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Gracefully signal the server to stop."""
        if self._server:
            logger.info("Stopping local API server...")
            self._server.should_exit = True
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=2.0)
            logger.info("Local API server stopped.")


# Global server manager
_api_server_manager: APIServerManager | None = None


def get_api_server_manager() -> APIServerManager:
    global _api_server_manager
    if _api_server_manager is None:
        _api_server_manager = APIServerManager()
    return _api_server_manager
