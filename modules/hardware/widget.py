"""HardwareWidget — onglet "Matériel" de l'application.

Permet à l'utilisateur de sélectionner son modèle de clavier et son MCU
depuis des listes peuplées par les fichiers YAML dans `keyboards/`.
"""
from __future__ import annotations

import logging

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QLabel,
    QWidget,
)

from config import KEYBOARDS_DIR
from models.project_model import ProjectModel
from modules.hardware.keyboard_loader import KeyboardDefinition, load_all_keyboards

logger = logging.getLogger(__name__)


class HardwareWidget(QWidget):
    """Widget de sélection du matériel : modèle de clavier et MCU.

    Charge les définitions depuis les fichiers YAML dans `keyboards/`.
    Met à jour ProjectModel directement lors des changements de sélection.
    Émet `capabilities_changed` à chaque changement de clavier pour permettre
    à MainWindow de mettre à jour la visibilité des onglets (FR3, FR4).
    """

    capabilities_changed = Signal(dict)  # {"oled": bool, "rgb": bool}

    def __init__(self, model: ProjectModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._model = model
        self._keyboards: list[KeyboardDefinition] = load_all_keyboards(KEYBOARDS_DIR)
        self._setup_ui()
        self._connect_signals()
        # Initialise le ProjectModel avec la sélection par défaut
        if self._keyboards:
            self._on_model_changed(0)

    def _setup_ui(self) -> None:
        layout = QFormLayout(self)
        layout.setSpacing(12)

        # Combo de sélection du modèle de clavier
        self._keyboard_combo = QComboBox()
        self._keyboard_combo.setObjectName("keyboard_combo")
        for kb in self._keyboards:
            self._keyboard_combo.addItem(kb.display_name)
            idx = self._keyboard_combo.count() - 1
            self._keyboard_combo.setItemData(idx, kb.description, Qt.ItemDataRole.ToolTipRole)
        layout.addRow(QLabel("Modèle de clavier :"), self._keyboard_combo)

        # Combo de sélection du MCU (peuplé dynamiquement)
        self._mcu_combo = QComboBox()
        self._mcu_combo.setObjectName("mcu_combo")
        layout.addRow(QLabel("Microcontrôleur :"), self._mcu_combo)

    def _connect_signals(self) -> None:
        self._keyboard_combo.currentIndexChanged.connect(self._on_model_changed)
        self._mcu_combo.currentIndexChanged.connect(self._on_mcu_changed)

    def _on_model_changed(self, index: int) -> None:
        """Met à jour le combo MCU et le ProjectModel quand le clavier change."""
        if index < 0 or index >= len(self._keyboards):
            return

        kb = self._keyboards[index]
        self._model.keyboard.model = kb.model
        logger.info("Clavier sélectionné : %s (%s)", kb.display_name, kb.model)

        # Re-peupler le combo MCU sans déclencher de signal MCU intermédiaire
        self._mcu_combo.blockSignals(True)
        self._mcu_combo.clear()
        for mcu in kb.mcu_options:
            self._mcu_combo.addItem(mcu.display_name)
            idx = self._mcu_combo.count() - 1
            self._mcu_combo.setItemData(idx, mcu.description, Qt.ItemDataRole.ToolTipRole)
        self._mcu_combo.blockSignals(False)

        # Sélectionner le premier MCU et mettre à jour le modèle
        if kb.mcu_options:
            self._model.keyboard.mcu = kb.mcu_options[0].id
            logger.info("MCU par défaut : %s", kb.mcu_options[0].id)

        # Notifier MainWindow des capacités du clavier sélectionné (FR3, FR4)
        self.capabilities_changed.emit(kb.capabilities)

    def _on_mcu_changed(self, index: int) -> None:
        """Met à jour ProjectModel quand le MCU change."""
        kb_index = self._keyboard_combo.currentIndex()
        if kb_index < 0 or kb_index >= len(self._keyboards):
            return
        kb = self._keyboards[kb_index]
        if index < 0 or index >= len(kb.mcu_options):
            return
        mcu = kb.mcu_options[index]
        self._model.keyboard.mcu = mcu.id
        logger.info("MCU sélectionné : %s (%s)", mcu.display_name, mcu.id)
