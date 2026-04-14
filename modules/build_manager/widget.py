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
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog,
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

from i18n import tr
from models.project_model import ProjectModel
from modules.build_manager.builder import MCU_FLASH, BuildWorker
from modules.build_manager.msys2_manager import Msys2Manager, Msys2SetupDialog, is_windows
from modules.build_manager.toolchain import INSTALL_GUIDE_MSG, detect_toolchain
from modules.build_manager.toolchain_installer import ToolchainInstaller, ToolchainSetupDialog
from modules.build_manager.vial_qmk_manager import VIAL_QMK_DIR, VialQmkManager
from modules.build_manager.zmk_template_generator import ZmkTemplateGenerator
from modules.hardware.keyboard_loader import load_keyboard, get_firmware_type

logger = logging.getLogger(__name__)

BASE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).parent.parent.parent))
KEYBOARDS_DIR = BASE_DIR / "keyboards"


class BuildWidget(QWidget):
    """Widget de l'onglet Build."""

    def __init__(self, model: ProjectModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._model = model
        self._worker: BuildWorker | None = None
        self._last_uf2: str | None = None  # chemin du dernier .uf2 compilé (FR28)
        self._last_zmk_dir: Path | None = None  # dossier du dernier zmk-config généré
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
        self._btn_build = QPushButton(tr("build.btn.generate"))
        self._btn_build.setObjectName("btn_build")
        self._btn_build.clicked.connect(self._on_build_clicked)
        btn_row.addWidget(self._btn_build)

        self._btn_export = QPushButton(tr("build.btn.export"))
        self._btn_export.setObjectName("btn_export")
        self._btn_export.setEnabled(False)  # activé seulement après succès (FR28)
        self._btn_export.clicked.connect(self._on_export_clicked)
        btn_row.addWidget(self._btn_export)

        self._btn_guide = QPushButton(tr("build.btn.guide"))
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

    # ──────────────────────────────────────────── Firmware type ──

    def _firmware_type(self) -> str:
        """Retourne 'qmk' ou 'zmk' selon le MCU sélectionné."""
        model_name = self._model.keyboard.model
        mcu = self._model.keyboard.mcu
        if not model_name or not mcu:
            return "qmk"
        yaml_path = KEYBOARDS_DIR / f"{model_name}.yaml"
        if not yaml_path.exists():
            return "qmk"
        kb_def = load_keyboard(yaml_path)
        return get_firmware_type(kb_def, mcu)

    def refresh_for_firmware(self) -> None:
        """Adapte l'UI selon le firmware (QMK vs ZMK). Appelé quand le MCU change."""
        is_zmk = self._firmware_type() == "zmk"
        if is_zmk:
            self._btn_build.setText(tr("build.zmk.generate_config"))
            self._btn_export.setText(tr("build.zmk.open_folder"))
            self._btn_guide.setVisible(False)
            self._lbl_toolchain.setText(tr("build.zmk.toolchain_info"))
            self._btn_export.setEnabled(self._last_zmk_dir is not None)
        else:
            self._btn_build.setText(tr("build.btn.generate"))
            self._btn_export.setText(tr("build.btn.export"))
            self._btn_guide.setVisible(True)
            self._refresh_toolchain_status()
            self._btn_export.setEnabled(self._last_uf2 is not None)

    # ─────────────────────────────────────────────────── Toolchain ──

    def _refresh_toolchain_status(self) -> None:
        """Affiche le statut de la toolchain détectée."""
        info = detect_toolchain()
        if info.is_available:
            self._lbl_toolchain.setText(
                tr("build.toolchain_found").format(
                    gcc_path=info.gcc_path, version=info.version, source=info.source
                )
            )
        else:
            self._lbl_toolchain.setText(
                tr("build.toolchain_not_found").format(msg=INSTALL_GUIDE_MSG)
            )

    # ─────────────────────────────────────────────────── Build ──

    def _on_build_clicked(self) -> None:
        """Lance la compilation QMK ou la génération zmk-config."""
        if self._firmware_type() == "zmk":
            self._on_zmk_generate()
            return
        # ── QMK flow ──
        # Windows : vérifier MSYS2 (fournit make + bash)
        if is_windows() and not Msys2Manager().is_ready():
            reply = QMessageBox.question(
                self,
                tr("msys2_setup.title"),
                tr("build.msys2_missing_msg"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                dlg = Msys2SetupDialog(self)
                if dlg.exec() != QDialog.DialogCode.Accepted:
                    return
            else:
                return

        # Vérifier la toolchain ARM
        toolchain = detect_toolchain()
        if not toolchain.is_available:
            if is_windows():
                reply = QMessageBox.question(
                    self,
                    tr("toolchain_setup.title"),
                    tr("build.toolchain_missing_install_msg"),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if reply == QMessageBox.StandardButton.Yes:
                    dlg = ToolchainSetupDialog(self)
                    if dlg.exec() == QDialog.DialogCode.Accepted:
                        toolchain = detect_toolchain()
                    else:
                        return
                else:
                    return
            else:
                QMessageBox.warning(
                    self,
                    tr("build.toolchain_missing_title"),
                    INSTALL_GUIDE_MSG,
                )
                return

        if not toolchain.is_available:
            QMessageBox.warning(self, tr("build.toolchain_missing_title"), INSTALL_GUIDE_MSG)
            return

        # Vérifier que qmk CLI est installé (requis par le Makefile QMK)
        if not shutil.which("qmk"):
            self._log.appendPlainText("Installation de qmk CLI (pip install qmk)…")
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "qmk"],
                capture_output=True, text=True,
            )
            if result.returncode != 0:
                QMessageBox.critical(
                    self,
                    tr("build.error_title"),
                    "Impossible d'installer qmk CLI.\n\n" + result.stderr[-500:],
                )
                return
            self._log.appendPlainText("qmk CLI installé.")

        if not VialQmkManager().is_ready():
            QMessageBox.warning(
                self,
                tr("build.vial_not_init_title"),
                tr("build.vial_not_init_msg"),
            )
            return

        self._btn_build.setEnabled(False)
        self._progress.setValue(0)
        self._log.clear()
        self._lbl_size.setText("")
        self._lbl_status.setText(tr("build.compiling"))

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

    # ─────────────────────────────────────────────── ZMK generate ──

    def _on_zmk_generate(self) -> None:
        """Génère la config ZMK dans un dossier choisi par l'utilisateur."""
        if not self._model.keyboard.model:
            QMessageBox.warning(self, tr("build.zmk.error_title"), tr("build.zmk.no_model"))
            return

        output_dir = QFileDialog.getExistingDirectory(
            self,
            tr("build.zmk.select_output_dir"),
            str(Path.home()),
        )
        if not output_dir:
            return

        self._btn_build.setEnabled(False)
        self._progress.setValue(0)
        self._log.clear()
        self._lbl_size.setText("")
        self._lbl_status.setText(tr("build.zmk.generating"))

        try:
            gen = ZmkTemplateGenerator()
            generated = gen.generate(self._model, Path(output_dir))

            for desc, path in generated.items():
                self._log.appendPlainText(f"  {desc}: {path}")

            self._progress.setValue(100)
            self._last_zmk_dir = Path(output_dir)
            self._btn_export.setEnabled(True)
            self._lbl_status.setText(tr("build.zmk.success"))
            self._lbl_size.setText(
                tr("build.zmk.output_ready").format(path=output_dir)
            )
            logger.info("zmk-config g\u00e9n\u00e9r\u00e9 : %d fichiers dans %s", len(generated), output_dir)

        except Exception as exc:
            self._lbl_status.setText(tr("build.error"))
            self._log.appendPlainText(str(exc))
            QMessageBox.critical(
                self,
                tr("build.zmk.error_title"),
                tr("build.zmk.error_msg").format(exc=exc),
            )
            logger.error("Erreur g\u00e9n\u00e9ration ZMK : %s", exc)

        finally:
            self._btn_build.setEnabled(True)

    # ─────────────────────────────────────────── QMK build callbacks ──

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
        self._lbl_size.setText(
            tr("build.firmware_size").format(size_kb=size_kb, flash_kb=flash_kb)
        )

        if size > flash_capacity:
            QMessageBox.warning(
                self,
                tr("build.oversized_title"),
                tr("build.oversized_msg").format(size_kb=size_kb, mcu=mcu, flash_kb=flash_kb),
            )

        self._lbl_status.setText(tr("build.success"))
        logger.info("Compilation réussie : %s (%s KB)", uf2_path, size_kb)

    def _on_build_error(self, msg: str) -> None:
        """Affiche l'erreur humanisée et réactive le bouton (NFR8)."""
        self._btn_build.setEnabled(True)
        self._lbl_status.setText(tr("build.error"))
        QMessageBox.critical(self, tr("build.error_title"), msg)
        logger.error("Erreur compilation : %s", msg)

    # ─────────────────────────────────────────────── Export + Guide ──

    def _on_export_clicked(self) -> None:
        """Exporte le .uf2 (QMK) ou ouvre le dossier zmk-config (ZMK)."""
        if self._firmware_type() == "zmk":
            if self._last_zmk_dir and self._last_zmk_dir.exists():
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._last_zmk_dir)))
            return
        if not self._last_uf2:
            return
        src = Path(self._last_uf2)
        # M2 : le fichier source peut avoir été nettoyé depuis la compilation
        if not src.exists():
            QMessageBox.warning(
                self,
                tr("build.file_not_found_title"),
                tr("build.file_not_found_msg"),
            )
            self._btn_export.setEnabled(False)
            self._last_uf2 = None
            return
        model = self._model.keyboard.model or "firmware"
        variant = self._model.keyboard.layout_variant
        default_name = f"KFM_{model}_{variant}.uf2" if variant else f"KFM_{model}.uf2"
        dest, _ = QFileDialog.getSaveFileName(
            self,
            tr("build.export_dialog_title"),
            default_name,
            tr("build.uf2_filter"),
        )
        if dest:
            try:
                # M1 : erreurs d'E/S (droits, disque plein, chemin invalide)
                shutil.copy2(src, dest)
            except OSError as exc:
                QMessageBox.critical(
                    self,
                    tr("build.export_error_title"),
                    tr("build.export_error_msg").format(exc=exc),
                )
                logger.error("Export firmware échoué : %s → %s : %s", src, dest, exc)
                return
            QMessageBox.information(
                self,
                tr("build.export_success_title"),
                tr("build.export_success_msg").format(dest=dest),
            )
            logger.info("Firmware exporté : %s → %s", src, dest)

    def _on_guide_clicked(self) -> None:
        """Ouvre le guide de flash illustré (FR23, FR33)."""
        from ui.widgets.flash_guide_dialog import FlashGuideDialog
        dlg = FlashGuideDialog(self)
        dlg.exec()
