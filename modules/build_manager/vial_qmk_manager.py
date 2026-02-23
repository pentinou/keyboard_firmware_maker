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
import urllib.request
import zipfile
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QProgressBar,
    QVBoxLayout,
)

logger = logging.getLogger(__name__)

# Version SHA verrouillée de Vial-QMK (NFR15) — branche vial @ 2026-02-22
VIAL_QMK_SHA = "72fb6f1fed4de5fc4ac9ecda1952f5d126388d48"
VIAL_QMK_URL = f"https://github.com/vial-kb/vial-qmk/archive/{VIAL_QMK_SHA}.zip"

CACHE_DIR = Path.home() / ".keyboard_firmware_maker"
VIAL_QMK_DIR = CACHE_DIR / "vial-qmk"


# ─────────────────────────────────────────────── Pure Python logic ──

class VialQmkManager:
    """Gère la présence et le téléchargement de Vial-QMK dans le cache local."""

    def is_ready(self) -> bool:
        """Vérifie que le cache Vial-QMK est présent et valide."""
        return VIAL_QMK_DIR.is_dir() and (VIAL_QMK_DIR / "Makefile").is_file()

    def download(self, progress_callback: Callable[[int], None] | None = None) -> None:
        """Télécharge et extrait Vial-QMK dans le cache local.

        Args:
            progress_callback: appelé avec un entier 0-100 pour la progression.

        Raises:
            OSError, urllib.error.URLError: si le téléchargement ou l'extraction échoue.
        """
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        zip_path = CACHE_DIR / "vial-qmk.zip"
        logger.info("Téléchargement de Vial-QMK depuis %s", VIAL_QMK_URL)

        def _reporthook(block_num: int, block_size: int, total_size: int) -> None:
            if total_size > 0 and progress_callback:
                pct = min(100, int(block_num * block_size / total_size * 100))
                progress_callback(pct)

        urllib.request.urlretrieve(VIAL_QMK_URL, zip_path, _reporthook)
        logger.info("Extraction de l'archive…")
        try:  # M1: toujours nettoyer le zip, même si l'extraction échoue
            _extract_zip(zip_path, CACHE_DIR)
        finally:
            zip_path.unlink(missing_ok=True)
        logger.info("Vial-QMK prêt dans %s", VIAL_QMK_DIR)


def _extract_zip(zip_path: Path, dest: Path) -> None:
    """Extrait le zip et renomme le répertoire extrait en 'vial-qmk'.

    Raises:
        RuntimeError: si aucun répertoire 'vial-qmk-*' n'est trouvé dans l'archive.
    """
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(dest)

    # GitHub archives : le répertoire extrait est nommé "vial-qmk-{sha}"
    for candidate in dest.iterdir():
        if candidate.is_dir() and candidate.name.startswith("vial-qmk-"):
            target = dest / "vial-qmk"
            if target.exists():
                shutil.rmtree(target)
            candidate.rename(target)
            return

    # L2: aucun dossier vial-qmk-* trouvé — archive invalide ou corrompue
    raise RuntimeError(
        f"Archive invalide : aucun répertoire 'vial-qmk-*' trouvé dans {dest}"
    )


# ─────────────────────────────────────────────────── Qt components ──

class DownloadWorker(QThread):
    """Thread de téléchargement Vial-QMK avec signaux de progression."""

    progress = Signal(int)    # 0-100
    finished = Signal()
    error = Signal(str)

    def run(self) -> None:
        try:
            VialQmkManager().download(progress_callback=self.progress.emit)
            self.finished.emit()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Erreur téléchargement Vial-QMK")
            self.error.emit(str(exc))


class VialQmkSetupDialog(QDialog):
    """Dialogue de progression affiché au premier lancement (AC: 1, 2)."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Initialisation de l'environnement")
        self.setModal(True)
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)
        self._label = QLabel("Téléchargement de Vial-QMK…")
        self._label.setObjectName("setup_label")
        self._progress = QProgressBar()
        self._progress.setObjectName("setup_progress")
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        layout.addWidget(self._label)
        layout.addWidget(self._progress)

        self._worker = DownloadWorker()
        self._worker.progress.connect(self._progress.setValue)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_finished(self) -> None:
        self._label.setText("Vial-QMK prêt.")
        self.accept()

    def _on_error(self, msg: str) -> None:
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.critical(self, "Erreur de téléchargement", msg)
        self.reject()
