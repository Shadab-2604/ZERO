"""
Database session and connection management for Zero AI.
"""

from contextlib import contextmanager
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.config.settings import get_settings
from app.memory.models import Base
from app.utils.paths import get_data_dir

logger = logging.getLogger(__name__)

_engine = None
_SessionLocal = None


def get_db_path() -> Path:
    """Return the resolved Path to the SQLite database file."""
    settings = get_settings()
    db_url = settings.database_url
    if db_url.startswith("sqlite"):
        db_path = db_url.replace("sqlite:///", "")
        p = Path(db_path)
        if not p.is_absolute():
            return (get_data_dir() / p.name).resolve()
        return p.resolve()
    return (get_data_dir() / "zero.db").resolve()


def get_engine():
    """Retrieve or create the SQLAlchemy engine."""
    global _engine
    if _engine is None:
        settings = get_settings()
        db_url = settings.database_url

        # Ensure directory exists if SQLite
        if db_url.startswith("sqlite"):
            full_path = get_db_path()
            db_url = f"sqlite:///{full_path}"
            connect_args = {"check_same_thread": False}
        else:
            connect_args = {}

        logger.info("Initializing database with URL: %s", db_url.split("@")[-1])
        _engine = create_engine(db_url, connect_args=connect_args)
    return _engine


def get_session_factory():
    """Retrieve or create the sessionmaker."""
    global _SessionLocal
    if _SessionLocal is None:
        engine = get_engine()
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return _SessionLocal


def init_db() -> None:
    """Initialize database tables."""
    engine = get_engine()
    logger.info("Creating database tables if not existing...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized successfully.")


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Provide a transactional database session scope."""
    session_factory = get_session_factory()
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error("Database transaction rolled back due to error: %s", e)
        raise
    finally:
        session.close()


def backup_database() -> Path | None:
    """Create a backup of the current SQLite database."""
    settings = get_settings()
    if not settings.database_url.startswith("sqlite"):
        logger.warning("Backup is only supported for local SQLite databases.")
        return None

    db_path = settings.database_url.replace("sqlite:///", "")
    source_file = Path(db_path)
    if not source_file.is_absolute():
        source_file = (get_data_dir() / source_file.name).resolve()

    if not source_file.exists():
        logger.warning("Database file %s does not exist, skipping backup.", source_file)
        return None

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_file = get_data_dir() / f"zero_backup_{timestamp}.db"
    try:
        shutil.copy2(source_file, backup_file)
        logger.info("Database backed up successfully to %s", backup_file)
        return backup_file
    except Exception as e:
        logger.error("Failed to backup database: %s", e)
        return None
