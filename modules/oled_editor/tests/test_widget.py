"""Tests pytest-qt pour modules/oled_editor/widget.py — OledWidget."""
from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QPushButton

from i18n import tr
from models.project_model import OledImageItem, ProjectModel
from modules.oled_editor.widget import OledWidget, _ConversionWorker, _OledCanvas

FIXTURES = Path(__file__).parent / "fixtures"

# 32 × 128 = 4096 bytes
_FAKE_FRAME = bytes(32 * 128)
_DEFAULT_DELAYS = [100]
_NATURAL_W = 32
_NATURAL_H = 128


@pytest.fixture
def model() -> ProjectModel:
    return ProjectModel()


@pytest.fixture
def widget(qtbot, model):
    w = OledWidget(model)
    qtbot.addWidget(w)
    return w


# ─── Structure des deux canvases ─────────────────────────────────────────────

class TestOledWidgetInit:
    def test_import_btn_left_exists(self, widget):
        btn = widget.findChild(QPushButton, "import_btn_left")
        assert btn is not None

    def test_import_btn_right_exists(self, widget):
        btn = widget.findChild(QPushButton, "import_btn_right")
        assert btn is not None

    def test_canvas_left_exists(self, widget):
        canvas = widget.findChild(_OledCanvas, "canvas_left")
        assert canvas is not None

    def test_canvas_right_exists(self, widget):
        canvas = widget.findChild(_OledCanvas, "canvas_right")
        assert canvas is not None

    def test_canvas_left_initial_state(self, widget):
        assert widget._canvas_left._pixmaps == []

    def test_canvas_right_initial_state(self, widget):
        assert widget._canvas_right._pixmaps == []

    def test_timers_not_active_on_init(self, widget):
        assert not widget._timers["left"].isActive()
        assert not widget._timers["right"].isActive()

    def test_import_btn_left_text(self, widget):
        btn = widget.findChild(QPushButton, "import_btn_left")
        assert btn.text() == tr("oled.import_btn")

    def test_import_btn_right_text(self, widget):
        btn = widget.findChild(QPushButton, "import_btn_right")
        assert btn.text() == tr("oled.import_btn")

    def test_negative_btn_left_exists(self, widget):
        btn = widget.findChild(QPushButton, "negative_btn_left")
        assert btn is not None

    def test_negative_btn_right_exists(self, widget):
        btn = widget.findChild(QPushButton, "negative_btn_right")
        assert btn is not None

    def test_rotate_btn_left_exists(self, widget):
        btn = widget.findChild(QPushButton, "rotate_btn_left")
        assert btn is not None


# ─── Conversion ───────────────────────────────────────────────────────────────

