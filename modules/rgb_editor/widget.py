"""RgbWidget — onglet de personnalisation RGB.

Affiche un layout visuel split du clavier (gauche/droite) avec des touches cliquables
pour assigner des couleurs par touche (FR11), et une section effets RGB (FR12-FR14).
"""
from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QFont, QHideEvent, QLinearGradient, QPainter, QPen, QShowEvent
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGraphicsItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsView,
    QGroupBox,
    QMessageBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from i18n import tr
from models.project_model import CustomEffect, EffectStep, EffectTrack, KeyOffset, ProjectModel, RgbEffect
from modules.hardware.keyboard_loader import KeyboardDefinition, KeyLayout, load_all_keyboards
from modules.rgb_editor.effect_preview import EffectPreview
from modules.rgb_editor.effects import EFFECT_TYPES, EffectDef

logger = logging.getLogger(__name__)

KEYBOARDS_DIR = Path(__file__).parent.parent.parent / "keyboards"
CUSTOM_KEYBOARDS_DIR = Path.home() / ".keyboard_firmware_maker" / "custom_keyboards"
KEY_SIZE = 36  # px

# ── Timeline constants ──
TIMELINE_DURATION_MS = 4000  # frise fixe de 0 à 4 secondes
PX_PER_MS = 0.3  # 1 seconde = 300px, 4s = 1200px
RULER_H = 22  # hauteur de la règle temporelle
CARTOUCHE_H = 54  # hauteur d'un cartouche d'événement
CARTOUCHE_MIN_W = 80  # largeur minimum (quand fade_ms == 0)
CARTOUCHE_Y = RULER_H + 4  # position Y des cartouches dans la scène
TRACK_SCENE_H = RULER_H + CARTOUCHE_H + 12  # hauteur totale de la scène


class EventCartouche(QGraphicsRectItem):
    """Cartouche draggable représentant un événement LED sur la frise.

    Affiche : couleur initiale, couleur d'arrivée (si fade), durée du fade,
    temps de déclenchement. Draggable horizontalement avec snap 50ms.
    """

    def __init__(
        self,
        track_idx: int,
        step_idx: int,
        step: EffectStep,
        prev_color: str,
        is_selected: bool,
        on_select,
        on_moved,
    ) -> None:
        self.track_idx = track_idx
        self.step_idx = step_idx
        self._step = step
        # Couleur d'arrivée : color_to explicite, sinon reste à step.color
        self._to_color = step.color_to if (step.fade_ms > 0 and step.color_to) else step.color
        self._on_select = on_select
        self._on_moved = on_moved
        total_ms = step.hold_ms + step.fade_ms
        w = max(CARTOUCHE_MIN_W, total_ms * PX_PER_MS) if total_ms > 0 else CARTOUCHE_MIN_W
        super().__init__(0, 0, w, CARTOUCHE_H)
        self.setPos(step.time_ms * PX_PER_MS, CARTOUCHE_Y)
        self.setBrush(QBrush(QColor("#252530")))
        self._update_pen(is_selected)
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
        self.setZValue(10)
        self._build_content()

    def _update_pen(self, selected: bool) -> None:
        if selected:
            self.setPen(QPen(QColor("#77AAFF"), 2.5))
        else:
            self.setPen(QPen(QColor("#4A4A5A"), 1))

    def _build_content(self) -> None:
        """Ajoute les éléments visuels dans le cartouche."""
        step = self._step
        w = self.rect().width()

        # ── Ligne 1 : label délai ──
        time_label = QGraphicsSimpleTextItem(f"{step.time_ms} ms", self)
        time_label.setFont(QFont("sans-serif", 8, QFont.Weight.Bold))
        time_label.setBrush(QBrush(QColor("#EEEEEE")))
        time_label.setPos(4, 2)

        # ── Ligne 2 : swatches couleur ──
        swatch_y = 18
        swatch_h = 16
        swatch_w = 22

        if step.fade_ms > 0:
            # Avec fondu : couleur de départ (step.color) → couleur d'arrivée (color_to)
            from_swatch = QGraphicsRectItem(0, 0, swatch_w, swatch_h, self)
            from_swatch.setPos(4, swatch_y)
            from_swatch.setBrush(QBrush(QColor(step.color)))
            from_swatch.setPen(QPen(QColor("#777777"), 1))
            # Flèche →
            arrow = QGraphicsSimpleTextItem("\u2192", self)
            arrow.setFont(QFont("sans-serif", 11))
            arrow.setBrush(QBrush(QColor("#AAAAAA")))
            arrow.setPos(swatch_w + 6, swatch_y - 2)
            # Swatch couleur d'arrivée
            to_swatch = QGraphicsRectItem(0, 0, swatch_w, swatch_h, self)
            to_swatch.setPos(swatch_w + 24, swatch_y)
            to_swatch.setBrush(QBrush(QColor(self._to_color)))
            to_swatch.setPen(QPen(QColor("#777777"), 1))
        else:
            # Pas de fade — couleur unique, large swatch
            swatch = QGraphicsRectItem(0, 0, min(w - 8, 50), swatch_h, self)
            swatch.setPos(4, swatch_y)
            swatch.setBrush(QBrush(QColor(step.color)))
            swatch.setPen(QPen(QColor("#777777"), 1))

        # ── Ligne 3 : info durée/fade ──
        info_parts = []
        if step.hold_ms > 0:
            info_parts.append(f"{step.hold_ms} ms")
        if step.fade_ms > 0:
            info_parts.append(f"fondu {step.fade_ms} ms")
        if info_parts:
            info_label = QGraphicsSimpleTextItem(" + ".join(info_parts), self)
            info_label.setFont(QFont("sans-serif", 7))
            info_label.setBrush(QBrush(QColor("#AAAAAA")))
            info_label.setPos(4, 38)
        else:
            instant_label = QGraphicsSimpleTextItem("instantan\u00e9", self)
            instant_label.setFont(QFont("sans-serif", 7))
            instant_label.setBrush(QBrush(QColor("#777777")))
            instant_label.setPos(4, 38)

        # ── Bande en bas : hold (couleur fixe) + fade (gradient) ──
        bar_h = 4
        bar_w = w
        total_ms = step.hold_ms + step.fade_ms
        if total_ms > 0 and step.hold_ms > 0 and step.fade_ms > 0:
            # Deux segments : hold (fixe) puis fade (gradient)
            hold_w = bar_w * step.hold_ms / total_ms
            hold_bar = QGraphicsRectItem(0, 0, hold_w, bar_h, self)
            hold_bar.setPos(0, CARTOUCHE_H - bar_h)
            hold_bar.setBrush(QBrush(QColor(step.color)))
            hold_bar.setPen(QPen(Qt.PenStyle.NoPen))
            fade_bar = QGraphicsRectItem(0, 0, bar_w - hold_w, bar_h, self)
            fade_bar.setPos(hold_w, CARTOUCHE_H - bar_h)
            grad = QLinearGradient(0, 0, bar_w - hold_w, 0)
            grad.setColorAt(0.0, QColor(step.color))
            grad.setColorAt(1.0, QColor(self._to_color))
            fade_bar.setBrush(QBrush(grad))
            fade_bar.setPen(QPen(Qt.PenStyle.NoPen))
        else:
            bar = QGraphicsRectItem(0, 0, bar_w, bar_h, self)
            bar.setPos(0, CARTOUCHE_H - bar_h)
            if step.fade_ms > 0:
                grad = QLinearGradient(0, 0, bar_w, 0)
                grad.setColorAt(0.0, QColor(step.color))
                grad.setColorAt(1.0, QColor(self._to_color))
                bar.setBrush(QBrush(grad))
            else:
                bar.setBrush(QBrush(QColor(step.color)))
            bar.setPen(QPen(Qt.PenStyle.NoPen))

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            from PySide6.QtCore import QPointF
            new_x = max(0.0, min(value.x(), TIMELINE_DURATION_MS * PX_PER_MS))
            # Snap aux 50ms
            snapped_ms = round(new_x / PX_PER_MS / 50) * 50
            snapped_x = snapped_ms * PX_PER_MS
            return QPointF(snapped_x, CARTOUCHE_Y)
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            new_time_ms = int(round(self.pos().x() / PX_PER_MS))
            if new_time_ms != self._step.time_ms:
                self._step.time_ms = new_time_ms
                # Mettre à jour le label de temps
                for child in self.childItems():
                    if isinstance(child, QGraphicsSimpleTextItem):
                        old = child.text()
                        if old.endswith(" ms") and not old.startswith("fade"):
                            child.setText(f"{new_time_ms} ms")
                            break
                self._on_moved(self.track_idx, self.step_idx, new_time_ms)
        return super().itemChange(change, value)

    def mousePressEvent(self, event) -> None:
        self._on_select(self.track_idx, self.step_idx)
        super().mousePressEvent(event)


