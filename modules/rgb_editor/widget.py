"""RgbWidget — onglet de personnalisation RGB.

Affiche un layout visuel split du clavier (gauche/droite) avec des touches cliquables
pour assigner des couleurs par touche (FR11), et une section effets RGB (FR12-FR14).
"""
from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QHideEvent, QPen, QShowEvent
from PySide6.QtWidgets import (
    QColorDialog,
    QFrame,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsView,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from i18n import tr
from models.project_model import ProjectModel, RgbEffect
from modules.hardware.keyboard_loader import KeyboardDefinition, KeyLayout, load_all_keyboards
from modules.rgb_editor.effect_preview import EffectPreview
from modules.rgb_editor.effects import EFFECT_TYPES

logger = logging.getLogger(__name__)

KEYBOARDS_DIR = Path(__file__).parent.parent.parent / "keyboards"
CUSTOM_KEYBOARDS_DIR = Path.home() / ".keyboard_firmware_maker" / "custom_keyboards"
KEY_SIZE = 36  # px


class KeyColorItem(QGraphicsRectItem):
    """Touche cliquable pour l'onglet RGB — supporte taille réelle et rotation."""

    def __init__(
        self,
        key_id: str,
        w_u: float,
        h_u: float,
        r_deg: float,
        on_click,
    ) -> None:
        w_px = w_u * KEY_SIZE - 2
        h_px = h_u * KEY_SIZE - 2
        super().__init__(0, 0, w_px, h_px)
        self.key_id = key_id
        self._on_click = on_click
        self.setTransformOriginPoint(w_px / 2, h_px / 2)
        if r_deg:
            self.setRotation(r_deg)
        self.setBrush(QBrush(QColor("#333333")))
        self.setPen(QPen(QColor("#555555"), 1))
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)

    def set_color(self, hex_color: str) -> None:
        self.setBrush(QBrush(QColor(hex_color)))
        self.update()

    def mousePressEvent(self, event) -> None:
        self._on_click(self.key_id)
        super().mousePressEvent(event)

# Index dans EFFECT_TYPES
_EFFECT_IDS = [e.id for e in EFFECT_TYPES]


def _stack_page_for(effect_id: str) -> int:
    """Retourne l'index de page du stack pour un effet donné."""
    if effect_id == "static":
        return 0
    if effect_id == "ripple":
        return 2
    return 1