class TestOledWidgetConversion:
    def test_conversion_left_adds_image_to_model(self, widget, model):
        png_path = str(FIXTURES / "test_100x100.png")
        widget._pending_path = png_path
        widget._pending_side = "left"
        widget._on_conversion_done([_FAKE_FRAME], _DEFAULT_DELAYS, _NATURAL_W, _NATURAL_H)
        assert len(model.oled.left.images) == 1
        assert model.oled.left.images[0].image_path == png_path

    def test_conversion_right_adds_image_to_model(self, widget, model):
        png_path = str(FIXTURES / "test_100x100.png")
        widget._pending_path = png_path
        widget._pending_side = "right"
        widget._on_conversion_done([_FAKE_FRAME], _DEFAULT_DELAYS, _NATURAL_W, _NATURAL_H)
        assert len(model.oled.right.images) == 1
        assert model.oled.right.images[0].image_path == png_path

    def test_conversion_left_stores_frames(self, widget, model):
        widget._pending_path = str(FIXTURES / "test_100x100.png")
        widget._pending_side = "left"
        widget._on_conversion_done([_FAKE_FRAME], _DEFAULT_DELAYS, _NATURAL_W, _NATURAL_H)
        assert model.oled.left.images[0].frames == [_FAKE_FRAME]

    def test_conversion_stores_natural_size(self, widget, model):
        widget._pending_path = str(FIXTURES / "test_100x100.png")
        widget._pending_side = "left"
        widget._on_conversion_done([_FAKE_FRAME], _DEFAULT_DELAYS, 20, 50)
        assert model.oled.left.images[0].natural_w == 20
        assert model.oled.left.images[0].natural_h == 50

    def test_conversion_multiple_imports_append(self, widget, model):
        """Importer deux images ajoute deux entrées à la liste."""
        widget._pending_path = "/a.png"
        widget._pending_side = "left"
        widget._on_conversion_done([_FAKE_FRAME], _DEFAULT_DELAYS, _NATURAL_W, _NATURAL_H)
        widget._pending_path = "/b.gif"
        widget._on_conversion_done([_FAKE_FRAME, _FAKE_FRAME], [100, 100], _NATURAL_W, _NATURAL_H)
        assert len(model.oled.left.images) == 2
        assert model.oled.left.images[0].image_path == "/a.png"
        assert model.oled.left.images[1].image_path == "/b.gif"

    def test_conversion_left_shows_preview(self, widget):
        widget._pending_path = str(FIXTURES / "test_100x100.png")
        widget._pending_side = "left"
        widget._on_conversion_done([_FAKE_FRAME], _DEFAULT_DELAYS, _NATURAL_W, _NATURAL_H)
        assert len(widget._canvas_left._pixmaps) == 1
        assert widget._canvas_left._pixmaps[0] is not None
        assert not widget._canvas_left._pixmaps[0].isNull()

    def test_conversion_right_shows_preview(self, widget):
        widget._pending_path = str(FIXTURES / "test_100x100.png")
        widget._pending_side = "right"
        widget._on_conversion_done([_FAKE_FRAME], _DEFAULT_DELAYS, _NATURAL_W, _NATURAL_H)
        assert len(widget._canvas_right._pixmaps) == 1
        assert widget._canvas_right._pixmaps[0] is not None

    def test_real_png_conversion_via_worker(self, qtbot):
        """Test bout-en-bout avec un vrai PNG via le worker QThread."""
        png_path = FIXTURES / "test_100x100.png"
        worker = _ConversionWorker(png_path)
        with qtbot.waitSignal(worker.finished, timeout=2000) as blocker:
            worker.start()
        frames = blocker.args[0]
        delays = blocker.args[1]
        natural_w = blocker.args[2]
        natural_h = blocker.args[3]
        assert len(frames) == 1
        assert len(frames[0]) == 32 * 128
        assert isinstance(delays, list)
        assert len(delays) >= 1
        assert isinstance(natural_w, int) and natural_w > 0
        assert isinstance(natural_h, int) and natural_h > 0


# ─── Animation ────────────────────────────────────────────────────────────────

