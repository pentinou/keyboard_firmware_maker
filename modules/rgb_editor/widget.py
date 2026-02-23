"""RgbWidget — onglet de personnalisation RGB.

Affiche un layout visuel split du clavier (gauche/droite) avec des touches cliquables
pour assigner des couleurs par touche (FR11), et une section effets RGB (FR12-FR14).
"""
from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QHideEvent, QShowEvent
from PySide6.QtWidgets import (
    QColorDialog,
    QComboBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from models.project_model import ProjectModel, RgbEffect
from modules.hardware.keyboard_loader import KeyboardDefinition, load_all_keyboards
from modules.rgb_editor.effect_preview import EffectPreview
from modules.rgb_editor.effects import EFFECT_TYPES

logger = logging.getLogger(__name__)

KEYBOARDS_DIR = Path(__file__).parent.parent.parent / "keyboards"
KEY_SIZE = 36  # px

# Index dans EFFECT_TYPES
_EFFECT_IDS = [et[0] for et in EFFECT_TYPES]


class RgbWidget(QWidget):
    """Widget de l'onglet RGB.

    Contient :
    - Un layout visuel split du clavier (touches colorées par click + QColorDialog)
    - Une section effets RGB (QComboBox + paramètres dynamiques)
    """

    def __init__(self, model: ProjectModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._model = model
        self._key_buttons: dict[str, QPushButton] = {}
        self._trigger_mode: bool = False
        self._setup_ui()
        self._build_layout()
        self._preview = EffectPreview(self._key_buttons)
        self._sync_from_model()

    # ──────────────────────────────────────────────────── Qt events ──

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        if self._preview and self._model.rgb.effects:
            self._preview.start(self._model.rgb.effects[0])

    def hideEvent(self, event: QHideEvent) -> None:
        super().hideEvent(event)
        if self._preview:
            self._preview.stop()
        # M2: restaurer les couleurs per-key après arrêt du preview
        for key_id, hex_color in self._model.rgb.per_key.items():
            self._apply_color(key_id, hex_color)

    # ─────────────────────────────────────────────────────────── UI setup ──

    def _setup_ui(self) -> None:
        outer = QVBoxLayout(self)

        # Section touches
        key_label = QLabel("Couleurs par touche — cliquez une touche pour assigner une couleur")
        key_label.setObjectName("rgb_instructions")
        outer.addWidget(key_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("rgb_scroll")
        container = QWidget()
        self._keys_hbox = QHBoxLayout(container)
        self._keys_hbox.setAlignment(Qt.AlignmentFlag.AlignLeft)
        scroll.setWidget(container)
        outer.addWidget(scroll)

        # Section effets
        effects_group = QGroupBox("Effets RGB")
        effects_group.setObjectName("effects_group")
        effects_layout = QVBoxLayout(effects_group)

        # Combo sélection effet
        combo_row = QHBoxLayout()
        combo_row.addWidget(QLabel("Type d'effet :"))
        self._effect_combo = QComboBox()
        self._effect_combo.setObjectName("effect_combo")
        for _, display in EFFECT_TYPES:
            self._effect_combo.addItem(display)
        self._effect_combo.currentIndexChanged.connect(self._on_effect_type_changed)
        combo_row.addWidget(self._effect_combo)
        combo_row.addStretch()
        effects_layout.addLayout(combo_row)

        # Panneau dynamique (QStackedWidget)
        self._effect_stack = QStackedWidget()
        self._effect_stack.setObjectName("effect_stack")
        self._effect_stack.addWidget(self._build_static_panel())   # index 0
        self._effect_stack.addWidget(self._build_ripple_panel())   # index 1
        effects_layout.addWidget(self._effect_stack)

        outer.addWidget(effects_group)
        outer.addStretch()

    def _build_static_panel(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName("static_panel")
        layout = QHBoxLayout(panel)
        layout.addWidget(QLabel("Couleur uniforme :"))
        self._btn_static_color = QPushButton()
        self._btn_static_color.setObjectName("btn_color_primary")
        self._btn_static_color.setFixedSize(32, 24)
        self._btn_static_color.setToolTip("Cliquer pour choisir la couleur")
        self._btn_static_color.clicked.connect(self._on_color_primary_clicked)
        layout.addWidget(self._btn_static_color)
        layout.addStretch()
        return panel

    def _build_ripple_panel(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName("ripple_panel")
        layout = QVBoxLayout(panel)

        # Couleur primaire
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Couleur touche pressée :"))
        self._btn_ripple_primary = QPushButton()
        self._btn_ripple_primary.setObjectName("btn_ripple_primary")
        self._btn_ripple_primary.setFixedSize(32, 24)
        self._btn_ripple_primary.clicked.connect(self._on_color_primary_clicked)
        row1.addWidget(self._btn_ripple_primary)
        row1.addStretch()
        layout.addLayout(row1)

        # Couleur secondaire
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Couleur touches voisines :"))
        self._btn_color_secondary = QPushButton()
        self._btn_color_secondary.setObjectName("btn_color_secondary")
        self._btn_color_secondary.setFixedSize(32, 24)
        self._btn_color_secondary.clicked.connect(self._on_color_secondary_clicked)
        row2.addWidget(self._btn_color_secondary)
        row2.addStretch()
        layout.addLayout(row2)

        # Fade ms
        row3 = QHBoxLayout()
        row3.addWidget(QLabel("Vitesse de fondu (ms) :"))
        self._fade_ms_spin = QSpinBox()
        self._fade_ms_spin.setObjectName("fade_ms_spin")
        self._fade_ms_spin.setRange(50, 5000)
        self._fade_ms_spin.setValue(500)
        self._fade_ms_spin.setSingleStep(50)
        self._fade_ms_spin.valueChanged.connect(self._on_fade_ms_changed)
        row3.addWidget(self._fade_ms_spin)
        row3.addStretch()
        layout.addLayout(row3)

        # Touche déclencheur
        row4 = QHBoxLayout()
        self._btn_trigger = QPushButton("Choisir touche déclencheur")
        self._btn_trigger.setObjectName("btn_trigger")
        self._btn_trigger.clicked.connect(self._on_trigger_clicked)
        self._lbl_trigger = QLabel("Non défini")
        self._lbl_trigger.setObjectName("lbl_trigger")
        row4.addWidget(self._btn_trigger)
        row4.addWidget(self._lbl_trigger)
        row4.addStretch()
        layout.addLayout(row4)

        return panel

    # ────────────────────────────────────────────────────── Key layout ──

    def _build_layout(self) -> None:
        for btn in self._key_buttons.values():
            btn.setParent(None)  # type: ignore[arg-type]
        self._key_buttons.clear()
        while self._keys_hbox.count():
            item = self._keys_hbox.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

        kb = self._find_current_keyboard()
        rows = kb.matrix.get("rows", 5) if kb else 5
        cols = kb.matrix.get("cols", 6) if kb else 6

        for side in ("L", "R"):
            frame = QFrame()
            frame.setFrameShape(QFrame.Shape.StyledPanel)
            frame.setObjectName(f"frame_{side}")
            grid = QGridLayout(frame)
            grid.setSpacing(2)
            for r in range(rows):
                for c in range(cols):
                    key_id = f"{side}_r{r}_c{c}"
                    btn = QPushButton()
                    btn.setFixedSize(KEY_SIZE, KEY_SIZE)
                    btn.setObjectName(key_id)
                    btn.setToolTip(key_id)
                    btn.clicked.connect(
                        lambda checked=False, kid=key_id: self._on_key_clicked(kid)
                    )
                    grid.addWidget(btn, r, c)
                    self._key_buttons[key_id] = btn
            self._keys_hbox.addWidget(frame)
            self._keys_hbox.addSpacing(16)

    def _find_current_keyboard(self) -> KeyboardDefinition | None:
        keyboards = load_all_keyboards(KEYBOARDS_DIR)
        return next((kb for kb in keyboards if kb.model == self._model.keyboard.model), None)

    # ────────────────────────────────────────────────── Key click handlers ──

    def _on_key_clicked(self, key_id: str) -> None:
        if self._trigger_mode:
            if self._model.rgb.effects:
                # M2: label et log uniquement si le modèle est bien mis à jour
                self._model.rgb.effects[0].trigger_key = key_id
                self._lbl_trigger.setText(key_id)
                logger.info("Touche déclencheur définie : %s", key_id)
            self._trigger_mode = False
            self._btn_trigger.setText("Choisir touche déclencheur")
            return
        current = QColor(self._model.rgb.per_key.get(key_id, "#FFFFFF"))
        color = QColorDialog.getColor(current, self, f"Couleur pour {key_id}")
        if color.isValid():
            hex_color = color.name().upper()
            self._apply_color(key_id, hex_color)

    def _apply_color(self, key_id: str, hex_color: str) -> None:
        btn = self._key_buttons.get(key_id)
        if btn:
            btn.setStyleSheet(f"background-color: {hex_color};")
            self._model.rgb.per_key[key_id] = hex_color
        else:
            logger.warning("Clé inconnue '%s' ignorée dans _apply_color", key_id)

    # ──────────────────────────────────────────────── Effect handlers ──

    def _ensure_effect(self, type_id: str) -> RgbEffect:
        """Retourne l'effet courant (index 0) ou en crée un nouveau."""
        if not self._model.rgb.effects:
            self._model.rgb.effects = [RgbEffect(type=type_id)]
        return self._model.rgb.effects[0]

    def _on_effect_type_changed(self, index: int) -> None:
        if index < 0 or index >= len(EFFECT_TYPES):
            return
        # M1: quitter le mode trigger si actif lors du changement d'effet
        if self._trigger_mode:
            self._trigger_mode = False
            self._btn_trigger.setText("Choisir touche déclencheur")
        effect_id = EFFECT_TYPES[index][0]
        effect = self._ensure_effect(effect_id)
        effect.type = effect_id
        self._effect_stack.setCurrentIndex(index)
        self._refresh_effect_buttons()
        self._update_preview()
        logger.info("Effet RGB changé : %s", effect_id)

    def _on_color_primary_clicked(self) -> None:
        effect = self._ensure_effect(_EFFECT_IDS[self._effect_combo.currentIndex()])
        current = QColor(effect.color_primary)
        color = QColorDialog.getColor(current, self, "Couleur principale")
        if color.isValid():
            effect.color_primary = color.name().upper()
            self._refresh_effect_buttons()
            self._update_preview()

    def _on_color_secondary_clicked(self) -> None:
        effect = self._ensure_effect(_EFFECT_IDS[self._effect_combo.currentIndex()])
        current = QColor(effect.color_secondary)
        color = QColorDialog.getColor(current, self, "Couleur secondaire")
        if color.isValid():
            effect.color_secondary = color.name().upper()
            self._refresh_effect_buttons()
            self._update_preview()

    def _update_preview(self) -> None:
        """Met à jour l'aperçu animé si un effet est configuré."""
        if self._preview and self._model.rgb.effects:
            self._preview.update(self._model.rgb.effects[0])

    def _on_fade_ms_changed(self, value: int) -> None:
        if self._model.rgb.effects:
            self._model.rgb.effects[0].fade_ms = value

    def _on_trigger_clicked(self) -> None:
        self._trigger_mode = True
        self._btn_trigger.setText("Cliquez une touche…")

    def _refresh_effect_buttons(self) -> None:
        """Met à jour les couleurs affichées sur les boutons de couleur."""
        if not self._model.rgb.effects:
            return
        effect = self._model.rgb.effects[0]
        primary_style = f"background-color: {effect.color_primary};"
        self._btn_static_color.setStyleSheet(primary_style)
        self._btn_ripple_primary.setStyleSheet(primary_style)
        self._btn_color_secondary.setStyleSheet(f"background-color: {effect.color_secondary};")

    # ────────────────────────────────────────────────────── Sync / Refresh ──

    def _sync_from_model(self) -> None:
        """Restaure les couleurs touches et l'état effets depuis le modèle."""
        for key_id, hex_color in self._model.rgb.per_key.items():
            self._apply_color(key_id, hex_color)
        if self._model.rgb.effects:
            effect = self._model.rgb.effects[0]
            # Combo effet
            try:
                idx = _EFFECT_IDS.index(effect.type)
            except ValueError:
                logger.warning("Type d'effet inconnu '%s' — retour à static", effect.type)
                idx = 0
            self._effect_combo.blockSignals(True)
            self._effect_combo.setCurrentIndex(idx)
            self._effect_combo.blockSignals(False)
            self._effect_stack.setCurrentIndex(idx)
            # Spinbox fade_ms
            self._fade_ms_spin.blockSignals(True)
            self._fade_ms_spin.setValue(effect.fade_ms)
            self._fade_ms_spin.blockSignals(False)
            # Trigger key label
            if effect.trigger_key:
                self._lbl_trigger.setText(effect.trigger_key)
            self._refresh_effect_buttons()

    def refresh_layout(self) -> None:
        """Reconstruit le layout quand le modèle de clavier change."""
        if self._preview:  # M1: arrêter l'ancien timer avant remplacement
            self._preview.stop()
        self._build_layout()
        self._preview = EffectPreview(self._key_buttons)
        self._sync_from_model()
