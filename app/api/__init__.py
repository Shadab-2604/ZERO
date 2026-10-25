"""
Zero AI — Isolated Loopback REST API Server (FastAPI).

Responsibilities:
- Local loopback REST interface bound strictly to 127.0.0.1:8765.
- Endpoints for assistant state, chat interaction, daily briefings, activity logs, knowledge sync, and telemetry.
- Desktop process isolation and secure IPC.
"""

from app.api.server import create_app, APIServerManager, get_api_server_manager

__all__ = [
    "create_app",
    "APIServerManager",
    "get_api_server_manager",
]
