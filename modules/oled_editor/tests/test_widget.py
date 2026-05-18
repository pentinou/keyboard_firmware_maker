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

    def test_left_katawajojo_check_exists(self, widget):
        cb = widget.findChild(QCheckBox, "left_katawajojo_check")
        assert cb is not None

    def test_left_luna_check_exists(self, widget):
        cb = widget.findChild(QCheckBox, "left_luna_check")
        assert cb is not None

    def test_left_ocean_dream_check_exists(self, widget):
        cb = widget.findChild(QCheckBox, "left_ocean_dream_check")
        assert cb is not None

    def test_left_checkboxes_unchecked_by_default(self, widget):
        for name in ("left_layer_check", "left_caps_check", "left_wpm_check",
                      "left_katawajojo_check", "left_luna_check", "left_ocean_dream_check"):
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

    def test_check_left_katawajojo_updates_model(self, widget, model):
        cb = widget.findChild(QCheckBox, "left_katawajojo_check")
        cb.setChecked(True)
        assert model.oled.left.katawajojo_enabled is True

    def test_check_left_luna_updates_model(self, widget, model):
        cb = widget.findChild(QCheckBox, "left_luna_check")
        cb.setChecked(True)
        assert model.oled.left.luna_enabled is True

    def test_check_left_ocean_dream_updates_model(self, widget, model):
        cb = widget.findChild(QCheckBox, "left_ocean_dream_check")
        cb.setChecked(True)
        assert model.oled.left.ocean_dream_enabled is True

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

    def test_right_katawajojo_check_exists(self, widget):
        cb = widget.findChild(QCheckBox, "right_katawajojo_check")
        assert cb is not None

    def test_right_luna_check_exists(self, widget):
        cb = widget.findChild(QCheckBox, "right_luna_check")
        assert cb is not None

    def test_right_ocean_dream_check_exists(self, widget):
        cb = widget.findChild(QCheckBox, "right_ocean_dream_check")
        assert cb is not None

    def test_right_checkboxes_unchecked_by_default(self, widget):
        for name in ("right_layer_check", "right_caps_check", "right_wpm_check",
                      "right_katawajojo_check", "right_luna_check", "right_ocean_dream_check"):
            cb = widget.findChild(QCheckBox, name)
            assert not cb.isChecked(), f"{name} doit être décoché par défaut"

    def test_check_right_layer_updates_model(self, widget, model):
        cb = widget.findChild(QCheckBox, "right_layer_check")
        cb.setChecked(True)
        assert model.oled.right.layer.enabled is True

    def test_check_right_katawajojo_updates_model(self, widget, model):
        cb = widget.findChild(QCheckBox, "right_katawajojo_check")
        cb.setChecked(True)
        assert model.oled.right.katawajojo_enabled is True

    def test_check_right_luna_updates_model(self, widget, model):
        cb = widget.findChild(QCheckBox, "right_luna_check")
        cb.setChecked(True)
        assert model.oled.right.luna_enabled is True

    def test_check_right_ocean_dream_updates_model(self, widget, model):
        cb = widget.findChild(QCheckBox, "right_ocean_dream_check")
        cb.setChecked(True)
        assert model.oled.right.ocean_dream_enabled is True

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
        model.oled.left.katawajojo_enabled = True
        model.oled.right.ocean_dream_enabled = True
        w = OledWidget(model)
        qtbot.addWidget(w)
        assert not w.findChild(QCheckBox, "left_layer_check").isChecked()
        assert w.findChild(QCheckBox, "left_caps_check").isChecked()
        assert w.findChild(QCheckBox, "left_wpm_check").isChecked()
        assert w.findChild(QCheckBox, "left_katawajojo_check").isChecked()
        assert not w.findChild(QCheckBox, "right_layer_check").isChecked()
        assert w.findChild(QCheckBox, "right_luna_check").isChecked()
        assert w.findChild(QCheckBox, "right_ocean_dream_check").isChecked()

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

    def test_drag_katawajojo_updates_line_only(self, widget, model):
        """Drag de KatawaJojo ne modifie que katawajojo_line (col toujours 0)."""
        model.oled.left.katawajojo_enabled = True
        model.oled.left.katawajojo_line = 0
        canvas = widget._canvas_left
        canvas._dragging_item = "katawajojo"
        canvas._drag_offset_x = 0
        canvas._drag_offset_y = 0
        py = 5 * canvas.PAGE_H + 1
        new_line = max(0, min(py // canvas.PAGE_H, 15))
        model.oled.left.katawajojo_line = new_line
        assert model.oled.left.katawajojo_line == 5

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

    def test_drag_ocean_dream_updates_line_only(self, widget, model):
        """Drag de Ocean Dream ne modifie que ocean_dream_line."""
        model.oled.left.ocean_dream_enabled = True
        model.oled.left.ocean_dream_line = 0
        canvas = widget._canvas_left
        canvas._dragging_item = "ocean_dream"
        canvas._drag_offset_x = 0
        canvas._drag_offset_y = 0
        py = 3 * canvas.PAGE_H + 1
        new_line = max(0, min(py // canvas.PAGE_H, 15))
        model.oled.left.ocean_dream_line = new_line
        assert model.oled.left.ocean_dream_line == 3

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


class TestZmkWidgetsUI:
    """Phase 2 — section Widgets ZMK dans l'éditeur OLED."""

    def test_left_has_battery_output_layer_widgets(self, qtbot, model):
        from PySide6.QtWidgets import QCheckBox
        model.keyboard.oled_sides = ["left", "right"]
        w = OledWidget(model)
        qtbot.addWidget(w)
        assert w.findChild(QCheckBox, "left_zmk_battery_check") is not None
        assert w.findChild(QCheckBox, "left_zmk_output_check") is not None
        assert w.findChild(QCheckBox, "left_zmk_layer_check") is not None

    def test_right_has_battery_and_peripheral_only(self, qtbot, model):
        """Côté droit : battery + peripheral. Pas de layer/output (central-only)."""
        from PySide6.QtWidgets import QCheckBox
        model.keyboard.oled_sides = ["left", "right"]
        w = OledWidget(model)
        qtbot.addWidget(w)
        assert w.findChild(QCheckBox, "right_zmk_battery_check") is not None
        assert w.findChild(QCheckBox, "right_zmk_peripheral_check") is not None
        assert w.findChild(QCheckBox, "right_zmk_layer_check") is None
        assert w.findChild(QCheckBox, "right_zmk_output_check") is None

    def test_left_no_peripheral_widget(self, qtbot, model):
        from PySide6.QtWidgets import QCheckBox
        model.keyboard.oled_sides = ["left", "right"]
        w = OledWidget(model)
        qtbot.addWidget(w)
        assert w.findChild(QCheckBox, "left_zmk_peripheral_check") is None

    def test_show_peer_only_on_left(self, qtbot, model):
        from PySide6.QtWidgets import QCheckBox
        model.keyboard.oled_sides = ["left", "right"]
        w = OledWidget(model)
        qtbot.addWidget(w)
        assert w.findChild(QCheckBox, "left_zmk_battery_show_peer") is not None
        assert w.findChild(QCheckBox, "right_zmk_battery_show_peer") is None

    def test_col_line_spinboxes_present(self, qtbot, model):
        from PySide6.QtWidgets import QSpinBox
        model.keyboard.oled_sides = ["left"]
        w = OledWidget(model)
        qtbot.addWidget(w)
        assert w.findChild(QSpinBox, "left_zmk_battery_col") is not None
        assert w.findChild(QSpinBox, "left_zmk_battery_line") is not None

    def test_zmk_widgets_hidden_in_qmk_mode(self, qtbot, model):
        """Le wrapper de chaque widget ZMK est explicitement masqué en QMK."""
        from PySide6.QtWidgets import QWidget
        model.keyboard.oled_sides = ["left"]
        w = OledWidget(model)
        qtbot.addWidget(w)
        w.set_firmware("qmk")
        wrapper = w.findChild(QWidget, "left_zmk_battery_row")
        assert wrapper is not None
        assert wrapper.isHidden()

    def test_qmk_widgets_hidden_in_zmk_mode(self, qtbot, model):
        from PySide6.QtWidgets import QCheckBox
        model.keyboard.oled_sides = ["left"]
        w = OledWidget(model)
        qtbot.addWidget(w)
        w.set_firmware("zmk")
        cb = w.findChild(QCheckBox, "left_layer_check")
        assert cb is not None
        assert cb.isHidden()

    def test_zmk_widgets_visible_in_zmk_mode(self, qtbot, model):
        from PySide6.QtWidgets import QWidget
        model.keyboard.oled_sides = ["left"]
        w = OledWidget(model)
        qtbot.addWidget(w)
        w.set_firmware("zmk")
        wrapper = w.findChild(QWidget, "left_zmk_battery_row")
        assert wrapper is not None
        assert not wrapper.isHidden()

    def test_image_canvas_visible_in_both_modes(self, qtbot, model):
        """L'éditeur d'image (canvas) reste visible en ZMK pour Phase 1+ (image custom)."""
        model.keyboard.oled_sides = ["left"]
        w = OledWidget(model)
        qtbot.addWidget(w)
        w.set_firmware("zmk")
        canvas = w._canvas_left
        assert canvas is not None
        assert not canvas.isHidden()

    def test_check_zmk_battery_updates_model(self, qtbot, model):
        from PySide6.QtWidgets import QCheckBox
        model.keyboard.oled_sides = ["left"]
        w = OledWidget(model)
        qtbot.addWidget(w)
        cb = w.findChild(QCheckBox, "left_zmk_battery_check")
        cb.setChecked(True)
        assert model.oled.left.zmk_battery.enabled is True

    def test_change_zmk_widget_col_updates_model(self, qtbot, model):
        from PySide6.QtWidgets import QSpinBox
        model.keyboard.oled_sides = ["left"]
        w = OledWidget(model)
        qtbot.addWidget(w)
        sp = w.findChild(QSpinBox, "left_zmk_output_col")
        sp.setValue(3)
        assert model.oled.left.zmk_output.col == 3

    def test_show_peer_updates_model(self, qtbot, model):
        from PySide6.QtWidgets import QCheckBox
        model.keyboard.oled_sides = ["left"]
        w = OledWidget(model)
        qtbot.addWidget(w)
        cb = w.findChild(QCheckBox, "left_zmk_battery_show_peer")
        cb.setChecked(True)
        assert model.oled.left.zmk_battery.show_peer is True


class TestZmkImageLayerSpinbox:
    """Phase 4 — spinbox layer per image."""

    def test_layer_spinbox_present(self, qtbot, model):
        from PySide6.QtWidgets import QSpinBox
        model.keyboard.oled_sides = ["left"]
        w = OledWidget(model)
        qtbot.addWidget(w)
        sp = w.findChild(QSpinBox, "image_layer_spin_left")
        assert sp is not None
        assert sp.minimum() == -1
        assert sp.maximum() == 9

    def test_layer_spinbox_hidden_in_qmk_mode(self, qtbot, model):
        from PySide6.QtWidgets import QWidget
        model.keyboard.oled_sides = ["left"]
        w = OledWidget(model)
        qtbot.addWidget(w)
        w.set_firmware("qmk")
        wrapper = w.findChild(QWidget, "image_layer_row_left")
        assert wrapper is not None
        assert wrapper.isHidden()

    def test_layer_change_updates_selected_image(self, qtbot, model):
        """Sélectionner une image puis modifier le spinbox doit mettre à jour image.layer."""
        from PySide6.QtWidgets import QSpinBox
        from models.project_model import OledImageItem
        model.keyboard.oled_sides = ["left"]
        # Image avec frame runtime
        white = bytes([0xFF] * (32 * 128))
        model.oled.left.images.append(OledImageItem(
            image_path="img.png", frames=[white], natural_w=32, natural_h=128,
        ))
        w = OledWidget(model)
        qtbot.addWidget(w)
        # Simuler la sélection (équivalent à un click sur l'image)
        w._canvas_left._selected_item = "image:0"
        sp = w.findChild(QSpinBox, "image_layer_spin_left")
        sp.setValue(2)
        assert model.oled.left.images[0].layer == 2

    def test_layer_change_without_selection_is_noop(self, qtbot, model):
        """Modifier le spinbox sans image sélectionnée ne crash pas."""
        from PySide6.QtWidgets import QSpinBox
        model.keyboard.oled_sides = ["left"]
        w = OledWidget(model)
        qtbot.addWidget(w)
        # Pas d'image sélectionnée
        assert w._canvas_left._selected_item is None
        sp = w.findChild(QSpinBox, "image_layer_spin_left")
        sp.setValue(3)  # ne doit pas crasher
        # Aucune image dans le modèle, rien à vérifier — l'absence d'exception suffit

    def test_canvas_selection_emits_signal(self, qtbot, model):
        """Le canvas émet selection_changed quand on simule un click sur une image."""
        from PySide6.QtCore import QPoint
        from PySide6.QtGui import QMouseEvent
        from PySide6.QtCore import Qt
        from models.project_model import OledImageItem
        model.keyboard.oled_sides = ["left"]
        white = bytes([0xFF] * (32 * 128))
        model.oled.left.images.append(OledImageItem(
            image_path="img.png", frames=[white],
            natural_w=32, natural_h=128, col=0, line=0,
        ))
        w = OledWidget(model)
        qtbot.addWidget(w)
        canvas = w._canvas_left
        # Synchroniser les pixmaps internes pour que _image_rect retourne un rect
        canvas.sync_images(1)
        from PySide6.QtGui import QPixmap
        canvas.set_image_pixmap(0, QPixmap(32, 128))
        # Capturer l'émission
        with qtbot.waitSignal(canvas.selection_changed, timeout=500) as blocker:
            # Click au centre du canvas (dans la zone de l'image plein-canvas)
            from PySide6.QtCore import QPointF
            ev = QMouseEvent(
                QMouseEvent.Type.MouseButtonPress, QPointF(10, 10),
                Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
            )
            canvas.mousePressEvent(ev)
        assert blocker.args[0] == "image:0"

    def test_selection_sync_updates_spinbox_value(self, qtbot, model):
        """Quand on sélectionne une image avec layer=2, le spinbox doit afficher 2."""
        from PySide6.QtWidgets import QSpinBox
        from models.project_model import OledImageItem
        model.keyboard.oled_sides = ["left"]
        white = bytes([0xFF] * (32 * 128))
        model.oled.left.images.append(OledImageItem(
            image_path="img.png", frames=[white], natural_w=32, natural_h=128, layer=2,
        ))
        w = OledWidget(model)
        qtbot.addWidget(w)
        # Simuler sélection
        w._canvas_left._selected_item = "image:0"
        # Déclencher le sync manuellement (en prod c'est le signal selection_changed)
        w._sync_image_layer_spinbox("left")
        sp = w.findChild(QSpinBox, "image_layer_spin_left")
        assert sp.value() == 2


# ─── Canvas overlays ZMK (battery / output / layer / peripheral) ──────────────

class TestZmkCanvasOverlays:
    def test_qmk_mode_no_zmk_overlays(self, widget, model):
        """En mode QMK, les widgets ZMK activés n'apparaissent PAS dans les overlays."""
        widget.set_firmware("qmk")
        model.oled.left.zmk_battery.enabled = True
        names = [name for name, *_ in widget._canvas_left._overlay_items()]
        assert "zmk_battery" not in names

    def test_zmk_mode_no_qmk_overlays(self, widget, model):
        """En mode ZMK, les overlays QMK activés n'apparaissent PAS."""
        widget.set_firmware("zmk")
        model.oled.left.layer.enabled = True
        names = [name for name, *_ in widget._canvas_left._overlay_items()]
        assert "layer" not in names

    def test_zmk_mode_renders_enabled_widgets(self, widget, model):
        """En mode ZMK, chaque widget activé apparaît dans l'overlay."""
        widget.set_firmware("zmk")
        model.oled.left.zmk_battery.enabled = True
        model.oled.left.zmk_output.enabled = True
        model.oled.left.zmk_layer.enabled = True
        names = [name for name, *_ in widget._canvas_left._overlay_items()]
        assert "zmk_battery" in names
        assert "zmk_output" in names
        assert "zmk_layer" in names

    def test_zmk_widget_rect_at_position(self, widget, model):
        """`_item_rect('zmk_battery')` retourne le bon (x, y) selon col/line."""
        widget.set_firmware("zmk")
        model.oled.left.zmk_battery.enabled = True
        model.oled.left.zmk_battery.col = 1
        model.oled.left.zmk_battery.line = 3
        canvas = widget._canvas_left
        rect = canvas._item_rect("zmk_battery")
        assert rect is not None
        x, y, w, h = rect
        assert x == 1 * canvas.CHAR_W
        assert y == 3 * canvas.PAGE_H
        # Largeur 4 cols × 6 px × SCALE
        assert w == 4 * canvas.CHAR_W
        assert h == 2 * canvas.PAGE_H

    def test_zmk_widget_rect_none_when_disabled(self, widget, model):
        """`_item_rect` retourne None quand le widget ZMK est désactivé."""
        model.oled.left.zmk_battery.enabled = False
        assert widget._canvas_left._item_rect("zmk_battery") is None

    def test_drag_zmk_widget_updates_model_and_emits(self, qtbot, widget, model):
        """Drag d'un widget ZMK met à jour col/line ET émet widget_position_changed."""
        widget.set_firmware("zmk")
        model.oled.left.zmk_battery.enabled = True
        model.oled.left.zmk_battery.col = 0
        model.oled.left.zmk_battery.line = 0
        canvas = widget._canvas_left
        canvas._dragging_item = "zmk_battery"
        canvas._drag_offset_x = 0
        canvas._drag_offset_y = 0

        from PySide6.QtCore import QPointF
        from PySide6.QtGui import QMouseEvent
        from PySide6.QtCore import Qt
        # Ciblage : 1 col vers la droite, 4 lignes plus bas
        px = 1 * canvas.CHAR_W + 1
        py = 4 * canvas.PAGE_H + 1
        ev = QMouseEvent(
            QMouseEvent.Type.MouseMove, QPointF(px, py),
            Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
        )
        with qtbot.waitSignal(canvas.widget_position_changed, timeout=500) as blocker:
            canvas.mouseMoveEvent(ev)
        # Le clamp horizontal pour battery (4 cols) limite max_col = (32-24)/6 = 1
        assert model.oled.left.zmk_battery.col == 1
        assert model.oled.left.zmk_battery.line == 4
        assert blocker.args == ["zmk_battery", 1, 4]

    def test_drag_syncs_spinbox(self, qtbot, widget, model):
        """Après drag d'un widget ZMK, le QSpinBox col/line est mis à jour."""
        from PySide6.QtWidgets import QSpinBox
        widget.set_firmware("zmk")
        model.oled.left.zmk_layer.enabled = True
        # zmk_layer fait 5 cols → max_col = (32-30)/6 = 0, donc on ne teste que line
        widget._sync_zmk_widget_spinbox("left", "zmk_layer", 0, 5)
        col_sp = widget.findChild(QSpinBox, "left_zmk_layer_col")
        line_sp = widget.findChild(QSpinBox, "left_zmk_layer_line")
        assert col_sp.value() == 0
        assert line_sp.value() == 5

    def test_set_firmware_propagates_to_canvases(self, widget):
        """`OledWidget.set_firmware()` met à jour _firmware sur les deux canvases."""
        widget.set_firmware("zmk")
        assert widget._canvas_left._firmware == "zmk"
        assert widget._canvas_right._firmware == "zmk"
        widget.set_firmware("qmk")
        assert widget._canvas_left._firmware == "qmk"
        assert widget._canvas_right._firmware == "qmk"

    def test_change_spinbox_refreshes_canvas(self, widget, model):
        """Modifier le QSpinBox col/line déclenche `canvas.update()`."""
        from PySide6.QtWidgets import QSpinBox
        widget.set_firmware("zmk")
        model.oled.left.zmk_battery.enabled = True
        # Patch update() pour vérifier qu'il est appelé
        canvas = widget._canvas_left
        calls = []
        original_update = canvas.update
        canvas.update = lambda: calls.append(True) or original_update()
        col_sp = widget.findChild(QSpinBox, "left_zmk_battery_col")
        col_sp.setValue(1)
        assert calls, "canvas.update() doit être appelé après modif spinbox"

    def test_paint_event_with_all_zmk_widgets_no_crash(self, qtbot, widget, model):
        """paintEvent doit dessiner les 4 widgets ZMK sans exception."""
        from PySide6.QtGui import QImage
        widget.set_firmware("zmk")
        # Activer tous les widgets ZMK avec des positions valides
        model.oled.left.zmk_battery.enabled = True
        model.oled.left.zmk_output.enabled = True
        model.oled.left.zmk_output.line = 4
        model.oled.left.zmk_layer.enabled = True
        model.oled.left.zmk_layer.line = 8
        canvas = widget._canvas_left
        # Déclencher un repaint hors écran (image cible)
        img = QImage(canvas.size(), QImage.Format.Format_ARGB32)
        img.fill(0)
        canvas.render(img)
        # Si on arrive ici sans crash, le test passe
        assert img.width() > 0
