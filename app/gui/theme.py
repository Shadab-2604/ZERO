"""
Zero AI — Obsidian Command Design System & QSS Theme.
Implements the exact tactile, surgical design language from Obsidian Command specification:
- Canvas Base: #050505
- Surface Panels: #101412
- Elevated Containers: #151A18
- Inset / Lowest: #0B0F0D
- High Surface: #272B29
- Structural Dividers: #1E2623
- Operational Accent: #00FF88 (Neon Green)
- Warning Indicator: #FFB800 (Amber)
- Critical Interruption / Error: #FF4444 (Crimson)
- Text Primary: #F5F7F6
- Text Secondary: #8A8A8A
- Text Dim: #525E59
"""

# Palette Constants
CANVAS_BG = "#050505"
SURFACE_PANEL = "#101412"
CONTAINER_BG = "#151A18"
CONTAINER_LOWEST = "#0B0F0D"
CONTAINER_HIGH = "#272B29"
BORDER_SUBTLE = "#1E2623"
ACCENT_NEON = "#00FF88"
ACCENT_NEON_HOVER = "#1AFF94"
ACCENT_WARNING = "#FFB800"
ACCENT_CRITICAL = "#FF4444"
TEXT_PRIMARY = "#F5F7F6"
TEXT_SECONDARY = "#8A8A8A"
TEXT_DIM = "#525E59"

