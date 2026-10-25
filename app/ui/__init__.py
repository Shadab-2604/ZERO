"""
Zero AI — Canonical Desktop User Interface & Captions Facade.

This module provides a clean facade to Zero's desktop graphical user interface,
theme engine, and HUD widgets, re-exporting them from `app.gui`.
"""

from app.gui.main_window import MainWindow
from app.gui.theme import DARK_THEME_QSS
from app.gui.widgets.caption_window import LiveCaptionWindow
from app.gui.widgets.ai_orb import AIOrbWidget

__all__ = [
    "MainWindow",
    "DARK_THEME_QSS",
    "LiveCaptionWindow",
    "AIOrbWidget",
]
