"""Dialogue "À propos" — affiche la version et le lien GitHub."""
from __future__ import annotations

import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout

from _version import __version__ as APP_VERSION
from i18n import tr

logger = logging.getLogger(__name__)
GITHUB_URL = "https://github.com/Pentinou/keyboard_firmware_maker"


class AboutDialog(QDialog):
    """Dialogue modal affichant la version de l'application et les informations du projet."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("about.title").format(version=APP_VERSION))
        self.setMinimumWidth(400)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title_label = QLabel("<h2>keyboard_firmware_maker</h2>")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        version_label = QLabel(tr("about.version").format(version=APP_VERSION))
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version_label)

        desc_label = QLabel(tr("about.description"))
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        github_label = QLabel(f'<a href="{GITHUB_URL}">GitHub : {GITHUB_URL}</a>')
        github_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        github_label.setOpenExternalLinks(True)
        layout.addWidget(github_label)

        close_button = QPushButton(tr("btn.close"))
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)