class TrackTimelineScene(QGraphicsScene):
    """Scène de frise temporelle 0-4s avec règle graduée."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        total_px = TIMELINE_DURATION_MS * PX_PER_MS + 40
        self.setSceneRect(0, 0, total_px, TRACK_SCENE_H)
        self._draw_ruler()
        # Fond de la zone événements
        track_bg = QGraphicsRectItem(0, RULER_H, total_px, TRACK_SCENE_H - RULER_H)
        track_bg.setBrush(QBrush(QColor("#1E1E1E")))
        track_bg.setPen(QPen(Qt.PenStyle.NoPen))
        track_bg.setZValue(-1)
        self.addItem(track_bg)

    def _draw_ruler(self) -> None:
        """Dessine les graduations toutes les 100ms, labels toutes les 500ms."""
        pen_major = QPen(QColor("#666666"), 1)
        pen_minor = QPen(QColor("#3A3A3A"), 1)
        pen_half = QPen(QColor("#4A4A4A"), 1)
        font_big = QFont("sans-serif", 8)
        font_small = QFont("sans-serif", 6)
        for ms in range(0, TIMELINE_DURATION_MS + 1, 100):
            x = ms * PX_PER_MS
            if ms % 1000 == 0:
                # Seconde entière : trait long + label gras
                self.addLine(x, 0, x, RULER_H, pen_major)
                label = self.addSimpleText(f"{ms // 1000}s", font_big)
                label.setBrush(QBrush(QColor("#CCCCCC")))
                label.setPos(x + 3, 2)
                # Ligne verticale de repère dans la zone événements
                guide = self.addLine(x, RULER_H, x, TRACK_SCENE_H, pen_minor)
                guide.setZValue(0)
            elif ms % 500 == 0:
                # Demi-seconde : trait moyen + petit label
                self.addLine(x, 4, x, RULER_H, pen_half)
                label = self.addSimpleText(f"{ms / 1000:.1f}", font_small)
                label.setBrush(QBrush(QColor("#777777")))
                label.setPos(x + 2, 6)
            else:
                # 100ms : petit trait
                self.addLine(x, RULER_H - 5, x, RULER_H, pen_minor)
        # Ligne horizontale de base de la règle
        total_px = TIMELINE_DURATION_MS * PX_PER_MS
        self.addLine(0, RULER_H, total_px, RULER_H, pen_major)


class TrackTimelineView(QGraphicsView):
    """Vue scrollable d'une frise de piste (0-4 secondes)."""

    def __init__(self, scene: TrackTimelineScene, parent=None) -> None:
        super().__init__(scene, parent)
        self.setFixedHeight(TRACK_SCENE_H + 20)
        self.setMinimumWidth(400)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setBackgroundBrush(QBrush(QColor("#141414")))
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Fond sombre sur la vue ET le viewport pour éviter les zones blanches
        self.setStyleSheet("QGraphicsView { background-color: #141414; border: none; }")

    def showEvent(self, event) -> None:
        """Force le fond sombre du viewport à chaque affichage (Qt peut recréer le viewport)."""
        super().showEvent(event)
        vp = self.viewport()
        vp.setAutoFillBackground(True)
        vp.setStyleSheet("background-color: #141414;")


class KeyColorItem(QGraphicsRectItem):
    """Touche cliquable pour l'onglet RGB — supporte taille réelle et rotation."""

    def __init__(
        self,
        key_id: str,
        w_u: float,
        h_u: float,
        r_deg: float,
        on_click,
        on_right_click=None,
    ) -> None:
        w_px = w_u * KEY_SIZE - 2
        h_px = h_u * KEY_SIZE - 2
        super().__init__(0, 0, w_px, h_px)
        self.key_id = key_id
        self._on_click = on_click
        self._on_right_click = on_right_click
        self.setTransformOriginPoint(w_px / 2, h_px / 2)
        if r_deg:
            self.setRotation(r_deg)
        self.setBrush(QBrush(QColor("#333333")))
        self.setPen(QPen(QColor("#555555"), 1))
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton | Qt.MouseButton.RightButton)

    def set_color(self, hex_color: str) -> None:
        self.setBrush(QBrush(QColor(hex_color)))
        self.update()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.RightButton and self._on_right_click:
            self._on_right_click(self.key_id)
        else:
            self._on_click(self.key_id)
        super().mousePressEvent(event)

