"""Tests pour modules/keyboard_editor/wiring_scene.py.

Vérifie la construction de la scène de câblage QGraphicsScene.
"""
from __future__ import annotations

import pytest

from modules.keyboard_editor.kle_parser import KleKey
from modules.keyboard_editor.wiring_scene import (
    WiringData,
    _col_color,
    _row_color,
    build_wiring_scene,
)


def _make_grid_keys(rows: int, cols: int) -> list[KleKey]:
    """Crée une grille simple de touches pour les tests."""
    keys = []
    for r in range(rows):
        for c in range(cols):
            keys.append(KleKey(x=float(c), y=float(r), row=r, col=c))
    return keys


class TestBuildWiringSceneMinimal:
    """Tests avec une grille minimale 2x3."""

    @pytest.fixture()
    def data(self) -> WiringData:
        return WiringData(
            keys=_make_grid_keys(2, 3),
            row_pins=["GP0", "GP1"],
            col_pins=["GP10", "GP11", "GP12"],
        )

    def test_returns_scene(self, qapp, data):
        scene = build_wiring_scene(data)
        from PySide6.QtWidgets import QGraphicsScene
        assert isinstance(scene, QGraphicsScene)

    def test_scene_not_empty(self, qapp, data):
        scene = build_wiring_scene(data)
        assert len(scene.items()) > 0

    def test_scene_has_mcu_body(self, qapp, data):
        """La scène contient au moins un QGraphicsRectItem pour le corps MCU."""
        from PySide6.QtWidgets import QGraphicsRectItem
        scene = build_wiring_scene(data)
        rects = [i for i in scene.items() if isinstance(i, QGraphicsRectItem)]
        # MCU body + key rects (6) + pin dots + legend dots
        assert len(rects) >= 7

    def test_scene_has_wires(self, qapp, data):
        """La scène contient des QGraphicsLineItem pour les fils de câblage."""
        from PySide6.QtWidgets import QGraphicsLineItem
        scene = build_wiring_scene(data)
        lines = [i for i in scene.items() if isinstance(i, QGraphicsLineItem)]
        assert len(lines) > 0

    def test_scene_has_text_labels(self, qapp, data):
        """La scène contient des labels texte (pin names, key labels)."""
        from PySide6.QtWidgets import QGraphicsSimpleTextItem
        scene = build_wiring_scene(data)
        texts = [i for i in scene.items() if isinstance(i, QGraphicsSimpleTextItem)]
        assert len(texts) > 0


class TestBuildWiringSceneEmpty:
    """Tests avec aucune touche."""

    def test_empty_keys_shows_message(self, qapp):
        data = WiringData(keys=[], row_pins=["GP0"], col_pins=["GP1"])
        scene = build_wiring_scene(data)
        from PySide6.QtWidgets import QGraphicsSimpleTextItem
        texts = [i for i in scene.items() if isinstance(i, QGraphicsSimpleTextItem)]
        assert len(texts) == 1

    def test_no_pins_still_draws_keys(self, qapp):
        data = WiringData(keys=_make_grid_keys(2, 2), row_pins=[], col_pins=[])
        scene = build_wiring_scene(data)
        from PySide6.QtWidgets import QGraphicsRectItem
        rects = [i for i in scene.items() if isinstance(i, QGraphicsRectItem)]
        # At least 4 key rects + MCU body
        assert len(rects) >= 5


class TestBuildWiringSceneWithOled:
    """Tests avec OLED activé."""

    def test_oled_adds_components(self, qapp):
        data = WiringData(
            keys=_make_grid_keys(2, 2),
            row_pins=["GP0", "GP1"],
            col_pins=["GP10", "GP11"],
            has_oled=True,
        )
        scene = build_wiring_scene(data)
        from PySide6.QtWidgets import QGraphicsSimpleTextItem
        texts = [i for i in scene.items() if isinstance(i, QGraphicsSimpleTextItem)]
        text_strings = [t.text() for t in texts]
        assert "OLED" in text_strings

    def test_oled_has_sda_scl_labels(self, qapp):
        data = WiringData(
            keys=_make_grid_keys(2, 2),
            row_pins=["GP0", "GP1"],
            col_pins=["GP10", "GP11"],
            has_oled=True,
        )
        scene = build_wiring_scene(data)
        from PySide6.QtWidgets import QGraphicsSimpleTextItem
        texts = [t.text() for t in scene.items() if isinstance(t, QGraphicsSimpleTextItem)]
        assert "SDA" in texts
        assert "SCL" in texts


