"""HardwareWidget — onglet "Matériel" de l'application.

Permet à l'utilisateur de sélectionner son modèle de clavier et son MCU
depuis des listes peuplées par les fichiers YAML dans `keyboards/`.
Deux parcours : Compatible Vial (620+ claviers indexés) ou Custom (import KLE).
"""
from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from config import KEYBOARDS_DIR
from i18n import tr
from models.project_model import ProjectModel
from modules.hardware.keyboard_loader import KeyboardDefinition, load_all_keyboards
from modules.hardware.vialqmk_scanner import (
    CATEGORY_SPLIT,
    VialKeyboardEntry,
    categorize_keyboard,
    count_keys_from_keymap,
    load_vial_keyboard,
    scan_vial_keyboards,
)
from modules.keyboard_editor.dialog import KleImportWidget

CUSTOM_KEYBOARDS_DIR: Path = Path.home() / ".keyboard_firmware_maker" / "custom_keyboards"
VIAL_QMK_DIR: Path = Path.home() / ".keyboard_firmware_maker" / "vial-qmk"

logger = logging.getLogger(__name__)

_OLED_SIDES_OPTIONS: list[tuple[list[str], str]] = [
    ([], "hardware.oled.none"),
    (["left"], "hardware.oled.left_only"),
    (["right"], "hardware.oled.right_only"),
    (["left", "right"], "hardware.oled.both"),
]

# Ordre d'affichage des catégories dans le combo
_CATEGORY_ORDER = [
    "all", "split", "macropad", "40pct", "60pct", "75pct", "tkl", "fullsize",
]


def _categorize_bundled(kb: KeyboardDefinition) -> str:
    """Détermine la catégorie d'un clavier bundled YAML."""
    key_count = 0
    # Compter depuis layout (left/right/keys)
    for side_keys in kb.layout.values():
        if isinstance(side_keys, list):
            key_count += len(side_keys)
    # Si layout vide, compter depuis la première layout_variant
    if key_count == 0 and kb.layout_variants:
        key_count = len(kb.layout_variants[0].keys)
    return categorize_keyboard(key_count, kb.split)