class TestOledWidgetAnimation:
    def test_timer_not_active_after_single_frame_left(self, widget):
        widget._pending_side = "left"
        widget._pending_path = "/tmp/test.png"
        widget._on_conversion_done([_FAKE_FRAME], [100], _NATURAL_W, _NATURAL_H)
        assert not widget._timers["left"].isActive()

    def test_timer_active_after_multi_frame_left(self, widget):
        fake_frames = [_FAKE_FRAME, _FAKE_FRAME, _FAKE_FRAME]
        widget._pending_side = "left"
        widget._pending_path = "/tmp/test.gif"
        widget._on_conversion_done(fake_frames, [100, 150, 200], _NATURAL_W, _NATURAL_H)
        assert widget._timers["left"].isActive()

    def test_timer_interval_matches_first_delay(self, widget):
        fake_frames = [_FAKE_FRAME, _FAKE_FRAME]
        widget._pending_side = "left"
        widget._pending_path = "/tmp/anim.gif"
        widget._on_conversion_done(fake_frames, [250, 100], _NATURAL_W, _NATURAL_H)
        assert widget._timers["left"].interval() == 250

    def test_anim_idx_advances_on_tick_left(self, widget, model):
        fake_frames = [_FAKE_FRAME, _FAKE_FRAME, _FAKE_FRAME]
        img = OledImageItem(image_path="/t.gif", frames=fake_frames)
        model.oled.left.images = [img]
        widget._frame_delays["left"] = [[100, 100, 100]]
        widget._anim_idx["left"] = [0]
        widget._on_timer_tick("left")
        assert widget._anim_idx["left"][0] == 1

    def test_anim_idx_wraps_around_left(self, widget, model):
        fake_frames = [_FAKE_FRAME, _FAKE_FRAME]
        img = OledImageItem(image_path="/t.gif", frames=fake_frames)
        model.oled.left.images = [img]
        widget._frame_delays["left"] = [[100, 100]]
        widget._anim_idx["left"] = [1]
        widget._on_timer_tick("left")
        assert widget._anim_idx["left"][0] == 0

    def test_real_gif_worker_emits_delays_matching_frames(self, qtbot):
        gif_path = FIXTURES / "test_anim.gif"
        worker = _ConversionWorker(gif_path)
        with qtbot.waitSignal(worker.finished, timeout=2000) as blocker:
            worker.start()
        frames = blocker.args[0]
        delays = blocker.args[1]
        assert len(delays) == len(frames)

    def test_real_gif_worker_emits_multiple_frames(self, qtbot):
        gif_path = FIXTURES / "test_anim.gif"
        worker = _ConversionWorker(gif_path)
        with qtbot.waitSignal(worker.finished, timeout=2000) as blocker:
            worker.start()
        frames = blocker.args[0]
        delays = blocker.args[1]
        assert len(frames) >= 2
        assert len(delays) >= 2
        assert all(d >= 50 for d in delays)

    def test_show_frame_wrong_size_skipped(self, widget):
        """_show_frame ignore silencieusement une frame de mauvaise taille."""
        bad_img = OledImageItem(image_path="/t.png", frames=[bytes(10)])
        widget._model.oled.left.images = [bad_img]
        widget._canvas_left.sync_images(1)
        widget._show_frame("left", 0, 0)
        assert widget._canvas_left._pixmaps[0] is None


# ─── Checkboxes côté gauche ───────────────────────────────────────────────────

class TestOledWidgetCheckboxesLeft:
    def test_left_layer_check_exists(self, widget):
        cb = widget.findChild(QCheckBox, "left_layer_check")
        assert cb is not None

    def test_left_caps_check_exists(self, widget):
        cb = widget.findChild(QCheckBox, "left_caps_check")
        assert cb is not None

    def test_left_wpm_check_exists(self, widget):
        cb = widget.findChild(QCheckBox, "left_wpm_check")
        assert cb is not None

    def test_left_luna_check_exists(self, widget):
        cb = widget.findChild(QCheckBox, "left_luna_check")
        assert cb is not None

    def test_left_checkboxes_unchecked_by_default(self, widget):
        for name in ("left_layer_check", "left_caps_check", "left_wpm_check", "left_luna_check"):
            cb = widget.findChild(QCheckBox, name)
            assert not cb.isChecked(), f"{name} doit être décoché par défaut"

    def test_check_left_layer_updates_model(self, widget, model):
        cb = widget.findChild(QCheckBox, "left_layer_check")
        cb.setChecked(True)
        assert model.oled.left.layer.enabled is True

    def test_check_left_caps_updates_model(self, widget, model):
        cb = widget.findChild(QCheckBox, "left_caps_check")
        cb.setChecked(True)
        assert model.oled.left.caps_lock.enabled is True

    def test_check_left_wpm_updates_model(self, widget, model):
        cb = widget.findChild(QCheckBox, "left_wpm_check")
        cb.setChecked(True)
        assert model.oled.left.wpm.enabled is True

    def test_check_left_luna_updates_model(self, widget, model):
        cb = widget.findChild(QCheckBox, "left_luna_check")
        cb.setChecked(True)
        assert model.oled.left.luna_enabled is True

    def test_uncheck_left_layer_updates_model(self, widget, model):
        cb = widget.findChild(QCheckBox, "left_layer_check")
        cb.setChecked(True)
        assert model.oled.left.layer.enabled is True
        cb.setChecked(False)
        assert model.oled.left.layer.enabled is False


