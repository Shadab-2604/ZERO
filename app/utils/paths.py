"""
Path resolution utilities for Zero AI.
"""

from pathlib import Path


def get_project_root() -> Path:
    """Return the absolute path to the root directory of the ZERO project."""
    # app/utils/paths.py -> app/utils -> app -> root
    return Path(__file__).resolve().parent.parent.parent


def get_data_dir() -> Path:
    """Return the absolute path to the persistent data directory."""
    data_dir = get_project_root() / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_logs_dir() -> Path:
    """Return the absolute path to the application logs directory."""
    logs_dir = get_project_root() / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir


def get_env_file_path() -> Path:
    """Return the path to the active .env file."""
    return get_project_root() / ".env"


def get_env_example_path() -> Path:
    """Return the path to .env.example."""
    return get_project_root() / ".env.example"


def get_knowledge_dir() -> Path:
    """Return the absolute path to the local Knowledge repository directory."""
    knowledge_dir = get_project_root() / "Knowledge"
    knowledge_dir.mkdir(parents=True, exist_ok=True)
    return knowledge_dir


def get_exports_dir() -> Path:
    """Return the absolute path to the generated artifacts/exports directory."""
    exports_dir = get_project_root() / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)
    return exports_dir
