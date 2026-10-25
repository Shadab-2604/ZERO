"""
Truthful daily briefing generator for Zero AI.
Grounded strictly in verified stored activity events, session summaries, task items, and health checks.
Never fabricates previous projects, unverified activities, or document updates.
"""

import logging
from app.config.settings import get_settings
from app.memory.activity_store import ActivityStore
from app.system.health_monitor import HealthMonitor
from app.utils.time_utils import get_time_appropriate_greeting

logger = logging.getLogger(__name__)


class BriefingService:
    """Generates accurate, truthful briefings from local telemetry and verified database records."""

    def __init__(self):
        self._briefing_delivered_this_session = False

    @property
    def has_delivered_session_briefing(self) -> bool:
        return self._briefing_delivered_this_session

    def mark_delivered(self) -> None:
        self._briefing_delivered_this_session = True

    def reset_session_flag(self) -> None:
        self._briefing_delivered_this_session = False

    def generate_briefing(self, force: bool = False) -> dict:
        """
        Generate complete structured and formatted briefing text.
        If already delivered in current session and not forced, returns a brief greeting.
        """
        settings = get_settings()
        greeting = get_time_appropriate_greeting(settings.timezone)

        # If already delivered and not requested explicitly, return short awake response
        if self._briefing_delivered_this_session and not force:
            return {
                "delivered": False,
                "text": f"{greeting}. Zero is awake and ready. What shall we work on?",
                "is_full_briefing": False,
            }

        # Gather real, persisted data
        summary_record = ActivityStore.get_latest_session_summary()
        recent_activities = ActivityStore.get_recent_activities(limit=10)
        tasks = ActivityStore.list_tasks(status="pending")
        health = HealthMonitor.get_full_health_report()

        lines = [f"{greeting}. Zero is online."]

        # Check for non-session project activities
        non_session_acts = [
            a["description"] for a in recent_activities
            if a.get("category") != "session"
        ]

        # Filter out corrupt/hallucinated summaries
        valid_summary = None
        if summary_record and summary_record.get("summary_text"):
            text = summary_record["summary_text"].strip()
            # Ignore AI refusal boilerplate and legacy hallucinated test strings
            if not any(bad in text.lower() for bad in ("i'm sorry", "can't assist", "secret recipe", "xyz pudding", "scan sequence")):
                if "no external tasks were executed" not in text.lower():
                    valid_summary = text

        if not summary_record and not non_session_acts and not tasks:
            lines.append(
                "This is your first recorded session. Your project history and activity will appear here as we work."
            )
        else:
            if valid_summary:
                lines.append(f"Previous session review: {valid_summary}")

            if non_session_acts:
                lines.append(f"Recent project activity: {non_session_acts[0]}")

            if tasks:
                pending_titles = [f"'{t['title']}'" for t in tasks[:3]]
                lines.append(f"Pending tasks ({len(tasks)}): {', '.join(pending_titles)}.")

        # Real system telemetry
        ai_info = health.get("ai_provider", {})
        db_info = health.get("database", {})
        mode = health.get("mode", "ONLINE")
        lines.append(
            f"System telemetry: AI mode is {mode}, database is {db_info.get('status', 'healthy')}."
        )

        if tasks:
            lines.append(f"Would you like to continue with '{tasks[0]['title']}' or start something new?")
        else:
            lines.append("Would you like to review previous work or start something new?")

        full_text = "\n\n".join(lines)
        self._briefing_delivered_this_session = True

        return {
            "delivered": True,
            "text": full_text,
            "is_full_briefing": True,
            "greeting": greeting,
            "mode": mode,
        }
