"""flash_guide_dialog.py — Guide de flash illustré en 4 étapes (FR23, FR29, FR33).

Chargement des images depuis les assets locaux uniquement — aucun appel réseau.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import TypedDict

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

# ── Assets path (compatible PyInstaller) ───────────────────────────────────
_BASE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).parent.parent.parent))
ASSETS_DIR = _BASE_DIR / "assets" / "flash_guide"


class _FlashStep(TypedDict):
    title: str
    text: str
    image: str


# ── Définition des 4 étapes ────────────────────────────────────────────────
FLASH_GUIDE_STEPS: list[_FlashStep] = [
    {
        "title": "Étape 1 : Localiser le bouton BOOT",
        "text": (
            "Sur le PCB de votre Sofle, repérez le bouton marqué BOOT\n"
            "(souvent près du microcontrôleur RP2040)."
        ),
        "image": "step1_boot_button.png",
    },
    {
        "title": "Étape 2 : Entrer en mode bootloader",
        "text": (
            "1. Maintenez le bouton BOOT appuyé\n"
            "2. Branchez le câble USB à votre clavier\n"
            "3. Relâchez le bouton BOOT"
        ),
        "image": "step2_usb_connect.png",
    },
    {
        "title": "Étape 3 : Lecteur RPI-RP2 détecté",
        "text": (
            "Un lecteur nommé 'RPI-RP2' apparaît dans votre explorateur de fichiers.\n"
            "Si le lecteur n'apparaît pas, répétez l'étape 2."
        ),
        "image": "step3_rpi_rp2.png",
    },
    {
        "title": "Étape 4 : Installer le firmware",
        "text": (
            "Glissez-déposez le fichier .uf2 dans le lecteur RPI-RP2.\n"
            "Le clavier redémarre automatiquement.\n\n"
            "Votre clavier est prêt ! Configurez les layers sur vial.rocks"
        ),
        "image": "step4_drag_drop.png",
    },
]


def _make_step_page(step: dict) -> QWidget:
    """Crée une page QWidget pour une étape donnée."""
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setSpacing(12)

    # Image (locale uniquement — FR29)
    lbl_img = QLabel()
    lbl_img.setObjectName(f"lbl_img_{step['image']}")
    lbl_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl_img.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    img_path = ASSETS_DIR / step["image"]
    pixmap = QPixmap(str(img_path))
    if not pixmap.isNull():
        lbl_img.setPixmap(
            pixmap.scaled(460, 280, Qt.AspectRatioMode.KeepAspectRatio,
                          Qt.TransformationMode.SmoothTransformation)
        )
    else:
        lbl_img.setText(f"[image manquante : {step['image']}]")

    layout.addWidget(lbl_img, stretch=1)

    # Texte de l'étape
    lbl_text = QLabel(step["text"])
    lbl_text.setObjectName("lbl_step_text")
    lbl_text.setWordWrap(True)
    lbl_text.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
    layout.addWidget(lbl_text)

    return page


class FlashGuideDialog(QDialog):
    """Dialogue illustré de 4 étapes pour flasher le firmware.

    Navigation : Précédent / Suivant.
    Le bouton Fermer remplace Suivant à la dernière étape.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Guide de flash du firmware")
        self.setMinimumSize(520, 480)
        self._current = 0
        self._setup_ui()
        self._go_to_step(0)

    # ──────────────────────────────────────────────────────────── UI ──

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Titre de l'étape courante
        self._lbl_title = QLabel()
        self._lbl_title.setObjectName("lbl_step_title")
        self._lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = self._lbl_title.font()
        font.setPointSize(14)
        font.setBold(True)
        self._lbl_title.setFont(font)
        layout.addWidget(self._lbl_title)

        # Zone empilée
        self._stack = QStackedWidget()
        self._stack.setObjectName("flash_guide_stack")
        for step in FLASH_GUIDE_STEPS:
            self._stack.addWidget(_make_step_page(step))
        layout.addWidget(self._stack, stretch=1)

        # Indicateur de progression (ex : "Étape 2 / 4")
        self._lbl_progress = QLabel()
        self._lbl_progress.setObjectName("lbl_step_progress")
        self._lbl_progress.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._lbl_progress)

        # Boutons de navigation
        nav_row = QHBoxLayout()
        self._btn_prev = QPushButton("Précédent")
        self._btn_prev.setObjectName("btn_prev")
        self._btn_prev.clicked.connect(self._on_prev)
        nav_row.addWidget(self._btn_prev)

        nav_row.addStretch()

        self._btn_next = QPushButton("Suivant")
        self._btn_next.setObjectName("btn_next")
        self._btn_next.clicked.connect(self._on_next)
        nav_row.addWidget(self._btn_next)

        self._btn_close = QPushButton("Fermer")
        self._btn_close.setObjectName("btn_close")
        self._btn_close.clicked.connect(self.accept)
        nav_row.addWidget(self._btn_close)

        layout.addLayout(nav_row)

    # ──────────────────────────────────────────────────── Navigation ──

    def _go_to_step(self, idx: int) -> None:
        """Navigue vers l'étape d'index `idx`."""
        if not 0 <= idx < len(FLASH_GUIDE_STEPS):
            return
        self._stack.setCurrentIndex(idx)
        self._current = idx

        step = FLASH_GUIDE_STEPS[idx]
        self._lbl_title.setText(step["title"])
        self._lbl_progress.setText(f"Étape {idx + 1} / {len(FLASH_GUIDE_STEPS)}")

        self._btn_prev.setEnabled(idx > 0)
        # Suivant visible sauf à la dernière étape
        self._btn_next.setVisible(idx < len(FLASH_GUIDE_STEPS) - 1)
        # Fermer visible seulement à la dernière étape
        self._btn_close.setVisible(idx == len(FLASH_GUIDE_STEPS) - 1)

    def _on_prev(self) -> None:
        if self._current > 0:
            self._go_to_step(self._current - 1)

    def _on_next(self) -> None:
        if self._current < len(FLASH_GUIDE_STEPS) - 1:
            self._go_to_step(self._current + 1)
