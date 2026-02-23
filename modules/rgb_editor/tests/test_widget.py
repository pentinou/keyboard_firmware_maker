"""Tests pytest-qt pour modules/rgb_editor/widget.py — RgbWidget."""
from __future__ import annotations

from unittest.mock import patch

import pytest
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QPushButton

from models.project_model import ProjectModel
from modules.rgb_editor.widget import RgbWidget


@pytest.fixture
def model() -> ProjectModel:
    m = ProjectModel()
    m.keyboard.model = "sofle-v2"
    return m


@pytest.fixture
def widget(qtbot, model):
    w = RgbWidget(model)
    qtbot.addWidget(w)
    return w


class TestRgbWidgetInit:
    def test_widget_creates(self, widget):
        assert widget is not None

    def test_key_buttons_not_empty(self, widget):
        assert len(widget._key_buttons) > 0

    def test_sofle_has_60_buttons(self, widget):
        # Sofle: 5 rows × 6 cols × 2 sides = 60 keys
        assert len(widget._key_buttons) == 60

    def test_left_buttons_present(self, widget):
        assert "L_r0_c0" in widget._key_buttons

    def test_right_buttons_present(self, widget):
        assert "R_r0_c0" in widget._key_buttons

    def test_buttons_have_correct_size(self, widget):
        btn = widget._key_buttons["L_r0_c0"]
        from modules.rgb_editor.widget import KEY_SIZE
        assert btn.width() == KEY_SIZE
        assert btn.height() == KEY_SIZE


class TestRgbWidgetColorAssignment:
    def test_apply_color_updates_model(self, widget, model):
        widget._apply_color("L_r0_c0", "#FF0000")
        assert model.rgb.per_key["L_r0_c0"] == "#FF0000"

    def test_apply_color_updates_button_stylesheet(self, widget):
        widget._apply_color("L_r1_c2", "#00FF00")
        btn = widget._key_buttons["L_r1_c2"]
        assert "#00FF00" in btn.styleSheet()

    def test_on_key_clicked_opens_color_dialog(self, widget, model, qtbot):
        """QColorDialog mocké retourne rouge → modèle mis à jour."""
        mock_color = QColor("#AA1122")
        with patch("modules.rgb_editor.widget.QColorDialog.getColor", return_value=mock_color):
            widget._on_key_clicked("L_r0_c0")
        assert model.rgb.per_key["L_r0_c0"] == "#AA1122"

    def test_on_key_clicked_cancelled_no_change(self, widget, model, qtbot):
        """Si QColorDialog annulé (couleur invalide), pas de mise à jour."""
        invalid_color = QColor()  # isValid() == False
        with patch("modules.rgb_editor.widget.QColorDialog.getColor", return_value=invalid_color):
            widget._on_key_clicked("L_r0_c0")
        assert "L_r0_c0" not in model.rgb.per_key

    def test_apply_multiple_colors(self, widget, model):
        widget._apply_color("L_r0_c0", "#FF0000")
        widget._apply_color("R_r2_c3", "#0000FF")
        assert model.rgb.per_key["L_r0_c0"] == "#FF0000"
        assert model.rgb.per_key["R_r2_c3"] == "#0000FF"


class TestRgbWidgetSyncFromModel:
    def test_sync_restores_colors(self, qtbot, model):
        model.rgb.per_key["L_r0_c0"] = "#CC0000"
        model.rgb.per_key["R_r1_c1"] = "#00CC00"
        w = RgbWidget(model)
        qtbot.addWidget(w)
        assert "#CC0000" in w._key_buttons["L_r0_c0"].styleSheet()
        assert "#00CC00" in w._key_buttons["R_r1_c1"].styleSheet()

    def test_sync_ignores_unknown_keys(self, qtbot, model):
        """Les clés inconnues dans per_key ne doivent pas provoquer d'erreur."""
        model.rgb.per_key["INVALID_KEY"] = "#FF0000"
        w = RgbWidget(model)
        qtbot.addWidget(w)
        # Aucune exception levée

    def test_apply_color_unknown_key_not_stored_in_model(self, widget, model):
        """M2 — _apply_color avec clé inconnue ne doit pas polluer model.rgb.per_key."""
        widget._apply_color("INVALID_KEY_XYZ", "#AABBCC")
        assert "INVALID_KEY_XYZ" not in model.rgb.per_key


