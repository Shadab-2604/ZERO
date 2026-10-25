"""
Application bootstrap logic for Zero AI.
Initializes directories, configuration, database, logging, and local background API server.
"""

import logging
import shutil
from app.utils.paths import (
    get_data_dir,
    get_logs_dir,
    get_env_file_path,
    get_env_example_path,
)
from app.config.settings import get_settings
from app.config.logging_config import setup_logging
from app.memory.database import init_db
from app.core.assistant import get_assistant
from app.api.server import get_api_server_manager

logger = logging.getLogger(__name__)


def bootstrap_application(start_api_server: bool = True) -> None:
    """
    Perform foundational boot sequence:
    1. Prepare data and logs directories
    2. Seed .env from .env.example only if .env does not exist
    3. Configure structured rotating logging
    4. Initialize SQLite database schema
    5. Spin up background local REST API
    6. Initialize assistant engine and session
    """
    # 1. Directories
    get_data_dir()
    get_logs_dir()

    # 2. Seed .env if missing (NEVER overwrite existing .env)
    env_file = get_env_file_path()
    env_example = get_env_example_path()
    if not env_file.exists() and env_example.exists():
        try:
            shutil.copy2(env_example, env_file)
            print("[BOOTSTRAP] Created default .env from .env.example")
        except Exception as e:
            print(f"[BOOTSTRAP WARNING] Could not copy .env.example to .env: {e}")

    # 3. Settings & Logging
    settings = get_settings(reload=True)
    setup_logging(log_level=settings.log_level)
    logger.info("Starting %s in %s environment...", settings.app_name, settings.app_env)

    # 4. Database Initialization
    init_db()

    # 5. Core Assistant Engine
    assistant = get_assistant()

    # 6. Background Local REST API
    if start_api_server:
        api_manager = get_api_server_manager()
        api_manager.start_background(host=settings.app_host, port=settings.app_port)

    logger.info("Zero AI bootstrap sequence completed successfully.")
