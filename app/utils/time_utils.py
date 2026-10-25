"""
Time and timezone utilities for Zero AI.
"""

from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import logging

logger = logging.getLogger(__name__)


def get_current_time(timezone_str: str = "UTC") -> datetime:
    """Return timezone-aware current datetime for given timezone string."""
    try:
        tz = ZoneInfo(timezone_str)
        return datetime.now(tz)
    except ZoneInfoNotFoundError:
        logger.warning("Timezone '%s' not found. Defaulting to local system time.", timezone_str)
        return datetime.now().astimezone()
    except Exception as e:
        logger.warning("Error resolving timezone '%s': %s. Using local time.", timezone_str, e)
        return datetime.now().astimezone()


def get_time_appropriate_greeting(timezone_str: str = "UTC") -> str:
    """
    Generate a time-based greeting (e.g. Good morning, Good afternoon, Good evening).
    """
    current = get_current_time(timezone_str)
    hour = current.hour

    if 5 <= hour < 12:
        return "Good morning"
    elif 12 <= hour < 17:
        return "Good afternoon"
    elif 17 <= hour < 22:
        return "Good evening"
    else:
        return "Good evening"


def format_iso(dt: datetime | None = None) -> str:
    """Format datetime as ISO 8601 string."""
    if dt is None:
        dt = datetime.now().astimezone()
    return dt.isoformat()
