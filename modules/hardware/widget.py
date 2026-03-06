"""HardwareWidget — onglet "Matériel" de l'application.

Permet à l'utilisateur de sélectionner son modèle de clavier et son MCU
depuis des listes peuplées par les fichiers YAML dans `keyboards/`.
"""
from __future__ import annotations

import logging

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QLabel,
    QPushButton,
    QWidget,
)

from config import KEYBOARDS_DIR
from i18n import tr
from models.project_model import ProjectModel
from modules.hardware.keyboard_loader import KeyboardDefinition, load_all_keyboards

CUSTOM_KEYBOARDS_DIR: Path = Path.home() / ".keyboard_firmware_maker" / "custom_keyboards"

logger = logging.getLogger(__name__)

_OLED_SIDES_OPTIONS: list[tuple[list[str], str]] = [
    ([], "hardware.oled.none"),
    (["left"], "hardware.oled.left_only"),
    (["right"], "hardware.oled.right_only"),
    (["left", "right"], "hardware.oled.both"),
]


class HardwareWidget(QWidget):
    """Widget de sélection du matériel : modèle de clavier et MCU.

    Charge les définitions depuis les fichiers YAML dans `keyboards/`.
    Met à jour ProjectModel directement lors des changements de sélection.
    Émet `capabilities_changed` à chaque changement de clavier pour permettre
    à MainWindow de mettre à jour la visibilité des onglets (FR3, FR4).
    """

    capabilities_changed = Signal(dict)  # {"oled": bool, "rgb": bool}
    oled_sides_changed = Signal(list)

    def __init__(self, model: ProjectModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._model = model
        self._keyboards: list[KeyboardDefinition] = load_all_keyboards(KEYBOARDS_DIR, CUSTOM_KEYBOARDS_DIR)
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
        layout.addRow(QLabel(tr("hardware.keyboard_model")), self._keyboard_combo)

        # Combo de sélection du MCU (peuplé dynamiquement)
        self._mcu_combo = QComboBox()
        self._mcu_combo.setObjectName("mcu_combo")
        layout.addRow(QLabel(tr("hardware.mcu")), self._mcu_combo)

        # Combo de sélection de variante layout (masqué par défaut)
        self._variant_label = QLabel(tr("hardware.layout_variant"))
        self._variant_combo = QComboBox()
        self._variant_combo.setObjectName("variant_combo")
        layout.addRow(self._variant_label, self._variant_combo)
        self._variant_label.hide()
        self._variant_combo.hide()

        # Combo de sélection des écrans OLED (masqué par défaut)
        self._oled_label = QLabel(tr("hardware.oled"))
        self._oled_combo = QComboBox()
        self._oled_combo.setObjectName("oled_combo")
        for _sides, key in _OLED_SIDES_OPTIONS:
            self._oled_combo.addItem(tr(key))
        layout.addRow(self._oled_label, self._oled_combo)
        self._oled_label.hide()
        self._oled_combo.hide()

        # Checkbox RGB — toujours visible (choix de build, pas contrainte PCB)
        self._rgb_checkbox = QCheckBox()
        self._rgb_checkbox.setObjectName("rgb_checkbox")
        layout.addRow(QLabel(tr("hardware.rgb")), self._rgb_checkbox)

        # Bouton créer clavier custom
        self._custom_btn = QPushButton(tr("hardware.custom_btn"))
        self._custom_btn.setObjectName("custom_keyboard_btn")
        layout.addRow(self._custom_btn)

    def _connect_signals(self) -> None:
        self._keyboard_combo.currentIndexChanged.connect(self._on_model_changed)
        self._mcu_combo.currentIndexChanged.connect(self._on_mcu_changed)
        self._variant_combo.currentIndexChanged.connect(self._on_variant_changed)
        self._oled_combo.currentIndexChanged.connect(self._on_oled_changed)
        self._rgb_checkbox.stateChanged.connect(self._on_rgb_changed)
        self._custom_btn.clicked.connect(self._open_custom_editor)

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

        # Afficher/masquer le combo variante selon le nombre de variantes
        self._variant_combo.blockSignals(True)
        self._variant_combo.clear()
        for v in kb.layout_variants:
            self._variant_combo.addItem(v.label)
        self._variant_combo.blockSignals(False)
        if len(kb.layout_variants) > 1:
            self._model.keyboard.layout_variant = kb.layout_variants[0].slug
            self._variant_label.show()
            self._variant_combo.show()
        else:
            self._model.keyboard.layout_variant = ""
            self._variant_label.hide()
            self._variant_combo.hide()

        # Afficher/masquer le combo OLED selon les capacités
        if kb.capabilities.get("oled", False):
            default_sides = ["left", "right"]
            default_idx = next(
                i for i, (s, _) in enumerate(_OLED_SIDES_OPTIONS) if s == default_sides
            )
            self._oled_combo.blockSignals(True)
            self._oled_combo.setCurrentIndex(default_idx)
            self._oled_combo.blockSignals(False)
            self._model.keyboard.oled_sides = default_sides
            self._oled_label.show()
            self._oled_combo.show()
        else:
            self._model.keyboard.oled_sides = []
            self._oled_label.hide()
            self._oled_combo.hide()

        # Initialiser la checkbox RGB depuis la capability YAML du clavier
        self._rgb_checkbox.blockSignals(True)
        self._rgb_checkbox.setChecked(kb.capabilities.get("rgb", False))
        self._rgb_checkbox.blockSignals(False)
        self._model.keyboard.rgb_enabled = kb.capabilities.get("rgb", False)

        # Notifier MainWindow des capacités du clavier sélectionné (FR3, FR4)
        # La checkbox vient d'être réinitialisée depuis le YAML — isChecked() == capabilities["rgb"]
        # set_rgb_enabled() surviendra ensuite si le projet sauvegardé override cette valeur
        self.capabilities_changed.emit({**kb.capabilities, "rgb": self._rgb_checkbox.isChecked()})
        self.oled_sides_changed.emit(list(self._model.keyboard.oled_sides))

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

    def _on_variant_changed(self, index: int) -> None:
        """Met à jour ProjectModel quand la variante layout change."""
        kb_index = self._keyboard_combo.currentIndex()
        if kb_index < 0 or kb_index >= len(self._keyboards):
            return
        kb = self._keyboards[kb_index]
        if 0 <= index < len(kb.layout_variants):
            self._model.keyboard.layout_variant = kb.layout_variants[index].slug

    def _on_oled_changed(self, index: int) -> None:
        """Met à jour ProjectModel et émet oled_sides_changed quand le combo OLED change."""
        if 0 <= index < len(_OLED_SIDES_OPTIONS):
            sides, _ = _OLED_SIDES_OPTIONS[index]
            self._model.keyboard.oled_sides = list(sides)
            self.oled_sides_changed.emit(list(sides))

    def _on_rgb_changed(self, state: int) -> None:
        """Met à jour ProjectModel et émet capabilities_changed quand la checkbox RGB change."""
        enabled = bool(state)
        self._model.keyboard.rgb_enabled = enabled
        kb_index = self._keyboard_combo.currentIndex()
        if 0 <= kb_index < len(self._keyboards):
            kb = self._keyboards[kb_index]
            self.capabilities_changed.emit({**kb.capabilities, "rgb": enabled})

    def set_layout_variant(self, variant_slug: str) -> None:
        """API publique pour restaurer la variante depuis un projet sauvegardé."""
        kb_index = self._keyboard_combo.currentIndex()
        if kb_index < 0 or kb_index >= len(self._keyboards):
            return
        kb = self._keyboards[kb_index]
        idx = next(
            (i for i, v in enumerate(kb.layout_variants) if v.slug == variant_slug), 0
        )
        resolved_slug = kb.layout_variants[idx].slug if kb.layout_variants else ""
        self._variant_combo.blockSignals(True)
        self._variant_combo.setCurrentIndex(idx)
        self._variant_combo.blockSignals(False)
        self._model.keyboard.layout_variant = resolved_slug

    def set_oled_sides(self, sides: list[str]) -> None:
        """API publique pour restaurer la sélection OLED depuis un projet sauvegardé."""
        idx = next(
            (i for i, (s, _) in enumerate(_OLED_SIDES_OPTIONS) if s == sides),
            len(_OLED_SIDES_OPTIONS) - 1,
        )
        self._oled_combo.blockSignals(True)
        self._oled_combo.setCurrentIndex(idx)
        self._oled_combo.blockSignals(False)
        self._model.keyboard.oled_sides = list(sides)
        self.oled_sides_changed.emit(list(sides))

    def _open_custom_editor(self) -> None:
        """Ouvre le dialog d'édition de clavier custom."""
        from modules.keyboard_editor.dialog import CustomKeyboardEditorDialog
        dlg = CustomKeyboardEditorDialog(list(self._keyboards), parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.saved_model_id:
            self._reload_keyboards(dlg.saved_model_id)

    def _reload_keyboards(self, select_model: str = "") -> None:
        """Recharge la liste des claviers (prédéfinis + custom) et sélectionne select_model."""
        self._keyboards = load_all_keyboards(KEYBOARDS_DIR, CUSTOM_KEYBOARDS_DIR)
        self._keyboard_combo.blockSignals(True)
        self._keyboard_combo.clear()
        for kb in self._keyboards:
            self._keyboard_combo.addItem(kb.display_name)
            idx = self._keyboard_combo.count() - 1
            self._keyboard_combo.setItemData(idx, kb.description, Qt.ItemDataRole.ToolTipRole)
        self._keyboard_combo.blockSignals(False)
        target_idx = next(
            (i for i, kb in enumerate(self._keyboards) if kb.model == select_model), 0
        )
        self._keyboard_combo.setCurrentIndex(target_idx)
        self._on_model_changed(target_idx)

    def set_rgb_enabled(self, value: bool) -> None:
        """API publique pour restaurer l'état RGB depuis un projet sauvegardé."""
        current = self._rgb_checkbox.isChecked()
        self._rgb_checkbox.blockSignals(True)
        self._rgb_checkbox.setChecked(value)
        self._rgb_checkbox.blockSignals(False)
        self._model.keyboard.rgb_enabled = value
        # N'emettre que si la valeur change pour eviter un double refresh_layout()
        if value != current:
            kb_index = self._keyboard_combo.currentIndex()
            if 0 <= kb_index < len(self._keyboards):
                kb = self._keyboards[kb_index]
                self.capabilities_changed.emit({**kb.capabilities, "rgb": value})
