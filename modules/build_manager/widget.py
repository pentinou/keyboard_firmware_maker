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
from modules.build_manager.zmk_builder import (
    ZEPHYR_SDK_DIR,
    ZmkBuildWorker,
    is_west_available,
    is_zephyr_sdk_installed,
)
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
        self._zmk_worker: ZmkBuildWorker | None = None
        self._last_uf2: str | None = None  # chemin du dernier .uf2 compilé (FR28)
        self._last_zmk_dir: Path | None = None  # dossier du dernier zmk-config généré
        self._last_zmk_uf2s: list[Path] = []  # .uf2 produits par la dernière compilation ZMK locale
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

        # Bouton ZMK secondaire : génère uniquement la config (pour GitHub Actions)
        self._btn_zmk_config = QPushButton(tr("build.zmk.generate_config"))
        self._btn_zmk_config.setObjectName("btn_zmk_config")
        self._btn_zmk_config.clicked.connect(self._on_zmk_generate)
        self._btn_zmk_config.setVisible(False)
        btn_row.addWidget(self._btn_zmk_config)

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
            self._btn_build.setText(tr("build.zmk.build_local"))
            self._btn_export.setText(tr("build.zmk.export_uf2"))
            self._btn_zmk_config.setVisible(True)
            self._btn_guide.setVisible(False)
            self._refresh_zmk_toolchain_status()
            self._btn_export.setEnabled(bool(self._last_zmk_uf2s))
        else:
            self._btn_build.setText(tr("build.btn.generate"))
            self._btn_export.setText(tr("build.btn.export"))
            self._btn_zmk_config.setVisible(False)
            self._btn_guide.setVisible(True)
            self._refresh_toolchain_status()
            self._btn_export.setEnabled(self._last_uf2 is not None)

    def _refresh_zmk_toolchain_status(self) -> None:
        """Affiche le statut de la toolchain ZMK (Zephyr SDK + west)."""
        sdk_ok = is_zephyr_sdk_installed()
        west_ok = is_west_available()
        if sdk_ok and west_ok:
            self._lbl_toolchain.setText(
                tr("build.zmk.toolchain_ready").format(sdk_dir=ZEPHYR_SDK_DIR)
            )
        else:
            missing = []
            if not sdk_ok:
                missing.append("Zephyr SDK")
            if not west_ok:
                missing.append("west")
            script = "setup_zmk.bat" if is_windows() else "setup_zmk.sh"
            self._lbl_toolchain.setText(
                tr("build.zmk.toolchain_missing").format(missing=", ".join(missing), script=script)
            )

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
        """Lance la compilation QMK ou ZMK locale."""
        if self._firmware_type() == "zmk":
            self._on_zmk_build_local()
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

    # ─────────────────────────────────────────────── ZMK local build ──

    def _on_zmk_build_local(self) -> None:
        """Lance la compilation ZMK locale dans le workspace cache."""
        if not self._model.keyboard.model:
            QMessageBox.warning(self, tr("build.zmk.error_title"), tr("build.zmk.no_model"))
            return

        # Vérifier prérequis ZMK
        if not is_zephyr_sdk_installed() or not is_west_available():
            script = "setup_zmk.bat" if is_windows() else "setup_zmk.sh"
            QMessageBox.warning(
                self,
                tr("build.zmk.toolchain_missing_title"),
                tr("build.zmk.toolchain_missing_msg").format(script=script),
            )
            return

        self._btn_build.setEnabled(False)
        self._btn_zmk_config.setEnabled(False)
        self._btn_export.setEnabled(False)
        self._progress.setValue(0)
        self._log.clear()
        self._lbl_size.setText("")
        self._last_zmk_uf2s = []
        self._lbl_status.setText(tr("build.zmk.compiling"))

        self._zmk_worker = ZmkBuildWorker(model=self._model)
        self._zmk_worker.progress.connect(self._progress.setValue)
        self._zmk_worker.log_line.connect(self._log.appendPlainText)
        self._zmk_worker.success.connect(self._on_zmk_build_success)
        self._zmk_worker.error.connect(self._on_zmk_build_error)
        self._zmk_worker.start()
        logger.info("Compilation ZMK locale démarrée")

    def _on_zmk_build_success(self, uf2_paths: list) -> None:
        """Affiche les .uf2 produits et active l'export."""
        self._btn_build.setEnabled(True)
        self._btn_zmk_config.setEnabled(True)
        self._last_zmk_uf2s = [Path(p) for p in uf2_paths]
        self._btn_export.setEnabled(bool(self._last_zmk_uf2s))
        self._lbl_status.setText(tr("build.zmk.success"))
        names = ", ".join(p.name for p in self._last_zmk_uf2s)
        self._lbl_size.setText(tr("build.zmk.uf2_produced").format(names=names))
        logger.info("Compilation ZMK réussie : %d .uf2", len(self._last_zmk_uf2s))

    def _on_zmk_build_error(self, msg: str) -> None:
        """Affiche l'erreur de compilation ZMK."""
        self._btn_build.setEnabled(True)
        self._btn_zmk_config.setEnabled(True)
        self._lbl_status.setText(tr("build.error"))
        QMessageBox.critical(self, tr("build.zmk.error_title"), msg)
        logger.error("Erreur compilation ZMK : %s", msg)

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
        self._btn_zmk_config.setEnabled(False)
        self._progress.setValue(0)
        self._log.clear()
        self._lbl_size.setText("")
        # On clear les UF2 du build local pour que Export tombe sur "ouvrir le dossier"
        self._last_zmk_uf2s = []
        self._btn_export.setEnabled(False)
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
            self._btn_zmk_config.setEnabled(True)

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
        """Exporte le ou les .uf2 (QMK/ZMK) ou ouvre le dossier zmk-config si seule config générée."""
        if self._firmware_type() == "zmk":
            # Priorité : .uf2 produits par compilation locale
            if self._last_zmk_uf2s:
                dest_dir = QFileDialog.getExistingDirectory(
                    self,
                    tr("build.zmk.export_uf2_dialog"),
                    str(Path.home()),
                )
                if not dest_dir:
                    return
                model = self._model.keyboard.model or "firmware"
                try:
                    for uf2 in self._last_zmk_uf2s:
                        if not uf2.exists():
                            continue
                        # uf2.stem = 'zmk' pour chaque moitié : utiliser le nom du
                        # build_dir (build/<shield>/zephyr/zmk.uf2) pour distinguer
                        # left/right et éviter que la seconde copie écrase la première.
                        build_tag = uf2.parent.parent.name
                        dest = Path(dest_dir) / f"KFM_{model}_{build_tag}.uf2"
                        shutil.copy2(uf2, dest)
                except OSError as exc:
                    QMessageBox.critical(
                        self,
                        tr("build.export_error_title"),
                        tr("build.export_error_msg").format(exc=exc),
                    )
                    return
                QMessageBox.information(
                    self,
                    tr("build.export_success_title"),
                    tr("build.zmk.export_success_msg").format(count=len(self._last_zmk_uf2s), dest=dest_dir),
                )
                return
            # Fallback : ouvrir le dossier zmk-config si seule config générée
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

    def cleanup(self) -> None:
        """Tue les builds en cours. Appelé à la fermeture de l'application."""
        if self._zmk_worker and self._zmk_worker.isRunning():
            self._zmk_worker.stop()
            self._zmk_worker.wait(5000)
