"""Entry point — keyboard_firmware_maker.

Lance QApplication, instancie ProjectModel et MainWindow.
"""
from __future__ import annotations

import logging
import sys

try:
    from PySide6.QtWidgets import QApplication
except ModuleNotFoundError:
    print("Error: PySide6 is not installed.")
    print("Run one of the following commands to install all dependencies:")
    print()
    print("  pip install -e .")
    print("  # or")
    print("  pip install -r requirements.txt")
    sys.exit(1)

from models.project_model import ProjectModel
from ui.main_window import MainWindow


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def main() -> int:
    """Point d'entrée principal de l'application."""
    _configure_logging()
    logger = logging.getLogger(__name__)

    app = QApplication(sys.argv)
    app.setApplicationName("keyboard_firmware_maker")
    app.setApplicationVersion("0.1.0")
    app.setOrganizationName("Pentinou")

    model = ProjectModel()
    window = MainWindow(model)
    window.show()

    logger.info("keyboard_firmware_maker 0.1.0 started")
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