class TestRgbWidgetRefreshLayout:
    def test_refresh_rebuilds_buttons(self, widget, model):
        initial_count = len(widget._key_buttons)
        widget.refresh_layout()
        assert len(widget._key_buttons) == initial_count

    def test_corne_has_48_buttons(self, qtbot):
        """Corne: 4 rows × 6 cols × 2 sides = 48 keys."""
        model = ProjectModel()
        model.keyboard.model = "corne"
        w = RgbWidget(model)
        qtbot.addWidget(w)
        assert len(w._key_buttons) == 48

    def test_refresh_layout_preserves_per_key_colors(self, qtbot, model):
        """L3 — refresh_layout() doit restaurer les couleurs per-key après reconstruction."""
        model.rgb.per_key["L_r0_c0"] = "#FF0000"
        model.rgb.per_key["R_r2_c3"] = "#0000FF"
        w = RgbWidget(model)
        qtbot.addWidget(w)
        w.refresh_layout()
        assert "#FF0000" in w._key_buttons["L_r0_c0"].styleSheet()
        assert "#0000FF" in w._key_buttons["R_r2_c3"].styleSheet()


class TestRgbWidgetEffects:
    def test_effect_combo_exists(self, widget):
        from PySide6.QtWidgets import QComboBox
        combo = widget.findChild(QComboBox, "effect_combo")
        assert combo is not None

    def test_effect_combo_has_static(self, widget):
        from PySide6.QtWidgets import QComboBox
        combo = widget.findChild(QComboBox, "effect_combo")
        items = [combo.itemText(i) for i in range(combo.count())]
        assert any("statique" in t.lower() for t in items)

    def test_effect_combo_has_ripple(self, widget):
        from PySide6.QtWidgets import QComboBox
        combo = widget.findChild(QComboBox, "effect_combo")
        items = [combo.itemText(i) for i in range(combo.count())]
        assert any("ripple" in t.lower() for t in items)

    def test_select_static_creates_effect(self, widget, model):
        from PySide6.QtWidgets import QComboBox
        combo = widget.findChild(QComboBox, "effect_combo")
        combo.setCurrentIndex(1)  # passer à ripple d'abord
        combo.setCurrentIndex(0)  # revenir à static → signal émis
        assert len(model.rgb.effects) >= 1
        assert model.rgb.effects[0].type == "static"

    def test_select_ripple_creates_effect(self, widget, model):
        from PySide6.QtWidgets import QComboBox
        combo = widget.findChild(QComboBox, "effect_combo")
        combo.setCurrentIndex(1)  # ripple
        assert model.rgb.effects[0].type == "ripple"

    def test_color_primary_button_exists(self, widget):
        btn = widget.findChild(QPushButton, "btn_color_primary")
        assert btn is not None

    def test_color_primary_dialog_updates_model(self, widget, model):
        from PySide6.QtWidgets import QComboBox
        widget.findChild(QComboBox, "effect_combo").setCurrentIndex(0)  # static
        mock_color = QColor("#FF1234")
        with patch("modules.rgb_editor.widget.QColorDialog.getColor", return_value=mock_color):
            widget._on_color_primary_clicked()
        assert model.rgb.effects[0].color_primary == "#FF1234"

    def test_color_secondary_button_exists(self, widget):
        btn = widget.findChild(QPushButton, "btn_color_secondary")
        assert btn is not None

    def test_color_secondary_updates_model(self, widget, model):
        from PySide6.QtWidgets import QComboBox
        widget.findChild(QComboBox, "effect_combo").setCurrentIndex(1)  # ripple
        mock_color = QColor("#00FF88")
        with patch("modules.rgb_editor.widget.QColorDialog.getColor", return_value=mock_color):
            widget._on_color_secondary_clicked()
        assert model.rgb.effects[0].color_secondary == "#00FF88"

    def test_fade_ms_spinbox_exists(self, widget):
        from PySide6.QtWidgets import QSpinBox
        spin = widget.findChild(QSpinBox, "fade_ms_spin")
        assert spin is not None

    def test_fade_ms_updates_model(self, widget, model):
        from PySide6.QtWidgets import QComboBox, QSpinBox
        widget.findChild(QComboBox, "effect_combo").setCurrentIndex(1)
        widget.findChild(QSpinBox, "fade_ms_spin").setValue(750)
        assert model.rgb.effects[0].fade_ms == 750

    def test_trigger_button_exists(self, widget):
        btn = widget.findChild(QPushButton, "btn_trigger")
        assert btn is not None

    def test_trigger_mode_activated_on_click(self, widget):
        widget._btn_trigger.clicked.emit()
        assert widget._trigger_mode is True

    def test_trigger_key_set_on_key_click_in_trigger_mode(self, widget, model):
        from PySide6.QtWidgets import QComboBox
        widget.findChild(QComboBox, "effect_combo").setCurrentIndex(1)  # ripple
        widget._trigger_mode = True
        widget._on_key_clicked("L_r0_c0")
        assert widget._trigger_mode is False
        assert model.rgb.effects[0].trigger_key == "L_r0_c0"

    def test_trigger_mode_exits_after_key_click(self, widget, model):
        from PySide6.QtWidgets import QComboBox
        widget.findChild(QComboBox, "effect_combo").setCurrentIndex(1)
        widget._trigger_mode = True
        widget._on_key_clicked("R_r2_c3")
        assert widget._trigger_mode is False

    def test_sync_restores_effect_type(self, qtbot):
        model = ProjectModel()
        model.keyboard.model = "sofle-v2"
        from models.project_model import RgbEffect
        model.rgb.effects = [RgbEffect(type="ripple", fade_ms=300)]
        from PySide6.QtWidgets import QComboBox
        w = RgbWidget(model)
        qtbot.addWidget(w)
        combo = w.findChild(QComboBox, "effect_combo")
        assert combo.currentIndex() == 1  # ripple

    def test_sync_restores_fade_ms(self, qtbot):
        model = ProjectModel()
        model.keyboard.model = "sofle-v2"
        from models.project_model import RgbEffect
        from PySide6.QtWidgets import QSpinBox
        model.rgb.effects = [RgbEffect(type="ripple", fade_ms=800)]
        w = RgbWidget(model)
        qtbot.addWidget(w)
        spin = w.findChild(QSpinBox, "fade_ms_spin")
        assert spin.value() == 800

    def test_ac4_full_ripple_state(self, widget, model):
        """AC4 — vérification complète de l'état ripple (type + les 3 paramètres)."""
        from PySide6.QtWidgets import QComboBox, QSpinBox
        widget.findChild(QComboBox, "effect_combo").setCurrentIndex(1)  # ripple
        with patch("modules.rgb_editor.widget.QColorDialog.getColor", return_value=QColor("#FF0000")):
            widget._on_color_primary_clicked()
        with patch("modules.rgb_editor.widget.QColorDialog.getColor", return_value=QColor("#FF8800")):
            widget._on_color_secondary_clicked()
        widget.findChild(QSpinBox, "fade_ms_spin").setValue(500)
        effect = model.rgb.effects[0]
        assert effect.type == "ripple"
        assert effect.color_primary == "#FF0000"
        assert effect.color_secondary == "#FF8800"
        assert effect.fade_ms == 500

    def test_trigger_mode_reset_on_effect_change(self, widget):
        """M1 — changer d'effet réinitialise le mode trigger."""
        from PySide6.QtWidgets import QComboBox
        combo = widget.findChild(QComboBox, "effect_combo")
        combo.setCurrentIndex(1)  # ripple
        widget._trigger_mode = True
        widget._btn_trigger.setText("Cliquez une touche…")
        combo.setCurrentIndex(0)  # switch to static → must reset trigger
        assert widget._trigger_mode is False
        assert widget._btn_trigger.text() == "Choisir touche déclencheur"

    def test_trigger_key_noop_label_when_effects_empty(self, widget, model):
        """M2 / L4 — label non modifié si effects vide lors du clic trigger."""
        model.rgb.effects = []
        widget._trigger_mode = True
        initial_label = widget._lbl_trigger.text()
        widget._on_key_clicked("L_r0_c0")
        assert widget._trigger_mode is False
        assert len(model.rgb.effects) == 0
        assert widget._lbl_trigger.text() == initial_label  # pas changé


