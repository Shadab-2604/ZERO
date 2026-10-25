"""
Conversation and message persistence repository for Zero AI.
"""

from datetime import datetime, timezone
import logging
from sqlalchemy import select, delete
from app.memory.database import get_db_session
from app.memory.models import Conversation, Message

logger = logging.getLogger(__name__)


class ConversationStore:
    """Store for managing conversations and chat messages."""

    @staticmethod
    def create_conversation(title: str = "New Conversation") -> Conversation:
        """Create a new conversation session."""
        with get_db_session() as session:
            conv = Conversation(title=title, created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc))
            session.add(conv)
            session.flush()
            session.refresh(conv)
            logger.info("Created conversation %s ('%s')", conv.id, title)
            return Conversation(id=conv.id, title=conv.title, created_at=conv.created_at, updated_at=conv.updated_at)

    @staticmethod
    def get_or_create_latest_conversation() -> Conversation:
        """Retrieve the most recent conversation or create one if none exists."""
        with get_db_session() as session:
            stmt = select(Conversation).order_by(Conversation.updated_at.desc()).limit(1)
            conv = session.scalars(stmt).first()
            if conv is not None:
                return Conversation(id=conv.id, title=conv.title, created_at=conv.created_at, updated_at=conv.updated_at)

        return ConversationStore.create_conversation("Default Session")

    @staticmethod
    def list_conversations(limit: int = 50) -> list[dict]:
        """List recent conversations sorted by latest update."""
        with get_db_session() as session:
            stmt = select(Conversation).order_by(Conversation.updated_at.desc()).limit(limit)
            results = session.scalars(stmt).all()
            return [
                {
                    "id": c.id,
                    "title": c.title,
                    "created_at": c.created_at.isoformat(),
                    "updated_at": c.updated_at.isoformat(),
                }
                for c in results
            ]

    @staticmethod
    def add_message(conversation_id: str, role: str, content: str) -> dict:
        """Add a message to a conversation and touch updated_at."""
        with get_db_session() as session:
            msg = Message(
                conversation_id=conversation_id,
                role=role,
                content=content,
                created_at=datetime.now(timezone.utc),
            )
            session.add(msg)

            # Update conversation timestamp
            conv = session.get(Conversation, conversation_id)
            if conv:
                conv.updated_at = datetime.now(timezone.utc)
                # Update title if it's the first user message
                if role == "user" and conv.title in ("New Conversation", "Default Session"):
                    snippet = content.strip().split("\n")[0][:40]
                    if snippet:
                        conv.title = snippet

            session.flush()
            session.refresh(msg)
            return {
                "id": msg.id,
                "conversation_id": msg.conversation_id,
                "role": msg.role,
                "content": msg.content,
                "created_at": msg.created_at.isoformat(),
            }

    @staticmethod
    def get_messages(conversation_id: str, limit: int = 100) -> list[dict]:
        """Fetch chronological messages for a conversation (up to `limit` most recent)."""
        with get_db_session() as session:
            stmt = (
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.created_at.desc())
                .limit(limit)
            )
            msgs = list(reversed(session.scalars(stmt).all()))
            return [
                {
                    "id": m.id,
                    "conversation_id": m.conversation_id,
                    "role": m.role,
                    "content": m.content,
                    "created_at": m.created_at.isoformat(),
                }
                for m in msgs
            ]

    @staticmethod
    def delete_conversation(conversation_id: str) -> bool:
        """Delete a conversation and its messages from storage."""
        with get_db_session() as session:
            # Delete child messages first
            session.execute(delete(Message).where(Message.conversation_id == conversation_id))
            stmt = delete(Conversation).where(Conversation.id == conversation_id)
            res = session.execute(stmt)
            count = res.rowcount
            logger.info("Deleted conversation %s (rows affected: %d)", conversation_id, count)
            return count > 0

    @staticmethod
    def search_conversations(query: str, limit: int = 50) -> list[dict]:
        """Search conversations by title or message content."""
        clean_q = query.strip()
        if not clean_q:
            return ConversationStore.list_conversations(limit=limit)

        with get_db_session() as session:
            pattern = f"%{clean_q}%"
            # 1. Matching titles
            conv_stmt = (
                select(Conversation)
                .where(Conversation.title.like(pattern))
                .order_by(Conversation.updated_at.desc())
                .limit(limit)
            )
            title_matches = list(session.scalars(conv_stmt).all())
            found_ids = {c.id for c in title_matches}

            # 2. Matching message contents
            msg_stmt = (
                select(Message.conversation_id)
                .where(Message.content.like(pattern))
                .distinct()
                .limit(limit)
            )
            msg_conv_ids = session.scalars(msg_stmt).all()

            for cid in msg_conv_ids:
                if cid not in found_ids:
                    conv = session.get(Conversation, cid)
                    if conv:
                        title_matches.append(conv)
                        found_ids.add(cid)

            # Sort by updated_at descending
            title_matches.sort(key=lambda x: x.updated_at, reverse=True)
            return [
                {
                    "id": c.id,
                    "title": c.title,
                    "created_at": c.created_at.isoformat(),
                    "updated_at": c.updated_at.isoformat(),
                }
                for c in title_matches[:limit]
            ]

    @staticmethod
    def search_messages(query: str, limit: int = 50) -> list[dict]:
        """Search specific message contents across all conversations."""
        clean_q = query.strip()
        if not clean_q:
            return []

        with get_db_session() as session:
            pattern = f"%{clean_q}%"
            stmt = (
                select(Message)
                .where(Message.content.like(pattern))
                .order_by(Message.created_at.desc())
                .limit(limit)
            )
            results = session.scalars(stmt).all()
            return [
                {
                    "id": m.id,
                    "conversation_id": m.conversation_id,
                    "role": m.role,
                    "content": m.content,
                    "created_at": m.created_at.isoformat(),
                }
                for m in results
            ]

    @staticmethod
    def clear_all_conversations() -> int:
        """Clear all conversation history from the database."""
        with get_db_session() as session:
            session.execute(delete(Message))
            stmt = delete(Conversation)
            result = session.execute(stmt)
            count = result.rowcount
            logger.info("Cleared %d conversations and associated messages.", count)
            return count
