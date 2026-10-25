"""
Zero AI — Canonical Database Access & Engine Facade.

This module provides a clean facade to Zero's database access layer,
re-exporting engine setup, session factories, and initialization helpers
from `app.memory.database`.
"""

from app.memory.database import (
    Base,
    get_engine,
    get_session_factory,
    get_db_session,
    init_db,
    backup_database,
)

__all__ = [
    "Base",
    "get_engine",
    "get_session_factory",
    "get_db_session",
    "init_db",
    "backup_database",
]