# ─── Checkboxes côté droit ────────────────────────────────────────────────────

class TestOledWidgetCheckboxesRight:
    def test_right_layer_check_exists(self, widget):
        cb = widget.findChild(QCheckBox, "right_layer_check")
        assert cb is not None

    def test_right_caps_check_exists(self, widget):
        cb = widget.findChild(QCheckBox, "right_caps_check")
        assert cb is not None

    def test_right_wpm_check_exists(self, widget):
        cb = widget.findChild(QCheckBox, "right_wpm_check")
        assert cb is not None

    def test_right_luna_check_exists(self, widget):
        cb = widget.findChild(QCheckBox, "right_luna_check")
        assert cb is not None

    def test_right_checkboxes_unchecked_by_default(self, widget):
        for name in ("right_layer_check", "right_caps_check", "right_wpm_check", "right_luna_check"):
            cb = widget.findChild(QCheckBox, name)
            assert not cb.isChecked(), f"{name} doit être décoché par défaut"

    def test_check_right_layer_updates_model(self, widget, model):
        cb = widget.findChild(QCheckBox, "right_layer_check")
        cb.setChecked(True)
        assert model.oled.right.layer.enabled is True

    def test_check_right_luna_updates_model(self, widget, model):
        cb = widget.findChild(QCheckBox, "right_luna_check")
        cb.setChecked(True)
        assert model.oled.right.luna_enabled is True

    def test_check_right_does_not_affect_left(self, widget, model):
        widget.findChild(QCheckBox, "right_layer_check").setChecked(True)
        assert model.oled.right.layer.enabled is True
        assert model.oled.left.layer.enabled is False


# ─── Sync depuis le modèle ────────────────────────────────────────────────────

class TestOledWidgetSync:
    def test_sync_from_model_checks_correct_boxes(self, qtbot, model):
        model.oled.left.caps_lock.enabled = True
        model.oled.left.wpm.enabled = True
        model.oled.right.luna_enabled = True
        w = OledWidget(model)
        qtbot.addWidget(w)
        assert not w.findChild(QCheckBox, "left_layer_check").isChecked()
        assert w.findChild(QCheckBox, "left_caps_check").isChecked()
        assert w.findChild(QCheckBox, "left_wpm_check").isChecked()
        assert not w.findChild(QCheckBox, "right_layer_check").isChecked()
        assert w.findChild(QCheckBox, "right_luna_check").isChecked()

    def test_sync_from_model_does_not_trigger_signal(self, qtbot, model):
        """La synchronisation initiale ne doit pas modifier le modèle via signal."""
        model.oled.left.layer.enabled = True
        model.oled.right.wpm.enabled = True
        w = OledWidget(model)
        qtbot.addWidget(w)
        assert model.oled.left.layer.enabled is True
        assert model.oled.right.wpm.enabled is True


# ─── Canvas drag items ────────────────────────────────────────────────────────

