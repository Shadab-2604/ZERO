"""
Futuristic JARVIS-style theme, color palette, and QSS stylesheets for Zero AI.
Colors:
- Primary background: #050505
- Panel background: #0b0f0e
- Card background: #111714
- Accent / Glow: #00FF88 (Neon Green)
- Accent Dark: #008f4c
- Text Primary: #FFFFFF
- Text Secondary: #8A8A8A
- Border Subtle: #1c2b23
- Warning: #FFB800
- Error: #FF4757
"""

DARK_THEME_QSS = """
/* Global Window Styles */
QMainWindow, QDialog, QWidget#root_container {
    background-color: #050505;
    color: #FFFFFF;
    font-family: 'Segoe UI', 'Consolas', 'Roboto', 'Arial', sans-serif;
    font-size: 13px;
}

/* Sidebar Styles */
QWidget#sidebar {
    background-color: #070a08;
    border-right: 1px solid #14221a;
}

/* Nav Buttons in Sidebar */
QPushButton.nav-button {
    background-color: transparent;
    color: #8A8A8A;
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 10px 14px;
    text-align: left;
    font-size: 13px;
    font-weight: 500;
}

QPushButton.nav-button:hover {
    background-color: #111a15;
    color: #00FF88;
    border: 1px solid #1c3325;
}

QPushButton.nav-button:checked, QPushButton.nav-button.active {
    background-color: #12241b;
    color: #00FF88;
    border-left: 3px solid #00FF88;
    border-radius: 4px;
    font-weight: bold;
}

/* Primary Futuristic Buttons */
QPushButton.btn-primary {
    background-color: #0d281a;
    color: #00FF88;
    border: 1px solid #00FF88;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
    font-size: 12px;
    letter-spacing: 0.5px;
}

QPushButton.btn-primary:hover {
    background-color: #00FF88;
    color: #050505;
}

QPushButton.btn-primary:pressed {
    background-color: #00cc6a;
    color: #050505;
}

QPushButton.btn-secondary {
    background-color: #111714;
    color: #FFFFFF;
    border: 1px solid #23382c;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 500;
}

QPushButton.btn-secondary:hover {
    background-color: #1b2620;
    border: 1px solid #00FF88;
    color: #00FF88;
}

/* Panels and Cards */
QFrame.hud-card {
    background-color: #090e0c;
    border: 1px solid #18261e;
    border-radius: 8px;
}

QFrame.hud-card:hover {
    border: 1px solid #233e30;
}

/* Text Inputs */
QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #090e0b;
    color: #FFFFFF;
    border: 1px solid #1c2b22;
    border-radius: 6px;
    padding: 8px 12px;
    selection-background-color: #00FF88;
    selection-color: #050505;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border: 1px solid #00FF88;
    background-color: #0c1410;
}

/* Chat Transcript */
QScrollArea {
    background-color: transparent;
    border: none;
}

QWidget#chat_container {
    background-color: transparent;
}

/* Custom Scrollbars */
QScrollBar:vertical {
    background: #070a08;
    width: 8px;
    margin: 0px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background: #1c3325;
    min-height: 20px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background: #00FF88;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

/* ComboBoxes */
QComboBox {
    background-color: #090e0b;
    color: #FFFFFF;
    border: 1px solid #1c2b22;
    border-radius: 6px;
    padding: 6px 12px;
}

QComboBox:hover, QComboBox:focus {
    border: 1px solid #00FF88;
}

QComboBox::drop-down {
    border: none;
}

QComboBox QAbstractItemView {
    background-color: #0c1410;
    color: #FFFFFF;
    border: 1px solid #1c3325;
    selection-background-color: #12241b;
    selection-color: #00FF88;
}

/* Checkboxes */
QCheckBox {
    color: #CCCCCC;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 3px;
    border: 1px solid #23382c;
    background-color: #090e0b;
}

QCheckBox::indicator:checked {
    background-color: #00FF88;
    border: 1px solid #00FF88;
}

/* Status Bar */
QFrame#status_bar {
    background-color: #060907;
    border-top: 1px solid #14221a;
    padding: 4px 10px;
}

QLabel.status-label {
    color: #8A8A8A;
    font-size: 11px;
}

QLabel.status-value-ok {
    color: #00FF88;
    font-weight: 600;
    font-size: 11px;
}

QLabel.status-value-warn {
    color: #FFB800;
    font-weight: 600;
    font-size: 11px;
}
"""
