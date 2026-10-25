"""
Desktop Application Entrypoint for Zero AI.
"""

import sys
import logging
from PySide6.QtWidgets import QApplication
from app.bootstrap import bootstrap_application
from app.gui.main_window import MainWindow
from app.api.server import get_api_server_manager

logger = logging.getLogger(__name__)


def main() -> int:
    """Launch Zero AI Desktop Application."""
    # 1. Bootstrap all subsystems
    bootstrap_application(start_api_server=True)

    # 2. Initialize Qt Application
    qt_app = QApplication(sys.argv)
    qt_app.setApplicationName("Zero AI")
    qt_app.setOrganizationName("Zero AI Systems")

    # 3. Create and show main window
    window = MainWindow()
    window.show()

    logger.info("Zero AI Desktop GUI launched.")
    exit_code = qt_app.exec()

    # 4. Clean shutdown
    logger.info("Exiting Zero AI Application...")
    get_api_server_manager().stop()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
