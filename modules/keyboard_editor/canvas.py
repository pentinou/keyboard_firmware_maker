"""canvas — canvas QGraphicsScene pour l'éditeur de clavier custom.

Contient KeyItem (touche draggable avec snap-to-grid) et KeyboardCanvas
(QGraphicsView avec scène unique pour claviers split et non-split).
"""
from __future__ import annotations

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QPen
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGraphicsEllipseItem,
    QGraphicsLineItem,
    QGraphicsPixmapItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsView,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from i18n import tr

GRID_PX: int = 40
KEY_FILL_COLOR = QColor("#4A90D9")
KEY_FILL_COLOR_FIXED = QColor("#2E6B9E")   # override manuel confirmé
KEY_SELECTED_COLOR = QColor("#F5A623")
KEY_BORDER_COLOR = QColor("#1C3A5E")
INDICATOR_OLED_COLOR = QColor("#7B52C8")
INDICATOR_ENC_COLOR = QColor("#2E8C6A")


class KeyItem(QGraphicsRectItem):
    """Représentation graphique d'une touche sur le canvas.

    Draggable, sélectionnable, snap-to-grid via itemChange.
    Double-clic → KeyPropsDialog pour override manuel de row/col/w.
    """

    def __init__(
        self,
        row: int,
        col: int,
        x_u: float,
        y_u: float,
        w_u: float,
        h_u: float,
        side: str,
        canvas: "KeyboardCanvas",
        r_deg: float = 0.0,
    ) -> None:
        px_x = x_u * GRID_PX
        px_y = y_u * GRID_PX
        px_w = w_u * GRID_PX
        px_h = h_u * GRID_PX
        super().__init__(0, 0, px_w - 2, px_h - 2)

        self._row = row        # -1 = auto-assigné à la sauvegarde
        self._col = col        # -1 = auto-assigné à la sauvegarde
        self._w_u = w_u
        self._h_u = h_u
        self._side = side
        self._canvas = canvas
        self._manually_fixed = (row >= 0 and col >= 0)

        self.setPos(px_x, px_y)
        # Rotation autour du centre de la touche
        self.setTransformOriginPoint((px_w - 2) / 2, (px_h - 2) / 2)
        if r_deg:
            self.setRotation(r_deg)
        self.setFlags(
            QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsRectItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        # Init apparence directement (évite isSelected() hors scène — F5)
        self.setBrush(QBrush(KEY_FILL_COLOR))
        self.setPen(QPen(KEY_BORDER_COLOR, 1))

    # ── Propriétés ──────────────────────────────────────────────────────────

    @property
    def row(self) -> int:
        return self._row

    @row.setter
    def row(self, value: int) -> None:
        self._row = value
        self._update_appearance()

    @property
    def col(self) -> int:
        return self._col

    @col.setter
    def col(self, value: int) -> None:
        self._col = value
        self._update_appearance()

    @property
    def w_u(self) -> float:
        return self._w_u

    @w_u.setter
    def w_u(self, value: float) -> None:
        self._w_u = value
        self.setRect(0, 0, value * GRID_PX - 2, self._h_u * GRID_PX - 2)

    @property
    def h_u(self) -> float:
        return self._h_u

    @property
    def side(self) -> str:
        return self._side

    @side.setter
    def side(self, value: str) -> None:
        self._side = value

    @property
    def manually_fixed(self) -> bool:
        return self._manually_fixed

    # ── Qt overrides ────────────────────────────────────────────────────────

    def itemChange(self, change: QGraphicsRectItem.GraphicsItemChange, value: object) -> object:
        """Snap-to-grid sur déplacement.

        CRITIQUE : retourner la position snappée — ne jamais appeler setPos() ici
        (boucle infinie). Qt applique la valeur retournée automatiquement.
        """
        if (
            change == QGraphicsRectItem.GraphicsItemChange.ItemPositionChange
            and self._canvas.snap_enabled
        ):
            snapped_x = round(value.x() / GRID_PX) * GRID_PX
            snapped_y = round(value.y() / GRID_PX) * GRID_PX
            return QPointF(snapped_x, snapped_y)
        return super().itemChange(change, value)

    def mouseDoubleClickEvent(self, event) -> None:
        """Ouvre KeyPropsDialog pour override manuel de row/col/w."""
        dlg = KeyPropsDialog(self)
        dlg.exec()

    def paint(self, painter, option, widget=None) -> None:
        """Dessine la touche avec label R{row}C{col}."""
        super().paint(painter, option, widget)
        label = f"R{self._row}C{self._col}" if self._row >= 0 else "?"
        painter.setPen(QPen(Qt.GlobalColor.white))
        font = QFont()
        font.setPointSize(7)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, label)

    # ── Interne ─────────────────────────────────────────────────────────────

    def _update_appearance(self) -> None:
        if self.isSelected():
            fill = KEY_SELECTED_COLOR
        elif self._manually_fixed:
            fill = KEY_FILL_COLOR_FIXED
        else:
            fill = KEY_FILL_COLOR
        self.setBrush(QBrush(fill))
        self.setPen(QPen(KEY_BORDER_COLOR, 1))