class HardwareWidget(QWidget):
    """Widget de sélection du matériel avec deux parcours : Compatible et Custom.

    Charge les définitions depuis les fichiers YAML dans `keyboards/`
    et l'index vial-qmk depuis le cache.
    """

    capabilities_changed = Signal(dict)  # {"oled": bool, "rgb": bool}
    oled_sides_changed = Signal(list)

    def __init__(self, model: ProjectModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._model = model
        self._keyboards: list[KeyboardDefinition] = load_all_keyboards(KEYBOARDS_DIR, CUSTOM_KEYBOARDS_DIR)
        self._vial_index: list[VialKeyboardEntry] = []
        if VIAL_QMK_DIR.is_dir():
            self._vial_index = scan_vial_keyboards(VIAL_QMK_DIR)
        # Liste combinée : bundled + vial chargés dynamiquement
        self._all_keyboard_entries: list[tuple[KeyboardDefinition | None, VialKeyboardEntry | None, str]] = []
        self._filtered_entries: list[int] = []  # indices dans _all_keyboard_entries
        self._setup_ui()
        self._connect_signals()
        # Initialise le ProjectModel avec la sélection par défaut
        if self._keyboards:
            self._on_model_changed(0)

    # ── Setup UI ─────────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(8, 8, 8, 8)

        # Page stack : 0 = choix, 1 = compatible, 2 = custom
        self._stack = QStackedWidget()
        main_layout.addWidget(self._stack)

        self._stack.addWidget(self._build_choice_page())      # page 0
        self._stack.addWidget(self._build_compatible_page())   # page 1
        self._stack.addWidget(self._build_custom_page())       # page 2

    def _build_choice_page(self) -> QWidget:
        """Page 0 : deux cartes de choix Compatible / Custom."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 40, 20, 20)

        title = QLabel(tr("hardware.step1"))
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 20px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(20)

        # Carte Compatible
        self._card_compatible = self._make_choice_card(
            tr("hardware.choice.compatible"),
            tr("hardware.choice.compatible_desc"),
            "#2E7D32",
        )
        self._card_compatible.setObjectName("card_compatible")
        cards_layout.addWidget(self._card_compatible)

        # Carte Custom
        self._card_custom = self._make_choice_card(
            tr("hardware.choice.custom"),
            tr("hardware.choice.custom_desc"),
            "#1565C0",
        )
        self._card_custom.setObjectName("card_custom")
        cards_layout.addWidget(self._card_custom)

        layout.addLayout(cards_layout)
        layout.addStretch()
        return page

    def _make_choice_card(self, title: str, desc: str, color: str) -> QPushButton:
        """Crée un bouton-carte de choix stylisé."""
        btn = QPushButton(f"{title}\n\n{desc}")
        btn.setMinimumSize(300, 160)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: 2px solid {color};
                border-radius: 12px;
                padding: 20px;
                font-size: 14px;
                text-align: center;
            }}
            QPushButton:hover {{
                background-color: {color}CC;
                border-color: white;
            }}
        """)
        return btn

    def _build_compatible_page(self) -> QWidget:
        """Page 1 : sélection parmi les claviers compatibles Vial."""
        page = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(12)
        layout.setContentsMargins(4, 4, 4, 4)

        # Bouton retour
        self._back_btn_compat = QPushButton(tr("hardware.choice.back"))
        self._back_btn_compat.setObjectName("back_btn_compat")
        self._back_btn_compat.setMaximumWidth(200)
        layout.addWidget(self._back_btn_compat)

        # ── Étape 1 : Catégorie ──────────────────────────────────────────
        step1_label = QLabel(tr("hardware.step1"))
        step1_label.setStyleSheet("font-size: 14px; font-weight: bold; margin-top: 8px;")
        layout.addWidget(step1_label)

        self._category_combo = QComboBox()
        self._category_combo.setObjectName("category_combo")
        # Peupler les catégories disponibles
        available_cats: set[str] = set()
        for entry in self._vial_index:
            if entry.category:
                available_cats.add(entry.category)
        for kb in self._keyboards:
            available_cats.add(_categorize_bundled(kb))

        for cat_id in _CATEGORY_ORDER:
            if cat_id == "all" or cat_id in available_cats:
                self._category_combo.addItem(
                    tr(f"hardware.category.{cat_id}"), cat_id
                )
        layout.addWidget(self._category_combo)

        # ── Étape 2 : Clavier ────────────────────────────────────────────
        step2_label = QLabel(tr("hardware.step2"))
        step2_label.setStyleSheet("font-size: 14px; font-weight: bold; margin-top: 8px;")
        layout.addWidget(step2_label)

        self._keyboard_combo = QComboBox()
        self._keyboard_combo.setObjectName("keyboard_combo")
        self._keyboard_combo.setMaxVisibleItems(20)
        layout.addWidget(self._keyboard_combo)

        # ── Étape 3 : Options ────────────────────────────────────────────
        step3_label = QLabel(tr("hardware.step3"))
        step3_label.setStyleSheet("font-size: 14px; font-weight: bold; margin-top: 8px;")
        layout.addWidget(step3_label)

        options_form = QFormLayout()
        options_form.setSpacing(8)

        # MCU
        self._mcu_combo = QComboBox()
        self._mcu_combo.setObjectName("mcu_combo")
        options_form.addRow(QLabel(tr("hardware.mcu")), self._mcu_combo)

        # Variante layout
        self._variant_label = QLabel(tr("hardware.layout_variant"))
        self._variant_combo = QComboBox()
        self._variant_combo.setObjectName("variant_combo")
        options_form.addRow(self._variant_label, self._variant_combo)
        self._variant_label.hide()
        self._variant_combo.hide()

        # OLED
        self._oled_label = QLabel(tr("hardware.oled"))
        self._oled_combo = QComboBox()
        self._oled_combo.setObjectName("oled_combo")
        for _sides, key in _OLED_SIDES_OPTIONS:
            self._oled_combo.addItem(tr(key))
        options_form.addRow(self._oled_label, self._oled_combo)
        self._oled_label.hide()
        self._oled_combo.hide()

        # RGB
        self._rgb_checkbox = QCheckBox()
        self._rgb_checkbox.setObjectName("rgb_checkbox")
        options_form.addRow(QLabel(tr("hardware.rgb")), self._rgb_checkbox)

        layout.addLayout(options_form)
        layout.addStretch()

        scroll.setWidget(content)
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.addWidget(scroll)
        return page

    def _build_custom_page(self) -> QWidget:
        """Page 2 : import KLE + config hardware (absorbe l'ancien onglet KLE)."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)

        # Bouton retour
        self._back_btn_custom = QPushButton(tr("hardware.choice.back"))
        self._back_btn_custom.setObjectName("back_btn_custom")
        self._back_btn_custom.setMaximumWidth(200)
        layout.addWidget(self._back_btn_custom)

        # KleImportWidget intégré
        self._kle_widget = KleImportWidget(list(self._keyboards))
        layout.addWidget(self._kle_widget)

        return page

    # ── Populate keyboard combo ──────────────────────────────────────────────

    def _populate_keyboard_combo(self) -> None:
        """Remplit le combo clavier selon la catégorie sélectionnée."""
        cat_idx = self._category_combo.currentIndex()
        selected_cat = self._category_combo.itemData(cat_idx) if cat_idx >= 0 else "all"

        self._keyboard_combo.blockSignals(True)
        self._keyboard_combo.clear()
        self._all_keyboard_entries.clear()
        self._filtered_entries.clear()

        # 1. Ajouter les claviers bundled YAML
        for kb in self._keyboards:
            cat = _categorize_bundled(kb)
            self._all_keyboard_entries.append((kb, None, cat))

        # 2. Ajouter les claviers vial-qmk (éviter les doublons avec bundled)
        bundled_vial_paths = {
            kb.vial_qmk_keyboard for kb in self._keyboards if kb.vial_qmk_keyboard
        }
        for entry in self._vial_index:
            if entry.qmk_path not in bundled_vial_paths:
                self._all_keyboard_entries.append((None, entry, entry.category))

        # 3. Filtrer par catégorie
        for i, (kb, entry, cat) in enumerate(self._all_keyboard_entries):
            if selected_cat == "all" or cat == selected_cat:
                self._filtered_entries.append(i)
                name = kb.display_name if kb else entry.name
                suffix = f"  [{entry.qmk_path}]" if entry and not kb else ""
                self._keyboard_combo.addItem(f"{name}{suffix}")

        self._keyboard_combo.blockSignals(False)

        # Sélectionner le premier
        if self._filtered_entries:
            self._keyboard_combo.setCurrentIndex(0)
            self._on_keyboard_selected(0)

    # ── Signals ──────────────────────────────────────────────────────────────

    def _connect_signals(self) -> None:
        self._card_compatible.clicked.connect(lambda: self._switch_to_page(1))
        self._card_custom.clicked.connect(lambda: self._switch_to_page(2))
        self._back_btn_compat.clicked.connect(lambda: self._switch_to_page(0))
        self._back_btn_custom.clicked.connect(lambda: self._switch_to_page(0))

        self._category_combo.currentIndexChanged.connect(self._on_category_changed)
        self._keyboard_combo.currentIndexChanged.connect(self._on_keyboard_selected)
        self._mcu_combo.currentIndexChanged.connect(self._on_mcu_changed)
        self._variant_combo.currentIndexChanged.connect(self._on_variant_changed)
        self._oled_combo.currentIndexChanged.connect(self._on_oled_changed)
        self._rgb_checkbox.stateChanged.connect(self._on_rgb_changed)

        self._kle_widget.keyboard_saved.connect(self._on_custom_keyboard_saved)

        # Peupler le combo initial
        self._populate_keyboard_combo()

    def _switch_to_page(self, page_index: int) -> None:
        self._stack.setCurrentIndex(page_index)

    # ── Handlers ─────────────────────────────────────────────────────────────

    def _on_category_changed(self, _index: int) -> None:
        self._populate_keyboard_combo()

    def _on_keyboard_selected(self, combo_index: int) -> None:
        """Met à jour MCU/options quand le clavier change dans le combo."""
        if combo_index < 0 or combo_index >= len(self._filtered_entries):
            return

        entry_idx = self._filtered_entries[combo_index]
        kb, vial_entry, _cat = self._all_keyboard_entries[entry_idx]

        # Si c'est un clavier vial-qmk non encore chargé, le charger
        if kb is None and vial_entry is not None:
            kb = load_vial_keyboard(vial_entry)
            self._all_keyboard_entries[entry_idx] = (kb, vial_entry, _cat)
            # Ajouter à la liste des keyboards chargés
            if kb not in self._keyboards:
                self._keyboards.append(kb)
            logger.info("Clavier vial-qmk chargé : %s", kb.display_name)

        if kb is None:
            return

        self._current_kb = kb
        self._model.keyboard.model = kb.model
        logger.info("Clavier sélectionné : %s (%s)", kb.display_name, kb.model)

        # Re-peupler MCU
        self._mcu_combo.blockSignals(True)
        self._mcu_combo.clear()
        for mcu in kb.mcu_options:
            self._mcu_combo.addItem(mcu.display_name)
            idx = self._mcu_combo.count() - 1
            self._mcu_combo.setItemData(idx, mcu.description, Qt.ItemDataRole.ToolTipRole)
        self._mcu_combo.blockSignals(False)

        if kb.mcu_options:
            self._model.keyboard.mcu = kb.mcu_options[0].id

        # Variantes
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

        # OLED
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

        # RGB
        self._rgb_checkbox.blockSignals(True)
        self._rgb_checkbox.setChecked(kb.capabilities.get("rgb", False))
        self._rgb_checkbox.blockSignals(False)
        self._model.keyboard.rgb_enabled = kb.capabilities.get("rgb", False)

        self.capabilities_changed.emit({**kb.capabilities, "rgb": self._rgb_checkbox.isChecked()})
        self.oled_sides_changed.emit(list(self._model.keyboard.oled_sides))

    # Alias pour compatibilité avec MainWindow._sync_hardware_widget
    def _on_model_changed(self, index: int) -> None:
        """Compatibilité : sélectionne le clavier bundled par index direct."""
        if index < 0 or index >= len(self._keyboards):
            return
        target_model = self._keyboards[index].model
        # Trouver dans le combo filtré
        for combo_idx, entry_idx in enumerate(self._filtered_entries):
            kb, _, _ = self._all_keyboard_entries[entry_idx]
            if kb and kb.model == target_model:
                self._keyboard_combo.setCurrentIndex(combo_idx)
                return
        # Si pas trouvé dans la catégorie filtrée, passer à "all"
        self._category_combo.setCurrentIndex(0)  # "all"
        for combo_idx, entry_idx in enumerate(self._filtered_entries):
            kb, _, _ = self._all_keyboard_entries[entry_idx]
            if kb and kb.model == target_model:
                self._keyboard_combo.setCurrentIndex(combo_idx)
                return

    def _on_mcu_changed(self, index: int) -> None:
        kb = getattr(self, "_current_kb", None)
        if kb is None:
            return
        if index < 0 or index >= len(kb.mcu_options):
            return
        mcu = kb.mcu_options[index]
        self._model.keyboard.mcu = mcu.id

    def _on_variant_changed(self, index: int) -> None:
        kb = getattr(self, "_current_kb", None)
        if kb is None:
            return
        if 0 <= index < len(kb.layout_variants):
            self._model.keyboard.layout_variant = kb.layout_variants[index].slug

    def _on_oled_changed(self, index: int) -> None:
        if 0 <= index < len(_OLED_SIDES_OPTIONS):
            sides, _ = _OLED_SIDES_OPTIONS[index]
            self._model.keyboard.oled_sides = list(sides)
            self.oled_sides_changed.emit(list(sides))

    def _on_rgb_changed(self, state: int) -> None:
        enabled = bool(state)
        self._model.keyboard.rgb_enabled = enabled
        kb = getattr(self, "_current_kb", None)
        if kb:
            self.capabilities_changed.emit({**kb.capabilities, "rgb": enabled})

    def _on_custom_keyboard_saved(self, model_id: str) -> None:
        """Après sauvegarde d'un clavier custom, recharger et sélectionner."""
        self._reload_keyboards(model_id)
        self._kle_widget.update_keyboards(list(self._keyboards))
        self._switch_to_page(1)  # Retour à la page Compatible pour voir le nouveau clavier

    # ── API publique ─────────────────────────────────────────────────────────

    def set_layout_variant(self, variant_slug: str) -> None:
        """Restaure la variante depuis un projet sauvegardé."""
        kb = getattr(self, "_current_kb", None)
        if kb is None:
            return
        idx = next(
            (i for i, v in enumerate(kb.layout_variants) if v.slug == variant_slug), 0
        )
        resolved_slug = kb.layout_variants[idx].slug if kb.layout_variants else ""
        self._variant_combo.blockSignals(True)
        self._variant_combo.setCurrentIndex(idx)
        self._variant_combo.blockSignals(False)
        self._model.keyboard.layout_variant = resolved_slug

    def set_oled_sides(self, sides: list[str]) -> None:
        """Restaure la sélection OLED depuis un projet sauvegardé."""
        idx = next(
            (i for i, (s, _) in enumerate(_OLED_SIDES_OPTIONS) if s == sides),
            len(_OLED_SIDES_OPTIONS) - 1,
        )
        self._oled_combo.blockSignals(True)
        self._oled_combo.setCurrentIndex(idx)
        self._oled_combo.blockSignals(False)
        self._model.keyboard.oled_sides = list(sides)
        self.oled_sides_changed.emit(list(sides))

    def set_rgb_enabled(self, value: bool) -> None:
        """Restaure l'état RGB depuis un projet sauvegardé."""
        current = self._rgb_checkbox.isChecked()
        self._rgb_checkbox.blockSignals(True)
        self._rgb_checkbox.setChecked(value)
        self._rgb_checkbox.blockSignals(False)
        self._model.keyboard.rgb_enabled = value
        if value != current:
            kb = getattr(self, "_current_kb", None)
            if kb:
                self.capabilities_changed.emit({**kb.capabilities, "rgb": value})

    def _reload_keyboards(self, select_model: str = "") -> None:
        """Recharge la liste des claviers (prédéfinis + custom) et sélectionne select_model."""
        self._keyboards = load_all_keyboards(KEYBOARDS_DIR, CUSTOM_KEYBOARDS_DIR)
        self._populate_keyboard_combo()
        if select_model:
            for combo_idx, entry_idx in enumerate(self._filtered_entries):
                kb, _, _ = self._all_keyboard_entries[entry_idx]
                if kb and kb.model == select_model:
                    self._keyboard_combo.setCurrentIndex(combo_idx)
                    return
