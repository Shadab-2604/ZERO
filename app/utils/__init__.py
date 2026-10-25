"""
Zero AI — Cross-Cutting Utility Functions.

Responsibilities:
- Workspace path resolution and project directory isolation (paths.py).
- Local timezone and greeting time utilities (time_utils.py).
"""

from app.utils.paths import (
    get_project_root,
    get_data_dir,
    get_logs_dir,
    get_exports_dir,
)
from app.utils.time_utils import (
    get_current_time,
    get_time_appropriate_greeting,
    format_iso,
)

__all__ = [
    "get_project_root",
    "get_data_dir",
    "get_logs_dir",
    "get_exports_dir",
    "get_current_time",
    "get_time_appropriate_greeting",
    "format_iso",
]
