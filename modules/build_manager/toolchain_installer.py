"""toolchain_installer.py — Téléchargement automatique de la toolchain ARM pour Windows.

Télécharge arm-none-eabi-gcc depuis developer.arm.com au premier lancement,
installe dans ~/.keyboard_firmware_maker/toolchain/windows/.

Pattern identique à VialQmkManager : logique pure + QThread + QDialog.
"""
from __future__ import annotations

import logging
import shutil
import zipfile
from pathlib import Path
from typing import Callable
from urllib.request import urlretrieve

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QProgressBar,
    QVBoxLayout,
)

from i18n import tr

logger = logging.getLogger(__name__)

CACHE_DIR = Path.home() / ".keyboard_firmware_maker"
TOOLCHAIN_INSTALL_DIR = CACHE_DIR / "toolchain" / "windows"

# ARM GNU Toolchain 13.3.Rel1 pour Windows (zip, ~250 MB compressé)
TOOLCHAIN_VERSION = "13.3.Rel1"
TOOLCHAIN_ARCHIVE = f"arm-gnu-toolchain-{TOOLCHAIN_VERSION}-mingw-w64-i686-arm-none-eabi.zip"
TOOLCHAIN_URL = (
    f"https://developer.arm.com/-/media/Files/downloads/gnu/"
    f"{TOOLCHAIN_VERSION}/binrel/{TOOLCHAIN_ARCHIVE}"
)


class ToolchainInstaller:
    """Gère le téléchargement et l'installation de la toolchain ARM."""

    def is_installed(self) -> bool:
        """Vérifie que arm-none-eabi-gcc.exe est présent dans le cache."""
        gcc = self._find_gcc()
        return gcc is not None and gcc.is_file()

    def get_gcc_path(self) -> Path | None:
        """Retourne le chemin vers gcc, ou None."""
        return self._find_gcc()

    def install(
        self,
        progress_callback: Callable[[int], None] | None = None,
        log_callback: Callable[[str], None] | None = None,
    ) -> None:
        """Télécharge et extrait la toolchain ARM.

        Args:
            progress_callback: appelé avec un entier 0-100.
            log_callback: appelé avec un message texte.

        Raises:
            OSError: si le téléchargement ou l'extraction échoue.
        """
        TOOLCHAIN_INSTALL_DIR.mkdir(parents=True, exist_ok=True)

        def _log(msg: str) -> None:
            logger.info(msg)
            if log_callback:
                log_callback(msg)

        archive_path = CACHE_DIR / TOOLCHAIN_ARCHIVE

        # Étape 1 — Téléchargement (0 → 70%)
        _log("Téléchargement de la toolchain ARM…")
        if progress_callback:
            progress_callback(5)

        def _report_progress(block_num: int, block_size: int, total_size: int) -> None:
            if total_size > 0 and progress_callback:
                pct = min(int(block_num * block_size / total_size * 65), 65)
                progress_callback(5 + pct)

        urlretrieve(TOOLCHAIN_URL, str(archive_path), reporthook=_report_progress)
        if progress_callback:
            progress_callback(70)

        # Étape 2 — Extraction (70 → 90%)
        _log("Extraction de la toolchain ARM…")
        with zipfile.ZipFile(archive_path) as zf:
            zf.extractall(path=TOOLCHAIN_INSTALL_DIR)
        if progress_callback:
            progress_callback(90)

        # Nettoyage de l'archive
        archive_path.unlink(missing_ok=True)

        # Étape 3 — Vérification (90 → 100%)
        _log("Vérification de l'installation…")
        gcc = self._find_gcc()
        if gcc is None or not gcc.is_file():
            raise FileNotFoundError(
                f"arm-none-eabi-gcc.exe introuvable après extraction dans {TOOLCHAIN_INSTALL_DIR}"
            )

        if progress_callback:
            progress_callback(100)
        _log("Toolchain ARM prête.")
        logger.info("Toolchain ARM installée dans %s", TOOLCHAIN_INSTALL_DIR)

    def _find_gcc(self) -> Path | None:
        """Cherche arm-none-eabi-gcc.exe dans le répertoire d'installation."""
        if not TOOLCHAIN_INSTALL_DIR.is_dir():
            return None
        # L'archive ARM extrait dans un sous-dossier nommé arm-gnu-toolchain-...
        candidates = list(TOOLCHAIN_INSTALL_DIR.rglob("arm-none-eabi-gcc.exe"))
        if candidates:
            return candidates[0]
        return None


# ─────────────────────────────────────────────────── Qt components ──


class ToolchainInstallWorker(QThread):
    """Thread de téléchargement toolchain ARM avec signaux de progression."""

    progress = Signal(int)
    log_line = Signal(str)
    finished = Signal()
    error = Signal(str)

    def run(self) -> None:
        try:
            ToolchainInstaller().install(
                progress_callback=self.progress.emit,
                log_callback=self.log_line.emit,
            )
            self.finished.emit()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Erreur installation toolchain ARM")
            self.error.emit(str(exc))


class ToolchainSetupDialog(QDialog):
    """Dialogue de progression pour l'installation de la toolchain ARM."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("toolchain_setup.title"))
        self.setModal(True)
        self.setMinimumWidth(450)

        layout = QVBoxLayout(self)
        self._label = QLabel(tr("toolchain_setup.downloading"))
        self._label.setObjectName("toolchain_setup_label")
        self._progress = QProgressBar()
        self._progress.setObjectName("toolchain_setup_progress")
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        layout.addWidget(self._label)
        layout.addWidget(self._progress)

        self._worker = ToolchainInstallWorker()
        self._worker.progress.connect(self._progress.setValue)
        self._worker.log_line.connect(self._label.setText)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_finished(self) -> None:
        self._label.setText(tr("toolchain_setup.ready"))
        self.accept()

    def _on_error(self, msg: str) -> None:
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.critical(self, tr("toolchain_setup.error_title"), msg)
        self.reject()
