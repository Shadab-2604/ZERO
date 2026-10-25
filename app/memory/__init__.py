"""
Zero AI — Persistence, Database Models & Activity Stores.

Responsibilities:
- SQLite engine initialization, connection pooling, and schema creation (database.py).
- SQLAlchemy ORM models: Conversation, Message, SessionRecord, ActivityEvent, SessionSummary, TaskItem, UserPreference (models.py).
- Conversation session history management (conversation_store.py).
- Audited system activity event recording (activity_store.py).
"""

from app.memory.database import (
    Base,
    init_db,
    get_engine,
    get_session_factory,
    get_db_session,
    backup_database,
)
from app.memory.models import (
    Conversation,
    Message,
    SessionRecord,
    ActivityEvent,
    SessionSummary,
    TaskItem,
    UserPreference,
)
from app.memory.conversation_store import ConversationStore
from app.memory.activity_store import ActivityStore

__all__ = [
    "Base",
    "init_db",
    "get_engine",
    "get_session_factory",
    "get_db_session",
    "backup_database",
    "Conversation",
    "Message",
    "SessionRecord",
    "ActivityEvent",
    "SessionSummary",
    "TaskItem",
    "UserPreference",
    "ConversationStore",
    "ActivityStore",
]
