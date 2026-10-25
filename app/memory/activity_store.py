"""
Activity, session summaries, task items, and preferences repository.
"""

from datetime import datetime, timezone
import json
import logging
from sqlalchemy import select, delete, desc
from app.memory.database import get_db_session
from app.memory.models import (
    ActivityEvent,
    SessionRecord,
    SessionSummary,
    TaskItem,
    UserPreference,
)

logger = logging.getLogger(__name__)


class ActivityStore:
    """Store for managing activities, summaries, tasks, and preferences."""

    @staticmethod
    def record_activity(category: str, description: str, project: str | None = None) -> dict:
        """Log an activity event with timestamp and category."""
        with get_db_session() as session:
            event = ActivityEvent(
                timestamp=datetime.now(timezone.utc),
                category=category,
                project=project,
                description=description,
            )
            session.add(event)
            session.flush()
            session.refresh(event)
            logger.info("Recorded activity: [%s] %s", category, description)
            return {
                "id": event.id,
                "timestamp": event.timestamp.isoformat(),
                "category": event.category,
                "project": event.project,
                "description": event.description,
            }

    @staticmethod
    def get_recent_activities(limit: int = 10) -> list[dict]:
        """Fetch latest activity records in descending chronological order."""
        with get_db_session() as session:
            stmt = select(ActivityEvent).order_by(desc(ActivityEvent.timestamp)).limit(limit)
            events = session.scalars(stmt).all()
            return [
                {
                    "id": e.id,
                    "timestamp": e.timestamp.isoformat(),
                    "category": e.category,
                    "project": e.project,
                    "description": e.description,
                }
                for e in events
            ]

    @staticmethod
    def start_session() -> str:
        """Mark a new application session started."""
        with get_db_session() as session:
            record = SessionRecord(
                started_at=datetime.now(timezone.utc),
                is_active=True,
            )
            session.add(record)
            session.flush()
            session_id = record.id

        ActivityStore.record_activity("session", f"Session started (ID: {session_id[:8]})")
        return session_id

    @staticmethod
    def end_session(session_id: str) -> None:
        """Mark a session as completed."""
        with get_db_session() as session:
            record = session.get(SessionRecord, session_id)
            if record:
                record.is_active = False
                record.ended_at = datetime.now(timezone.utc)
        ActivityStore.record_activity("session", f"Session ended (ID: {session_id[:8]})")

    @staticmethod
    def save_session_summary(
        summary_text: str,
        session_id: str | None = None,
        tasks_pending: list[str] | None = None,
        tasks_completed: list[str] | None = None,
    ) -> dict:
        """Save an explicit session summary."""
        with get_db_session() as session:
            summary = SessionSummary(
                session_id=session_id,
                timestamp=datetime.now(timezone.utc),
                summary_text=summary_text,
                tasks_pending=json.dumps(tasks_pending or []),
                tasks_completed=json.dumps(tasks_completed or []),
            )
            session.add(summary)
            session.flush()
            session.refresh(summary)
            logger.info("Saved session summary for session: %s", session_id)
            return {
                "id": summary.id,
                "session_id": summary.session_id,
                "timestamp": summary.timestamp.isoformat(),
                "summary_text": summary.summary_text,
                "tasks_pending": tasks_pending or [],
                "tasks_completed": tasks_completed or [],
            }

    @staticmethod
    def get_latest_session_summary() -> dict | None:
        """Retrieve the most recent session summary if one exists."""
        with get_db_session() as session:
            stmt = select(SessionSummary).order_by(desc(SessionSummary.timestamp)).limit(1)
            summary = session.scalars(stmt).first()
            if not summary:
                return None
            try:
                pending = json.loads(summary.tasks_pending or "[]")
            except Exception:
                pending = []
            try:
                completed = json.loads(summary.tasks_completed or "[]")
            except Exception:
                completed = []

            return {
                "id": summary.id,
                "session_id": summary.session_id,
                "timestamp": summary.timestamp.isoformat(),
                "summary_text": summary.summary_text,
                "tasks_pending": pending,
                "tasks_completed": completed,
            }

    @staticmethod
    def add_task(title: str, description: str = "", priority: str = "medium") -> dict:
        """Add a new task item."""
        with get_db_session() as session:
            task = TaskItem(
                title=title,
                description=description,
                status="pending",
                priority=priority,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            session.add(task)
            session.flush()
            session.refresh(task)
            ActivityStore.record_activity("task", f"Created task: {title}")
            return {
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "status": task.status,
                "priority": task.priority,
                "created_at": task.created_at.isoformat(),
            }

    @staticmethod
    def list_tasks(status: str | None = None) -> list[dict]:
        """List tasks optionally filtered by status."""
        with get_db_session() as session:
            stmt = select(TaskItem)
            if status:
                stmt = stmt.where(TaskItem.status == status)
            stmt = stmt.order_by(desc(TaskItem.created_at))
            tasks = session.scalars(stmt).all()
            return [
                {
                    "id": t.id,
                    "title": t.title,
                    "description": t.description,
                    "status": t.status,
                    "priority": t.priority,
                    "created_at": t.created_at.isoformat(),
                }
                for t in tasks
            ]

    @staticmethod
    def update_task_status(task_id: str, new_status: str) -> bool:
        """Update the status of a task."""
        with get_db_session() as session:
            task = session.get(TaskItem, task_id)
            if not task:
                return False
            task.status = new_status
            task.updated_at = datetime.now(timezone.utc)
            ActivityStore.record_activity("task", f"Updated task '{task.title}' to status: {new_status}")
            return True

    @staticmethod
    def get_preference(key: str, default: str | None = None) -> str | None:
        """Get a persistent user preference."""
        with get_db_session() as session:
            pref = session.get(UserPreference, key)
            return pref.value if pref else default

    @staticmethod
    def set_preference(key: str, value: str) -> None:
        """Set a persistent user preference."""
        with get_db_session() as session:
            pref = session.get(UserPreference, key)
            if pref:
                pref.value = value
                pref.updated_at = datetime.now(timezone.utc)
            else:
                pref = UserPreference(key=key, value=value, updated_at=datetime.now(timezone.utc))
                session.add(pref)

    @staticmethod
    def clear_all_activities() -> int:
        """Clear all activity logs, session records, and summaries."""
        with get_db_session() as session:
            count = session.execute(delete(ActivityEvent)).rowcount
            session.execute(delete(SessionSummary))
            session.execute(delete(SessionRecord))
            logger.info("Cleared %d activity records.", count)
            return count
