"""OledWidget — onglet de personnalisation OLED.

Deux canvases indépendants (gauche / droite) pour clavier split.
Chaque côté supporte plusieurs images importées (PNG, BMP, GIF),
positionnables par drag & drop avec snap-to-grid.
Les overlays (Layer, Caps Lock, WPM, Luna, Bongo Cat) sont également draggables.
"""
from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from i18n import tr
from models.project_model import OledImageItem, OledSideConfig, ProjectModel
from modules.oled_editor.processor import (
    OLED_HEIGHT,
    OLED_WIDTH,
    convert_image_natural,
    rotate_frame_90cw,
)

logger = logging.getLogger(__name__)

# Dimensions du sprite Luna (en pixels OLED)
_LUNA_W = 32
_LUNA_H = 22


class _OledCanvas(QWidget):
    """Zone de prévisualisation OLED 32×128 avec overlays draggables.

    Supporte plusieurs images indépendantes positionnables par drag & drop.
    La frame de sélection (jaune pointillée) s'ajuste à la taille réelle du contenu.
    """

    # Émis quand la sélection change (mouse press / deselect). La valeur est le
    # nom de l'item sélectionné (ex: "image:0", "layer") ou "" si aucun.
    # Utilisé par le widget parent pour synchroniser des contrôles per-item
    # (ex: Phase 4 OLED ZMK custom — spinbox layer suit l'image sélectionnée).
    selection_changed = Signal(str)

    # Émis quand un widget ZMK natif est déplacé par drag. Permet au parent
    # OledWidget de re-synchroniser les QSpinBox col/line correspondants.
    # Args : (widget_name, col, line). widget_name ∈ {zmk_battery, zmk_output,
    # zmk_layer, zmk_peripheral}.
    widget_position_changed = Signal(str, int, int)

    SCALE = 3
    CHAR_W = 6 * SCALE   # 18px par colonne curseur QMK
    PAGE_H = 8 * SCALE   # 24px par page QMK

    def __init__(self, side: OledSideConfig, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._side = side
        self._pixmaps: list[QPixmap | None] = []  # one per side.images entry
        self._dragging_item: str | None = None  # "layer", "caps_lock", "wpm", "katawajojo", "luna", "ocean_dream", "bongo", "image:N"
        self._drag_offset_x = 0
        self._drag_offset_y = 0
        self._selected_item: str | None = None
        self._firmware: str = "qmk"  # défini par OledWidget.set_firmware()
        w = OLED_WIDTH * self.SCALE
        h = OLED_HEIGHT * self.SCALE
        self.setMinimumSize(w, h)
        self.setFixedSize(w, h)
        self.setMouseTracking(True)

    def set_firmware(self, firmware: str) -> None:
        """Choisit quel jeu d'overlays afficher (qmk ou zmk)."""
        self._firmware = firmware
        # Désélectionner si l'item courant n'existe plus dans le nouveau mode
        if self._selected_item and not self._selected_item.startswith("image:"):
            self._selected_item = None
        self.update()

    def set_image_pixmap(self, idx: int, pixmap: QPixmap) -> None:
        """Met à jour le pixmap de l'image à l'index idx."""
        while len(self._pixmaps) <= idx:
            self._pixmaps.append(None)
        self._pixmaps[idx] = pixmap
        self.update()

    def sync_images(self, count: int) -> None:
        """Ajuste la liste _pixmaps au nombre d'images actuel."""
        while len(self._pixmaps) < count:
            self._pixmaps.append(None)
        self._pixmaps = self._pixmaps[:count]
        self.update()

    def _image_rect(self, idx: int) -> tuple[int, int, int, int] | None:
        """Rect (x, y, w, h) en pixels widget pour l'image idx, basé sur sa taille naturelle."""
        images = self._side.images
        if idx >= len(images):
            return None
        img_item = images[idx]
        if not img_item.frames:
            return None
        nat_w = max(1, img_item.natural_w)
        nat_h = max(1, img_item.natural_h)
        x = img_item.col * self.CHAR_W
        y = img_item.line * self.PAGE_H
        return (x, y, nat_w * self.SCALE, nat_h * self.SCALE)

    def _item_rect(self, name: str) -> tuple[int, int, int, int] | None:
        """Rect (x, y, w, h) en pixels widget pour l'item donné, ou None si désactivé."""
        if name.startswith("image:"):
            return self._image_rect(int(name.split(":")[1]))
        s = self._side
        if name == "layer" and s.layer.enabled:
            return (s.layer.col * self.CHAR_W, s.layer.line * self.PAGE_H,
                    OLED_WIDTH * self.SCALE, 3 * self.PAGE_H)
        if name == "caps_lock" and s.caps_lock.enabled:
            return (s.caps_lock.col * self.CHAR_W, s.caps_lock.line * self.PAGE_H,
                    OLED_WIDTH * self.SCALE, 3 * self.PAGE_H)
        if name == "wpm" and s.wpm.enabled:
            return (s.wpm.col * self.CHAR_W, s.wpm.line * self.PAGE_H,
                    OLED_WIDTH * self.SCALE, 1 * self.PAGE_H)
        if name == "rgb_mode" and s.rgb_mode.enabled:
            return (s.rgb_mode.col * self.CHAR_W, s.rgb_mode.line * self.PAGE_H,
                    OLED_WIDTH * self.SCALE, 4 * self.PAGE_H)
        if name == "kfm" and s.kfm.enabled:
            return (s.kfm.col * self.CHAR_W, s.kfm.line * self.PAGE_H,
                    OLED_WIDTH * self.SCALE, 1 * self.PAGE_H)
        if name == "katawajojo" and s.katawajojo_enabled:
            return (0, s.katawajojo_line * self.PAGE_H,
                    OLED_WIDTH * self.SCALE, _LUNA_H * self.SCALE)
        if name == "luna" and s.luna_enabled:
            return (0, s.luna_line * self.PAGE_H,
                    OLED_WIDTH * self.SCALE, _LUNA_H * self.SCALE)
        if name == "ocean_dream" and s.ocean_dream_enabled:
            return (0, s.ocean_dream_line * self.PAGE_H,
                    OLED_WIDTH * self.SCALE, 16 * self.PAGE_H)
        if name == "bongo" and s.bongo_enabled:
            return (0, s.bongo_line * self.PAGE_H,
                    OLED_WIDTH * self.SCALE, 4 * self.PAGE_H)
        if name == "crab" and s.crab_enabled:
            return (0, s.crab_line * self.PAGE_H,
                    OLED_WIDTH * self.SCALE, 4 * self.PAGE_H)
        # ZMK widgets natifs — taille approximative du rendu LVGL
        if name == "zmk_battery" and s.zmk_battery.enabled:
            return (s.zmk_battery.col * self.CHAR_W, s.zmk_battery.line * self.PAGE_H,
                    4 * self.CHAR_W, 2 * self.PAGE_H)
        if name == "zmk_output" and s.zmk_output.enabled:
            return (s.zmk_output.col * self.CHAR_W, s.zmk_output.line * self.PAGE_H,
                    4 * self.CHAR_W, 2 * self.PAGE_H)
        if name == "zmk_layer" and s.zmk_layer.enabled:
            return (s.zmk_layer.col * self.CHAR_W, s.zmk_layer.line * self.PAGE_H,
                    5 * self.CHAR_W, 2 * self.PAGE_H)
        if name == "zmk_peripheral" and s.zmk_peripheral.enabled:
            return (s.zmk_peripheral.col * self.CHAR_W, s.zmk_peripheral.line * self.PAGE_H,
                    3 * self.CHAR_W, 2 * self.PAGE_H)
        return None

    def _overlay_items(self) -> list[tuple[str, tuple[int, int, int, int], QColor, str]]:
        """Liste des overlays visibles (hors images) : (name, rect, color, label).

        En mode QMK : layer/caps/wpm/rgb_mode/kfm + animations (luna, etc.).
        En mode ZMK : widgets natifs battery/output/layer/peripheral.
        Les images sont rendues séparément dans paintEvent quel que soit le mode.
        """
        result = []
        if self._firmware == "qmk":
            r = self._item_rect("layer")
            if r:
                result.append(("layer", r, QColor(0, 200, 0, 160), "LAYER"))
            r = self._item_rect("caps_lock")
            if r:
                result.append(("caps_lock", r, QColor(220, 200, 0, 160), "CAPS"))
            r = self._item_rect("wpm")
            if r:
                result.append(("wpm", r, QColor(0, 100, 220, 160), "WPM"))
            r = self._item_rect("rgb_mode")
            if r:
                result.append(("rgb_mode", r, QColor(220, 50, 220, 160), "RGB"))
            r = self._item_rect("kfm")
            if r:
                result.append(("kfm", r, QColor(160, 160, 160, 160), "<KFM>"))
            r = self._item_rect("katawajojo")
            if r:
                result.append(("katawajojo", r, QColor(0, 200, 200, 160), "Ktw"))
            r = self._item_rect("luna")
            if r:
                result.append(("luna", r, QColor(0, 180, 120, 160), "Luna"))
            r = self._item_rect("ocean_dream")
            if r:
                result.append(("ocean_dream", r, QColor(30, 80, 220, 160), "Ocean"))
            r = self._item_rect("bongo")
            if r:
                result.append(("bongo", r, QColor(220, 100, 0, 160), "BngoCat"))
            r = self._item_rect("crab")
            if r:
                result.append(("crab", r, QColor(200, 60, 60, 160), "Crab"))
        elif self._firmware == "zmk":
            r = self._item_rect("zmk_battery")
            if r:
                result.append(("zmk_battery", r, QColor(50, 130, 220, 160), "BAT"))
            r = self._item_rect("zmk_output")
            if r:
                result.append(("zmk_output", r, QColor(150, 80, 220, 160), "OUT"))
            r = self._item_rect("zmk_layer")
            if r:
                result.append(("zmk_layer", r, QColor(70, 200, 70, 160), "LAY"))
            r = self._item_rect("zmk_peripheral")
            if r:
                result.append(("zmk_peripheral", r, QColor(220, 130, 50, 160), "PER"))
        return result

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(40, 40, 40))

        # Draw images (natural size, at col/line position)
        for i, img_item in enumerate(self._side.images):
            if i >= len(self._pixmaps) or self._pixmaps[i] is None:
                continue
            r = self._image_rect(i)
            if r is None:
                continue
            x, y, w, h = r
            pix = self._pixmaps[i]
            if img_item.inverted:
                tmp = pix.toImage()
                tmp.invertPixels()
                pix = QPixmap.fromImage(tmp)
            painter.drawPixmap(x, y, pix)
            # Label "Img0" on non-selected images
            if self._selected_item != f"image:{i}":
                painter.setPen(QPen(QColor(200, 200, 200)))
                font = painter.font()
                font.setPointSize(8)
                painter.setFont(font)
                painter.drawText(x + 2, y + 10, f"Img{i}")

        # Draw overlays
        for name, (x, y, w, h), color, label in self._overlay_items():
            if name.startswith("zmk_"):
                # Rendu fidèle au widget OLED ZMK natif (blanc sur noir)
                self._paint_zmk_widget(painter, name, x, y, w, h)
            else:
                painter.fillRect(x, y, w, h, color)
                border_color = QColor(color.red(), color.green(), color.blue(), 255)
                painter.setPen(QPen(border_color))
                painter.drawRect(x, y, w - 1, h - 1)
                painter.setPen(QPen(QColor(255, 255, 255)))
                painter.drawText(x + 3, y + h // 2 + 4, label)

        # Selection frame (yellow dashed) around selected item
        if self._selected_item:
            sel_rect = self._item_rect(self._selected_item)
            if sel_rect:
                sx, sy, sw, sh = sel_rect
                pen = QPen(QColor(255, 220, 0))
                pen.setStyle(Qt.PenStyle.DashLine)
                pen.setWidth(2)
                painter.setPen(pen)
                painter.drawRect(sx + 1, sy + 1, sw - 3, sh - 3)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        px = int(event.position().x())
        py = int(event.position().y())

        # Test overlays first (higher z-order)
        for name, (x, y, w, h), _, _ in reversed(self._overlay_items()):
            if x <= px < x + w and y <= py < y + h:
                self._dragging_item = name
                self._drag_offset_x = px - x
                self._drag_offset_y = py - y
                self._selected_item = name
                self.selection_changed.emit(name)
                self.update()
                return

        # Test images in reverse order (last imported = top)
        for i in range(len(self._side.images) - 1, -1, -1):
            r = self._image_rect(i)
            if r is None:
                continue
            x, y, w, h = r
            if x <= px < x + w and y <= py < y + h:
                self._dragging_item = f"image:{i}"
                self._drag_offset_x = px - x
                self._drag_offset_y = py - y
                self._selected_item = f"image:{i}"
                self.selection_changed.emit(self._selected_item)
                self.update()
                return

        # Click on empty area → deselect
        self._selected_item = None
        self.selection_changed.emit("")
        self.update()

    # Height in pages for each item type (for drag clamping)
    _ITEM_PAGES = {
        "layer": 3, "caps_lock": 3, "rgb_mode": 4,
        "wpm": 1, "kfm": 1,
        "katawajojo": 3, "luna": 3, "ocean_dream": 16, "bongo": 4, "crab": 4,
        "zmk_battery": 2, "zmk_output": 2, "zmk_layer": 2, "zmk_peripheral": 2,
    }

    # Width in cols (6 px) pour les items qui n'occupent PAS toute la largeur OLED.
    # Absent → comportement legacy (max_col = 4, suffisant pour overlays QMK full-width).
    _ITEM_COLS = {
        "zmk_battery": 4, "zmk_output": 4, "zmk_layer": 5, "zmk_peripheral": 3,
    }

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if not self._dragging_item:
            return
        px = int(event.position().x())
        py = int(event.position().y())
        item_w = self._ITEM_COLS.get(self._dragging_item)
        if item_w is not None:
            max_col = max(0, (OLED_WIDTH - item_w * 6) // 6)
        else:
            max_col = 4
        new_col = max(0, min((px - self._drag_offset_x) // self.CHAR_W, max_col))
        item_pages = self._ITEM_PAGES.get(self._dragging_item, 1)
        max_line = 16 - item_pages
        new_line = max(0, min((py - self._drag_offset_y) // self.PAGE_H, max_line))
        s = self._side
        emit_zmk_pos = False
        if self._dragging_item.startswith("image:"):
            idx = int(self._dragging_item.split(":")[1])
            if idx < len(s.images):
                s.images[idx].col = new_col
                s.images[idx].line = new_line
        elif self._dragging_item == "layer":
            s.layer.col = new_col
            s.layer.line = new_line
        elif self._dragging_item == "caps_lock":
            s.caps_lock.col = new_col
            s.caps_lock.line = new_line
        elif self._dragging_item == "wpm":
            s.wpm.col = new_col
            s.wpm.line = new_line
        elif self._dragging_item == "rgb_mode":
            s.rgb_mode.col = new_col
            s.rgb_mode.line = new_line
        elif self._dragging_item == "kfm":
            s.kfm.col = new_col
            s.kfm.line = new_line
        elif self._dragging_item == "katawajojo":
            s.katawajojo_line = new_line
        elif self._dragging_item == "luna":
            s.luna_line = new_line
        elif self._dragging_item == "ocean_dream":
            s.ocean_dream_line = new_line
        elif self._dragging_item == "bongo":
            s.bongo_line = new_line
        elif self._dragging_item == "crab":
            s.crab_line = new_line
        elif self._dragging_item == "zmk_battery":
            s.zmk_battery.col = new_col
            s.zmk_battery.line = new_line
            emit_zmk_pos = True
        elif self._dragging_item == "zmk_output":
            s.zmk_output.col = new_col
            s.zmk_output.line = new_line
            emit_zmk_pos = True
        elif self._dragging_item == "zmk_layer":
            s.zmk_layer.col = new_col
            s.zmk_layer.line = new_line
            emit_zmk_pos = True
        elif self._dragging_item == "zmk_peripheral":
            s.zmk_peripheral.col = new_col
            s.zmk_peripheral.line = new_line
            emit_zmk_pos = True
        if emit_zmk_pos:
            self.widget_position_changed.emit(self._dragging_item, new_col, new_line)
        self.update()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        self._dragging_item = None

    # ─── Rendu fidèle des widgets ZMK natifs ──────────────────────────────────
    # Style monochrome blanc sur noir, comme l'OLED réel. Les coordonnées sont
    # en pixels widget (= pixels OLED × SCALE). Un "OLED pixel" virtuel est
    # donc un carré de SCALE × SCALE pixels widget.

    def _paint_zmk_widget(self, painter: QPainter, name: str, x: int, y: int, w: int, h: int) -> None:
        """Dispatcher vers le rendu fidèle du widget ZMK donné."""
        # Fond noir (OLED éteint)
        painter.fillRect(x, y, w, h, QColor(0, 0, 0))
        # Contour discret pour matérialiser la zone draggable (gris foncé,
        # invisible si l'OLED est en pleine zone d'image)
        painter.setPen(QPen(QColor(70, 70, 70)))
        painter.drawRect(x, y, w - 1, h - 1)
        # Le contenu se dessine en blanc (pixel OLED allumé)
        painter.setPen(QPen(QColor(255, 255, 255)))
        painter.setBrush(QColor(255, 255, 255))
        if name == "zmk_battery":
            self._paint_battery_icon(painter, x, y, w, h)
        elif name == "zmk_output":
            self._paint_output_icon(painter, x, y, w, h)
        elif name == "zmk_layer":
            self._paint_layer_text(painter, x, y, w, h)
        elif name == "zmk_peripheral":
            self._paint_peripheral_icon(painter, x, y, w, h)
        painter.setBrush(Qt.BrushStyle.NoBrush)

    def _paint_battery_icon(self, painter: QPainter, x: int, y: int, w: int, h: int) -> None:
        """Icône batterie horizontale 14×8 px OLED, remplie à 70 % (valeur fictive)."""
        s = self.SCALE
        # Marge intérieure de 2 px OLED
        bx = x + 2 * s
        by = y + (h - 8 * s) // 2
        bw = 14 * s
        bh = 8 * s
        # Contour batterie
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(bx, by, bw, bh)
        # Tip à droite (2×4 px OLED)
        tip_h = 4 * s
        painter.fillRect(bx + bw, by + (bh - tip_h) // 2, 2 * s, tip_h, QColor(255, 255, 255))
        # Remplissage à 70 % avec marge intérieure 1 px
        fill_w = int((bw - 2 * s) * 0.7)
        painter.fillRect(bx + 1 * s, by + 1 * s, fill_w, bh - 2 * s, QColor(255, 255, 255))
        # Texte "70%" à droite si la place le permet
        if w >= 22 * s:
            font = painter.font()
            font.setPixelSize(6 * s)
            font.setFamily("monospace")
            painter.setFont(font)
            painter.setPen(QPen(QColor(255, 255, 255)))
            painter.drawText(bx + bw + 4 * s, by + bh - 1, "70%")

    def _paint_output_icon(self, painter: QPainter, x: int, y: int, w: int, h: int) -> None:
        """Icône BLE + numéro de profil (style ZMK natif)."""
        s = self.SCALE
        # Petite icône Bluetooth stylisée à gauche (forme losange croisé)
        cx = x + 4 * s
        cy = y + h // 2
        # Trait vertical principal
        painter.setPen(QPen(QColor(255, 255, 255), s))
        painter.drawLine(cx, cy - 4 * s, cx, cy + 4 * s)
        # Triangles "supérieur" et "inférieur" du B Bluetooth
        painter.drawLine(cx, cy - 4 * s, cx + 3 * s, cy - 1 * s)
        painter.drawLine(cx + 3 * s, cy - 1 * s, cx, cy + 2 * s)
        painter.drawLine(cx, cy + 4 * s, cx + 3 * s, cy + 1 * s)
        painter.drawLine(cx + 3 * s, cy + 1 * s, cx, cy - 2 * s)
        # Texte "BLE 1" à droite
        font = painter.font()
        font.setPixelSize(6 * s)
        font.setFamily("monospace")
        painter.setFont(font)
        painter.drawText(x + 9 * s, cy + 2 * s, "BLE 1")

    def _paint_layer_text(self, painter: QPainter, x: int, y: int, w: int, h: int) -> None:
        """Affichage couche active — texte 'Layer 0' (style ZMK natif)."""
        s = self.SCALE
        font = painter.font()
        font.setPixelSize(6 * s)
        font.setFamily("monospace")
        painter.setFont(font)
        # 2 lignes : "LAYER" puis "  0"
        painter.drawText(x + 2 * s, y + 7 * s, "LAYER")
        painter.drawText(x + 2 * s, y + 14 * s, "  0")

    def _paint_peripheral_icon(self, painter: QPainter, x: int, y: int, w: int, h: int) -> None:
        """Icône lien split — 2 carrés reliés par une ligne (état connecté)."""
        s = self.SCALE
        cy = y + h // 2
        # Carré gauche
        painter.fillRect(x + 2 * s, cy - 2 * s, 4 * s, 4 * s, QColor(255, 255, 255))
        # Carré droit
        painter.fillRect(x + w - 6 * s, cy - 2 * s, 4 * s, 4 * s, QColor(255, 255, 255))
        # Ligne de connexion entre les deux
        painter.setPen(QPen(QColor(255, 255, 255), s))
        painter.drawLine(x + 6 * s, cy, x + w - 6 * s, cy)


class _ConversionWorker(QThread):
    """QThread pour la conversion image — délégué hors du thread UI."""

    finished = Signal(list, list, int, int)  # (frames, delays_ms, natural_w, natural_h)
    error = Signal(str)

    def __init__(self, path: Path) -> None:
        super().__init__()
        self._path = path

    def run(self) -> None:
        try:
            frames, delays, nw, nh = convert_image_natural(self._path)
            assert len(frames) == len(delays), (
                f"Désynchronisation frames/delays : {len(frames)} vs {len(delays)}"
            )
            self.finished.emit(frames, delays, nw, nh)
        except Exception as e:
            self.error.emit(str(e))


class OledWidget(QWidget):
    """Widget de l'onglet OLED — deux canvases indépendants (gauche / droite).

    Chaque côté supporte plusieurs images importées, drag & drop des overlays,
    et les boutons Négatif / Rotation 90° s'appliquent à l'image sélectionnée.
    """

    def __init__(self, model: ProjectModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._model = model
        self._worker: _ConversionWorker | None = None
        self._pending_side: str = "left"
        self._pending_path: str = ""
        # Per-side, per-image animation state
        self._frame_delays: dict[str, list[list[int]]] = {"left": [], "right": []}
        self._anim_idx: dict[str, list[int]] = {"left": [], "right": []}
        self._timers: dict[str, QTimer] = {}
        self._reimport_queue: list[tuple[str, int, str]] = []  # (side, idx, path)
        self._reimport_worker: _ConversionWorker | None = None
        self._canvas_left: _OledCanvas | None = None
        self._canvas_right: _OledCanvas | None = None
        self._group_left: QGroupBox | None = None
        self._group_right: QGroupBox | None = None
        # Widgets cachés en mode ZMK (overlays QMK, anti-burnin) — non compilables côté ZMK.
        # En revanche image + canvas restent visibles : Phase 1 ZMK custom OLED réutilise
        # le pipeline d'images. Anti-burnin reste QMK-only car ZMK gère le sleep différemment.
        self._qmk_only_widgets: list[QWidget] = []
        # Widgets visibles uniquement en mode ZMK (Phase 2 — widgets natifs ZMK).
        self._zmk_only_widgets: list[QWidget] = []
        self._setup_ui()
        self.set_active_sides(model.keyboard.oled_sides)
        self._sync_from_model()

    def _setup_ui(self) -> None:
        from PySide6.QtWidgets import QVBoxLayout
        main = QVBoxLayout(self)
        main.setContentsMargins(0, 0, 0, 0)

        # Bandeau d'info ZMK — caché par défaut, affiché par set_firmware("zmk")
        self._zmk_info_banner = QLabel(tr("oled.zmk.status_screen_only"))
        self._zmk_info_banner.setObjectName("oled_zmk_info")
        self._zmk_info_banner.setWordWrap(True)
        self._zmk_info_banner.setStyleSheet(
            "background-color: #2A4860; color: #E0F0FF; "
            "padding: 8px 12px; border-radius: 6px; "
            "border: 1px solid #4A78A0; margin-bottom: 6px;"
        )
        self._zmk_info_banner.hide()
        main.addWidget(self._zmk_info_banner)

        # ZMK uniquement : toggle "utiliser le status screen built-in ZMK"
        # Coche pour forcer STATUS_SCREEN_BUILT_IN (layer + battery + output natifs)
        # et désactiver l'éditeur canvas. Visible seulement en mode ZMK.
        self._zmk_builtin_screen_check = QCheckBox(tr("oled.zmk.use_builtin_screen"))
        self._zmk_builtin_screen_check.setObjectName("zmk_builtin_screen_check")
        self._zmk_builtin_screen_check.setChecked(bool(self._model.oled.use_builtin_screen))
        self._zmk_builtin_screen_check.stateChanged.connect(self._on_use_builtin_screen_changed)
        self._zmk_builtin_screen_check.hide()
        main.addWidget(self._zmk_builtin_screen_check)
        self._zmk_only_widgets.append(self._zmk_builtin_screen_check)

        # ZMK uniquement : affiche le % de batterie en texte à côté de l'icône
        # (CONFIG_ZMK_WIDGET_BATTERY_STATUS_SHOW_PERCENTAGE=y)
        self._zmk_battery_pct_check = QCheckBox(tr("oled.zmk.show_battery_percentage"))
        self._zmk_battery_pct_check.setObjectName("zmk_battery_pct_check")
        self._zmk_battery_pct_check.setChecked(bool(self._model.oled.show_battery_percentage))
        self._zmk_battery_pct_check.stateChanged.connect(self._on_show_battery_pct_changed)
        self._zmk_battery_pct_check.hide()
        main.addWidget(self._zmk_battery_pct_check)
        self._zmk_only_widgets.append(self._zmk_battery_pct_check)

        self._anti_burnin_check = QCheckBox(tr("oled.anti_burnin"))
        self._anti_burnin_check.setObjectName("anti_burnin_check")
        self._anti_burnin_check.stateChanged.connect(self._on_anti_burnin_changed)
        main.addWidget(self._anti_burnin_check)
        self._qmk_only_widgets.append(self._anti_burnin_check)

        sleep_row = QHBoxLayout()
        self._sleep_check = QCheckBox(tr("oled.sleep"))
        self._sleep_check.setObjectName("sleep_check")
        self._sleep_check.stateChanged.connect(self._on_sleep_changed)
        sleep_row.addWidget(self._sleep_check)
        self._sleep_label = QLabel(tr("oled.sleep_timeout"))
        self._sleep_label.setObjectName("sleep_label")
        self._sleep_label.setEnabled(False)
        sleep_row.addWidget(self._sleep_label)
        self._sleep_spin = QSpinBox()
        self._sleep_spin.setObjectName("sleep_spin")
        self._sleep_spin.setRange(10, 3600)
        self._sleep_spin.setValue(240)
        self._sleep_spin.setEnabled(False)
        self._sleep_spin.valueChanged.connect(self._on_sleep_timeout_changed)
        sleep_row.addWidget(self._sleep_spin)
        sleep_row.addStretch()
        main.addLayout(sleep_row)

        sides = QHBoxLayout()
        sides.addWidget(self._make_side_group("left", tr("oled.side.left")))
        sides.addWidget(self._make_side_group("right", tr("oled.side.right")))
        main.addLayout(sides)

    def _make_side_group(self, side: str, title: str) -> QGroupBox:
        group = QGroupBox(title)
        vl = QVBoxLayout(group)

        # Import image — partagé QMK / ZMK (le pipeline ZMK custom OLED utilise
        # les mêmes images que QMK).
        btn = QPushButton(tr("oled.import_btn"))
        btn.setObjectName(f"import_btn_{side}")
        btn.clicked.connect(lambda _=None, s=side: self._on_import_clicked(s))
        vl.addWidget(btn)

        utils_label = QLabel(f"<b>{tr('oled.group.utils')}</b>")
        vl.addWidget(utils_label)
        self._qmk_only_widgets.append(utils_label)
        for name, label in [
            ("layer", tr("oled.overlay.layer")),
            ("caps", tr("oled.overlay.caps_lock")),
            ("rgb_mode", tr("oled.overlay.rgb_mode")),
        ]:
            cb = QCheckBox(label)
            cb.setObjectName(f"{side}_{name}_check")
            cb.stateChanged.connect(
                lambda state, s=side, n=name: self._on_check_changed(s, n, bool(state))
            )
            vl.addWidget(cb)
            self._qmk_only_widgets.append(cb)

        eyecandy_label = QLabel(f"<b>{tr('oled.group.eyecandy')}</b>")
        vl.addWidget(eyecandy_label)
        self._qmk_only_widgets.append(eyecandy_label)
        for name, label in [
            ("wpm", tr("oled.overlay.wpm")),
            ("kfm", tr("oled.overlay.kfm")),
            ("katawajojo", tr("oled.overlay.katawajojo")),
            ("luna", tr("oled.overlay.luna")),
            ("ocean_dream", tr("oled.overlay.ocean_dream")),
            ("bongo", tr("oled.overlay.bongo")),
            ("crab", tr("oled.overlay.crab")),
        ]:
            cb = QCheckBox(label)
            cb.setObjectName(f"{side}_{name}_check")
            cb.stateChanged.connect(
                lambda state, s=side, n=name: self._on_check_changed(s, n, bool(state))
            )
            vl.addWidget(cb)
            self._qmk_only_widgets.append(cb)

        # Widgets ZMK natifs (Phase 2) — uniquement visibles en mode ZMK.
        zmk_label = QLabel(f"<b>{tr('oled.group.zmk_widgets')}</b>")
        vl.addWidget(zmk_label)
        self._zmk_only_widgets.append(zmk_label)
        # Battery + show_peer dans une même ligne pour économiser l'espace.
        # Layer / output uniquement côté gauche (central). Peripheral uniquement côté droit.
        zmk_widget_specs: list[tuple[str, str]] = [("zmk_battery", tr("oled.zmk_widget.battery"))]
        if side == "left":
            zmk_widget_specs += [
                ("zmk_output", tr("oled.zmk_widget.output")),
                ("zmk_layer", tr("oled.zmk_widget.layer")),
            ]
        if side == "right":
            zmk_widget_specs.append(("zmk_peripheral", tr("oled.zmk_widget.peripheral")))
        for name, label in zmk_widget_specs:
            row = QHBoxLayout()
            cb = QCheckBox(label)
            cb.setObjectName(f"{side}_{name}_check")
            cb.stateChanged.connect(
                lambda state, s=side, n=name: self._on_check_changed(s, n, bool(state))
            )
            row.addWidget(cb)
            col_spin = QSpinBox()
            col_spin.setObjectName(f"{side}_{name}_col")
            col_spin.setPrefix("col ")
            col_spin.setRange(0, 5)
            col_spin.valueChanged.connect(
                lambda v, s=side, n=name: self._on_zmk_widget_pos_changed(s, n, "col", v)
            )
            row.addWidget(col_spin)
            line_spin = QSpinBox()
            line_spin.setObjectName(f"{side}_{name}_line")
            line_spin.setPrefix("line ")
            line_spin.setRange(0, 15)
            line_spin.valueChanged.connect(
                lambda v, s=side, n=name: self._on_zmk_widget_pos_changed(s, n, "line", v)
            )
            row.addWidget(line_spin)
            row.addStretch()
            wrapper = QWidget()
            wrapper.setLayout(row)
            wrapper.setObjectName(f"{side}_{name}_row")
            vl.addWidget(wrapper)
            self._zmk_only_widgets.append(wrapper)
        # show_peer pour battery (central only)
        if side == "left":
            peer_cb = QCheckBox(tr("oled.zmk_widget.battery_show_peer"))
            peer_cb.setObjectName(f"{side}_zmk_battery_show_peer")
            peer_cb.stateChanged.connect(
                lambda state, s=side: self._on_zmk_battery_show_peer_changed(s, bool(state))
            )
            vl.addWidget(peer_cb)
            self._zmk_only_widgets.append(peer_cb)

        btn_neg = QPushButton(tr("oled.btn.negative"))
        btn_neg.setObjectName(f"negative_btn_{side}")
        btn_neg.clicked.connect(lambda _=None, s=side: self._on_negative_clicked(s))
        vl.addWidget(btn_neg)

        btn_rot = QPushButton(tr("oled.btn.rotate"))
        btn_rot.setObjectName(f"rotate_btn_{side}")
        btn_rot.clicked.connect(lambda _=None, s=side: self._on_rotate_clicked(s))
        vl.addWidget(btn_rot)

        # Phase 4 OLED ZMK custom — spinbox couche pour l'image sélectionnée.
        # -1 = toutes couches (image globale). 0/1/.../9 = image visible
        # uniquement quand cette couche est la plus haute active.
        layer_row = QHBoxLayout()
        layer_label = QLabel(tr("oled.zmk_image.layer_label"))
        layer_row.addWidget(layer_label)
        layer_spin = QSpinBox()
        layer_spin.setObjectName(f"image_layer_spin_{side}")
        layer_spin.setRange(-1, 9)
        layer_spin.setSpecialValueText(tr("oled.zmk_image.layer_all"))
        layer_spin.setValue(-1)
        layer_spin.valueChanged.connect(
            lambda v, s=side: self._on_image_layer_changed(s, v)
        )
        layer_row.addWidget(layer_spin)
        layer_row.addStretch()
        layer_wrapper = QWidget()
        layer_wrapper.setLayout(layer_row)
        layer_wrapper.setObjectName(f"image_layer_row_{side}")
        vl.addWidget(layer_wrapper)
        self._zmk_only_widgets.append(layer_wrapper)

        btn_reset = QPushButton(tr("oled.btn.reset"))
        btn_reset.setObjectName(f"reset_btn_{side}")
        btn_reset.clicked.connect(lambda _=None, s=side: self._on_reset_clicked(s))
        vl.addWidget(btn_reset)

        side_config = self._model.oled.left if side == "left" else self._model.oled.right
        canvas = _OledCanvas(side_config)
        canvas.setObjectName(f"canvas_{side}")
        # Phase 4 — sync spinbox layer avec l'image sélectionnée sur le canvas.
        canvas.selection_changed.connect(
            lambda _name, s=side: self._sync_image_layer_spinbox(s)
        )
        # Drag d'un widget ZMK natif → re-sync les QSpinBox col/line correspondants.
        canvas.widget_position_changed.connect(
            lambda n, c, l, s=side: self._sync_zmk_widget_spinbox(s, n, c, l)
        )
        vl.addWidget(canvas)

        if side == "left":
            self._canvas_left = canvas
            self._group_left = group
        else:
            self._canvas_right = canvas
            self._group_right = group

        timer = QTimer(self)
        timer.timeout.connect(lambda s=side: self._on_timer_tick(s))
        self._timers[side] = timer

        return group

    def _on_import_clicked(self, side: str) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, tr("oled.import_dialog_title"), str(Path.home()), tr("oled.image_filter")
        )
        if not path:
            return
        if self._worker and self._worker.isRunning():
            logger.warning("Import ignoré : un worker est déjà en cours d'exécution")
            return
        self._pending_side = side
        self._pending_path = path
        btn = self.findChild(QPushButton, f"import_btn_{side}")
        if btn:
            btn.setEnabled(False)
        self._worker = _ConversionWorker(Path(path))
        self._worker.finished.connect(self._on_conversion_done)
        self._worker.error.connect(self._on_conversion_error)
        self._worker.finished.connect(lambda *_: btn.setEnabled(True) if btn else None)
        self._worker.error.connect(lambda _: btn.setEnabled(True) if btn else None)
        self._worker.start()

    def _on_conversion_done(self, frames: list, delays: list,
                            natural_w: int, natural_h: int) -> None:
        side = self._pending_side
        self._timers[side].stop()
        side_config = self._model.oled.left if side == "left" else self._model.oled.right

        new_item = OledImageItem(
            image_path=self._pending_path,
            frames=frames,
            delays=delays,
            natural_w=natural_w,
            natural_h=natural_h,
        )
        side_config.images.append(new_item)
        img_idx = len(side_config.images) - 1

        # Expand animation tracking lists
        while len(self._anim_idx[side]) <= img_idx:
            self._anim_idx[side].append(0)
        while len(self._frame_delays[side]) <= img_idx:
            self._frame_delays[side].append([100])
        self._frame_delays[side][img_idx] = delays
        self._anim_idx[side][img_idx] = 0

        canvas = self._canvas_left if side == "left" else self._canvas_right
        if canvas:
            canvas.sync_images(len(side_config.images))
        self._show_frame(side, img_idx, 0)

        if any(len(img.frames) > 1 for img in side_config.images):
            self._timers[side].setInterval(delays[0] if delays else 100)
            self._timers[side].start()

        logger.info("Import OLED %s[%d] terminé : %s (%d frame(s)) %dx%d px",
                    side, img_idx, self._pending_path, len(frames), natural_w, natural_h)

    def _on_conversion_error(self, message: str) -> None:
        QMessageBox.critical(
            self,
            tr("oled.import_error_title"),
            tr("oled.import_error_msg").format(msg=message),
        )
        logger.error("Erreur conversion OLED : %s", message)

    def _on_timer_tick(self, side: str) -> None:
        side_config = self._model.oled.left if side == "left" else self._model.oled.right
        any_anim = False
        for img_idx, img_item in enumerate(side_config.images):
            if len(img_item.frames) <= 1:
                continue
            any_anim = True
            while len(self._anim_idx[side]) <= img_idx:
                self._anim_idx[side].append(0)
            self._anim_idx[side][img_idx] = (
                (self._anim_idx[side][img_idx] + 1) % len(img_item.frames)
            )
            self._show_frame(side, img_idx, self._anim_idx[side][img_idx])
        if not any_anim:
            self._timers[side].stop()
        self._timers[side].setInterval(100)

    def _on_anti_burnin_changed(self, state: int) -> None:
        self._model.oled.anti_burnin = bool(state)
        logger.info("Anti burn-in : %s", bool(state))

    def _on_use_builtin_screen_changed(self, state: int) -> None:
        """Toggle ZMK built-in screen : force STATUS_SCREEN_BUILT_IN.

        Quand activé, l'éditeur canvas (images + widgets ZMK) est désactivé
        car le firmware ignorera ces éléments — il utilisera le screen natif
        ZMK (layer + battery + output).
        """
        enabled = bool(state)
        self._model.oled.use_builtin_screen = enabled
        # Désactive / réactive les contrôles de l'éditeur custom
        for canvas in (self._canvas_left, self._canvas_right):
            if canvas is not None:
                canvas.setEnabled(not enabled)
        logger.info("OLED ZMK : built-in screen = %s", enabled)

    def _on_show_battery_pct_changed(self, state: int) -> None:
        """Toggle pourcentage batterie texte dans le widget natif."""
        self._model.oled.show_battery_percentage = bool(state)
        logger.info("OLED ZMK : show battery %% = %s", bool(state))

    def _on_sleep_changed(self, state: int) -> None:
        enabled = bool(state)
        self._model.oled.sleep_enabled = enabled
        lbl = self.findChild(QLabel, "sleep_label")
        sp = self.findChild(QSpinBox, "sleep_spin")
        if lbl:
            lbl.setEnabled(enabled)
        if sp:
            sp.setEnabled(enabled)
        logger.info("Sleep mode : %s", enabled)

    def _on_sleep_timeout_changed(self, value: int) -> None:
        self._model.oled.sleep_timeout_s = value

    def _on_check_changed(self, side: str, name: str, checked: bool) -> None:
        side_config = self._model.oled.left if side == "left" else self._model.oled.right
        if name == "layer":
            side_config.layer.enabled = checked
        elif name == "caps":
            side_config.caps_lock.enabled = checked
        elif name == "wpm":
            side_config.wpm.enabled = checked
        elif name == "rgb_mode":
            side_config.rgb_mode.enabled = checked
        elif name == "kfm":
            side_config.kfm.enabled = checked
        elif name == "katawajojo":
            side_config.katawajojo_enabled = checked
        elif name == "luna":
            side_config.luna_enabled = checked
        elif name == "ocean_dream":
            side_config.ocean_dream_enabled = checked
        elif name == "bongo":
            side_config.bongo_enabled = checked
        elif name == "crab":
            side_config.crab_enabled = checked
        elif name == "zmk_battery":
            side_config.zmk_battery.enabled = checked
        elif name == "zmk_output":
            side_config.zmk_output.enabled = checked
        elif name == "zmk_layer":
            side_config.zmk_layer.enabled = checked
        elif name == "zmk_peripheral":
            side_config.zmk_peripheral.enabled = checked
        canvas = self._canvas_left if side == "left" else self._canvas_right
        if canvas:
            canvas.update()
        logger.info("Overlay %s.%s : %s", side, name, checked)

    def _on_zmk_widget_pos_changed(self, side: str, name: str, axis: str, value: int) -> None:
        """Met à jour la position (col ou line) d'un widget ZMK dans le modèle."""
        side_config = self._model.oled.left if side == "left" else self._model.oled.right
        widget = {
            "zmk_battery": side_config.zmk_battery,
            "zmk_output": side_config.zmk_output,
            "zmk_layer": side_config.zmk_layer,
            "zmk_peripheral": side_config.zmk_peripheral,
        }.get(name)
        if widget is None:
            return
        if axis == "col":
            widget.col = value
        elif axis == "line":
            widget.line = value
        canvas = self._canvas_left if side == "left" else self._canvas_right
        if canvas:
            canvas.update()
        logger.info("ZMK widget %s.%s.%s = %d", side, name, axis, value)

    def _sync_zmk_widget_spinbox(self, side: str, name: str, col: int, line: int) -> None:
        """Synchronise les QSpinBox col/line après un drag canvas du widget ZMK.

        blockSignals évite de réémettre `_on_zmk_widget_pos_changed` (loop).
        """
        col_sp = self.findChild(QSpinBox, f"{side}_{name}_col")
        if col_sp:
            col_sp.blockSignals(True)
            col_sp.setValue(col)
            col_sp.blockSignals(False)
        line_sp = self.findChild(QSpinBox, f"{side}_{name}_line")
        if line_sp:
            line_sp.blockSignals(True)
            line_sp.setValue(line)
            line_sp.blockSignals(False)

    def _on_zmk_battery_show_peer_changed(self, side: str, checked: bool) -> None:
        side_config = self._model.oled.left if side == "left" else self._model.oled.right
        side_config.zmk_battery.show_peer = checked
        logger.info("ZMK widget %s.zmk_battery.show_peer = %s", side, checked)

    def _on_image_layer_changed(self, side: str, value: int) -> None:
        """Met à jour le champ `layer` de l'image sélectionnée sur ce côté.

        Si aucune image n'est sélectionnée, ignore l'événement avec un log.
        Phase 4 — assignation per-image d'une couche keymap pour le pipeline
        layer-aware ZMK. -1 = toutes couches, 0..9 = couche spécifique.
        """
        canvas = self._canvas_left if side == "left" else self._canvas_right
        if canvas is None:
            return
        selected = canvas._selected_item
        if selected is None or not selected.startswith("image:"):
            logger.debug("Layer change %s = %d ignoré : pas d'image sélectionnée", side, value)
            return
        idx = int(selected.split(":")[1])
        side_config = self._model.oled.left if side == "left" else self._model.oled.right
        if idx >= len(side_config.images):
            return
        side_config.images[idx].layer = value
        logger.info("Image %s[%d] layer = %d", side, idx, value)

    def _sync_image_layer_spinbox(self, side: str) -> None:
        """Met à jour le spinbox `layer` selon l'image actuellement sélectionnée.

        Appelé après changement de sélection canvas (mouse press) pour refléter
        la couche assignée à l'image que l'utilisateur vient de cliquer.
        """
        canvas = self._canvas_left if side == "left" else self._canvas_right
        if canvas is None:
            return
        sp = self.findChild(QSpinBox, f"image_layer_spin_{side}")
        if sp is None:
            return
        selected = canvas._selected_item
        if selected is None or not selected.startswith("image:"):
            return
        idx = int(selected.split(":")[1])
        side_config = self._model.oled.left if side == "left" else self._model.oled.right
        if idx >= len(side_config.images):
            return
        sp.blockSignals(True)
        sp.setValue(side_config.images[idx].layer)
        sp.blockSignals(False)

    def _on_negative_clicked(self, side: str) -> None:
        """Bascule l'inversion de l'image sélectionnée sur ce côté."""
        canvas = self._canvas_left if side == "left" else self._canvas_right
        if canvas is None:
            return
        selected = canvas._selected_item
        if selected is None or not selected.startswith("image:"):
            return
        idx = int(selected.split(":")[1])
        side_config = self._model.oled.left if side == "left" else self._model.oled.right
        if idx < len(side_config.images):
            side_config.images[idx].inverted = not side_config.images[idx].inverted
            canvas.update()
            logger.info("Négatif %s[%d] : %s", side, idx, side_config.images[idx].inverted)

    def _on_rotate_clicked(self, side: str) -> None:
        """Rotation 90° CW de l'image sélectionnée sur ce côté."""
        canvas = self._canvas_left if side == "left" else self._canvas_right
        if canvas is None:
            return
        selected = canvas._selected_item
        if selected is None or not selected.startswith("image:"):
            return
        idx = int(selected.split(":")[1])
        side_config = self._model.oled.left if side == "left" else self._model.oled.right
        if idx >= len(side_config.images):
            return
        img_item = side_config.images[idx]
        if not img_item.frames:
            return
        img_item.frames = [rotate_frame_90cw(f) for f in img_item.frames]
        # After rotation the content fills the full 32×128 frame
        img_item.natural_w = OLED_WIDTH
        img_item.natural_h = OLED_HEIGHT
        frame_idx = (self._anim_idx[side][idx]
                     if idx < len(self._anim_idx[side]) else 0)
        self._show_frame(side, idx, frame_idx)
        logger.info("Rotation 90° %s[%d] (%d frame(s))", side, idx, len(img_item.frames))

    def _on_reset_clicked(self, side: str) -> None:
        """Efface toutes les images et désactive tous les overlays de ce côté."""
        side_config = self._model.oled.left if side == "left" else self._model.oled.right
        # Clear images
        side_config.images.clear()
        # Disable all overlays
        side_config.layer.enabled = False
        side_config.caps_lock.enabled = False
        side_config.wpm.enabled = False
        side_config.rgb_mode.enabled = False
        side_config.kfm.enabled = False
        side_config.katawajojo_enabled = False
        side_config.luna_enabled = False
        side_config.ocean_dream_enabled = False
        side_config.bongo_enabled = False
        side_config.crab_enabled = False
        # Clear animation state
        self._anim_idx[side] = []
        # Sync checkboxes and refresh canvas
        self._sync_from_model()
        canvas = self._canvas_left if side == "left" else self._canvas_right
        if canvas:
            canvas._pixmaps.clear()
            canvas._selected_item = None
            canvas.update()
        logger.info("Reset écran %s", side)

    def set_active_sides(self, sides: list[str]) -> None:
        """Affiche/masque les groupes gauche/droite selon la config matérielle."""
        if self._group_left is not None:
            self._group_left.setVisible("left" in sides)
        if self._group_right is not None:
            self._group_right.setVisible("right" in sides)

    def set_firmware(self, firmware: str) -> None:
        """Adapte l'UI au firmware cible (qmk/zmk).

        Phase 2 (2026-05-03) : ZMK custom OLED supporte image plein écran + widgets
        natifs ZMK (battery / output / layer / peripheral). L'image et le canvas
        restent visibles dans les deux modes. Les overlays QMK (layer/caps/wpm/etc.
        et animations) sont masqués en ZMK car ils dépendent de code C QMK qui
        n'a pas d'équivalent ZMK natif. Les widgets ZMK sont masqués en QMK.
        """
        is_zmk = firmware == "zmk"
        self._zmk_info_banner.setVisible(is_zmk)
        for w in self._qmk_only_widgets:
            w.setVisible(not is_zmk)
        for w in self._zmk_only_widgets:
            w.setVisible(is_zmk)
        # Propagation aux canvases : ils décident quels overlays rendre.
        for canvas in (self._canvas_left, self._canvas_right):
            if canvas is not None:
                canvas.set_firmware(firmware)

    def _sync_from_model(self) -> None:
        """Synchronise les checkboxes et le canvas depuis le modèle (ex : après chargement projet)."""
        cb = self.findChild(QCheckBox, "anti_burnin_check")
        if cb:
            cb.blockSignals(True)
            cb.setChecked(self._model.oled.anti_burnin)
            cb.blockSignals(False)
        # ZMK built-in screen toggle
        builtin_enabled = bool(self._model.oled.use_builtin_screen)
        cb = self.findChild(QCheckBox, "zmk_builtin_screen_check")
        if cb:
            cb.blockSignals(True)
            cb.setChecked(builtin_enabled)
            cb.blockSignals(False)
        # Grise les canvas selon l'état builtin
        for canvas in (self._canvas_left, self._canvas_right):
            if canvas is not None:
                canvas.setEnabled(not builtin_enabled)
        # ZMK show_battery_percentage
        cb = self.findChild(QCheckBox, "zmk_battery_pct_check")
        if cb:
            cb.blockSignals(True)
            cb.setChecked(bool(self._model.oled.show_battery_percentage))
            cb.blockSignals(False)
        sleep_enabled = self._model.oled.sleep_enabled
        cb = self.findChild(QCheckBox, "sleep_check")
        if cb:
            cb.blockSignals(True)
            cb.setChecked(sleep_enabled)
            cb.blockSignals(False)
        lbl = self.findChild(QLabel, "sleep_label")
        if lbl:
            lbl.setEnabled(sleep_enabled)
        sp = self.findChild(QSpinBox, "sleep_spin")
        if sp:
            sp.blockSignals(True)
            sp.setValue(self._model.oled.sleep_timeout_s)
            sp.setEnabled(sleep_enabled)
            sp.blockSignals(False)
        for side in ("left", "right"):
            side_config = self._model.oled.left if side == "left" else self._model.oled.right
            mapping = [
                (f"{side}_layer_check", side_config.layer.enabled),
                (f"{side}_caps_check", side_config.caps_lock.enabled),
                (f"{side}_wpm_check", side_config.wpm.enabled),
                (f"{side}_rgb_mode_check", side_config.rgb_mode.enabled),
                (f"{side}_kfm_check", side_config.kfm.enabled),
                (f"{side}_katawajojo_check", side_config.katawajojo_enabled),
                (f"{side}_luna_check", side_config.luna_enabled),
                (f"{side}_ocean_dream_check", side_config.ocean_dream_enabled),
                (f"{side}_bongo_check", side_config.bongo_enabled),
                (f"{side}_crab_check", side_config.crab_enabled),
                (f"{side}_zmk_battery_check", side_config.zmk_battery.enabled),
                (f"{side}_zmk_output_check", side_config.zmk_output.enabled),
                (f"{side}_zmk_layer_check", side_config.zmk_layer.enabled),
                (f"{side}_zmk_peripheral_check", side_config.zmk_peripheral.enabled),
            ]
            for obj_name, value in mapping:
                cb = self.findChild(QCheckBox, obj_name)
                if cb:
                    cb.blockSignals(True)
                    cb.setChecked(value)
                    cb.blockSignals(False)
            # Sync ZMK widget positions (col/line spinboxes)
            zmk_pos_mapping = [
                (f"{side}_zmk_battery", side_config.zmk_battery.col, side_config.zmk_battery.line),
                (f"{side}_zmk_output", side_config.zmk_output.col, side_config.zmk_output.line),
                (f"{side}_zmk_layer", side_config.zmk_layer.col, side_config.zmk_layer.line),
                (f"{side}_zmk_peripheral", side_config.zmk_peripheral.col, side_config.zmk_peripheral.line),
            ]
            for prefix, col, line in zmk_pos_mapping:
                col_sp = self.findChild(QSpinBox, f"{prefix}_col")
                if col_sp:
                    col_sp.blockSignals(True)
                    col_sp.setValue(col)
                    col_sp.blockSignals(False)
                line_sp = self.findChild(QSpinBox, f"{prefix}_line")
                if line_sp:
                    line_sp.blockSignals(True)
                    line_sp.setValue(line)
                    line_sp.blockSignals(False)
            # show_peer (left only)
            if side == "left":
                peer_cb = self.findChild(QCheckBox, "left_zmk_battery_show_peer")
                if peer_cb:
                    peer_cb.blockSignals(True)
                    peer_cb.setChecked(side_config.zmk_battery.show_peer)
                    peer_cb.blockSignals(False)

            # Re-sync canvas images from model (handles project load)
            canvas = self._canvas_left if side == "left" else self._canvas_right
            if canvas is None:
                continue
            # Rebind canvas to new side config (model.oled may have been replaced)
            canvas._side = side_config
            canvas._pixmaps.clear()
            canvas.sync_images(len(side_config.images))
            self._anim_idx[side] = [0] * len(side_config.images)
            self._frame_delays[side] = [[100]] * len(side_config.images)
            for idx, img in enumerate(side_config.images):
                if img.image_path and not img.frames:
                    self._reimport_queue.append((side, idx, img.image_path))
                elif img.frames:
                    self._frame_delays[side][idx] = img.delays if img.delays else [100]
                    self._show_frame(side, idx, 0)
            canvas.update()
        self._process_reimport_queue()

    def _process_reimport_queue(self) -> None:
        """Traite le prochain item de la queue de re-import d'images."""
        if not self._reimport_queue:
            return
        if self._reimport_worker and self._reimport_worker.isRunning():
            return  # Attendre la fin du worker en cours

        side, idx, path = self._reimport_queue.pop(0)
        p = Path(path)
        if not p.is_file():
            logger.warning("Re-import OLED ignoré : fichier introuvable %s", path)
            self._process_reimport_queue()
            return

        self._reimport_worker = _ConversionWorker(p)
        self._reimport_worker._reimport_side = side  # type: ignore[attr-defined]
        self._reimport_worker._reimport_idx = idx  # type: ignore[attr-defined]
        self._reimport_worker.finished.connect(self._on_reimport_done)
        self._reimport_worker.error.connect(self._on_reimport_error)
        self._reimport_worker.start()

    def _on_reimport_done(self, frames: list, delays: list,
                          natural_w: int, natural_h: int) -> None:
        """Callback quand le re-import d'une image est terminé."""
        worker = self._reimport_worker
        if worker is None:
            return
        side = worker._reimport_side  # type: ignore[attr-defined]
        idx = worker._reimport_idx  # type: ignore[attr-defined]
        worker.finished.disconnect(self._on_reimport_done)
        worker.error.disconnect(self._on_reimport_error)

        side_config = self._model.oled.left if side == "left" else self._model.oled.right
        if idx < len(side_config.images):
            img_item = side_config.images[idx]
            img_item.frames = frames
            img_item.delays = delays
            img_item.natural_w = natural_w
            img_item.natural_h = natural_h

            # Update animation tracking
            while len(self._anim_idx[side]) <= idx:
                self._anim_idx[side].append(0)
            while len(self._frame_delays[side]) <= idx:
                self._frame_delays[side].append([100])
            self._frame_delays[side][idx] = delays
            self._anim_idx[side][idx] = 0

            canvas = self._canvas_left if side == "left" else self._canvas_right
            if canvas:
                canvas.sync_images(len(side_config.images))
            self._show_frame(side, idx, 0)

            if len(frames) > 1:
                self._timers[side].setInterval(delays[0] if delays else 100)
                self._timers[side].start()

            logger.info("Re-import OLED %s[%d] terminé : %d frame(s) %dx%d px",
                        side, idx, len(frames), natural_w, natural_h)

        self._reimport_worker = None
        self._process_reimport_queue()

    def _on_reimport_error(self, message: str) -> None:
        """Callback quand le re-import échoue — log silencieux, pas de popup."""
        worker = self._reimport_worker
        if worker is not None:
            worker.finished.disconnect(self._on_reimport_done)
            worker.error.disconnect(self._on_reimport_error)
        logger.warning("Erreur re-import OLED : %s", message)
        self._reimport_worker = None
        self._process_reimport_queue()

    def _show_frame(self, side: str, img_idx: int, frame_idx: int) -> None:
        """Affiche la frame frame_idx de l'image img_idx sur le canvas du côté side.

        Crée un pixmap à la taille naturelle du thumbnail (sans padding OLED),
        ce qui permet un drag & drop et une sélection précis.
        """
        side_config = self._model.oled.left if side == "left" else self._model.oled.right
        if img_idx >= len(side_config.images):
            return
        img_item = side_config.images[img_idx]
        frames = img_item.frames
        if not frames or frame_idx >= len(frames):
            return
        data = frames[frame_idx]
        expected_size = OLED_WIDTH * OLED_HEIGHT
        if len(data) != expected_size:
            logger.warning(
                "Frame %d (img %d, %s) taille inattendue : %d octets (attendu %d) — ignorée",
                frame_idx, img_idx, side, len(data), expected_size,
            )
            return

        # Create full OLED image, then crop to actual thumbnail content region
        full_img = QImage(data, OLED_WIDTH, OLED_HEIGHT, OLED_WIDTH,
                          QImage.Format.Format_Grayscale8)
        nat_w = max(1, img_item.natural_w)
        nat_h = max(1, img_item.natural_h)
        # Processor top-aligns and h-centers the thumbnail: compute crop offsets
        crop_x = (OLED_WIDTH - nat_w) // 2
        crop_y = 0
        cropped = full_img.copy(crop_x, crop_y, nat_w, nat_h)
        pixmap = QPixmap.fromImage(cropped).scaled(
            nat_w * _OledCanvas.SCALE,
            nat_h * _OledCanvas.SCALE,
            Qt.AspectRatioMode.IgnoreAspectRatio,
        )
        canvas = self._canvas_left if side == "left" else self._canvas_right
        if canvas:
            canvas.set_image_pixmap(img_idx, pixmap)
