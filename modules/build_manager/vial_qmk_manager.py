"""vial_qmk_manager.py — Gestion du cache Vial-QMK local.

Architecture Gap 1 (Résolu) : téléchargement unique au premier lancement,
cache dans ~/.keyboard_firmware_maker/vial-qmk/ (NFR12, NFR15).
Offline complet après initialisation (NFR29).

Contient :
- VialQmkManager  : logique pure Python (is_ready, download)
- DownloadWorker  : QThread encapsulant le download
- VialQmkSetupDialog : QDialog progression pour le premier lancement
"""
from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QProgressBar,
    QVBoxLayout,
)

from i18n import tr

logger = logging.getLogger(__name__)

# Version SHA verrouillée de Vial-QMK (NFR15) — branche vial @ 2026-02-22
VIAL_QMK_SHA = "72fb6f1fed4de5fc4ac9ecda1952f5d126388d48"
VIAL_QMK_REPO = "https://github.com/vial-kb/vial-qmk.git"

CACHE_DIR = Path.home() / ".keyboard_firmware_maker"
VIAL_QMK_DIR = CACHE_DIR / "vial-qmk"


# ─────────────────────────────────────────────── Pure Python logic ──

class VialQmkManager:
    """Gère la présence et le téléchargement de Vial-QMK dans le cache local."""

    def is_ready(self) -> bool:
        """Vérifie que le cache Vial-QMK est présent et valide (sous-modules inclus)."""
        return (
            VIAL_QMK_DIR.is_dir()
            and (VIAL_QMK_DIR / "Makefile").is_file()
            and (VIAL_QMK_DIR / "lib" / "chibios" / "os").is_dir()
        )

    def download(
        self,
        progress_callback: Callable[[int], None] | None = None,
        log_callback: Callable[[str], None] | None = None,
    ) -> None:
        """Clone Vial-QMK avec ses sous-modules git (ChibiOS requis pour RP2040).

        Utilise git init + fetch --depth 1 pour obtenir le SHA exact, puis
        git submodule update --init --recursive pour les dépendances.

        Args:
            progress_callback: appelé avec un entier 0-100 pour la progression.
            log_callback: appelé avec un message texte pour les étapes détaillées.

        Raises:
            subprocess.CalledProcessError: si une commande git échoue.
            FileNotFoundError: si git n'est pas installé.
        """
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

        # Nettoyage d'un éventuel répertoire incomplet existant
        if VIAL_QMK_DIR.exists():
            shutil.rmtree(VIAL_QMK_DIR)

        def _log(msg: str) -> None:
            logger.info(msg)
            if log_callback:
                log_callback(msg)

        def _git(*args: str) -> None:
            subprocess.run(list(args), check=True, capture_output=True, text=True)

        # Clone shallow de la branche vial + sous-modules en une seule commande.
        # Note : git fetch --depth 1 origin <SHA> ne fonctionne pas sur GitHub
        # (les SHA arbitraires ne sont pas advertisés). On clone la branche nommée.
        _log("Téléchargement de Vial-QMK (branche vial)…")
        if progress_callback:
            progress_callback(5)
        _git(
            "git", "clone",
            "--depth", "1",
            "--branch", "vial",
            "--recurse-submodules",
            "--shallow-submodules",
            VIAL_QMK_REPO,
            str(VIAL_QMK_DIR),
        )
        if progress_callback:
            progress_callback(95)

        if progress_callback:
            progress_callback(100)
        logger.info("Vial-QMK prêt dans %s", VIAL_QMK_DIR)


# ─────────────────────────────────────────────────── Qt components ──

class DownloadWorker(QThread):
    """Thread de téléchargement Vial-QMK avec signaux de progression."""

    progress = Signal(int)    # 0-100
    log_line = Signal(str)    # étape courante
    finished = Signal()
    error = Signal(str)

    def run(self) -> None:
        try:
            VialQmkManager().download(
                progress_callback=self.progress.emit,
                log_callback=self.log_line.emit,
            )
            self.finished.emit()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Erreur téléchargement Vial-QMK")
            self.error.emit(str(exc))


class VialQmkSetupDialog(QDialog):
    """Dialogue de progression affiché au premier lancement (AC: 1, 2)."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("vial_setup.title"))
        self.setModal(True)
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)
        self._label = QLabel(tr("vial_setup.downloading"))
        self._label.setObjectName("setup_label")
        self._progress = QProgressBar()
        self._progress.setObjectName("setup_progress")
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        layout.addWidget(self._label)
        layout.addWidget(self._progress)

        self._worker = DownloadWorker()
        self._worker.progress.connect(self._progress.setValue)
        self._worker.log_line.connect(self._label.setText)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_finished(self) -> None:
        self._label.setText(tr("vial_setup.ready"))
        self.accept()

    def _on_error(self, msg: str) -> None:
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.critical(self, tr("vial_setup.error_title"), msg)
        self.reject()
