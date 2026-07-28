"""Entry point — keyboard_firmware_maker.

Lance QApplication, instancie ProjectModel et MainWindow.
"""
from __future__ import annotations

import ctypes
import logging
import os
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


def _xcb_plugin_usable() -> bool:
    """Vrai si le plugin Qt xcb peut se charger (libxcb-cursor requise depuis Qt 6.5)."""
    if not os.environ.get("DISPLAY"):
        return False
    try:
        ctypes.CDLL("libxcb-cursor.so.0")
    except OSError:
        return False
    return True


def _configure_qt_platform() -> None:
    """Sous WSLg, préfère X11 (xcb) à Wayland pour l'affichage.

    Le compositeur de WSLg ne repeint pas la zone d'un popup Qt après sa
    fermeture : les listes déroulantes et les menus restent « gravés » à
    l'écran. XWayland n'a pas ce défaut.

    On ne force rien si l'utilisateur a explicitement choisi une plateforme,
    ni si le plugin xcb n'est pas chargeable — Qt garde alors Wayland plutôt
    que d'échouer au démarrage.
    """
    if not _is_wsl() or os.environ.get("QT_QPA_PLATFORM"):
        return
    if not _xcb_plugin_usable():
        logging.getLogger(__name__).info(
            "Plugin Qt xcb indisponible (libxcb-cursor0 manquant ?) — "
            "affichage Wayland conservé ; des artefacts de popup sont possibles sous WSLg."
        )
        return
    os.environ["QT_QPA_PLATFORM"] = "xcb"


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
    _configure_qt_platform()

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