class KeyPropsDialog(QDialog):
    """Dialog pour éditer row, col, largeur d'une touche.

    Valide l'override manuel — marque la touche comme "fixée".
    """

    def __init__(self, item: KeyItem, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._item = item
        self.setWindowTitle(tr("keyboard_editor.key_props_title"))

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self._row_spin = QSpinBox()
        self._row_spin.setRange(0, 63)
        self._row_spin.setValue(max(item.row, 0))
        form.addRow(tr("keyboard_editor.key_row"), self._row_spin)

        self._col_spin = QSpinBox()
        self._col_spin.setRange(0, 63)
        self._col_spin.setValue(max(item.col, 0))
        form.addRow(tr("keyboard_editor.key_col"), self._col_spin)

        self._w_spin = QDoubleSpinBox()
        self._w_spin.setRange(0.5, 8.0)
        self._w_spin.setSingleStep(0.25)
        self._w_spin.setDecimals(2)
        self._w_spin.setValue(item.w_u)
        form.addRow(tr("keyboard_editor.key_w"), self._w_spin)

        self._r_spin = QDoubleSpinBox()
        self._r_spin.setRange(-180.0, 180.0)
        self._r_spin.setSingleStep(5.0)
        self._r_spin.setDecimals(1)
        self._r_spin.setSuffix("°")
        self._r_spin.setWrapping(True)
        self._r_spin.setValue(round(item.rotation(), 1))
        form.addRow(tr("keyboard_editor.key_r"), self._r_spin)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._apply)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _apply(self) -> None:
        self._item.row = self._row_spin.value()
        self._item.col = self._col_spin.value()
        self._item.w_u = self._w_spin.value()
        self._item.setRotation(self._r_spin.value())
        self._item._manually_fixed = True
        self._item._update_appearance()
        self.accept()


class PcbImageItem(QGraphicsPixmapItem):
    """Image PCB déplaçable en fond du canvas (z=-1)."""

    def __init__(self, pixmap) -> None:
        super().__init__(pixmap)
        self.setZValue(-1)
        self.setOpacity(0.6)
        self.setFlags(
            QGraphicsPixmapItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsPixmapItem.GraphicsItemFlag.ItemIsSelectable
        )


class OledIndicatorItem(QGraphicsRectItem):
    """Indicateur OLED déplaçable sur le canvas.

    Double-clic → rotation horizontal ↔ vertical.
    """

    _W_H = (2.0 * GRID_PX - 2, 0.75 * GRID_PX - 2)  # horizontal (défaut)
    _W_V = (0.75 * GRID_PX - 2, 2.0 * GRID_PX - 2)  # vertical

    def __init__(self, label: str, x_u: float, y_u: float) -> None:
        w, h = self._W_H
        super().__init__(0, 0, w, h)
        self._horizontal = True
        self.setPos(x_u * GRID_PX, y_u * GRID_PX)
        self._label = label
        self.setBrush(QBrush(INDICATOR_OLED_COLOR))
        self.setPen(QPen(QColor("#3A1E7C"), 1))
        self.setFlags(
            QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable
        )
        self.setToolTip("Double-clic : pivoter")

    def rotate(self) -> None:
        """Bascule orientation horizontal ↔ vertical."""
        self._horizontal = not self._horizontal
        w, h = self._W_H if self._horizontal else self._W_V
        self.setRect(0, 0, w, h)
        self.update()

    def mouseDoubleClickEvent(self, event) -> None:
        self.rotate()

    def paint(self, painter, option, widget=None) -> None:
        super().paint(painter, option, widget)
        painter.setPen(QPen(Qt.GlobalColor.white))
        font = QFont()
        font.setPointSize(6)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self._label)