class TestBuildWiringSceneWithEncoder:
    """Tests avec encodeur activé."""

    def test_encoder_adds_circle(self, qapp):
        data = WiringData(
            keys=_make_grid_keys(2, 2),
            row_pins=["GP0", "GP1"],
            col_pins=["GP10", "GP11"],
            has_encoder=True,
            encoder_a="GP29",
            encoder_b="GP28",
        )
        scene = build_wiring_scene(data)
        from PySide6.QtWidgets import QGraphicsEllipseItem
        circles = [i for i in scene.items() if isinstance(i, QGraphicsEllipseItem)]
        # At least 1 for encoder + 1 for MCU notch
        assert len(circles) >= 2

    def test_encoder_has_label(self, qapp):
        data = WiringData(
            keys=_make_grid_keys(2, 2),
            row_pins=["GP0", "GP1"],
            col_pins=["GP10", "GP11"],
            has_encoder=True,
            encoder_a="GP29",
            encoder_b="GP28",
        )
        scene = build_wiring_scene(data)
        from PySide6.QtWidgets import QGraphicsSimpleTextItem
        texts = [t.text() for t in scene.items() if isinstance(t, QGraphicsSimpleTextItem)]
        assert "ENC" in texts


class TestColorPalettes:
    """Tests des palettes de couleurs."""

    def test_row_colors_distinct(self):
        colors = [_row_color(i).name() for i in range(8)]
        assert len(set(colors)) == 8

    def test_col_colors_distinct(self):
        colors = [_col_color(i).name() for i in range(8)]
        assert len(set(colors)) == 8

    def test_row_colors_cycle(self):
        assert _row_color(0).name() == _row_color(8).name()

    def test_col_colors_cycle(self):
        assert _col_color(0).name() == _col_color(8).name()

    def test_row_col_palettes_different(self):
        row_set = {_row_color(i).name() for i in range(8)}
        col_set = {_col_color(i).name() for i in range(8)}
        assert row_set != col_set


class TestWiringDataDefaults:
    """Tests des valeurs par défaut de WiringData."""

    def test_default_empty(self):
        data = WiringData()
        assert data.keys == []
        assert data.row_pins == []
        assert data.col_pins == []
        assert data.has_oled is False
        assert data.has_encoder is False
        assert data.split is False

    def test_constructor_with_kwargs(self):
        keys = _make_grid_keys(1, 1)
        data = WiringData(keys=keys, row_pins=["GP0"], col_pins=["GP1"], has_oled=True)
        assert len(data.keys) == 1
        assert data.has_oled is True


class TestBuildWiringSceneLegend:
    """Tests de la légende."""

    def test_legend_contains_pin_names(self, qapp):
        data = WiringData(
            keys=_make_grid_keys(2, 2),
            row_pins=["GP5", "GP6"],
            col_pins=["GP27", "GP26"],
        )
        scene = build_wiring_scene(data)
        from PySide6.QtWidgets import QGraphicsSimpleTextItem
        texts = [t.text() for t in scene.items() if isinstance(t, QGraphicsSimpleTextItem)]
        assert any("GP5" in t for t in texts)
        assert any("GP27" in t for t in texts)

    def test_legend_with_peripherals(self, qapp):
        data = WiringData(
            keys=_make_grid_keys(2, 2),
            row_pins=["GP0", "GP1"],
            col_pins=["GP10", "GP11"],
            has_oled=True,
            has_rgb=True,
            ws2812="GP16",
            serial_tx="GP1",
        )
        scene = build_wiring_scene(data)
        from PySide6.QtWidgets import QGraphicsSimpleTextItem
        texts = [t.text() for t in scene.items() if isinstance(t, QGraphicsSimpleTextItem)]
        assert "OLED (I2C)" in texts
        assert "WS2812" in texts
        assert "Serial TX" in texts
