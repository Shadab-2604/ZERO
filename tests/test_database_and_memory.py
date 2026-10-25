"""
Tests covering Database Initialization, Memory Persistence, and Truthful Activity Grounding.
Covers:
- Scenario 3: Database initializes on first launch
- Scenario 5: First session does not fabricate previous activity
- Scenario 6: Previous session summaries load correctly
- Scenario 7: Activity entries appear in the briefing
- Scenario 17: Session history and saved preferences persist after restart
"""

import pytest
from app.memory.database import init_db, get_engine
from app.memory.models import Base
from app.memory.conversation_store import ConversationStore
from app.memory.activity_store import ActivityStore
from app.core.briefing_service import BriefingService


@pytest.fixture(autouse=True)
def setup_clean_db():
    """Ensure database is initialized and fresh for each test."""
    init_db()
    ConversationStore.clear_all_conversations()
    ActivityStore.clear_all_activities()
    yield


def test_database_initializes_on_first_launch():
    """Scenario 3: Verify all expected tables are created cleanly in SQLite."""
    engine = get_engine()
    init_db()
    table_names = list(Base.metadata.tables.keys())
    assert "conversations" in table_names
    assert "messages" in table_names
    assert "sessions" in table_names
    assert "activity_events" in table_names
    assert "session_summaries" in table_names
    assert "tasks" in table_names
    assert "user_preferences" in table_names


def test_first_session_does_not_fabricate_previous_activity():
    """Scenario 5: Truthful briefing check when no prior activity exists."""
    # With clean database:
    briefing_svc = BriefingService()
    briefing = briefing_svc.generate_briefing(force=True)

    expected_notice = "This is your first recorded session. Your project history and activity will appear here as we work."
    assert expected_notice in briefing["text"]
    assert "Yesterday" not in briefing["text"]


def test_previous_session_summaries_load_correctly():
    """Scenario 6: Stored session summary is restored accurately."""
    ActivityStore.save_session_summary(
        summary_text="Completed security hardening and added unit test suite.",
        session_id="test-session-001",
        tasks_pending=["Deploy to production"],
        tasks_completed=["Setup database"],
    )

    latest = ActivityStore.get_latest_session_summary()
    assert latest is not None
    assert latest["summary_text"] == "Completed security hardening and added unit test suite."
    assert "Deploy to production" in latest["tasks_pending"]
    assert "Setup database" in latest["tasks_completed"]


def test_activity_entries_appear_in_briefing():
    """Scenario 7: Recorded activity events ground the daily briefing."""
    ActivityStore.record_activity(
        category="project_action",
        description="Refactored database layer and optimized query execution.",
    )

    briefing_svc = BriefingService()
    briefing = briefing_svc.generate_briefing(force=True)

    assert "Refactored database layer and optimized query execution." in briefing["text"]


def test_session_history_and_preferences_persist():
    """Scenario 17: Verify conversations, messages, and preferences persist in DB."""
    # 1. Create conversation and message
    conv = ConversationStore.create_conversation("Project Apollo")
    ConversationStore.add_message(conv.id, "user", "Initiate scan sequence")
    ConversationStore.add_message(conv.id, "assistant", "Scanning local workspace...")

    # 2. Save preference
    ActivityStore.set_preference("hud_color", "#00FF88")

    # 3. Read back
    messages = ConversationStore.get_messages(conv.id)
    assert len(messages) == 2
    assert messages[0]["content"] == "Initiate scan sequence"
    assert messages[1]["content"] == "Scanning local workspace..."

    pref_val = ActivityStore.get_preference("hud_color")
    assert pref_val == "#00FF88"