class EncoderIndicatorItem(QGraphicsEllipseItem):
    """Indicateur encodeur déplaçable sur le canvas."""

    def __init__(self, label: str, x_u: float, y_u: float) -> None:
        size_px = 0.9 * GRID_PX
        super().__init__(0, 0, size_px, size_px)
        self.setPos(x_u * GRID_PX, y_u * GRID_PX)
        self._label = label
        self.setBrush(QBrush(INDICATOR_ENC_COLOR))
        self.setPen(QPen(QColor("#1A5C3A"), 1))
        self.setFlags(
            QGraphicsEllipseItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsEllipseItem.GraphicsItemFlag.ItemIsSelectable
        )

    def paint(self, painter, option, widget=None) -> None:
        super().paint(painter, option, widget)
        painter.setPen(QPen(Qt.GlobalColor.white))
        font = QFont()
        font.setPointSize(6)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self._label)


class KeyboardCanvas(QGraphicsView):
    """Vue QGraphicsScene unique pour le layout de touches.

    Gère split (séparateur visuel + side sur KeyItem) et non-split.
    La scène est unique — W1 : pas de deux scènes séparées.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.snap_enabled: bool = True
        self._separator: QGraphicsLineItem | None = None
        self._pcb_images: list[PcbImageItem] = []
        self._oled_indicators: list[OledIndicatorItem] = []
        self._encoder_indicators: list[EncoderIndicatorItem] = []

        self.setMinimumSize(600, 300)
        self.setBackgroundBrush(QBrush(QColor("#2B2B2B")))
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)

    # ── API publique ────────────────────────────────────────────────────────

    def add_key(
        self,
        row: int = -1,
        col: int = -1,
        x_u: float = 0.0,
        y_u: float = 0.0,
        w_u: float = 1.0,
        h_u: float = 1.0,
        side: str = "keys",
        r_deg: float = 0.0,
    ) -> KeyItem:
        """Ajoute une touche au canvas et retourne le KeyItem créé."""
        item = KeyItem(row, col, x_u, y_u, w_u, h_u, side, self, r_deg)
        self._scene.addItem(item)
        return item

    def remove_selected(self) -> None:
        """Supprime les items sélectionnés (touches, indicateurs OLED/encodeur)."""
        for item in list(self._scene.selectedItems()):
            if isinstance(item, KeyItem):
                self._scene.removeItem(item)
            elif isinstance(item, OledIndicatorItem):
                self._scene.removeItem(item)
                if item in self._oled_indicators:
                    self._oled_indicators.remove(item)
            elif isinstance(item, EncoderIndicatorItem):
                self._scene.removeItem(item)
                if item in self._encoder_indicators:
                    self._encoder_indicators.remove(item)

    def get_keys(self, side: str | None = None) -> list[KeyItem]:
        """Retourne les KeyItems, filtrés par side si fourni."""
        items = [i for i in self._scene.items() if isinstance(i, KeyItem)]
        if side is not None:
            items = [i for i in items if i.side == side]
        return items

    def clear_keys(self, side: str | None = None) -> None:
        """Supprime tous les KeyItems (ou ceux d'un side donné)."""
        for item in self.get_keys(side):
            self._scene.removeItem(item)

    def mirror_left_to_right(self) -> None:
        """Duplique les touches gauche en miroir vers le côté droit.

        Utilise la position du séparateur comme axe de symétrie (défaut : 7U).
        La rotation est inversée (ex : 15° → -15°) pour un vrai miroir physique.
        """
        sep_px = self._separator.line().x1() if self._separator else 7 * GRID_PX
        sep_u = sep_px / GRID_PX
        self.clear_keys(side="right")
        for item in self.get_keys(side="left"):
            x_u = item.pos().x() / GRID_PX
            y_u = item.pos().y() / GRID_PX
            right_x_u = 2 * sep_u - x_u - item.w_u
            self.add_key(
                row=-1,
                col=-1,
                x_u=right_x_u,
                y_u=y_u,
                w_u=item.w_u,
                h_u=item.h_u,
                side="right",
                r_deg=-item.rotation(),
            )

    def load_from_layout(self, keys: list, side: str = "keys") -> None:
        """Peuple le canvas depuis une liste de KeyLayout."""
        for k in keys:
            self.add_key(
                row=k.row,
                col=k.col,
                x_u=k.x,
                y_u=k.y,
                w_u=k.w,
                h_u=k.h,
                side=side,
                r_deg=getattr(k, "r", 0.0),
            )

    def add_pcb_image(self, pixmap, x_offset_px: int = 0) -> PcbImageItem:
        """Ajoute une image PCB déplaçable au canvas.

        Args:
            pixmap: QPixmap à afficher (déjà scalé par l'appelant).
            x_offset_px: Décalage horizontal en pixels (pour la moitié droite d'un split).
        """
        item = PcbImageItem(pixmap)
        item.setPos(x_offset_px, 0)
        self._scene.addItem(item)
        self._pcb_images.append(item)
        return item

    def remove_background_images(self) -> None:
        """Retire toutes les images PCB du canvas."""
        for item in self._pcb_images:
            self._scene.removeItem(item)
        self._pcb_images.clear()

    def set_oled_indicators(self, visible: bool, split: bool) -> None:
        """Affiche ou masque les indicateurs OLED sur le canvas."""
        for item in self._oled_indicators:
            self._scene.removeItem(item)
        self._oled_indicators.clear()
        if not visible:
            return
        left = OledIndicatorItem(tr("keyboard_editor.indicator_oled_left"), 0.0, 0.0)
        self._scene.addItem(left)
        self._oled_indicators.append(left)
        if split:
            right = OledIndicatorItem(tr("keyboard_editor.indicator_oled_right"), 8.0, 0.0)
            self._scene.addItem(right)
            self._oled_indicators.append(right)

    def set_encoder_indicator(self, visible: bool, split: bool) -> None:
        """Affiche ou masque les indicateurs encodeur sur le canvas."""
        for item in self._encoder_indicators:
            self._scene.removeItem(item)
        self._encoder_indicators.clear()
        if not visible:
            return
        label = tr("keyboard_editor.indicator_encoder")
        enc = EncoderIndicatorItem(label, 5.0, 4.0)
        self._scene.addItem(enc)
        self._encoder_indicators.append(enc)
        if split:
            enc_r = EncoderIndicatorItem(label, 9.0, 4.0)
            self._scene.addItem(enc_r)
            self._encoder_indicators.append(enc_r)

    def add_split_separator(self, x_px: int | None = None) -> None:
        """Ajoute un séparateur vertical visuel pour les claviers split."""
        if self._separator is not None:
            self._scene.removeItem(self._separator)
        if x_px is None:
            x_px = 7 * GRID_PX   # séparateur par défaut à 7U
        line = QGraphicsLineItem(x_px, -20, x_px, 20 * GRID_PX)
        line.setPen(QPen(QColor("#FF6B6B"), 2, Qt.PenStyle.DashLine))
        line.setFlag(QGraphicsLineItem.GraphicsItemFlag.ItemIsSelectable, False)
        line.setFlag(QGraphicsLineItem.GraphicsItemFlag.ItemIsMovable, False)
        self._scene.addItem(line)
        self._separator = line

    def remove_split_separator(self) -> None:
        """Retire le séparateur split si présent."""
        if self._separator is not None:
            self._scene.removeItem(self._separator)
            self._separator = None
