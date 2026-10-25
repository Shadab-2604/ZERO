"""
Project activity tracking helper functions.
"""

from app.memory.activity_store import ActivityStore


def record_project_event(category: str, description: str, project: str | None = None) -> dict:
    """Helper to record project events."""
    return ActivityStore.record_activity(category=category, description=description, project=project)


def record_test_run(test_name: str, passed: bool, details: str = "") -> dict:
    """Record a test execution outcome."""
    desc = f"Test '{test_name}' {'PASSED' if passed else 'FAILED'}. {details}".strip()
    return ActivityStore.record_activity(category="test", description=desc)