DARK_THEME_QSS = """
/* Global Window Styles */
QMainWindow, QDialog, QWidget#root_container {
    background-color: #050505;
    color: #F5F7F6;
    font-family: 'Segoe UI', 'Inter', -apple-system, sans-serif;
    font-size: 13px;
}

/* Custom 36px Titlebar */
QWidget#title_bar {
    background-color: #0B0F0D;
    border-bottom: 1px solid #1E2623;
    min-height: 36px;
    max-height: 36px;
}

QWidget#title_bar QLabel {
    font-family: 'Consolas', 'JetBrains Mono', monospace;
    font-size: 11px;
}

/* Window Control Buttons */
QPushButton.titlebar-btn {
    background-color: transparent;
    color: #8A8A8A;
    border: none;
    border-radius: 2px;
    padding: 4px 8px;
    min-width: 28px;
    min-height: 24px;
}

QPushButton.titlebar-btn:hover {
    background-color: #272B29;
    color: #00FF88;
}

QPushButton.titlebar-btn-close:hover {
    background-color: #FF4444;
    color: #FFFFFF;
}

/* Slim 64px Navigation Rail */
QWidget#sidebar, QWidget#nav_rail {
    background-color: #101412;
    border-right: 1px solid #1E2623;
    min-width: 64px;
    max-width: 64px;
}

QPushButton.rail-button {
    background-color: transparent;
    color: #8A8A8A;
    border: none;
    border-left: 2px solid transparent;
    border-radius: 0px;
    padding: 6px 2px;
    text-align: center;
    font-family: 'Segoe UI', 'Inter', sans-serif;
    font-size: 9px;
    font-weight: 500;
}

QPushButton.rail-button:hover {
    background-color: #151A18;
    color: #00FF88;
}

QPushButton.rail-button:checked, QPushButton.rail-button.active {
    background-color: #272B29;
    color: #00FF88;
    border-left: 2px solid #00FF88;
    font-weight: bold;
}

/* Primary Operational Buttons */
QPushButton.btn-primary {
    background-color: #00FF88;
    color: #050505;
    border: 1px solid #00FF88;
    border-radius: 4px;
    padding: 7px 14px;
    font-family: 'Consolas', 'JetBrains Mono', monospace;
    font-weight: 700;
    font-size: 11px;
    letter-spacing: 0.5px;
}

QPushButton.btn-primary:hover {
    background-color: #1AFF94;
    border: 1px solid #1AFF94;
}

QPushButton.btn-primary:pressed {
    background-color: #00CC6A;
}

QPushButton.btn-primary:disabled {
    background-color: #1A221F;
    color: #525E59;
    border: 1px solid #1E2623;
}

/* Secondary Surface Buttons */
QPushButton.btn-secondary {
    background-color: #151A18;
    color: #F5F7F6;
    border: 1px solid #1E2623;
    border-radius: 4px;
    padding: 6px 12px;
    font-family: 'Consolas', 'JetBrains Mono', monospace;
    font-size: 11px;
    font-weight: 500;
}

QPushButton.btn-secondary:hover {
    background-color: #1A221F;
    border: 1px solid #00FF88;
    color: #00FF88;
}

QPushButton.btn-secondary:pressed {
    background-color: #0B0F0D;
}

/* Warning & Danger Buttons */
QPushButton.btn-warning {
    background-color: #FFB800;
    color: #050505;
    border: 1px solid #FFB800;
    border-radius: 4px;
    padding: 6px 12px;
    font-family: 'Consolas', 'JetBrains Mono', monospace;
    font-weight: 700;
    font-size: 11px;
}

QPushButton.btn-warning:hover {
    background-color: #FFC933;
}

QPushButton.btn-danger {
    background-color: #271212;
    color: #FF4444;
    border: 1px solid #FF4444;
    border-radius: 4px;
    padding: 6px 12px;
    font-family: 'Consolas', 'JetBrains Mono', monospace;
    font-weight: 600;
    font-size: 11px;
}

QPushButton.btn-danger:hover {
    background-color: #FF4444;
    color: #FFFFFF;
}

/* Panels and Containers */
QFrame.hud-card, QFrame.telemetry-module {
    background-color: #151A18;
    border: 1px solid #1E2623;
    border-radius: 4px;
}

QFrame.hud-card:hover, QFrame.telemetry-module:hover {
    border: 1px solid #272B29;
}

QFrame.card-focused {
    border: 1px solid #00FF88;
}

QFrame.card-warning {
    border: 1px solid #FFB800;
}

QFrame.card-critical {
    border: 1px solid #FF4444;
}

/* Text Inputs & Search */
QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #0B0F0D;
    color: #F5F7F6;
    border: 1px solid #1E2623;
    border-radius: 4px;
    padding: 7px 10px;
    font-family: 'Segoe UI', 'Inter', sans-serif;
    selection-background-color: #00FF88;
    selection-color: #050505;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border: 1px solid #00FF88;
    background-color: #101412;
}

QLineEdit.mono-input, QTextEdit.mono-input, QPlainTextEdit.mono-input {
    font-family: 'Consolas', 'JetBrains Mono', monospace;
    font-size: 12px;
}

/* Custom Scrollbars */
QScrollBar:vertical {
    background: #0B0F0D;
    width: 6px;
    margin: 0px;
    border-radius: 3px;
}

QScrollBar::handle:vertical {
    background: #1E2623;
    min-height: 24px;
    border-radius: 3px;
}

QScrollBar::handle:vertical:hover {
    background: #00FF88;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background: #0B0F0D;
    height: 6px;
    margin: 0px;
    border-radius: 3px;
}

QScrollBar::handle:horizontal {
    background: #1E2623;
    min-width: 24px;
    border-radius: 3px;
}

QScrollBar::handle:horizontal:hover {
    background: #00FF88;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* ComboBoxes */
QComboBox {
    background-color: #0B0F0D;
    color: #F5F7F6;
    border: 1px solid #1E2623;
    border-radius: 4px;
    padding: 5px 10px;
    font-family: 'Consolas', 'JetBrains Mono', monospace;
    font-size: 12px;
}

QComboBox:hover, QComboBox:focus {
    border: 1px solid #00FF88;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

QComboBox QAbstractItemView {
    background-color: #101412;
    color: #F5F7F6;
    border: 1px solid #1E2623;
    selection-background-color: #272B29;
    selection-color: #00FF88;
}

/* Checkboxes */
QCheckBox {
    color: #8A8A8A;
    spacing: 8px;
    font-size: 12px;
}

QCheckBox::indicator {
    width: 14px;
    height: 14px;
    border-radius: 2px;
    border: 1px solid #1E2623;
    background-color: #0B0F0D;
}

QCheckBox::indicator:checked {
    background-color: #00FF88;
    border: 1px solid #00FF88;
}

/* Filter Segmented Tab Buttons */
QPushButton.filter-tab {
    background-color: transparent;
    color: #8A8A8A;
    border: none;
    border-bottom: 2px solid transparent;
    padding: 6px 12px;
    font-family: 'Consolas', 'JetBrains Mono', monospace;
    font-size: 11px;
    font-weight: 500;
}

QPushButton.filter-tab:hover {
    color: #F5F7F6;
}

QPushButton.filter-tab:checked {
    color: #00FF88;
    border-bottom: 2px solid #00FF88;
    background-color: #272B29;
    font-weight: bold;
}

/* Persistent Voice & Footer Dock */
QWidget#footer_voice_bar, QFrame#footer_voice_bar {
    background-color: #0B0F0D;
    border-top: 1px solid #1E2623;
    min-height: 40px;
    max-height: 40px;
}

QLabel.telemetry-key {
    color: #8A8A8A;
    font-family: 'Consolas', 'JetBrains Mono', monospace;
    font-size: 11px;
}

QLabel.telemetry-val {
    color: #00FF88;
    font-family: 'Consolas', 'JetBrains Mono', monospace;
    font-weight: bold;
    font-size: 11px;
}

QLabel.badge-status {
    background-color: #272B29;
    color: #00FF88;
    border: 1px solid #1E2623;
    border-radius: 3px;
    padding: 2px 6px;
    font-family: 'Consolas', 'JetBrains Mono', monospace;
    font-size: 10px;
}
"""
