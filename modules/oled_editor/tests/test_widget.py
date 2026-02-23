"""Tests pytest-qt pour modules/oled_editor/widget.py — OledWidget."""
from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QLabel, QPushButton

from models.project_model import ProjectModel
from modules.oled_editor.widget import OledWidget, _ConversionWorker

FIXTURES = Path(__file__).parent / "fixtures"

_FAKE_FRAME = bytes(64 * 128)
_DEFAULT_DELAYS = [100]


@pytest.fixture
def model() -> ProjectModel:
    return ProjectModel()


@pytest.fixture
def widget(qtbot, model):
    w = OledWidget(model)
    qtbot.addWidget(w)
    return w


class TestOledWidgetInit:
    def test_import_btn_exists(self, widget):
        btn = widget.findChild(QPushButton, "import_btn")
        assert btn is not None

    def test_preview_label_exists(self, widget):
        label = widget.findChild(QLabel, "preview_label")
        assert label is not None

    def test_import_btn_text(self, widget):
        btn = widget.findChild(QPushButton, "import_btn")
        assert "Importer" in btn.text()

    def test_preview_label_initial_text(self, widget):
        label = widget.findChild(QLabel, "preview_label")
        assert label.pixmap() is None or label.pixmap().isNull()

    def test_timer_not_active_on_init(self, widget):
        assert not widget._timer.isActive()


class TestOledWidgetConversion:
    def test_conversion_updates_model_image_path(self, widget, model):
        """Après conversion, model.oled.image_path doit être mis à jour."""
        png_path = str(FIXTURES / "test_100x100.png")
        widget._pending_path = png_path
        widget._on_conversion_done([_FAKE_FRAME], _DEFAULT_DELAYS)
        assert model.oled.image_path == png_path

    def test_conversion_updates_model_frames(self, widget, model):
        """Après conversion, model.oled.frames doit contenir les frames."""
        widget._pending_path = str(FIXTURES / "test_100x100.png")  # L2 : plus de /tmp hardcodé
        widget._on_conversion_done([_FAKE_FRAME], _DEFAULT_DELAYS)
        assert model.oled.frames == [_FAKE_FRAME]

    def test_conversion_shows_preview(self, widget):
        """Après conversion, le QLabel preview doit afficher un pixmap non-nul."""
        widget._pending_path = str(FIXTURES / "test_100x100.png")  # L2 : plus de /tmp hardcodé
        widget._on_conversion_done([_FAKE_FRAME], _DEFAULT_DELAYS)
        label = widget.findChild(QLabel, "preview_label")
        assert label.pixmap() is not None
        assert not label.pixmap().isNull()

    def test_real_png_conversion_via_worker(self, widget, model, qtbot):
        """Test bout-en-bout avec un vrai PNG via le worker QThread."""
        png_path = FIXTURES / "test_100x100.png"
        worker = _ConversionWorker(png_path)
        with qtbot.waitSignal(worker.finished, timeout=2000) as blocker:
            worker.start()
        frames = blocker.args[0]
        delays = blocker.args[1]
        assert len(frames) == 1
        assert len(frames[0]) == 64 * 128
        assert isinstance(delays, list)
        assert len(delays) >= 1


