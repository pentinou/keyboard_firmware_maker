"""Tests pytest-qt pour modules/hardware/widget.py — HardwareWidget."""
from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtWidgets import QComboBox

from models.project_model import ProjectModel
from modules.hardware.widget import HardwareWidget

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def model() -> ProjectModel:
    return ProjectModel()


@pytest.fixture
def widget(qtbot, model, tmp_path):
    """HardwareWidget chargé avec les vrais YAML du projet."""
    w = HardwareWidget(model)
    qtbot.addWidget(w)
    return w


class TestHardwareWidgetInit:
    def test_keyboard_combo_exists(self, widget):
        combo = widget.findChild(QComboBox, "keyboard_combo")
        assert combo is not None

    def test_mcu_combo_exists(self, widget):
        combo = widget.findChild(QComboBox, "mcu_combo")
        assert combo is not None

    def test_keyboard_combo_has_at_least_3_items(self, widget):
        combo = widget.findChild(QComboBox, "keyboard_combo")
        assert combo.count() >= 3

    def test_keyboard_combo_contains_sofle(self, widget):
        combo = widget.findChild(QComboBox, "keyboard_combo")
        items = [combo.itemText(i) for i in range(combo.count())]
        assert any("Sofle" in item for item in items)

    def test_keyboard_combo_contains_corne(self, widget):
        combo = widget.findChild(QComboBox, "keyboard_combo")
        items = [combo.itemText(i) for i in range(combo.count())]
        assert any("Corne" in item for item in items)

    def test_keyboard_combo_contains_lily58(self, widget):
        combo = widget.findChild(QComboBox, "keyboard_combo")
        items = [combo.itemText(i) for i in range(combo.count())]
        assert any("Lily58" in item for item in items)

    def test_mcu_combo_populated_on_init(self, widget):
        combo = widget.findChild(QComboBox, "mcu_combo")
        assert combo.count() >= 1

    def test_model_keyboard_model_set_on_init(self, widget, model):
        assert model.keyboard.model != ""

    def test_model_keyboard_mcu_set_on_init(self, widget, model):
        assert model.keyboard.mcu != ""


class TestHardwareWidgetSelection:
    def test_changing_keyboard_updates_model(self, widget, model, qtbot):
        keyboard_combo = widget.findChild(QComboBox, "keyboard_combo")
        # On prend un index différent du courant
        new_index = (keyboard_combo.currentIndex() + 1) % keyboard_combo.count()
        with qtbot.waitSignal(keyboard_combo.currentIndexChanged, timeout=1000):
            keyboard_combo.setCurrentIndex(new_index)
        assert model.keyboard.model != ""

    def test_changing_keyboard_updates_mcu_combo(self, widget, qtbot):
        keyboard_combo = widget.findChild(QComboBox, "keyboard_combo")
        mcu_combo = widget.findChild(QComboBox, "mcu_combo")
        # Parcourir tous les claviers — le combo MCU ne doit jamais être vide
        for i in range(keyboard_combo.count()):
            keyboard_combo.setCurrentIndex(i)
            assert mcu_combo.count() >= 1, f"MCU combo vide pour le clavier index {i}"

    def test_changing_mcu_updates_model(self, widget, model, qtbot):
        mcu_combo = widget.findChild(QComboBox, "mcu_combo")
        if mcu_combo.count() > 1:
            with qtbot.waitSignal(mcu_combo.currentIndexChanged, timeout=1000):
                mcu_combo.setCurrentIndex(1)
        assert model.keyboard.mcu != ""

    def test_sofle_has_rp2040_mcu(self, widget, qtbot):
        keyboard_combo = widget.findChild(QComboBox, "keyboard_combo")
        mcu_combo = widget.findChild(QComboBox, "mcu_combo")
        # Trouver le Sofle dans le combo
        sofle_index = next(
            (i for i in range(keyboard_combo.count()) if "Sofle" in keyboard_combo.itemText(i)),
            None,
        )
        assert sofle_index is not None, "Sofle non trouvé dans le combo"
        keyboard_combo.setCurrentIndex(sofle_index)
        mcu_items = [mcu_combo.itemText(i) for i in range(mcu_combo.count())]
        assert any("RP2040" in item for item in mcu_items)


class TestCapabilitiesSignal:
    def test_capabilities_changed_signal_shape(self, widget, qtbot):
        """Le signal capabilities_changed émet un dict avec les clés oled et rgb."""
        keyboard_combo = widget.findChild(QComboBox, "keyboard_combo")
        new_index = (keyboard_combo.currentIndex() + 1) % keyboard_combo.count()
        with qtbot.waitSignal(widget.capabilities_changed, timeout=1000) as blocker:
            keyboard_combo.setCurrentIndex(new_index)
        caps = blocker.args[0]
        assert isinstance(caps, dict)
        assert "oled" in caps
        assert "rgb" in caps

    def test_sofle_capabilities_oled_and_rgb_true(self, widget, qtbot):
        keyboard_combo = widget.findChild(QComboBox, "keyboard_combo")
        sofle_index = next(
            (i for i in range(keyboard_combo.count()) if "Sofle" in keyboard_combo.itemText(i)),
            None,
        )
        assert sofle_index is not None
        with qtbot.waitSignal(widget.capabilities_changed, timeout=1000) as blocker:
            keyboard_combo.setCurrentIndex(sofle_index)
        assert blocker.args[0].get("oled") is True
        assert blocker.args[0].get("rgb") is True

    def test_corne_capabilities_rgb_false(self, widget, qtbot):
        keyboard_combo = widget.findChild(QComboBox, "keyboard_combo")
        corne_index = next(
            (i for i in range(keyboard_combo.count()) if "Corne" in keyboard_combo.itemText(i)),
            None,
        )
        assert corne_index is not None
        # S'assurer qu'on part d'un index différent pour déclencher le signal
        other_index = (corne_index + 1) % keyboard_combo.count()
        keyboard_combo.setCurrentIndex(other_index)
        with qtbot.waitSignal(widget.capabilities_changed, timeout=1000) as blocker:
            keyboard_combo.setCurrentIndex(corne_index)
        assert blocker.args[0].get("rgb") is False


