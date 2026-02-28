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
        w = OLED_WIDTH * self.SCALE
        h = OLED_HEIGHT * self.SCALE
        self.setMinimumSize(w, h)
        self.setFixedSize(w, h)
        self.setMouseTracking(True)

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
                    3 * self.CHAR_W, 2 * self.PAGE_H)
        if name == "caps_lock" and s.caps_lock.enabled:
            return (s.caps_lock.col * self.CHAR_W, s.caps_lock.line * self.PAGE_H,
                    3 * self.CHAR_W, 2 * self.PAGE_H)
        if name == "wpm" and s.wpm.enabled:
            return (s.wpm.col * self.CHAR_W, s.wpm.line * self.PAGE_H,
                    3 * self.CHAR_W, 2 * self.PAGE_H)
        if name == "rgb_mode" and s.rgb_mode.enabled:
            return (s.rgb_mode.col * self.CHAR_W, s.rgb_mode.line * self.PAGE_H,
                    OLED_WIDTH * self.SCALE, 4 * self.PAGE_H)
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
        return None

    def _overlay_items(self) -> list[tuple[str, tuple[int, int, int, int], QColor, str]]:
        """Liste des overlays visibles (hors images) : (name, rect, color, label)."""
        result = []
        r = self._item_rect("layer")
        if r:
            result.append(("layer", r, QColor(0, 200, 0, 160), "LAYER"))
        r = self._item_rect("caps_lock")
        if r:
            result.append(("caps_lock", r, QColor(220, 200, 0, 160), "Cp"))
        r = self._item_rect("wpm")
        if r:
            result.append(("wpm", r, QColor(0, 100, 220, 160), "Wp"))
        r = self._item_rect("rgb_mode")
        if r:
            result.append(("rgb_mode", r, QColor(220, 50, 220, 160), "RGB"))
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
                self.update()
                return

        # Click on empty area → deselect
        self._selected_item = None
        self.update()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if not self._dragging_item:
            return
        px = int(event.position().x())
        py = int(event.position().y())
        new_col = max(0, min((px - self._drag_offset_x) // self.CHAR_W, 4))
        new_line = max(0, min((py - self._drag_offset_y) // self.PAGE_H, 15))
        s = self._side
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
        elif self._dragging_item == "katawajojo":
            s.katawajojo_line = new_line
        elif self._dragging_item == "luna":
            s.luna_line = new_line
        elif self._dragging_item == "ocean_dream":
            s.ocean_dream_line = new_line
        elif self._dragging_item == "bongo":
            s.bongo_line = new_line
        self.update()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        self._dragging_item = None


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
        self._canvas_left: _OledCanvas | None = None
        self._canvas_right: _OledCanvas | None = None
        self._group_left: QGroupBox | None = None
        self._group_right: QGroupBox | None = None
        self._setup_ui()
        self.set_active_sides(model.keyboard.oled_sides)
        self._sync_from_model()

    def _setup_ui(self) -> None:
        from PySide6.QtWidgets import QVBoxLayout
        main = QVBoxLayout(self)
        main.setContentsMargins(0, 0, 0, 0)

        self._anti_burnin_check = QCheckBox(tr("oled.anti_burnin"))
        self._anti_burnin_check.setObjectName("anti_burnin_check")
        self._anti_burnin_check.stateChanged.connect(self._on_anti_burnin_changed)
        main.addWidget(self._anti_burnin_check)

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

        btn = QPushButton(tr("oled.import_btn"))
        btn.setObjectName(f"import_btn_{side}")
        btn.clicked.connect(lambda _=None, s=side: self._on_import_clicked(s))
        vl.addWidget(btn)

        utils_label = QLabel(f"<b>{tr('oled.group.utils')}</b>")
        vl.addWidget(utils_label)
        for name, label in [
            ("layer", tr("oled.overlay.layer")),
            ("caps", tr("oled.overlay.caps_lock")),
            ("wpm", tr("oled.overlay.wpm")),
            ("rgb_mode", tr("oled.overlay.rgb_mode")),
        ]:
            cb = QCheckBox(label)
            cb.setObjectName(f"{side}_{name}_check")
            cb.stateChanged.connect(
                lambda state, s=side, n=name: self._on_check_changed(s, n, bool(state))
            )
            vl.addWidget(cb)

        eyecandy_label = QLabel(f"<b>{tr('oled.group.eyecandy')}</b>")
        vl.addWidget(eyecandy_label)
        for name, label in [
            ("katawajojo", tr("oled.overlay.katawajojo")),
            ("luna", tr("oled.overlay.luna")),
            ("ocean_dream", tr("oled.overlay.ocean_dream")),
            ("bongo", tr("oled.overlay.bongo")),
        ]:
            cb = QCheckBox(label)
            cb.setObjectName(f"{side}_{name}_check")
            cb.stateChanged.connect(
                lambda state, s=side, n=name: self._on_check_changed(s, n, bool(state))
            )
            vl.addWidget(cb)

        btn_neg = QPushButton(tr("oled.btn.negative"))
        btn_neg.setObjectName(f"negative_btn_{side}")
        btn_neg.clicked.connect(lambda _=None, s=side: self._on_negative_clicked(s))
        vl.addWidget(btn_neg)

        btn_rot = QPushButton(tr("oled.btn.rotate"))
        btn_rot.setObjectName(f"rotate_btn_{side}")
        btn_rot.clicked.connect(lambda _=None, s=side: self._on_rotate_clicked(s))
        vl.addWidget(btn_rot)

        side_config = self._model.oled.left if side == "left" else self._model.oled.right
        canvas = _OledCanvas(side_config)
        canvas.setObjectName(f"canvas_{side}")
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
        elif name == "katawajojo":
            side_config.katawajojo_enabled = checked
        elif name == "luna":
            side_config.luna_enabled = checked
        elif name == "ocean_dream":
            side_config.ocean_dream_enabled = checked
        elif name == "bongo":
            side_config.bongo_enabled = checked
        canvas = self._canvas_left if side == "left" else self._canvas_right
        if canvas:
            canvas.update()
        logger.info("Overlay %s.%s : %s", side, name, checked)

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

    def set_active_sides(self, sides: list[str]) -> None:
        """Affiche/masque les groupes gauche/droite selon la config matérielle."""
        if self._group_left is not None:
            self._group_left.setVisible("left" in sides)
        if self._group_right is not None:
            self._group_right.setVisible("right" in sides)

    def _sync_from_model(self) -> None:
        """Synchronise les checkboxes depuis le modèle (ex : après chargement projet)."""
        cb = self.findChild(QCheckBox, "anti_burnin_check")
        if cb:
            cb.blockSignals(True)
            cb.setChecked(self._model.oled.anti_burnin)
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
                (f"{side}_katawajojo_check", side_config.katawajojo_enabled),
                (f"{side}_luna_check", side_config.luna_enabled),
                (f"{side}_ocean_dream_check", side_config.ocean_dream_enabled),
                (f"{side}_bongo_check", side_config.bongo_enabled),
            ]
            for obj_name, value in mapping:
                cb = self.findChild(QCheckBox, obj_name)
                if cb:
                    cb.blockSignals(True)
                    cb.setChecked(value)
                    cb.blockSignals(False)

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
