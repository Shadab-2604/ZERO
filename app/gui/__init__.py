"""
Zero AI — PySide6 Desktop User Interface Package.

Responsibilities:
- Main JARVIS desktop interface window with reactive vector AI orb and sidebar navigation.
- Floating semi-transparent Live Caption HUD window with real-time speech streaming.
- UI styling, dark/neon palette themes, and accessibility states.
"""

from app.gui.main_window import MainWindow
from app.gui.theme import DARK_THEME_QSS

__all__ = ["MainWindow", "DARK_THEME_QSS"]
