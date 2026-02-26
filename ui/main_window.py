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
        # L'onglet OLED est géré par _on_oled_sides_changed
        self._tabs.setTabEnabled(2, True)
        self._tab_rgb.refresh_layout()
        logger.info(
            "Capacités mises à jour : OLED=%s, RGB=%s",
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
        path, _ = QFileDialog.getSaveFileName(
            self, tr("dlg.save_title"), str(Path.home()), tr("dlg.file_filter")
        )
        if not path:
            return
        try:
            save_project(self._model, Path(path))  # L3 : file_io loggue déjà, pas besoin ici
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

        # Mettre à jour les champs (conserver la référence existante)
        self._model.keyboard = loaded.keyboard
        self._model.oled = loaded.oled
        self._model.rgb = loaded.rgb
        self._model.build = loaded.build

        self._sync_hardware_widget()
        # M1 : resynchroniser les widgets OLED et RGB avec les nouvelles données
        self._tab_oled._sync_from_model()
        self._tab_rgb._sync_from_model()
        logger.info("Projet ouvert : %s", path)

    def _sync_hardware_widget(self) -> None:
        """Synchronise les combos clavier, MCU et OLED avec model.keyboard après un chargement."""
        target_kb_model = self._model.keyboard.model
        target_mcu = self._model.keyboard.mcu
        target_oled_sides = list(self._model.keyboard.oled_sides)
        combo = self._tab_hardware._keyboard_combo
        found = False
        for i in range(combo.count()):
            if self._tab_hardware._keyboards[i].model == target_kb_model:
                combo.setCurrentIndex(i)  # déclenche _on_model_changed() → réinitialise MCU
                found = True
                break
        if not found:
            logger.warning(
                "Modèle de clavier '%s' introuvable dans la liste — widget non synchronisé",
                target_kb_model,
            )
            return
        # M1 : restaurer le MCU sauvegardé (écrasé par _on_model_changed qui choisit le premier)
        kb_idx = combo.currentIndex()
        kb = self._tab_hardware._keyboards[kb_idx]
        mcu_combo = self._tab_hardware._mcu_combo
        for i, mcu_opt in enumerate(kb.mcu_options):
            if mcu_opt.id == target_mcu:
                mcu_combo.setCurrentIndex(i)  # déclenche _on_mcu_changed → met à jour model
                break
        # Restaurer oled_sides sauvegardé (écrasé par _on_model_changed qui met le défaut)
        self._tab_hardware.set_oled_sides(target_oled_sides)

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