class TestRgbWidgetPreview:
    def test_preview_created_on_init(self, widget):
        from modules.rgb_editor.effect_preview import EffectPreview
        assert isinstance(widget._preview, EffectPreview)

    def test_select_ripple_starts_preview(self, widget):
        from PySide6.QtWidgets import QComboBox
        widget.findChild(QComboBox, "effect_combo").setCurrentIndex(1)  # ripple
        assert widget._preview.is_active()
        widget._preview.stop()

    def test_select_static_stops_timer(self, widget):
        from PySide6.QtWidgets import QComboBox
        combo = widget.findChild(QComboBox, "effect_combo")
        combo.setCurrentIndex(1)  # ripple → timer démarre
        combo.setCurrentIndex(0)  # static → timer doit s'arrêter
        assert not widget._preview.is_active()

    def test_hide_event_stops_preview(self, widget):
        from PySide6.QtGui import QHideEvent
        from PySide6.QtWidgets import QComboBox
        widget.findChild(QComboBox, "effect_combo").setCurrentIndex(1)  # ripple
        assert widget._preview.is_active()
        widget.hideEvent(QHideEvent())
        assert not widget._preview.is_active()

    def test_show_event_starts_preview_with_effect(self, widget):
        from PySide6.QtGui import QShowEvent
        from PySide6.QtWidgets import QComboBox
        widget.findChild(QComboBox, "effect_combo").setCurrentIndex(1)  # crée l'effet ripple
        widget._preview.stop()  # stopper manuellement
        assert not widget._preview.is_active()
        widget.showEvent(QShowEvent())
        assert widget._preview.is_active()
        widget._preview.stop()

    def test_show_event_no_effect_no_start(self, widget):
        from PySide6.QtGui import QShowEvent
        widget.showEvent(QShowEvent())
        assert not widget._preview.is_active()

    def test_refresh_layout_recreates_preview(self, widget):
        old_preview = widget._preview
        widget.refresh_layout()
        assert widget._preview is not old_preview

    def test_refresh_layout_stops_old_preview_timer(self, qtbot, model):
        """M1 — refresh_layout arrête l'ancien timer avant de le remplacer."""
        from models.project_model import RgbEffect
        model.rgb.effects = [RgbEffect(type="ripple")]
        w = RgbWidget(model)
        qtbot.addWidget(w)
        w._preview.start(model.rgb.effects[0])
        old_preview = w._preview
        assert old_preview.is_active()
        w.refresh_layout()
        assert not old_preview.is_active()
        assert w._preview is not old_preview

    def test_hide_event_restores_per_key_colors(self, qtbot, model):
        """M2 — hideEvent restaure les couleurs per-key après arrêt du preview."""
        from PySide6.QtGui import QHideEvent
        from models.project_model import RgbEffect
        model.rgb.per_key = {"L_r0_c0": "#FF0000"}
        w = RgbWidget(model)
        qtbot.addWidget(w)
        # Le preview static écrase la couleur per-key
        w._preview.start(RgbEffect(type="static", color_primary="#FFFFFF"))
        assert "#FFFFFF" in w._key_buttons["L_r0_c0"].styleSheet()
        # hideEvent doit restaurer la couleur per-key
        w.hideEvent(QHideEvent())
        assert "#FF0000" in w._key_buttons["L_r0_c0"].styleSheet()