class TestOledSidesSelector:
    def _sofle_index(self, widget):
        combo = widget.findChild(QComboBox, "keyboard_combo")
        return next(
            (i for i in range(combo.count()) if "Sofle" in combo.itemText(i)),
            None,
        )

    def test_oled_combo_exists(self, widget):
        combo = widget.findChild(QComboBox, "oled_combo")
        assert combo is not None

    def test_oled_combo_visible_for_sofle(self, widget, qtbot):
        combo_kb = widget.findChild(QComboBox, "keyboard_combo")
        sofle_idx = self._sofle_index(widget)
        assert sofle_idx is not None
        combo_kb.setCurrentIndex(sofle_idx)
        combo = widget.findChild(QComboBox, "oled_combo")
        assert not combo.isHidden()

    def test_oled_combo_has_four_options(self, widget):
        combo = widget.findChild(QComboBox, "oled_combo")
        assert combo.count() == 4

    def test_default_oled_sides_is_both(self, widget, model, qtbot):
        combo_kb = widget.findChild(QComboBox, "keyboard_combo")
        sofle_idx = self._sofle_index(widget)
        assert sofle_idx is not None
        combo_kb.setCurrentIndex(sofle_idx)
        assert model.keyboard.oled_sides == ["left", "right"]

    def test_oled_combo_left_only_updates_model(self, widget, model, qtbot):
        combo_kb = widget.findChild(QComboBox, "keyboard_combo")
        sofle_idx = self._sofle_index(widget)
        assert sofle_idx is not None
        combo_kb.setCurrentIndex(sofle_idx)
        oled_combo = widget.findChild(QComboBox, "oled_combo")
        oled_combo.setCurrentIndex(1)  # "Gauche seulement"
        assert model.keyboard.oled_sides == ["left"]

    def test_oled_combo_right_only_updates_model(self, widget, model, qtbot):
        combo_kb = widget.findChild(QComboBox, "keyboard_combo")
        sofle_idx = self._sofle_index(widget)
        assert sofle_idx is not None
        combo_kb.setCurrentIndex(sofle_idx)
        oled_combo = widget.findChild(QComboBox, "oled_combo")
        oled_combo.setCurrentIndex(2)  # "Droite seulement"
        assert model.keyboard.oled_sides == ["right"]

    def test_oled_sides_changed_signal(self, widget, model, qtbot):
        combo_kb = widget.findChild(QComboBox, "keyboard_combo")
        sofle_idx = self._sofle_index(widget)
        assert sofle_idx is not None
        combo_kb.setCurrentIndex(sofle_idx)
        oled_combo = widget.findChild(QComboBox, "oled_combo")
        with qtbot.waitSignal(widget.oled_sides_changed, timeout=1000) as blocker:
            oled_combo.setCurrentIndex(1)
        assert blocker.args[0] == ["left"]

    def test_set_oled_sides_restores(self, widget, model, qtbot):
        combo_kb = widget.findChild(QComboBox, "keyboard_combo")
        sofle_idx = self._sofle_index(widget)
        assert sofle_idx is not None
        combo_kb.setCurrentIndex(sofle_idx)
        widget.set_oled_sides(["right"])
        assert model.keyboard.oled_sides == ["right"]
        oled_combo = widget.findChild(QComboBox, "oled_combo")
        assert oled_combo.currentIndex() == 2  # index of ["right"] in _OLED_SIDES_OPTIONS


class TestHardwareWidgetTooltips:
    def test_keyboard_combo_items_have_tooltips(self, widget):
        from PySide6.QtCore import Qt
        combo = widget.findChild(QComboBox, "keyboard_combo")
        for i in range(combo.count()):
            tooltip = combo.itemData(i, Qt.ItemDataRole.ToolTipRole)
            assert tooltip is not None and len(tooltip) > 0, f"Pas de tooltip pour le clavier index {i}"

    def test_mcu_combo_items_have_tooltips(self, widget):
        from PySide6.QtCore import Qt
        combo = widget.findChild(QComboBox, "mcu_combo")
        for i in range(combo.count()):
            tooltip = combo.itemData(i, Qt.ItemDataRole.ToolTipRole)
            assert tooltip is not None and len(tooltip) > 0, f"Pas de tooltip pour le MCU index {i}"
