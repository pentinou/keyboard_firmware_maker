"""MainWindow — fenêtre principale de keyboard_firmware_maker.

Contient le QTabWidget avec les 4 onglets principaux, les menus Fichier, Configuration et Aide.
Reçoit le ProjectModel par injection de dépendance au constructeur.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from PySide6.QtGui import QActionGroup
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QMainWindow,
    QMenuBar,
    QMessageBox,
    QTabWidget,
    QWidget,
)

from i18n import AVAILABLE_LANGUAGES, get_language, set_language, tr
from models.project_model import ProjectModel
from modules.hardware.widget import HardwareWidget
from modules.oled_editor.widget import OledWidget
from modules.build_manager.vial_qmk_manager import VialQmkManager, VialQmkSetupDialog
from modules.build_manager.widget import BuildWidget
from modules.project_manager.file_io import load_project, save_project
from modules.rgb_editor.widget import RgbWidget
from ui.widgets.about_dialog import AboutDialog

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Fenêtre principale de l'application.

    Owns the ProjectModel instance and will pass it to child module widgets
    as they are implemented in subsequent stories.
    """

    def __init__(self, model: ProjectModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._model = model
        self._project_path: Path | None = None
        self._setup_ui()
        self._setup_menu()
        self._check_vial_qmk()
        logger.info("MainWindow initialized")

    @property
    def model(self) -> ProjectModel:
        """Accès en lecture au ProjectModel central."""
        return self._model

    def _setup_ui(self) -> None:
        self.setWindowTitle(tr("app.title"))
        self.setMinimumSize(900, 600)

        self._tabs = QTabWidget()
        self.setCentralWidget(self._tabs)

        self._tab_hardware = HardwareWidget(self._model)
        self._tab_oled = OledWidget(self._model)
        self._tab_rgb = RgbWidget(self._model)
        self._tab_build = BuildWidget(self._model)

        self._tabs.addTab(self._tab_hardware, tr("tab.hardware"))
        self._tabs.addTab(self._tab_oled,     tr("tab.oled"))
        self._tabs.addTab(self._tab_rgb,      tr("tab.rgb"))
        self._tabs.addTab(self._tab_build,    tr("tab.build"))

        # Désactivés par défaut — activés selon les capacités du clavier (FR3, FR4)
        self._tabs.setTabEnabled(1, False)
        self._tabs.setTabEnabled(2, False)

        # Signal de sauvegarde rapide depuis l'onglet RGB
        self._tab_rgb.save_requested.connect(self._save_project)

        # Connexion après addTab() pour que setTabEnabled() soit valide
        self._tab_hardware.capabilities_changed.connect(self._on_capabilities_changed)
        self._tab_hardware.oled_sides_changed.connect(self._on_oled_sides_changed)
        # Forcer l'état initial — le signal a pu être émis avant la connexion
        keyboards = self._tab_hardware._keyboards
        idx = self._tab_hardware._keyboard_combo.currentIndex()
        if keyboards and 0 <= idx < len(keyboards):
            self._on_capabilities_changed(keyboards[idx].capabilities)
        self._on_oled_sides_changed(self._model.keyboard.oled_sides)

    def _on_capabilities_changed(self, capabilities: dict) -> None:
        """Met à jour la visibilité des onglets selon les capacités du clavier sélectionné."""
        self._tabs.setTabEnabled(2, bool(capabilities.get("rgb", False)))
        # Passer le KeyboardDefinition courant au widget RGB
        current_kb = getattr(self._tab_hardware, "_current_kb", None)
        self._tab_rgb.refresh_layout(current_kb)
        # Propager le firmware (qmk/zmk) aux widgets Hardware/OLED/RGB pour que
        # ceux-ci masquent les fonctionnalités QMK-only en mode ZMK (overlays
        # OLED, per-key colors, custom effects).
        firmware = capabilities.get("firmware", "qmk")
        self._tab_hardware.set_firmware(firmware)
        self._tab_oled.set_firmware(firmware)
        self._tab_rgb.set_firmware(firmware)
        # Adapter l'onglet Build au firmware (QMK vs ZMK)
        self._tab_build.refresh_for_firmware()
        logger.info(
            "Capacités mises à jour : firmware=%s, OLED=%s, RGB=%s",
            firmware,
            capabilities.get("oled"),
            capabilities.get("rgb"),
        )

    def _on_oled_sides_changed(self, sides: list) -> None:
        """Active/désactive l'onglet OLED et met à jour les groupes visibles."""
        self._tabs.setTabEnabled(1, len(sides) > 0)
        self._tab_oled.set_active_sides(sides)

    def _setup_menu(self) -> None:
        menu_bar = self.menuBar()

        # Menu Fichier
        file_menu = menu_bar.addMenu(tr("menu.file"))
        save_action = file_menu.addAction(tr("menu.file.save"))
        save_action.triggered.connect(self._save_project)
        save_as_action = file_menu.addAction(tr("menu.file.save_as"))
        save_as_action.triggered.connect(self._save_project_as)
        open_action = file_menu.addAction(tr("menu.file.open"))
        open_action.triggered.connect(self._open_project)
        file_menu.addSeparator()
        quit_action = file_menu.addAction(tr("menu.file.quit"))
        quit_action.triggered.connect(QApplication.quit)

        # Menu Configuration (entre Fichier et Aide)
        config_menu = menu_bar.addMenu(tr("menu.config"))
        lang_menu = config_menu.addMenu(tr("menu.config.language"))
        lang_group = QActionGroup(lang_menu)
        lang_group.setExclusive(True)
        for code, name in AVAILABLE_LANGUAGES.items():
            act = lang_menu.addAction(name)
            act.setCheckable(True)
            act.setChecked(code == get_language())
            act.triggered.connect(lambda checked, lc=code: self._on_language_changed(lc))
            lang_group.addAction(act)

        # Menu Aide
        help_menu = menu_bar.addMenu(tr("menu.help"))
        about_action = help_menu.addAction(tr("menu.help.about"))
        about_action.triggered.connect(self._show_about)

    def _on_language_changed(self, lang: str) -> None:
        set_language(lang)
        QMessageBox.information(self, tr("dlg.lang_change_title"), tr("dlg.lang_change_msg"))

    def _save_project(self) -> None:
        if self._project_path and self._project_path.exists():
            # Quick save au même emplacement
            try:
                save_project(self._model, self._project_path)
                logger.info("Projet sauvegardé : %s", self._project_path)
            except OSError as e:
                QMessageBox.critical(self, tr("dlg.error"), tr("dlg.save_error").format(e=e))
            return
        self._save_project_as()

    def _save_project_as(self) -> None:
        default_dir = str(self._project_path.parent) if self._project_path else str(Path.home())
        path, _ = QFileDialog.getSaveFileName(
            self, tr("dlg.save_title"), default_dir, tr("dlg.file_filter")
        )
        if not path:
            return
        if not path.endswith(".kfm.json"):
            path += ".kfm.json"
        self._project_path = Path(path)
        try:
            save_project(self._model, self._project_path)
            logger.info("Projet sauvegardé : %s", self._project_path)
        except OSError as e:
            QMessageBox.critical(self, tr("dlg.error"), tr("dlg.save_error").format(e=e))

    def _open_project(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, tr("dlg.open_title"), str(Path.home()), tr("dlg.file_filter")
        )
        if not path:
            return
        try:
            loaded = load_project(Path(path))
        except (OSError, json.JSONDecodeError, KeyError, ValueError, TypeError) as e:
            QMessageBox.critical(self, tr("dlg.error"), tr("dlg.load_error").format(e=e))
            return

        self._project_path = Path(path)
        # Mettre à jour les champs (conserver la référence existante)
        self._model.keyboard = loaded.keyboard
        self._model.oled = loaded.oled
        self._model.rgb = loaded.rgb
        self._model.build = loaded.build

        self._sync_hardware_widget()
        # Resynchroniser les widgets OLED et RGB avec les nouvelles données
        self._tab_oled._sync_from_model()
        self._tab_rgb._sync_from_model()
        logger.info("Projet ouvert : %s", path)

    def _sync_hardware_widget(self) -> None:
        """Synchronise les combos clavier, MCU et OLED avec model.keyboard après un chargement."""
        target_kb_model = self._model.keyboard.model
        target_mcu = self._model.keyboard.mcu
        target_oled_sides = list(self._model.keyboard.oled_sides)

        # Trouver le clavier dans la liste et le sélectionner
        combo = self._tab_hardware._keyboard_combo
        found = False
        for i in range(combo.count()):
            entry_idx = self._tab_hardware._filtered_entries[i] if i < len(self._tab_hardware._filtered_entries) else -1
            if entry_idx < 0:
                continue
            kb, _, _ = self._tab_hardware._all_keyboard_entries[entry_idx]
            if kb and kb.model == target_kb_model:
                combo.setCurrentIndex(i)
                found = True
                break

        if not found:
            # Essayer avec catégorie "all"
            self._tab_hardware._category_combo.setCurrentIndex(0)
            for i in range(combo.count()):
                entry_idx = self._tab_hardware._filtered_entries[i] if i < len(self._tab_hardware._filtered_entries) else -1
                if entry_idx < 0:
                    continue
                kb, _, _ = self._tab_hardware._all_keyboard_entries[entry_idx]
                if kb and kb.model == target_kb_model:
                    combo.setCurrentIndex(i)
                    found = True
                    break

        if not found:
            logger.warning(
                "Modèle de clavier '%s' introuvable dans la liste — widget non synchronisé",
                target_kb_model,
            )
            return

        # Restaurer le MCU sauvegardé
        kb = getattr(self._tab_hardware, "_current_kb", None)
        if kb:
            mcu_combo = self._tab_hardware._mcu_combo
            for i, mcu_opt in enumerate(kb.mcu_options):
                if mcu_opt.id == target_mcu:
                    mcu_combo.setCurrentIndex(i)
                    break

        # Restaurer la variante layout sauvegardée
        self._tab_hardware.set_layout_variant(self._model.keyboard.layout_variant)
        # Restaurer oled_sides sauvegardé
        self._tab_hardware.set_oled_sides(target_oled_sides)
        # Restaurer rgb_enabled sauvegardé
        self._tab_hardware.set_rgb_enabled(self._model.keyboard.rgb_enabled)

    def _check_vial_qmk(self) -> None:
        """Lance le dialogue de setup si le cache Vial-QMK est absent (AC: 1, 3)."""
        if not VialQmkManager().is_ready():
            dlg = VialQmkSetupDialog(self)
            if dlg.exec() != QDialog.DialogCode.Accepted:
                QMessageBox.warning(
                    self,
                    tr("dlg.vial_unavailable"),
                    tr("dlg.vial_unavailable_msg"),
                )

    def _show_about(self) -> None:
        dialog = AboutDialog(self)
        dialog.exec()
