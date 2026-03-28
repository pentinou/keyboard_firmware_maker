"""Entry point — keyboard_firmware_maker.

Lance QApplication, instancie ProjectModel et MainWindow.
"""
from __future__ import annotations

import logging
import platform
import subprocess
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

from PySide6.QtCore import QObject, QUrl, Slot
from PySide6.QtGui import QDesktopServices

from _version import __version__
from models.project_model import ProjectModel
from ui.main_window import MainWindow


def _is_wsl() -> bool:
    """Détecte si on tourne sous WSL."""
    try:
        return "microsoft" in platform.uname().release.lower()
    except Exception:
        return False


class _WslUrlHandler(QObject):
    """Redirige les ouvertures d'URL vers le navigateur Windows sous WSL."""

    @Slot(QUrl)
    def handleUrl(self, url: QUrl) -> None:  # noqa: N802
        try:
            subprocess.Popen(
                ["cmd.exe", "/c", "start", "", url.toString()],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError:
            pass


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
    app.setApplicationVersion(__version__)
    app.setOrganizationName("Pentinou")

    if _is_wsl():
        url_handler = _WslUrlHandler(app)
        QDesktopServices.setUrlHandler("http", url_handler, "handleUrl")
        QDesktopServices.setUrlHandler("https", url_handler, "handleUrl")

    model = ProjectModel()
    window = MainWindow(model)
    window.show()

    logger.info("keyboard_firmware_maker %s started", __version__)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