class _NewCustomEffectDialog(QDialog):
    """Dialog wizard pour créer un nouvel effet custom (nom + type)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("rgb.custom_effects.new_title"))
        self.setMinimumWidth(360)
        layout = QVBoxLayout(self)

        # Nom
        layout.addWidget(QLabel(tr("rgb.custom_effects.name_label")))
        self._name_edit = QLineEdit()
        self._name_edit.setObjectName("custom_effect_name_edit")
        self._name_edit.setPlaceholderText(tr("rgb.custom_effects.name_placeholder"))
        self._name_edit.setText(tr("rgb.custom_effects.name_default"))
        layout.addWidget(self._name_edit)

        layout.addSpacing(12)

        # Type
        layout.addWidget(QLabel(tr("rgb.custom_effects.type_label")))
        self._radio_reactive = QRadioButton(tr("rgb.custom_effects.type_reactive_desc"))
        self._radio_reactive.setObjectName("radio_reactive")
        self._radio_reactive.setChecked(True)
        self._radio_ambient = QRadioButton(tr("rgb.custom_effects.type_ambient_desc"))
        self._radio_ambient.setObjectName("radio_ambient")
        layout.addWidget(self._radio_reactive)
        layout.addWidget(self._radio_ambient)

        layout.addSpacing(12)

        # Boutons OK/Annuler
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def effect_name(self) -> str:
        return self._name_edit.text().strip() or tr("rgb.custom_effects.name_default")

    def effect_type(self) -> str:
        return "reactive" if self._radio_reactive.isChecked() else "ambient"


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

    from PySide6.QtCore import Signal
    save_requested = Signal()

    def __init__(self, model: ProjectModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._model = model
        self._current_kb: KeyboardDefinition | None = None
        self._key_buttons: dict[str, KeyColorItem] = {}
        self._trigger_mode: bool = False
        # État d'édition custom effect
        self._editing_custom_idx: int | None = None
        self._editing_track_idx: int = 0
        self._editing_step_idx: int = 0
        self._relative_ref_key: str | None = None  # clé de référence pour mode relative
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

        # QListWidget (gauche) — avec checkboxes + séparateurs de catégories
        self._effect_list = QListWidget()
        self._effect_list.setObjectName("effect_list")
        self._effect_list.setFixedWidth(240)
        self._row_to_effect: dict[int, int] = {}  # list row → EFFECT_TYPES index
        enabled_set = set(self._model.rgb.enabled_effects) if self._model.rgb.enabled_effects else None
        current_cat = None
        row = 0
        for i, e in enumerate(EFFECT_TYPES):
            # Séparateur de catégorie
            if e.category != current_cat:
                current_cat = e.category
                sep = QListWidgetItem(tr(f"rgb.category.{current_cat}"))
                sep.setFlags(Qt.ItemFlag.NoItemFlags)  # non sélectionnable/cliquable
                font = sep.font()
                font.setBold(True)
                sep.setFont(font)
                sep.setBackground(QColor("#2A2A2A"))
                sep.setForeground(QColor("#AAAAAA"))
                self._effect_list.addItem(sep)
                row += 1
            item = QListWidgetItem(f"  {e.name}")
            if not e.custom and e.id != "static":
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                if enabled_set is None or e.id in enabled_set:
                    item.setCheckState(Qt.CheckState.Checked)
                else:
                    item.setCheckState(Qt.CheckState.Unchecked)
            self._effect_list.addItem(item)
            self._row_to_effect[row] = i
            row += 1
        # Section "Mes effets" — effets custom de l'utilisateur
        self._row_to_custom: dict[int, int] = {}  # list row → custom_effects index
        self._rebuild_custom_section(row)

        self._effect_list.currentRowChanged.connect(self._on_effect_type_changed)
        self._effect_list.itemChanged.connect(self._on_effect_check_changed)

        # Bouton [+ Nouvel effet] sous la liste
        left_vbox = QVBoxLayout()
        left_vbox.setContentsMargins(0, 0, 0, 0)
        left_vbox.addWidget(self._effect_list)
        self._btn_new_custom = QPushButton(tr("rgb.custom_effects.new"))
        self._btn_new_custom.setObjectName("btn_new_custom")
        self._btn_new_custom.clicked.connect(self._on_new_custom_effect)
        left_vbox.addWidget(self._btn_new_custom)
        effects_hbox.addLayout(left_vbox)

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
        self._effect_stack.addWidget(self._build_static_panel())    # index 0 : static
        self._effect_stack.addWidget(self._build_native_panel())    # index 1 : effets QMK natifs
        self._effect_stack.addWidget(self._build_ripple_panel())    # index 2 : ripple custom
        self._effect_stack.addWidget(self._build_custom_editor())   # index 3 : éditeur timeline
        right_vbox.addWidget(self._effect_stack)

        # Sliders globaux speed + brightness (s'appliquent à tous les effets)
        sliders_layout = QHBoxLayout()

        speed_layout = QVBoxLayout()
        speed_layout.addWidget(QLabel(tr("rgb.speed")))
        self._speed_slider = QSlider(Qt.Orientation.Horizontal)
        self._speed_slider.setObjectName("speed_slider")
        self._speed_slider.setRange(0, 255)
        self._speed_slider.setValue(128)
        self._speed_slider.setTickInterval(32)
        self._speed_label = QLabel("128")
        self._speed_label.setFixedWidth(30)
        speed_row = QHBoxLayout()
        speed_row.addWidget(self._speed_slider)
        speed_row.addWidget(self._speed_label)
        speed_layout.addLayout(speed_row)
        sliders_layout.addLayout(speed_layout)

        bright_layout = QVBoxLayout()
        bright_layout.addWidget(QLabel(tr("rgb.brightness")))
        self._brightness_slider = QSlider(Qt.Orientation.Horizontal)
        self._brightness_slider.setObjectName("brightness_slider")
        self._brightness_slider.setRange(0, 255)
        self._brightness_slider.setValue(128)
        self._brightness_slider.setTickInterval(32)
        self._brightness_label = QLabel("128")
        self._brightness_label.setFixedWidth(30)
        bright_row = QHBoxLayout()
        bright_row.addWidget(self._brightness_slider)
        bright_row.addWidget(self._brightness_label)
        bright_layout.addLayout(bright_row)
        sliders_layout.addLayout(bright_layout)

        right_vbox.addLayout(sliders_layout)

        self._speed_slider.valueChanged.connect(self._on_speed_changed)
        self._brightness_slider.valueChanged.connect(self._on_brightness_changed)

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

    def _build_custom_editor(self) -> QWidget:
        """Page 3 du stack — éditeur timeline interactif pour les effets custom."""
        # Splitter horizontal : éditeur à gauche, code preview à droite
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setObjectName("custom_editor_splitter")

        # ── Panneau gauche : éditeur timeline ──
        left_panel = QWidget()
        left_panel.setObjectName("custom_editor_panel")
        layout = QVBoxLayout(left_panel)
        layout.setContentsMargins(4, 4, 4, 4)

        # ── En-tête : nom + type + supprimer ──
        header = QHBoxLayout()
        self._lbl_custom_name = QLabel()
        self._lbl_custom_name.setObjectName("custom_effect_name")
        font = self._lbl_custom_name.font()
        font.setBold(True)
        font.setPointSize(font.pointSize() + 1)
        self._lbl_custom_name.setFont(font)
        header.addWidget(self._lbl_custom_name)
        self._lbl_custom_type = QLabel()
        self._lbl_custom_type.setObjectName("custom_effect_type")
        self._lbl_custom_type.setStyleSheet("color: #888888;")
        header.addWidget(self._lbl_custom_type)
        header.addStretch()
        self._btn_save_effect = QPushButton(tr("rgb.custom_effects.save"))
        self._btn_save_effect.setObjectName("btn_save_effect")
        self._btn_save_effect.setStyleSheet("font-weight: bold;")
        self._btn_save_effect.clicked.connect(self.save_requested.emit)
        header.addWidget(self._btn_save_effect)
        self._btn_delete_custom = QPushButton(tr("rgb.custom_effects.delete"))
        self._btn_delete_custom.setObjectName("btn_delete_custom")
        self._btn_delete_custom.clicked.connect(self._on_delete_custom_effect)
        header.addWidget(self._btn_delete_custom)
        layout.addLayout(header)

        # ── Conteneur vertical de toutes les pistes (empilées) ──
        self._tracks_container = QVBoxLayout()
        layout.addLayout(self._tracks_container)

        # ── Boutons ajouter/supprimer piste ──
        tracks_btns = QHBoxLayout()
        self._btn_add_track = QPushButton(tr("rgb.custom_effects.add_track"))
        self._btn_add_track.setObjectName("btn_add_track")
        self._btn_add_track.setFixedHeight(28)
        self._btn_add_track.clicked.connect(self._on_add_track)
        tracks_btns.addWidget(self._btn_add_track)
        self._btn_remove_track = QPushButton(tr("rgb.custom_effects.remove_track"))
        self._btn_remove_track.setObjectName("btn_remove_track")
        self._btn_remove_track.setFixedHeight(28)
        self._btn_remove_track.clicked.connect(self._on_remove_track)
        tracks_btns.addWidget(self._btn_remove_track)
        tracks_btns.addStretch()
        layout.addLayout(tracks_btns)

        # ── Paramètres de l'événement sélectionné ──
        step_group = QGroupBox(tr("rgb.custom_effects.selected_event"))
        step_group.setObjectName("step_group")
        step_vlayout = QVBoxLayout(step_group)

        # Ligne 1 : Délai + Couleur
        row1 = QHBoxLayout()
        row1.addWidget(QLabel(tr("rgb.custom_effects.step_delay")))
        self._spin_step_time = QSpinBox()
        self._spin_step_time.setObjectName("spin_step_time")
        self._spin_step_time.setRange(0, 4000)
        self._spin_step_time.setSingleStep(50)
        self._spin_step_time.setSuffix(" ms")
        self._spin_step_time.valueChanged.connect(self._on_step_time_changed)
        row1.addWidget(self._spin_step_time)
        row1.addSpacing(20)
        row1.addWidget(QLabel(tr("rgb.custom_effects.step_color")))
        self._btn_step_color = QPushButton()
        self._btn_step_color.setObjectName("btn_step_color")
        self._btn_step_color.setFixedSize(36, 24)
        self._btn_step_color.clicked.connect(self._on_step_color_clicked)
        row1.addWidget(self._btn_step_color)
        row1.addSpacing(20)
        row1.addWidget(QLabel(tr("rgb.custom_effects.hold_duration")))
        self._spin_hold = QSpinBox()
        self._spin_hold.setObjectName("spin_hold")
        self._spin_hold.setRange(0, 4000)
        self._spin_hold.setSingleStep(50)
        self._spin_hold.setSuffix(" ms")
        self._spin_hold.valueChanged.connect(self._on_step_hold_changed)
        row1.addWidget(self._spin_hold)
        row1.addStretch()
        step_vlayout.addLayout(row1)

        # Ligne 2 : Checkbox Fondu + couleur d'arrivée + durée
        row2 = QHBoxLayout()
        self._chk_fade = QCheckBox(tr("rgb.custom_effects.fade_enabled"))
        self._chk_fade.setObjectName("chk_fade")
        self._chk_fade.toggled.connect(self._on_fade_toggled)
        row2.addWidget(self._chk_fade)
        row2.addSpacing(12)
        self._lbl_color_to = QLabel(tr("rgb.custom_effects.step_color_to"))
        row2.addWidget(self._lbl_color_to)
        self._btn_color_to = QPushButton()
        self._btn_color_to.setObjectName("btn_color_to")
        self._btn_color_to.setFixedSize(36, 24)
        self._btn_color_to.clicked.connect(self._on_color_to_clicked)
        row2.addWidget(self._btn_color_to)
        row2.addSpacing(12)
        self._lbl_fade_duration = QLabel(tr("rgb.custom_effects.fade_duration"))
        row2.addWidget(self._lbl_fade_duration)
        self._spin_step_fade = QSpinBox()
        self._spin_step_fade.setObjectName("spin_step_fade")
        self._spin_step_fade.setRange(50, 5000)
        self._spin_step_fade.setSingleStep(50)
        self._spin_step_fade.setSuffix(" ms")
        self._spin_step_fade.valueChanged.connect(self._on_step_fade_changed)
        row2.addWidget(self._spin_step_fade)
        row2.addStretch()
        step_vlayout.addLayout(row2)
        layout.addWidget(step_group)

        # ── Encart d'aide : mode d'emploi de l'éditeur ──
        help_group = QGroupBox(tr("rgb.custom_effects.help_title"))
        help_group.setObjectName("editor_help")
        help_layout = QVBoxLayout(help_group)
        self._lbl_editor_hint = QLabel(tr("rgb.custom_effects.help_text"))
        self._lbl_editor_hint.setObjectName("editor_hint")
        self._lbl_editor_hint.setWordWrap(True)
        self._lbl_editor_hint.setStyleSheet(
            "color: #AABBDD; font-size: 11px; line-height: 1.4; padding: 4px;"
        )
        help_layout.addWidget(self._lbl_editor_hint)
        layout.addWidget(help_group)

        # ── Panneau droit : preview du code C ──
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(4, 4, 4, 4)
        # Titre + bouton copier
        code_header = QHBoxLayout()
        code_header.addWidget(QLabel(tr("rgb.custom_effects.code_preview")))
        code_header.addStretch()
        self._btn_copy_code = QPushButton(tr("rgb.custom_effects.copy_code"))
        self._btn_copy_code.setObjectName("btn_copy_code")
        self._btn_copy_code.setFixedHeight(24)
        self._btn_copy_code.clicked.connect(self._on_copy_code)
        code_header.addWidget(self._btn_copy_code)
        right_layout.addLayout(code_header)
        # Code editor
        self._code_preview = QPlainTextEdit()
        self._code_preview.setObjectName("code_preview")
        self._code_preview.setStyleSheet(
            "QPlainTextEdit { background-color: #1E1E1E; color: #D4D4D4;"
            " font-family: 'Consolas', 'Monaco', monospace; font-size: 11px; }"
        )
        right_layout.addWidget(self._code_preview)

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([600, 400])
        return splitter

    # ───────────────────────────── Custom effects list management ──

    def _rebuild_custom_section(self, start_row: int) -> None:
        """Reconstruit la section 'Mes effets' dans la QListWidget."""
        # Supprimer les anciennes entrées custom
        rows_to_remove = sorted(self._row_to_custom.keys(), reverse=True)
        for r in rows_to_remove:
            self._effect_list.takeItem(r)
        self._row_to_custom.clear()

        # Trouver le séparateur existant "Mes effets" pour le supprimer
        for r in range(self._effect_list.count() - 1, -1, -1):
            item = self._effect_list.item(r)
            if item and item.text() == tr("rgb.category.custom"):
                self._effect_list.takeItem(r)
                start_row = r
                break

        row = start_row
        if self._model.rgb.custom_effects:
            # Séparateur
            sep = QListWidgetItem(tr("rgb.category.custom"))
            sep.setFlags(Qt.ItemFlag.NoItemFlags)
            font = sep.font()
            font.setBold(True)
            sep.setFont(font)
            sep.setBackground(QColor("#2A2A2A"))
            sep.setForeground(QColor("#AAAAAA"))
            self._effect_list.addItem(sep)
            row += 1
            # Entrées custom
            for ci, ce in enumerate(self._model.rgb.custom_effects):
                icon = "⚡" if ce.effect_type == "reactive" else "🎵"
                item = QListWidgetItem(f"  {icon} {ce.name}")
                self._effect_list.addItem(item)
                self._row_to_custom[row] = ci
                row += 1
        self._custom_section_start = start_row

    def _on_new_custom_effect(self) -> None:
        """Ouvre le dialog de création d'un nouvel effet custom."""
        dlg = _NewCustomEffectDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            name = dlg.effect_name()
            effect_type = dlg.effect_type()
            # Créer l'effet avec une piste par défaut
            default_track = EffectTrack(
                name=tr("rgb.custom_effects.default_track"),
                target_mode="default",
                steps=[EffectStep(time_ms=0, color="#FFFFFF", fade_ms=0)],
            )
            new_effect = CustomEffect(
                name=name,
                effect_type=effect_type,
                tracks=[default_track],
            )
            self._model.rgb.custom_effects.append(new_effect)
            self._rebuild_custom_section(self._custom_section_start)
            # Sélectionner le nouvel effet
            for row, ci in self._row_to_custom.items():
                if ci == len(self._model.rgb.custom_effects) - 1:
                    self._effect_list.setCurrentRow(row)
                    break
            logger.info("Nouvel effet custom créé : %s (%s)", name, effect_type)

    def _on_delete_custom_effect(self) -> None:
        """Supprime l'effet custom actuellement sélectionné après confirmation."""
        row = self._effect_list.currentRow()
        ci = self._row_to_custom.get(row)
        if ci is not None and 0 <= ci < len(self._model.rgb.custom_effects):
            name = self._model.rgb.custom_effects[ci].name
            reply = QMessageBox.warning(
                self,
                tr("rgb.custom_effects.delete_title"),
                tr("rgb.custom_effects.delete_confirm").format(name=name),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
            del self._model.rgb.custom_effects[ci]
            self._editing_custom_idx = None
            self._rebuild_custom_section(self._custom_section_start)
            logger.info("Effet custom supprimé : %s", name)

    def _load_custom_into_editor(self, custom_idx: int) -> None:
        """Charge un effet custom dans l'éditeur timeline (page 3 du stack)."""
        if custom_idx < 0 or custom_idx >= len(self._model.rgb.custom_effects):
            return
        self._editing_custom_idx = custom_idx
        self._editing_track_idx = 0
        self._editing_step_idx = 0
        ce = self._model.rgb.custom_effects[custom_idx]
        self._lbl_custom_name.setText(ce.name)
        type_label = tr("rgb.custom_effects.type_reactive") if ce.effect_type == "reactive" else tr("rgb.custom_effects.type_ambient")
        self._lbl_custom_type.setText(f"({type_label})")
        self._refresh_tracks_ui()
        self._refresh_step_params()
        self._refresh_key_highlights()

    def _current_custom_effect(self) -> CustomEffect | None:
        """Retourne l'effet custom en cours d'édition."""
        if self._editing_custom_idx is None:
            return None
        ces = self._model.rgb.custom_effects
        if 0 <= self._editing_custom_idx < len(ces):
            return ces[self._editing_custom_idx]
        return None

    def _current_track(self) -> EffectTrack | None:
        """Retourne la piste en cours d'édition."""
        ce = self._current_custom_effect()
        if ce and 0 <= self._editing_track_idx < len(ce.tracks):
            return ce.tracks[self._editing_track_idx]
        return None

    def _current_step(self) -> EffectStep | None:
        """Retourne le step en cours d'édition."""
        track = self._current_track()
        if track and 0 <= self._editing_step_idx < len(track.steps):
            return track.steps[self._editing_step_idx]
        return None

    def _refresh_tracks_ui(self) -> None:
        """Reconstruit toutes les pistes avec leur frise temporelle 0-4s."""
        # Vider le conteneur
        while self._tracks_container.count():
            item = self._tracks_container.takeAt(0)
            w = item.widget() if item else None
            if w:
                w.deleteLater()
        ce = self._current_custom_effect()
        if not ce:
            return

        for ti, track in enumerate(ce.tracks):
            is_selected = (ti == self._editing_track_idx)
            # Cadre de la piste
            frame = QFrame()
            frame.setObjectName(f"track_frame_{ti}")
            frame.setFrameShape(QFrame.Shape.StyledPanel)
            frame.setStyleSheet(
                "QFrame#track_frame_%d { border: 2px solid #77AAFF; border-radius: 6px; }" % ti
                if is_selected else
                "QFrame#track_frame_%d { border: 1px solid #333333; border-radius: 6px; }" % ti
            )
            frame_layout = QVBoxLayout(frame)
            frame_layout.setContentsMargins(8, 6, 8, 6)
            frame_layout.setSpacing(4)

            # Ligne 1 : nom de la piste + info cibles + boutons +/- événement
            name_row = QHBoxLayout()
            name_btn = QPushButton(track.name)
            name_btn.setObjectName(f"track_name_{ti}")
            name_btn.setFlat(True)
            font = name_btn.font()
            font.setBold(is_selected)
            name_btn.setFont(font)
            name_btn.setStyleSheet(
                "color: #77AAFF; text-align: left; padding: 2px 4px;"
                if is_selected else
                "color: #AAAAAA; text-align: left; padding: 2px 4px;"
            )
            name_btn.clicked.connect(lambda checked, idx=ti: self._on_select_track(idx))
            name_row.addWidget(name_btn)
            # Info cibles
            mode_str = tr(f"rgb.custom_effects.mode_{track.target_mode}")
            if track.target_mode == "fixed" and track.keys_fixed:
                keys_info = f" [{', '.join(track.keys_fixed[:4])}{'...' if len(track.keys_fixed) > 4 else ''}]"
            elif track.target_mode == "relative" and track.keys_offset:
                keys_info = f" [{', '.join(f'({k.dr:+d},{k.dc:+d})' for k in track.keys_offset[:3])}]"
            else:
                keys_info = ""
            lbl_info = QLabel(f"{mode_str}{keys_info}")
            lbl_info.setStyleSheet("color: #666666; font-size: 10px;")
            name_row.addWidget(lbl_info)
            name_row.addStretch()
            # Boutons +/- événement
            if is_selected:
                btn_add = QPushButton(tr("rgb.custom_effects.add_step"))
                btn_add.setObjectName(f"btn_add_step_{ti}")
                btn_add.setFixedHeight(24)
                btn_add.setStyleSheet("font-size: 11px; padding: 2px 8px;")
                btn_add.clicked.connect(self._on_add_step)
                name_row.addWidget(btn_add)
                btn_rm = QPushButton(tr("rgb.custom_effects.remove_step"))
                btn_rm.setObjectName(f"btn_rm_step_{ti}")
                btn_rm.setFixedHeight(24)
                btn_rm.setStyleSheet("font-size: 11px; padding: 2px 8px;")
                btn_rm.setEnabled(len(track.steps) > 1)
                btn_rm.clicked.connect(self._on_remove_step)
                name_row.addWidget(btn_rm)
            frame_layout.addLayout(name_row)

            # Ligne 1b : sélecteur de mode cible (visible quand la piste est sélectionnée)
            if is_selected:
                mode_row = QHBoxLayout()
                mode_row.addWidget(QLabel(tr("rgb.custom_effects.target_mode")))
                combo = QComboBox()
                combo.setObjectName(f"combo_target_mode_{ti}")
                combo.addItem(tr("rgb.custom_effects.mode_default"), "default")
                combo.addItem(tr("rgb.custom_effects.mode_relative"), "relative")
                combo.addItem(tr("rgb.custom_effects.mode_fixed"), "fixed")
                # Sélectionner le mode actuel
                for ci_m in range(combo.count()):
                    if combo.itemData(ci_m) == track.target_mode:
                        combo.setCurrentIndex(ci_m)
                        break
                combo.currentIndexChanged.connect(
                    lambda idx, c=combo: self._on_target_mode_changed(c.itemData(idx))
                )
                mode_row.addWidget(combo)
                # Hint spécifique au mode relative
                if track.target_mode == "relative":
                    ref_text = self._relative_ref_key or "—"
                    lbl_ref = QLabel(tr("rgb.custom_effects.relative_ref").format(key=ref_text))
                    lbl_ref.setStyleSheet("color: #AAAAAA; font-size: 10px; margin-left: 12px;")
                    mode_row.addWidget(lbl_ref)
                mode_row.addStretch()
                frame_layout.addLayout(mode_row)

            # Ligne 2 : frise temporelle avec cartouches d'événements
            scene = TrackTimelineScene()
            for si, step in enumerate(track.steps):
                prev_color = track.steps[si - 1].color if si > 0 else "#000000"
                is_active = is_selected and si == self._editing_step_idx
                cartouche = EventCartouche(
                    ti, si, step, prev_color, is_active,
                    on_select=self._on_select_track_step,
                    on_moved=self._on_step_moved,
                )
                scene.addItem(cartouche)
            timeline_view = TrackTimelineView(scene)
            timeline_view.setObjectName(f"timeline_{ti}")
            scene.setParent(timeline_view)  # prevent garbage collection
            frame_layout.addWidget(timeline_view)

            self._tracks_container.addWidget(frame)
        # Masquer le bouton supprimer piste si 1 seule
        self._btn_remove_track.setEnabled(len(ce.tracks) > 1)
        # Rafraîchir le code preview
        self._refresh_code_preview()

    def _refresh_step_params(self) -> None:
        """Met à jour le panneau de paramètres de l'événement sélectionné."""
        step = self._current_step()
        has_step = step is not None
        # Activer/désactiver tous les contrôles
        self._spin_step_time.setEnabled(has_step)
        self._btn_step_color.setEnabled(has_step)
        self._spin_hold.setEnabled(has_step)
        self._chk_fade.setEnabled(has_step)
        if not has_step:
            self._btn_color_to.setEnabled(False)
            self._spin_step_fade.setEnabled(False)
            self._lbl_color_to.setVisible(False)
            self._btn_color_to.setVisible(False)
            self._lbl_fade_duration.setVisible(False)
            self._spin_step_fade.setVisible(False)
            return
        # Délai
        self._spin_step_time.blockSignals(True)
        self._spin_step_time.setValue(step.time_ms)
        self._spin_step_time.blockSignals(False)
        # Durée de maintien
        self._spin_hold.blockSignals(True)
        self._spin_hold.setValue(step.hold_ms)
        self._spin_hold.blockSignals(False)
        # Couleur de départ (toujours visible)
        self._btn_step_color.setStyleSheet(f"background-color: {step.color};")
        # Fondu checkbox
        has_fade = step.fade_ms > 0
        self._chk_fade.blockSignals(True)
        self._chk_fade.setChecked(has_fade)
        self._chk_fade.blockSignals(False)
        # Afficher/masquer les contrôles de fondu
        self._lbl_color_to.setVisible(has_fade)
        self._btn_color_to.setVisible(has_fade)
        self._lbl_fade_duration.setVisible(has_fade)
        self._spin_step_fade.setVisible(has_fade)
        if has_fade:
            to_color = step.color_to or step.color
            self._btn_color_to.setStyleSheet(f"background-color: {to_color};")
            self._btn_color_to.setEnabled(True)
            self._spin_step_fade.setEnabled(True)
            self._spin_step_fade.blockSignals(True)
            self._spin_step_fade.setValue(step.fade_ms)
            self._spin_step_fade.blockSignals(False)
        # L'aide statique ne change plus

    def _refresh_key_highlights(self) -> None:
        """Met en surbrillance les touches ciblées par le step courant."""
        # Reset toutes les touches à la couleur per-key ou gris
        for key_id, item in self._key_buttons.items():
            color = self._model.rgb.per_key.get(key_id, "#333333")
            item.set_color(color)
            item.setPen(QPen(QColor("#555555"), 1))
        track = self._current_track()
        if not track:
            return
        # Highlight les touches ciblées par la piste
        if track.target_mode == "fixed":
            for key_id in track.keys_fixed:
                item = self._key_buttons.get(key_id)
                if item:
                    item.setPen(QPen(QColor("#77AAFF"), 2))
        elif track.target_mode == "relative":
            # Highlight la touche de référence (orange) et les offsets (bleu)
            if self._relative_ref_key:
                ref_item = self._key_buttons.get(self._relative_ref_key)
                if ref_item:
                    ref_item.setPen(QPen(QColor("#FF8800"), 3))
                ref_qmk = self._key_to_qmk_rc(self._relative_ref_key)
                if ref_qmk:
                    for offset in track.keys_offset:
                        target_key = self._qmk_rc_to_key_id(
                            ref_qmk[0] + offset.dr, ref_qmk[1] + offset.dc,
                        )
                        if target_key:
                            item = self._key_buttons.get(target_key)
                            if item:
                                item.setPen(QPen(QColor("#77AAFF"), 2))
        # Pour "default", pas de highlight spécifique (la touche d'origine)

    def _key_to_qmk_rc(self, key_id: str) -> tuple[int, int] | None:
        """Convertit key_id en coordonnées matricielles QMK (row offset pour R en split)."""
        try:
            parts = key_id.split("_")
            side = parts[0]
            row = int(parts[1][1:])
            col = int(parts[2][1:])
            kb = self._current_kb
            if kb and kb.split and side == "R":
                row += kb.matrix.get("rows", 5)
            return row, col
        except (IndexError, ValueError):
            return None

    def _qmk_rc_to_key_id(self, qmk_row: int, col: int) -> str | None:
        """Convertit des coordonnées QMK en key_id, en déterminant le bon côté."""
        kb = self._current_kb
        rows_per_side = kb.matrix.get("rows", 5) if kb else 5
        is_split = kb.split if kb else False
        if is_split and qmk_row >= rows_per_side:
            key_id = f"R_r{qmk_row - rows_per_side}_c{col}"
        else:
            key_id = f"L_r{qmk_row}_c{col}"
        return key_id if key_id in self._key_buttons else None

    def _on_select_track(self, track_idx: int) -> None:
        """Sélectionne une piste dans les onglets."""
        self._editing_track_idx = track_idx
        self._editing_step_idx = 0
        self._relative_ref_key = None  # reset la référence relative
        self._refresh_tracks_ui()
        self._refresh_step_params()
        self._refresh_key_highlights()

    def _on_select_step(self, step_idx: int) -> None:
        """Sélectionne un step dans la timeline."""
        self._editing_step_idx = step_idx
        self._refresh_tracks_ui()
        self._refresh_step_params()
        self._refresh_key_highlights()

    def _on_select_track_step(self, track_idx: int, step_idx: int) -> None:
        """Sélectionne une piste et un step en un clic sur un bouton timeline."""
        self._editing_track_idx = track_idx
        self._editing_step_idx = step_idx
        self._refresh_tracks_ui()
        self._refresh_step_params()
        self._refresh_key_highlights()

    def _on_add_track(self) -> None:
        """Ajoute une nouvelle piste à l'effet custom en cours d'édition."""
        ce = self._current_custom_effect()
        if not ce:
            return
        track_num = len(ce.tracks) + 1
        new_track = EffectTrack(
            name=f"Piste {track_num}",
            target_mode="fixed",
            steps=[EffectStep(time_ms=0, color="#FFFFFF", fade_ms=0)],
        )
        ce.tracks.append(new_track)
        self._editing_track_idx = len(ce.tracks) - 1
        self._editing_step_idx = 0
        self._refresh_tracks_ui()
        self._refresh_step_params()
        self._refresh_key_highlights()
        self._restart_custom_preview()

    def _on_remove_track(self) -> None:
        """Supprime la piste courante."""
        ce = self._current_custom_effect()
        if not ce or len(ce.tracks) <= 1:
            return
        del ce.tracks[self._editing_track_idx]
        self._editing_track_idx = min(self._editing_track_idx, len(ce.tracks) - 1)
        self._editing_step_idx = 0
        self._refresh_tracks_ui()
        self._refresh_step_params()
        self._refresh_key_highlights()
        self._restart_custom_preview()

    def _on_target_mode_changed(self, mode: str) -> None:
        """Change le mode cible de la piste courante."""
        track = self._current_track()
        if not track or track.target_mode == mode:
            return
        track.target_mode = mode
        # Reset la référence relative quand on change de mode
        self._relative_ref_key = None
        self._refresh_tracks_ui()
        self._refresh_key_highlights()
        self._restart_custom_preview()
        self._refresh_code_preview()

    def _on_add_step(self) -> None:
        """Ajoute un step à la piste courante."""
        track = self._current_track()
        if not track:
            return
        last = track.steps[-1] if track.steps else EffectStep()
        new_step = EffectStep(
            time_ms=last.time_ms + last.hold_ms + last.fade_ms + 100,
            color=last.color,
            hold_ms=last.hold_ms,
            fade_ms=last.fade_ms,
        )
        track.steps.append(new_step)
        self._editing_step_idx = len(track.steps) - 1
        self._refresh_tracks_ui()
        self._refresh_step_params()
        self._restart_custom_preview()

    def _on_remove_step(self) -> None:
        """Supprime le step courant de la piste."""
        track = self._current_track()
        if not track or len(track.steps) <= 1:
            return
        del track.steps[self._editing_step_idx]
        self._editing_step_idx = min(self._editing_step_idx, len(track.steps) - 1)
        self._refresh_tracks_ui()
        self._refresh_step_params()
        self._restart_custom_preview()

    def _on_step_time_changed(self, value: int) -> None:
        """Met à jour le temps du step sélectionné."""
        step = self._current_step()
        if step:
            step.time_ms = value
            self._refresh_tracks_ui()

    def _on_step_color_clicked(self) -> None:
        """Ouvre un QColorDialog pour la couleur d'arrivée du step."""
        step = self._current_step()
        if not step:
            return
        current = QColor(step.color)
        color = QColorDialog.getColor(current, self, tr("rgb.custom_effects.step_color_to"))
        if color.isValid():
            step.color = color.name().upper()
            self._btn_step_color.setStyleSheet(f"background-color: {step.color};")
            self._refresh_tracks_ui()
            self._restart_custom_preview()

    def _on_color_to_clicked(self) -> None:
        """Ouvre un QColorDialog pour la couleur d'arrivée du fondu."""
        step = self._current_step()
        if not step:
            return
        current_to = step.color_to or step.color
        color = QColorDialog.getColor(
            QColor(current_to), self, tr("rgb.custom_effects.step_color_to"),
        )
        if color.isValid():
            step.color_to = color.name().upper()
            self._btn_color_to.setStyleSheet(f"background-color: {step.color_to};")
            self._refresh_tracks_ui()
            self._restart_custom_preview()

    def _on_fade_toggled(self, checked: bool) -> None:
        """Active/désactive le fondu pour le step sélectionné."""
        step = self._current_step()
        if not step:
            return
        if checked:
            step.fade_ms = max(step.fade_ms, 200)  # valeur par défaut si était 0
            if not step.color_to:
                step.color_to = step.color  # pré-remplir avec la même couleur
        else:
            step.fade_ms = 0
            step.color_to = ""
        self._refresh_step_params()
        self._refresh_tracks_ui()
        self._restart_custom_preview()

    def _on_step_hold_changed(self, value: int) -> None:
        """Met à jour la durée de maintien du step sélectionné."""
        step = self._current_step()
        if step:
            step.hold_ms = value
            self._refresh_tracks_ui()

    def _on_step_fade_changed(self, value: int) -> None:
        """Met à jour la durée du fondu du step sélectionné."""
        step = self._current_step()
        if step:
            step.fade_ms = value
            self._refresh_tracks_ui()

    def _on_step_moved(self, track_idx: int, step_idx: int, new_time_ms: int) -> None:
        """Appelé quand un StepItem est déplacé sur la timeline."""
        self._spin_step_time.blockSignals(True)
        self._spin_step_time.setValue(new_time_ms)
        self._spin_step_time.blockSignals(False)
        self._refresh_code_preview()

    def _on_copy_code(self) -> None:
        """Copie le code C du preview dans le presse-papier."""
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(self._code_preview.toPlainText())

    def _refresh_code_preview(self) -> None:
        """Rend le template rgb_matrix_user.inc.j2 avec l'effet custom courant."""
        ce = self._current_custom_effect()
        if not ce:
            self._code_preview.setPlainText("")
            return
        try:
            from jinja2 import Environment, FileSystemLoader
            from modules.build_manager.template_generator import TEMPLATES_DIR, _build_timeline_effects

            kb = self._find_current_keyboard()
            matrix_rows = kb.matrix.get("rows", 5) if kb else 5
            is_split = kb.split if kb else True

            timeline_ctx = _build_timeline_effects([ce], matrix_rows, is_split)
            env = Environment(
                loader=FileSystemLoader(str(TEMPLATES_DIR)),
                autoescape=False,
                keep_trailing_newline=True,
            )
            tmpl = env.get_template("rgb_matrix_user.inc.j2")
            code = tmpl.render(
                custom_effects=[],
                timeline_effects=timeline_ctx,
                has_custom_effects=False,
                has_reactive_effects=False,
                has_timeline_effects=bool(timeline_ctx),
            )
            self._code_preview.setPlainText(code)
        except Exception:
            logger.exception("Erreur lors du rendu du code preview")

    def _restart_custom_preview(self) -> None:
        """Relance le preview custom après une modification de l'effet."""
        ce = self._current_custom_effect()
        if ce and self._preview:
            self._preview.start_custom(ce)
        self._refresh_code_preview()

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
        is_split = kb.split if kb else True
        padding = 4
        canvas_w = cols * KEY_SIZE + padding * 2
        canvas_h = rows * KEY_SIZE + padding * 2
        for side_code in (("L", "R") if is_split else ("L",)):
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
                    item = KeyColorItem(key_id, 1.0, 1.0, 0.0, self._on_key_clicked, self._on_key_right_clicked)
                    item.setPos(padding + c * KEY_SIZE, padding + r * KEY_SIZE)
                    scene.addItem(item)
                    self._key_buttons[key_id] = item
            self._keys_hbox.addWidget(view)
            self._keys_hbox.addSpacing(16)

    def _build_physical_layout(self, kb: KeyboardDefinition) -> None:
        """Positionnement absolu d'après les coordonnées physiques du YAML."""
        # Split : deux panneaux left/right ; non-split : un seul panneau "keys"
        if kb.split:
            panels = [("L", "left"), ("R", "right")]
        else:
            panels = [("L", "keys")]

        padding = 4
        for side_code, yaml_side in panels:
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
                    key_id, k.w, k.h, getattr(k, "r", 0.0),
                    self._on_key_clicked, self._on_key_right_clicked,
                )
                item.setPos(padding + (k.x - min_x) * KEY_SIZE, padding + (k.y - min_y) * KEY_SIZE)
                scene.addItem(item)
                self._key_buttons[key_id] = item

            self._keys_hbox.addWidget(view)
            self._keys_hbox.addSpacing(16)

    def _find_current_keyboard(self) -> KeyboardDefinition | None:
        if self._current_kb and self._current_kb.model == self._model.keyboard.model:
            return self._current_kb
        keyboards = load_all_keyboards(KEYBOARDS_DIR, CUSTOM_KEYBOARDS_DIR)
        return next((kb for kb in keyboards if kb.model == self._model.keyboard.model), None)

    # ────────────────────────────────────────────────── Key click handlers ──

    def _on_key_clicked(self, key_id: str) -> None:
        if self._trigger_mode:
            if self._model.rgb.effects:
                self._model.rgb.effects[0].trigger_key = key_id
                self._lbl_trigger.setText(key_id)
                logger.info("Touche déclencheur définie : %s", key_id)
            self._trigger_mode = False
            self._btn_trigger.setText(tr("rgb.ripple.trigger_btn"))
            return
        # Mode édition custom : toggle la touche dans keys_fixed ou relative
        if self._editing_custom_idx is not None and self._effect_stack.currentIndex() == 3:
            track = self._current_track()
            if track and track.target_mode == "fixed":
                if key_id in track.keys_fixed:
                    track.keys_fixed.remove(key_id)
                else:
                    track.keys_fixed.append(key_id)
                self._refresh_tracks_ui()
                self._refresh_key_highlights()
                self._restart_custom_preview()
                self._refresh_code_preview()
                return
            if track and track.target_mode == "relative":
                if self._relative_ref_key is None:
                    # Premier clic = touche de référence (centre du motif)
                    self._relative_ref_key = key_id
                    self._refresh_tracks_ui()
                    self._refresh_key_highlights()
                    return
                # Clic gauche = ajouter l'offset (coordonnées QMK)
                ref_rc = self._key_to_qmk_rc(self._relative_ref_key)
                click_rc = self._key_to_qmk_rc(key_id)
                if ref_rc and click_rc:
                    dr = click_rc[0] - ref_rc[0]
                    dc = click_rc[1] - ref_rc[1]
                    already = any(o.dr == dr and o.dc == dc for o in track.keys_offset)
                    if not already:
                        track.keys_offset.append(KeyOffset(dr=dr, dc=dc))
                    self._refresh_tracks_ui()
                    self._refresh_key_highlights()
                    self._restart_custom_preview()
                    self._refresh_code_preview()
                return
        current = QColor(self._model.rgb.per_key.get(key_id, "#FFFFFF"))
        color = QColorDialog.getColor(current, self, tr("rgb.key_color_fmt").format(key_id=key_id))
        if color.isValid():
            hex_color = color.name().upper()
            self._apply_color(key_id, hex_color)

    def _on_key_right_clicked(self, key_id: str) -> None:
        """Clic droit : retirer une touche de la sélection (fixed ou relative)."""
        if self._editing_custom_idx is None or self._effect_stack.currentIndex() != 3:
            return
        track = self._current_track()
        if not track:
            return
        if track.target_mode == "fixed":
            if key_id in track.keys_fixed:
                track.keys_fixed.remove(key_id)
                self._refresh_tracks_ui()
                self._refresh_key_highlights()
                self._restart_custom_preview()
                self._refresh_code_preview()
        elif track.target_mode == "relative" and self._relative_ref_key:
            # Clic droit sur la référence = reset la référence
            if key_id == self._relative_ref_key:
                self._relative_ref_key = None
                track.keys_offset.clear()
                self._refresh_tracks_ui()
                self._refresh_key_highlights()
                self._restart_custom_preview()
                self._refresh_code_preview()
                return
            ref_rc = self._key_to_qmk_rc(self._relative_ref_key)
            click_rc = self._key_to_qmk_rc(key_id)
            if ref_rc and click_rc:
                dr = click_rc[0] - ref_rc[0]
                dc = click_rc[1] - ref_rc[1]
                before = len(track.keys_offset)
                track.keys_offset = [o for o in track.keys_offset if not (o.dr == dr and o.dc == dc)]
                if len(track.keys_offset) < before:
                    self._refresh_tracks_ui()
                    self._refresh_key_highlights()
                    self._restart_custom_preview()
                    self._refresh_code_preview()

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

    def _current_effect_def(self) -> EffectDef | None:
        """Retourne l'EffectDef correspondant au row sélectionné (ignore les séparateurs)."""
        idx = self._row_to_effect.get(self._effect_list.currentRow())
        if idx is not None and 0 <= idx < len(EFFECT_TYPES):
            return EFFECT_TYPES[idx]
        return None

    def _on_effect_type_changed(self, row: int) -> None:
        # Custom effect sélectionné ?
        ci = self._row_to_custom.get(row)
        if ci is not None:
            self._lbl_effect_desc.setText(tr("rgb.custom_effects.editor_desc"))
            self._effect_stack.setCurrentIndex(3)  # page éditeur timeline
            self._load_custom_into_editor(ci)
            # Lancer le preview custom
            ce = self._model.rgb.custom_effects[ci]
            if self._preview:
                self._preview.start_custom(ce)
            return

        idx = self._row_to_effect.get(row)
        if idx is None:
            return  # séparateur cliqué — ignorer
        self._editing_custom_idx = None  # quitter le mode édition custom
        if self._preview:
            self._preview.stop_custom()
        effect_def = EFFECT_TYPES[idx]
        # M1: quitter le mode trigger si actif lors du changement d'effet
        if self._trigger_mode:
            self._trigger_mode = False
            self._btn_trigger.setText(tr("rgb.ripple.trigger_btn"))
        effect = self._ensure_effect(effect_def.id)
        effect.type = effect_def.id
        self._lbl_effect_desc.setText(effect_def.description)
        self._effect_stack.setCurrentIndex(_stack_page_for(effect_def.id))
        self._refresh_effect_buttons()
        self._update_preview()
        logger.info("Effet RGB changé : %s", effect_def.id)

    def _on_color_primary_clicked(self) -> None:
        edef = self._current_effect_def()
        if not edef:
            return
        effect = self._ensure_effect(edef.id)
        current = QColor(effect.color_primary)
        color = QColorDialog.getColor(current, self, tr("rgb.dialog.primary_color"))
        if color.isValid():
            effect.color_primary = color.name().upper()
            self._refresh_effect_buttons()
            self._update_preview()

    def _on_color_secondary_clicked(self) -> None:
        edef = self._current_effect_def()
        if not edef:
            return
        effect = self._ensure_effect(edef.id)
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

    def _on_speed_changed(self, value: int) -> None:
        self._speed_label.setText(str(value))
        edef = self._current_effect_def()
        if edef:
            effect = self._ensure_effect(edef.id)
            effect.speed = value

    def _on_brightness_changed(self, value: int) -> None:
        self._brightness_label.setText(str(value))
        edef = self._current_effect_def()
        if edef:
            effect = self._ensure_effect(edef.id)
            effect.brightness = value

    def _on_trigger_clicked(self) -> None:
        self._trigger_mode = True
        self._btn_trigger.setText(tr("rgb.ripple.trigger_click"))

    # ──────────────────────── Effect enable/disable (checkboxes) ──

    def _on_effect_check_changed(self, item: QListWidgetItem) -> None:
        """Met à jour enabled_effects quand une checkbox change."""
        row = self._effect_list.row(item)
        eidx = self._row_to_effect.get(row)
        if eidx is None:
            return
        effect_def = EFFECT_TYPES[eidx]
        if effect_def.custom or effect_def.id == "static":
            return
        # Rebuild the enabled list from all checked items
        enabled = []
        for list_row, effect_idx in self._row_to_effect.items():
            edef = EFFECT_TYPES[effect_idx]
            if edef.custom or edef.id == "static":
                continue
            list_item = self._effect_list.item(list_row)
            if list_item and list_item.checkState() == Qt.CheckState.Checked:
                enabled.append(edef.id)
        self._model.rgb.enabled_effects = enabled

    def _refresh_effect_buttons(self) -> None:
        """Met à jour les couleurs affichées sur les boutons de couleur."""
        if not self._model.rgb.effects:
            return
        effect = self._model.rgb.effects[0]
        primary_style = f"background-color: {effect.color_primary};"
        secondary_style = f"background-color: {effect.color_secondary};"
        self._btn_static_color.setStyleSheet(primary_style)
        self._btn_ripple_primary.setStyleSheet(primary_style)
        self._btn_color_secondary.setStyleSheet(secondary_style)

    # ────────────────────────────────────────────────────── Sync / Refresh ──

    def _sync_from_model(self) -> None:
        """Restaure les couleurs touches et l'état effets depuis le modèle."""
        for key_id, hex_color in self._model.rgb.per_key.items():
            self._apply_color(key_id, hex_color)
        if self._model.rgb.effects:
            effect = self._model.rgb.effects[0]
            # Trouver le row de la liste correspondant au type d'effet
            target_row = 0
            for list_row, effect_idx in self._row_to_effect.items():
                if EFFECT_TYPES[effect_idx].id == effect.type:
                    target_row = list_row
                    break
            else:
                logger.warning("Type d'effet inconnu '%s' — retour à static", effect.type)
            self._effect_list.blockSignals(True)
            self._effect_list.setCurrentRow(target_row)
            self._effect_list.blockSignals(False)
            eidx = self._row_to_effect.get(target_row, 0)
            effect_def = EFFECT_TYPES[eidx]
            self._lbl_effect_desc.setText(effect_def.description)
            self._effect_stack.setCurrentIndex(_stack_page_for(effect.type))
            # Spinbox fade_ms
            self._fade_ms_spin.blockSignals(True)
            self._fade_ms_spin.setValue(effect.fade_ms)
            self._fade_ms_spin.blockSignals(False)
            # Speed + brightness sliders
            self._speed_slider.blockSignals(True)
            self._speed_slider.setValue(effect.speed)
            self._speed_slider.blockSignals(False)
            self._speed_label.setText(str(effect.speed))
            self._brightness_slider.blockSignals(True)
            self._brightness_slider.setValue(effect.brightness)
            self._brightness_slider.blockSignals(False)
            self._brightness_label.setText(str(effect.brightness))
            # Trigger key label
            if effect.trigger_key:
                self._lbl_trigger.setText(effect.trigger_key)
            # Checkbox sync
            enabled_set = set(self._model.rgb.enabled_effects) if self._model.rgb.enabled_effects else None
            self._effect_list.blockSignals(True)
            for list_row, effect_idx in self._row_to_effect.items():
                edef = EFFECT_TYPES[effect_idx]
                if edef.custom or edef.id == "static":
                    continue
                list_item = self._effect_list.item(list_row)
                if list_item:
                    if enabled_set is None or edef.id in enabled_set:
                        list_item.setCheckState(Qt.CheckState.Checked)
                    else:
                        list_item.setCheckState(Qt.CheckState.Unchecked)
            self._effect_list.blockSignals(False)
            self._refresh_effect_buttons()

    def refresh_layout(self, keyboard: KeyboardDefinition | None = None) -> None:
        """Reconstruit le layout quand le modèle de clavier change."""
        self._current_kb = keyboard
        if self._preview:  # M1: arrêter l'ancien timer avant remplacement
            self._preview.stop()
        self._build_layout()
        self._preview = EffectPreview(self._key_buttons)
        self._sync_from_model()