class TestOledWidgetAnimation:
    def test_timer_not_active_after_single_frame(self, widget):
        """Pas d'animation pour image statique (1 frame)."""
        widget._pending_path = "/tmp/test.png"
        widget._on_conversion_done([_FAKE_FRAME], [100])
        assert not widget._timer.isActive()

    def test_timer_active_after_multi_frame(self, widget):
        """Timer démarré pour GIF multi-frames."""
        fake_frames = [_FAKE_FRAME, _FAKE_FRAME, _FAKE_FRAME]
        widget._pending_path = "/tmp/test.gif"
        widget._on_conversion_done(fake_frames, [100, 150, 200])
        assert widget._timer.isActive()

    def test_timer_stopped_on_new_import(self, widget):
        """Ancienne animation stoppée quand une nouvelle image est importée."""
        fake_frames = [_FAKE_FRAME, _FAKE_FRAME]
        widget._pending_path = "/tmp/anim.gif"
        widget._on_conversion_done(fake_frames, [100, 100])
        assert widget._timer.isActive()
        # Nouvelle image statique → timer stoppé
        widget._pending_path = "/tmp/static.png"
        widget._on_conversion_done([_FAKE_FRAME], [100])
        assert not widget._timer.isActive()

    def test_timer_interval_matches_first_delay(self, widget):
        """L'intervalle du timer correspond au délai de la première frame."""
        fake_frames = [_FAKE_FRAME, _FAKE_FRAME]
        widget._pending_path = "/tmp/anim.gif"
        widget._on_conversion_done(fake_frames, [250, 100])
        assert widget._timer.interval() == 250

    def test_anim_idx_advances_on_tick(self, widget):
        """_on_timer_tick doit avancer l'index de frame."""
        fake_frames = [_FAKE_FRAME, _FAKE_FRAME, _FAKE_FRAME]
        widget._model.oled.frames = fake_frames
        widget._frame_delays = [100, 100, 100]
        widget._anim_idx = 0
        widget._on_timer_tick()
        assert widget._anim_idx == 1

    def test_anim_idx_wraps_around(self, widget):
        """L'index de frame revient à 0 après la dernière frame."""
        fake_frames = [_FAKE_FRAME, _FAKE_FRAME]
        widget._model.oled.frames = fake_frames
        widget._frame_delays = [100, 100]
        widget._anim_idx = 1  # dernière frame
        widget._on_timer_tick()
        assert widget._anim_idx == 0

    def test_real_gif_worker_emits_delays_matching_frames(self, qtbot):
        """Le nombre de délais doit correspondre au nombre de frames."""
        gif_path = FIXTURES / "test_anim.gif"
        worker = _ConversionWorker(gif_path)
        with qtbot.waitSignal(worker.finished, timeout=2000) as blocker:
            worker.start()
        frames = blocker.args[0]
        delays = blocker.args[1]
        assert len(delays) == len(frames)

    def test_real_gif_worker_emits_multiple_frames(self, qtbot):
        """Worker GIF multi-frames émet bien (frames, delays) avec N>1."""
        gif_path = FIXTURES / "test_anim.gif"
        worker = _ConversionWorker(gif_path)
        with qtbot.waitSignal(worker.finished, timeout=2000) as blocker:
            worker.start()
        frames = blocker.args[0]
        delays = blocker.args[1]
        assert len(frames) >= 2
        assert len(delays) >= 2
        assert all(d >= 50 for d in delays)

    def test_timer_tick_short_delays_no_error(self, widget):
        """L3/M2 — _on_timer_tick ne lève pas IndexError si delays plus court que frames."""
        fake_frames = [_FAKE_FRAME, _FAKE_FRAME, _FAKE_FRAME]
        widget._model.oled.frames = fake_frames
        widget._frame_delays = [100]  # 1 délai pour 3 frames → hors-bornes potentiel
        widget._anim_idx = 0
        # Ne doit pas lever d'exception
        widget._on_timer_tick()
        assert widget._anim_idx == 1
        widget._on_timer_tick()  # idx=2, _frame_delays[2] inexistant → fallback 100ms
        assert widget._anim_idx == 2
        assert widget._timer.interval() == 100  # fallback

    def test_show_frame_wrong_size_skipped(self, widget):
        """L4/M1 — _show_frame ignore silencieusement une frame de mauvaise taille."""
        bad_frame = bytes(10)  # trop court : 10 octets au lieu de 64*128
        widget._model.oled.frames = [bad_frame]
        label = widget.findChild(__import__("PySide6.QtWidgets", fromlist=["QLabel"]).QLabel, "preview_label")
        # Le pixmap ne doit pas être mis à jour (pas de crash, pas de segfault)
        widget._show_frame(0)
        # Le label ne doit pas avoir de pixmap valide issu d'une frame corrompue
        assert label.pixmap() is None or label.pixmap().isNull()


class TestOledWidgetOverlays:
    def test_layer_checkbox_exists(self, widget):
        cb = widget.findChild(QCheckBox, "layer_check")
        assert cb is not None

    def test_caps_lock_checkbox_exists(self, widget):
        cb = widget.findChild(QCheckBox, "caps_lock_check")
        assert cb is not None

    def test_wpm_checkbox_exists(self, widget):
        cb = widget.findChild(QCheckBox, "wpm_check")
        assert cb is not None

    def test_checkboxes_unchecked_by_default(self, widget):
        for name in ("layer_check", "caps_lock_check", "wpm_check"):
            cb = widget.findChild(QCheckBox, name)
            assert not cb.isChecked(), f"{name} doit être décoché par défaut"

    def test_overlays_empty_by_default(self, widget, model):
        assert model.oled.overlays == []

    def test_check_layer_adds_to_overlays(self, widget, model, qtbot):
        cb = widget.findChild(QCheckBox, "layer_check")
        cb.setChecked(True)
        assert "layer" in model.oled.overlays

    def test_check_caps_lock_adds_to_overlays(self, widget, model, qtbot):
        cb = widget.findChild(QCheckBox, "caps_lock_check")
        cb.setChecked(True)
        assert "caps_lock" in model.oled.overlays

    def test_check_wpm_adds_to_overlays(self, widget, model, qtbot):
        cb = widget.findChild(QCheckBox, "wpm_check")
        cb.setChecked(True)
        assert "wpm" in model.oled.overlays

    def test_uncheck_removes_from_overlays(self, widget, model, qtbot):
        cb = widget.findChild(QCheckBox, "layer_check")
        cb.setChecked(True)
        assert "layer" in model.oled.overlays
        cb.setChecked(False)
        assert "layer" not in model.oled.overlays

    def test_multiple_overlays_all_present(self, widget, model, qtbot):
        widget.findChild(QCheckBox, "layer_check").setChecked(True)
        widget.findChild(QCheckBox, "wpm_check").setChecked(True)
        assert "layer" in model.oled.overlays
        assert "wpm" in model.oled.overlays
        assert "caps_lock" not in model.oled.overlays

    def test_sync_from_model_checks_correct_boxes(self, qtbot, model):
        """_sync_overlays_from_model doit cocher les cases selon model.oled.overlays."""
        model.oled.overlays = ["caps_lock", "wpm"]
        w = OledWidget(model)
        qtbot.addWidget(w)
        assert not w.findChild(QCheckBox, "layer_check").isChecked()
        assert w.findChild(QCheckBox, "caps_lock_check").isChecked()
        assert w.findChild(QCheckBox, "wpm_check").isChecked()

    def test_sync_from_model_does_not_trigger_signal(self, qtbot, model):
        """La synchronisation ne doit pas modifier model.oled.overlays via signal."""
        model.oled.overlays = ["layer"]
        w = OledWidget(model)
        qtbot.addWidget(w)
        # overlays doit rester ["layer"], pas être reconstruit via signal
        assert model.oled.overlays == ["layer"]