class RgbWidget(QWidget):
    """Widget de l'onglet RGB.

    Contient :
    - Un layout visuel split du clavier (touches colorées par click + QColorDialog)
    - Une section effets RGB (QListWidget + description + paramètres dynamiques)
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
        key_label = QLabel(tr("rgb.instructions"))
        key_label.setObjectName("rgb_instructions")
        outer.addWidget(key_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("rgb_scroll")
        container = QWidget()
        self._keys_hbox = QHBoxLayout(container)
        self._keys_hbox.setAlignment(Qt.AlignmentFlag.AlignLeft)
        scroll.setWidget(container)

        # Section effets — QListWidget à gauche, description + stack à droite
        effects_group = QGroupBox(tr("rgb.effects_group"))
        effects_group.setObjectName("effects_group")
        effects_hbox = QHBoxLayout(effects_group)

        # QListWidget (gauche)
        self._effect_list = QListWidget()
        self._effect_list.setObjectName("effect_list")
        self._effect_list.setFixedWidth(220)
        for e in EFFECT_TYPES:
            self._effect_list.addItem(e.name)
        self._effect_list.currentRowChanged.connect(self._on_effect_type_changed)
        effects_hbox.addWidget(self._effect_list)

        # Panneau droite : description + stack
        right_vbox = QVBoxLayout()
        right_vbox.setContentsMargins(0, 0, 0, 0)

        # Label description
        self._lbl_effect_desc = QLabel()
        self._lbl_effect_desc.setObjectName("effect_desc")
        self._lbl_effect_desc.setWordWrap(True)
        right_vbox.addWidget(self._lbl_effect_desc)

        # Panneau dynamique (QStackedWidget) — 3 pages
        self._effect_stack = QStackedWidget()
        self._effect_stack.setObjectName("effect_stack")
        self._effect_stack.addWidget(self._build_static_panel())   # index 0 : static
        self._effect_stack.addWidget(self._build_native_panel())   # index 1 : effets QMK natifs
        self._effect_stack.addWidget(self._build_ripple_panel())   # index 2 : ripple custom
        right_vbox.addWidget(self._effect_stack)
        right_vbox.addStretch()

        effects_hbox.addLayout(right_vbox, 1)

        # Splitter vertical : scroll (clavier) | effects_group
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(scroll)
        splitter.addWidget(effects_group)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        outer.addWidget(splitter)

    def _build_static_panel(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName("static_panel")
        layout = QHBoxLayout(panel)
        layout.addWidget(QLabel(tr("rgb.static.color")))
        self._btn_static_color = QPushButton()
        self._btn_static_color.setObjectName("btn_color_primary")
        self._btn_static_color.setFixedSize(32, 24)
        self._btn_static_color.setToolTip(tr("rgb.static.tooltip"))
        self._btn_static_color.clicked.connect(self._on_color_primary_clicked)
        layout.addWidget(self._btn_static_color)
        layout.addStretch()
        return panel

    def _build_native_panel(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName("native_panel")
        layout = QHBoxLayout(panel)
        lbl = QLabel(tr("rgb.native.info"))
        lbl.setWordWrap(True)
        lbl.setObjectName("native_info_label")
        layout.addWidget(lbl)
        return panel

    def _build_ripple_panel(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName("ripple_panel")
        layout = QVBoxLayout(panel)

        # Couleur primaire
        row1 = QHBoxLayout()
        row1.addWidget(QLabel(tr("rgb.ripple.primary")))
        self._btn_ripple_primary = QPushButton()
        self._btn_ripple_primary.setObjectName("btn_ripple_primary")
        self._btn_ripple_primary.setFixedSize(32, 24)
        self._btn_ripple_primary.clicked.connect(self._on_color_primary_clicked)
        row1.addWidget(self._btn_ripple_primary)
        row1.addStretch()
        layout.addLayout(row1)

        # Couleur secondaire
        row2 = QHBoxLayout()
        row2.addWidget(QLabel(tr("rgb.ripple.secondary")))
        self._btn_color_secondary = QPushButton()
        self._btn_color_secondary.setObjectName("btn_color_secondary")
        self._btn_color_secondary.setFixedSize(32, 24)
        self._btn_color_secondary.clicked.connect(self._on_color_secondary_clicked)
        row2.addWidget(self._btn_color_secondary)
        row2.addStretch()
        layout.addLayout(row2)

        # Fade ms
        row3 = QHBoxLayout()
        row3.addWidget(QLabel(tr("rgb.ripple.fade")))
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
        self._btn_trigger = QPushButton(tr("rgb.ripple.trigger_btn"))
        self._btn_trigger.setObjectName("btn_trigger")
        self._btn_trigger.clicked.connect(self._on_trigger_clicked)
        self._lbl_trigger = QLabel(tr("rgb.ripple.trigger_none"))
        self._lbl_trigger.setObjectName("lbl_trigger")
        row4.addWidget(self._btn_trigger)
        row4.addWidget(self._lbl_trigger)
        row4.addStretch()
        layout.addLayout(row4)

        return panel

    # ────────────────────────────────────────────────────── Key layout ──

    def _build_layout(self) -> None:
        self._key_buttons.clear()
        while self._keys_hbox.count():
            item = self._keys_hbox.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

        kb = self._find_current_keyboard()
        if kb and kb.layout:
            self._build_physical_layout(kb)
        else:
            self._build_grid_layout(kb)

    def _build_grid_layout(self, kb: KeyboardDefinition | None) -> None:
        """Fallback : grille uniforme rows × cols."""
        rows = kb.matrix.get("rows", 5) if kb else 5
        cols = kb.matrix.get("cols", 6) if kb else 6
        padding = 4
        canvas_w = cols * KEY_SIZE + padding * 2
        canvas_h = rows * KEY_SIZE + padding * 2
        for side_code in ("L", "R"):
            scene = QGraphicsScene(self)
            scene.setSceneRect(0, 0, canvas_w, canvas_h)
            view = QGraphicsView(scene)
            view.setObjectName(f"frame_{side_code}")
            view.setFixedSize(canvas_w + 4, canvas_h + 4)
            view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            view.setBackgroundBrush(QBrush(QColor("#1E1E1E")))
            view.setFrameShape(QFrame.Shape.StyledPanel)
            view.setDragMode(QGraphicsView.DragMode.NoDrag)
            for r in range(rows):
                for c in range(cols):
                    key_id = f"{side_code}_r{r}_c{c}"
                    item = KeyColorItem(key_id, 1.0, 1.0, 0.0, self._on_key_clicked)
                    item.setPos(padding + c * KEY_SIZE, padding + r * KEY_SIZE)
                    scene.addItem(item)
                    self._key_buttons[key_id] = item
            self._keys_hbox.addWidget(view)
            self._keys_hbox.addSpacing(16)

    def _build_physical_layout(self, kb: KeyboardDefinition) -> None:
        """Positionnement absolu d'après les coordonnées physiques du YAML."""
        side_map = {"L": "left", "R": "right"}
        padding = 4
        for side_code, yaml_side in side_map.items():
            keys: list[KeyLayout] = kb.layout.get(yaml_side, [])
            non_enc = [k for k in keys if not k.encoder]
            if not non_enc:
                continue

            # Normalise les coordonnées : chaque panneau commence en (0,0)
            min_x = min(k.x for k in non_enc)
            min_y = min(k.y for k in non_enc)
            canvas_w = int((max(k.x + k.w for k in non_enc) - min_x) * KEY_SIZE) + padding * 2
            canvas_h = int((max(k.y + k.h for k in non_enc) - min_y) * KEY_SIZE) + padding * 2

            scene = QGraphicsScene(self)
            scene.setSceneRect(0, 0, canvas_w, canvas_h)
            view = QGraphicsView(scene)
            view.setObjectName(f"frame_{side_code}")
            view.setFixedSize(canvas_w + 4, canvas_h + 4)
            view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            view.setBackgroundBrush(QBrush(QColor("#1E1E1E")))
            view.setFrameShape(QFrame.Shape.StyledPanel)
            view.setDragMode(QGraphicsView.DragMode.NoDrag)

            for k in non_enc:
                key_id = f"{side_code}_r{k.row}_c{k.col}"
                item = KeyColorItem(
                    key_id, k.w, k.h, getattr(k, "r", 0.0), self._on_key_clicked
                )
                item.setPos(padding + (k.x - min_x) * KEY_SIZE, padding + (k.y - min_y) * KEY_SIZE)
                scene.addItem(item)
                self._key_buttons[key_id] = item

            self._keys_hbox.addWidget(view)
            self._keys_hbox.addSpacing(16)

    def _find_current_keyboard(self) -> KeyboardDefinition | None:
        keyboards = load_all_keyboards(KEYBOARDS_DIR, CUSTOM_KEYBOARDS_DIR)
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
            self._btn_trigger.setText(tr("rgb.ripple.trigger_btn"))
            return
        current = QColor(self._model.rgb.per_key.get(key_id, "#FFFFFF"))
        color = QColorDialog.getColor(current, self, tr("rgb.key_color_fmt").format(key_id=key_id))
        if color.isValid():
            hex_color = color.name().upper()
            self._apply_color(key_id, hex_color)

    def _apply_color(self, key_id: str, hex_color: str) -> None:
        item = self._key_buttons.get(key_id)
        if item:
            item.set_color(hex_color)
            self._model.rgb.per_key[key_id] = hex_color
        else:
            logger.warning("Clé inconnue '%s' ignorée dans _apply_color", key_id)

    # ──────────────────────────────────────────────── Effect handlers ──

    def _ensure_effect(self, type_id: str) -> RgbEffect:
        """Retourne l'effet courant (index 0) ou en crée un nouveau."""
        if not self._model.rgb.effects:
            self._model.rgb.effects = [RgbEffect(type=type_id)]
        return self._model.rgb.effects[0]

    def _on_effect_type_changed(self, row: int) -> None:
        if row < 0 or row >= len(EFFECT_TYPES):
            return
        # M1: quitter le mode trigger si actif lors du changement d'effet
        if self._trigger_mode:
            self._trigger_mode = False
            self._btn_trigger.setText(tr("rgb.ripple.trigger_btn"))
        effect_def = EFFECT_TYPES[row]
        effect = self._ensure_effect(effect_def.id)
        effect.type = effect_def.id
        self._lbl_effect_desc.setText(effect_def.description)
        self._effect_stack.setCurrentIndex(_stack_page_for(effect_def.id))
        self._refresh_effect_buttons()
        self._update_preview()
        logger.info("Effet RGB changé : %s", effect_def.id)

    def _on_color_primary_clicked(self) -> None:
        effect = self._ensure_effect(_EFFECT_IDS[self._effect_list.currentRow()])
        current = QColor(effect.color_primary)
        color = QColorDialog.getColor(current, self, tr("rgb.dialog.primary_color"))
        if color.isValid():
            effect.color_primary = color.name().upper()
            self._refresh_effect_buttons()
            self._update_preview()

    def _on_color_secondary_clicked(self) -> None:
        effect = self._ensure_effect(_EFFECT_IDS[self._effect_list.currentRow()])
        current = QColor(effect.color_secondary)
        color = QColorDialog.getColor(current, self, tr("rgb.dialog.secondary_color"))
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
        self._btn_trigger.setText(tr("rgb.ripple.trigger_click"))

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
            # Liste effet
            try:
                idx = _EFFECT_IDS.index(effect.type)
            except ValueError:
                logger.warning("Type d'effet inconnu '%s' — retour à static", effect.type)
                idx = 0
            self._effect_list.blockSignals(True)
            self._effect_list.setCurrentRow(idx)
            self._effect_list.blockSignals(False)
            effect_def = EFFECT_TYPES[idx]
            self._lbl_effect_desc.setText(effect_def.description)
            self._effect_stack.setCurrentIndex(_stack_page_for(effect.type))
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
