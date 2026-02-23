"""Dialogue "À propos" — affiche la version et le lien GitHub."""
from __future__ import annotations

import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout

logger = logging.getLogger(__name__)

APP_VERSION = "0.1.0"
GITHUB_URL = "https://github.com/Pentinou/keyboard_firmware_maker"


class AboutDialog(QDialog):
    """Dialogue modal affichant la version de l'application et les informations du projet."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"À propos — keyboard_firmware_maker {APP_VERSION}")
        self.setMinimumWidth(400)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title_label = QLabel("<h2>keyboard_firmware_maker</h2>")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        version_label = QLabel(f"Version : {APP_VERSION}")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version_label)

        desc_label = QLabel(
            "Application desktop pour créer et personnaliser des firmwares\n"
            "QMK/Vial-QMK pour claviers mécaniques split."
        )
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        github_label = QLabel(f'<a href="{GITHUB_URL}">GitHub : {GITHUB_URL}</a>')
        github_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        github_label.setOpenExternalLinks(True)
        layout.addWidget(github_label)

        close_button = QPushButton("Fermer")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)
