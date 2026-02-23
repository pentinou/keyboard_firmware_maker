"""BuildWidget — onglet Build de keyboard_firmware_maker (FR16-FR20, FR17-FR18, FR28).

Affiche :
- Statut de la toolchain détectée
- Bouton "Générer firmware"
- Barre de progression 0-100%
- Zone de log en temps réel (QPlainTextEdit)
- Taille du firmware après compilation (FR17)
- Avertissement si dépassement flash (FR18)
- Bouton "Exporter le firmware" (FR28)
- Bouton "Guide de flash" (FR23)
"""
from __future__ import annotations

import logging
import shutil
from pathlib import Path

from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from models.project_model import ProjectModel
from modules.build_manager.builder import MCU_FLASH, BuildWorker
from modules.build_manager.toolchain import INSTALL_GUIDE_MSG, detect_toolchain
from modules.build_manager.vial_qmk_manager import VIAL_QMK_DIR, VialQmkManager

logger = logging.getLogger(__name__)


class BuildWidget(QWidget):
    """Widget de l'onglet Build."""

    def __init__(self, model: ProjectModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._model = model
        self._worker: BuildWorker | None = None
        self._last_uf2: str | None = None  # chemin du dernier .uf2 compilé (FR28)
        self._setup_ui()
        self._refresh_toolchain_status()

    # ─────────────────────────────────────────────────────── UI setup ──

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Statut toolchain
        self._lbl_toolchain = QLabel()
        self._lbl_toolchain.setObjectName("lbl_toolchain")
        self._lbl_toolchain.setWordWrap(True)
        layout.addWidget(self._lbl_toolchain)

        # Bouton générer + export + guide
        btn_row = QHBoxLayout()
        self._btn_build = QPushButton("Générer firmware")
        self._btn_build.setObjectName("btn_build")
        self._btn_build.clicked.connect(self._on_build_clicked)
        btn_row.addWidget(self._btn_build)

        self._btn_export = QPushButton("Exporter le firmware")
        self._btn_export.setObjectName("btn_export")
        self._btn_export.setEnabled(False)  # activé seulement après succès (FR28)
        self._btn_export.clicked.connect(self._on_export_clicked)
        btn_row.addWidget(self._btn_export)

        self._btn_guide = QPushButton("Guide de flash")
        self._btn_guide.setObjectName("btn_guide")
        self._btn_guide.clicked.connect(self._on_guide_clicked)
        btn_row.addWidget(self._btn_guide)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        # Barre de progression
        self._progress = QProgressBar()
        self._progress.setObjectName("build_progress")
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        layout.addWidget(self._progress)

        # Zone de log
        self._log = QPlainTextEdit()
        self._log.setObjectName("build_log")
        self._log.setReadOnly(True)
        self._log.setMaximumBlockCount(2000)
        layout.addWidget(self._log)

        # Label taille firmware
        self._lbl_size = QLabel("")
        self._lbl_size.setObjectName("lbl_firmware_size")
        layout.addWidget(self._lbl_size)

        # Label statut courant
        self._lbl_status = QLabel("")
        self._lbl_status.setObjectName("lbl_build_status")
        layout.addWidget(self._lbl_status)

    # ─────────────────────────────────────────────────── Toolchain ──

    def _refresh_toolchain_status(self) -> None:
        """Affiche le statut de la toolchain détectée."""
        info = detect_toolchain()
        if info.is_available:
            self._lbl_toolchain.setText(
                f"Toolchain : {info.gcc_path}  |  version {info.version}  |  source : {info.source}"
            )
        else:
            self._lbl_toolchain.setText(f"⚠ Toolchain introuvable\n{INSTALL_GUIDE_MSG}")

    # ─────────────────────────────────────────────────── Build ──

    def _on_build_clicked(self) -> None:
        """Lance la compilation après vérification des prérequis."""
        toolchain = detect_toolchain()
        if not toolchain.is_available:
            QMessageBox.warning(
                self,
                "Toolchain introuvable",
                INSTALL_GUIDE_MSG,
            )
            return

        if not VialQmkManager().is_ready():
            QMessageBox.warning(
                self,
                "Vial-QMK non initialisé",
                "Vial-QMK n'est pas disponible dans le cache.\n"
                "Relancez l'application pour le télécharger.",
            )
            return

        self._btn_build.setEnabled(False)
        self._progress.setValue(0)
        self._log.clear()
        self._lbl_size.setText("")
        self._lbl_status.setText("Compilation en cours…")

        self._worker = BuildWorker(
            model=self._model,
            vial_qmk_dir=VIAL_QMK_DIR,
            gcc_path=toolchain.gcc_path,
        )
        self._worker.progress.connect(self._progress.setValue)
        self._worker.log_line.connect(self._log.appendPlainText)
        self._worker.success.connect(self._on_build_success)
        self._worker.error.connect(self._on_build_error)
        self._worker.start()
        logger.info("Compilation démarrée")

    def _on_build_success(self, uf2_path: str) -> None:
        """Affiche la taille du firmware et avertit si dépassement flash (FR17, FR18)."""
        self._btn_build.setEnabled(True)
        self._last_uf2 = uf2_path
        self._btn_export.setEnabled(True)
        path = Path(uf2_path)
        size = path.stat().st_size
        mcu = self._model.keyboard.mcu or "rp2040"
        flash_capacity = MCU_FLASH.get(mcu, 2 * 1024 * 1024)

        size_kb = size // 1024
        flash_kb = flash_capacity // 1024
        self._lbl_size.setText(f"Firmware : {size_kb} KB / {flash_kb} KB utilisés")

        if size > flash_capacity:
            QMessageBox.warning(
                self,
                "Firmware trop volumineux",
                f"Le firmware ({size_kb} KB) dépasse la capacité flash du MCU "
                f"{mcu} ({flash_kb} KB).\n"
                "Réduisez les fonctionnalités activées avant de flasher.",
            )

        self._lbl_status.setText("Compilation réussie.")
        logger.info("Compilation réussie : %s (%s KB)", uf2_path, size_kb)

    def _on_build_error(self, msg: str) -> None:
        """Affiche l'erreur humanisée et réactive le bouton (NFR8)."""
        self._btn_build.setEnabled(True)
        self._lbl_status.setText("Échec de la compilation.")
        QMessageBox.critical(self, "Erreur de compilation", msg)
        logger.error("Erreur compilation : %s", msg)

    # ─────────────────────────────────────────────── Export + Guide ──

    def _on_export_clicked(self) -> None:
        """Exporte le .uf2 vers l'emplacement choisi par l'utilisateur (FR28)."""
        if not self._last_uf2:
            return
        src = Path(self._last_uf2)
        # M2 : le fichier source peut avoir été nettoyé depuis la compilation
        if not src.exists():
            QMessageBox.warning(
                self,
                "Fichier introuvable",
                "Le fichier firmware n'est plus disponible.\n"
                "Relancez une compilation avant d'exporter.",
            )
            self._btn_export.setEnabled(False)
            self._last_uf2 = None
            return
        dest, _ = QFileDialog.getSaveFileName(
            self,
            "Exporter le firmware",
            src.name,
            "Firmware UF2 (*.uf2)",
        )
        if dest:
            try:
                # M1 : erreurs d'E/S (droits, disque plein, chemin invalide)
                shutil.copy2(src, dest)
            except OSError as exc:
                QMessageBox.critical(
                    self,
                    "Erreur d'export",
                    f"Impossible d'exporter le firmware :\n{exc}",
                )
                logger.error("Export firmware échoué : %s → %s : %s", src, dest, exc)
                return
            QMessageBox.information(
                self,
                "Export réussi",
                f"Firmware exporté vers :\n{dest}",
            )
            logger.info("Firmware exporté : %s → %s", src, dest)

    def _on_guide_clicked(self) -> None:
        """Ouvre le guide de flash illustré (FR23, FR33)."""
        from ui.widgets.flash_guide_dialog import FlashGuideDialog
        dlg = FlashGuideDialog(self)
        dlg.exec()