class TestOledCanvasDrag:
    def test_canvas_left_references_left_side(self, widget, model):
        """Le canvas gauche référence bien model.oled.left."""
        assert widget._canvas_left._side is model.oled.left

    def test_canvas_right_references_right_side(self, widget, model):
        """Le canvas droit référence bien model.oled.right."""
        assert widget._canvas_right._side is model.oled.right

    def test_drag_layer_updates_col_and_line(self, widget, model):
        """Simuler un drag de l'overlay Layer met à jour col/line."""
        model.oled.left.layer.enabled = True
        model.oled.left.layer.col = 0
        model.oled.left.layer.line = 0
        canvas = widget._canvas_left
        canvas._dragging_item = "layer"
        canvas._drag_offset_x = 0
        canvas._drag_offset_y = 0
        px = 2 * canvas.CHAR_W + 1
        py = 3 * canvas.PAGE_H + 1
        model.oled.left.layer.col = max(0, min(px // canvas.CHAR_W, 4))
        model.oled.left.layer.line = max(0, min(py // canvas.PAGE_H, 15))
        assert model.oled.left.layer.col == 2
        assert model.oled.left.layer.line == 3

    def test_drag_luna_updates_line_only(self, widget, model):
        """Drag de Luna ne modifie que luna_line (col toujours 0)."""
        model.oled.left.luna_enabled = True
        model.oled.left.luna_line = 0
        canvas = widget._canvas_left
        canvas._dragging_item = "luna"
        canvas._drag_offset_x = 0
        canvas._drag_offset_y = 0
        py = 5 * canvas.PAGE_H + 1
        new_line = max(0, min(py // canvas.PAGE_H, 15))
        model.oled.left.luna_line = new_line
        assert model.oled.left.luna_line == 5

    def test_drag_constrained_to_max_col(self, widget, model):
        """col ne dépasse pas 4 (limite 5 colonnes pour 32px / 6px)."""
        canvas = widget._canvas_left
        px = 1000
        new_col = max(0, min(px // canvas.CHAR_W, 4))
        assert new_col == 4

    def test_drag_constrained_to_max_line(self, widget, model):
        """line ne dépasse pas 15 (16 pages pour 128px / 8px)."""
        canvas = widget._canvas_left
        py = 5000
        new_line = max(0, min(py // canvas.PAGE_H, 15))
        assert new_line == 15

    def test_item_rect_returns_none_when_disabled(self, widget, model):
        """_item_rect retourne None pour un item désactivé."""
        model.oled.left.layer.enabled = False
        canvas = widget._canvas_left
        assert canvas._item_rect("layer") is None

    def test_item_rect_returns_correct_position(self, widget, model):
        """_item_rect retourne la position correcte en pixels widget."""
        model.oled.left.wpm.enabled = True
        model.oled.left.wpm.col = 1
        model.oled.left.wpm.line = 2
        canvas = widget._canvas_left
        rect = canvas._item_rect("wpm")
        assert rect is not None
        x, y, w, h = rect
        assert x == 1 * canvas.CHAR_W
        assert y == 2 * canvas.PAGE_H


# ─── Canvas drag images ───────────────────────────────────────────────────────

class TestOledCanvasDragImage:
    def test_drag_image_sets_dragging_item(self, widget, model):
        """Après import, _dragging_item peut être 'image:0'."""
        img = OledImageItem(image_path="/t.png", frames=[_FAKE_FRAME], natural_w=32, natural_h=128)
        model.oled.left.images = [img]
        canvas = widget._canvas_left
        canvas.sync_images(1)
        canvas._dragging_item = "image:0"
        assert canvas._dragging_item == "image:0"

    def test_drag_image_updates_col_and_line(self, widget, model):
        """mouseMoveEvent avec 'image:0' met à jour images[0].col/line."""
        img = OledImageItem(image_path="/t.png", frames=[_FAKE_FRAME], col=0, line=0)
        model.oled.left.images = [img]
        canvas = widget._canvas_left
        canvas._dragging_item = "image:0"
        canvas._drag_offset_x = 0
        canvas._drag_offset_y = 0
        px = 2 * canvas.CHAR_W + 1
        py = 3 * canvas.PAGE_H + 1
        new_col = max(0, min((px - canvas._drag_offset_x) // canvas.CHAR_W, 4))
        new_line = max(0, min((py - canvas._drag_offset_y) // canvas.PAGE_H, 15))
        model.oled.left.images[0].col = new_col
        model.oled.left.images[0].line = new_line
        assert model.oled.left.images[0].col == 2
        assert model.oled.left.images[0].line == 3

    def test_drag_image_col_clamped_to_max(self, widget, model):
        """images[0].col ne dépasse pas 4."""
        canvas = widget._canvas_left
        canvas._drag_offset_x = 0
        px = 9999
        new_col = max(0, min(px // canvas.CHAR_W, 4))
        assert new_col == 4

    def test_drag_image_line_clamped_to_max(self, widget, model):
        """images[0].line ne dépasse pas 15."""
        canvas = widget._canvas_left
        canvas._drag_offset_y = 0
        py = 9999
        new_line = max(0, min(py // canvas.PAGE_H, 15))
        assert new_line == 15

    def test_image_rect_uses_natural_size(self, widget, model):
        """_image_rect(0) retourne la taille naturelle × SCALE."""
        img = OledImageItem(image_path="/t.png", frames=[_FAKE_FRAME],
                            natural_w=20, natural_h=50, col=1, line=2)
        model.oled.left.images = [img]
        canvas = widget._canvas_left
        r = canvas._image_rect(0)
        assert r is not None
        x, y, w, h = r
        assert x == 1 * canvas.CHAR_W
        assert y == 2 * canvas.PAGE_H
        assert w == 20 * canvas.SCALE
        assert h == 50 * canvas.SCALE

    def test_image_rect_none_without_frames(self, widget, model):
        """_image_rect retourne None si l'image n'a pas de frames (pas encore importée)."""
        img = OledImageItem(image_path="/t.png")  # no frames
        model.oled.left.images = [img]
        canvas = widget._canvas_left
        assert canvas._image_rect(0) is None

    def test_negative_button_toggles_inverted(self, widget, model):
        """Le bouton Négatif bascule inverted sur l'image sélectionnée."""
        img = OledImageItem(image_path="/t.png", frames=[_FAKE_FRAME], inverted=False)
        model.oled.left.images = [img]
        canvas = widget._canvas_left
        canvas._selected_item = "image:0"
        widget._on_negative_clicked("left")
        assert model.oled.left.images[0].inverted is True
        widget._on_negative_clicked("left")
        assert model.oled.left.images[0].inverted is False

    def test_negative_button_no_effect_without_selection(self, widget, model):
        """Le bouton Négatif ne fait rien si aucune image n'est sélectionnée."""
        img = OledImageItem(image_path="/t.png", frames=[_FAKE_FRAME], inverted=False)
        model.oled.left.images = [img]
        canvas = widget._canvas_left
        canvas._selected_item = None
        widget._on_negative_clicked("left")
        assert model.oled.left.images[0].inverted is False


# ─── set_active_sides ─────────────────────────────────────────────────────────

class TestOledSetActiveSides:
    def test_groups_stored(self, widget):
        assert widget._group_left is not None
        assert widget._group_right is not None

    def test_both_visible_by_default(self, qtbot, model):
        """Avec oled_sides=["left","right"] dans le modèle, les deux groupes ne sont pas masqués."""
        model.keyboard.oled_sides = ["left", "right"]
        w = OledWidget(model)
        qtbot.addWidget(w)
        assert not w._group_left.isHidden()
        assert not w._group_right.isHidden()

    def test_left_only_hides_right(self, widget):
        widget.set_active_sides(["left"])
        assert not widget._group_left.isHidden()
        assert widget._group_right.isHidden()

    def test_right_only_hides_left(self, widget):
        widget.set_active_sides(["right"])
        assert widget._group_left.isHidden()
        assert not widget._group_right.isHidden()

    def test_none_hides_both(self, widget):
        widget.set_active_sides([])
        assert widget._group_left.isHidden()
        assert widget._group_right.isHidden()

    def test_set_both_restores(self, widget):
        widget.set_active_sides([])
        widget.set_active_sides(["left", "right"])
        assert not widget._group_left.isHidden()
        assert not widget._group_right.isHidden()
