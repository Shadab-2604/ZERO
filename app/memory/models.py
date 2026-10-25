from datetime import datetime, timezone
import uuid
from sqlalchemy import (
    Column,
    String,
    Text,
    DateTime,
    ForeignKey,
    Boolean,
    Integer,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def generate_uuid() -> str:
    return str(uuid.uuid4())


class Conversation(Base):
    """Conversation thread model."""

    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    title = Column(String(255), nullable=False, default="New Conversation")
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=utcnow, onupdate=utcnow, nullable=False
    )

    messages = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at"
    )


class Message(Base):
    """Individual chat message within a conversation."""

    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    conversation_id = Column(
        String(36), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    role = Column(String(32), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)

    conversation = relationship("Conversation", back_populates="messages")


class SessionRecord(Base):
    """Zero assistant runtime session tracking."""

    __tablename__ = "sessions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    started_at = Column(DateTime, default=utcnow, nullable=False)
    ended_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)


class ActivityEvent(Base):
    """Tracked user or project activity events."""

    __tablename__ = "activity_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    timestamp = Column(DateTime, default=utcnow, nullable=False)
    category = Column(String(64), nullable=False)  # session, task, note, test, project_action
    project = Column(String(128), nullable=True)
    description = Column(Text, nullable=False)


class SessionSummary(Base):
    """Stored summaries of previous user sessions."""

    __tablename__ = "session_summaries"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    session_id = Column(String(36), nullable=True)
    timestamp = Column(DateTime, default=utcnow, nullable=False)
    summary_text = Column(Text, nullable=False)
    tasks_pending = Column(Text, nullable=True)  # JSON or newline-separated
    tasks_completed = Column(Text, nullable=True)


class TaskItem(Base):
    """Tracked pending or completed tasks."""

    __tablename__ = "tasks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(32), default="pending", nullable=False)  # pending, in_progress, completed
    priority = Column(String(16), default="medium", nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=utcnow, onupdate=utcnow, nullable=False
    )


class UserPreference(Base):
    """Persistent non-secret user preferences."""

    __tablename__ = "user_preferences"

    key = Column(String(64), primary_key=True)
    value = Column(Text, nullable=False)
    updated_at = Column(
        DateTime, default=utcnow, onupdate=utcnow, nullable=False
    )
