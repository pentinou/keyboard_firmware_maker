"""Tests du widget AdvancedOptionsWidget."""
from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QLineEdit, QSpinBox

from models.project_model import ProjectModel
from modules.advanced_options.widget import AdvancedOptionsWidget


class TestAdvancedOptionsWidgetCreation:
    """Le widget se construit sans erreur et reflète le modèle par défaut."""

    def test_widget_created(self, qtbot):
        model = ProjectModel()
        widget = AdvancedOptionsWidget(model)
        qtbot.addWidget(widget)
        assert widget is not None

    def test_default_hid_indicators_checked(self, qtbot):
        # HID Indicators est opt-in par défaut (utile pour CapsLock OLED)
        model = ProjectModel()
        widget = AdvancedOptionsWidget(model)
        qtbot.addWidget(widget)
        cb = widget.findChild(QCheckBox, "adv_hid_indicators_enabled")
        assert cb is not None
        assert cb.isChecked() is True

    def test_default_rgb_on_start_checked(self, qtbot):
        model = ProjectModel()
        widget = AdvancedOptionsWidget(model)
        qtbot.addWidget(widget)
        cb = widget.findChild(QCheckBox, "adv_rgb_on_start")
        assert cb is not None
        assert cb.isChecked() is True

    def test_default_nkro_unchecked(self, qtbot):
        model = ProjectModel()
        widget = AdvancedOptionsWidget(model)
        qtbot.addWidget(widget)
        cb = widget.findChild(QCheckBox, "adv_nkro_enabled")
        assert cb is not None
        assert cb.isChecked() is False


class TestAdvancedOptionsWidgetSync:
    """L'UI et le modèle sont synchronisés bidirectionnellement."""

    def test_check_nkro_updates_model(self, qtbot):
        model = ProjectModel()
        widget = AdvancedOptionsWidget(model)
        qtbot.addWidget(widget)
        cb = widget.findChild(QCheckBox, "adv_nkro_enabled")
        cb.setChecked(True)
        assert model.advanced.nkro_enabled is True

    def test_check_mousekey_enabled_updates_model(self, qtbot):
        model = ProjectModel()
        widget = AdvancedOptionsWidget(model)
        qtbot.addWidget(widget)
        cb = widget.findChild(QCheckBox, "adv_mousekey_enabled")
        assert cb is not None
        assert cb.isChecked() is False  # désactivé par défaut
        cb.setChecked(True)
        assert model.advanced.mousekey_enabled is True

    def test_keyboard_name_updates_model(self, qtbot):
        model = ProjectModel()
        widget = AdvancedOptionsWidget(model)
        qtbot.addWidget(widget)
        line = widget.findChild(QLineEdit, "adv_keyboard_name")
        line.setText("Sofle Boulot")
        assert model.advanced.keyboard_name == "Sofle Boulot"

    def test_tapping_term_updates_model(self, qtbot):
        model = ProjectModel()
        widget = AdvancedOptionsWidget(model)
        qtbot.addWidget(widget)
        sp = widget.findChild(QSpinBox, "adv_tapping_term_ms")
        sp.setValue(150)
        assert model.advanced.tapping_term_ms == 150

    def test_rgb_hue_updates_model(self, qtbot):
        model = ProjectModel()
        widget = AdvancedOptionsWidget(model)
        qtbot.addWidget(widget)
        sp = widget.findChild(QSpinBox, "adv_rgb_hue_start")
        sp.setValue(120)  # vert
        assert model.advanced.rgb_hue_start == 120

    def test_reload_from_model_syncs_ui(self, qtbot):
        model = ProjectModel()
        model.advanced.nkro_enabled = True
        model.advanced.tapping_term_ms = 250
        model.advanced.keyboard_name = "Test KB"
        widget = AdvancedOptionsWidget(model)
        qtbot.addWidget(widget)

        # Changer le modèle après création
        model.advanced.nkro_enabled = False
        model.advanced.tapping_term_ms = 300
        widget.reload_from_model()

        assert widget.findChild(QCheckBox, "adv_nkro_enabled").isChecked() is False
        assert widget.findChild(QSpinBox, "adv_tapping_term_ms").value() == 300


class TestAdvancedOptionsFirmwareSwitching:
    """set_firmware() grise les options non-applicables avec tooltip."""

    def test_zmk_mode_disables_qmk_only_widgets(self, qtbot):
        model = ProjectModel()
        widget = AdvancedOptionsWidget(model)
        qtbot.addWidget(widget)
        widget.set_firmware("zmk")

        # Auto-shift est QMK only
        auto_shift = widget.findChild(QCheckBox, "adv_auto_shift_enabled")
        assert auto_shift.isEnabled() is False
        # Mousekey delay est QMK only
        mk = widget.findChild(QSpinBox, "adv_mousekey_delay_ms")
        assert mk.isEnabled() is False

    def test_qmk_mode_disables_zmk_only_widgets(self, qtbot):
        model = ProjectModel()
        widget = AdvancedOptionsWidget(model)
        qtbot.addWidget(widget)
        widget.set_firmware("qmk")

        # BLE passkey est ZMK only
        ble = widget.findChild(QCheckBox, "adv_ble_passkey_entry")
        assert ble.isEnabled() is False
        # Pointing est ZMK only
        pointing = widget.findChild(QCheckBox, "adv_pointing_enabled")
        assert pointing.isEnabled() is False

    def test_common_options_enabled_both_firmwares(self, qtbot):
        model = ProjectModel()
        widget = AdvancedOptionsWidget(model)
        qtbot.addWidget(widget)

        for firmware in ("qmk", "zmk"):
            widget.set_firmware(firmware)
            assert widget.findChild(QCheckBox, "adv_nkro_enabled").isEnabled() is True
            assert widget.findChild(QCheckBox, "adv_tap_dance_enabled").isEnabled() is True
            assert widget.findChild(QLineEdit, "adv_keyboard_name").isEnabled() is True


class TestAdvancedOptionsSerialization:
    """Le modèle se sérialise et se restaure complètement."""

    def test_roundtrip_preserves_advanced_options(self):
        m1 = ProjectModel()
        m1.advanced.nkro_enabled = True
        m1.advanced.tapping_term_ms = 175
        m1.advanced.rgb_hue_start = 240
        m1.advanced.keyboard_name = "My KB"
        m1.advanced.soft_off_enabled = True
        m1.advanced.mousekey_enabled = True

        d = m1.to_dict()
        m2 = ProjectModel.from_dict(d)

        assert m2.advanced.nkro_enabled is True
        assert m2.advanced.tapping_term_ms == 175
        assert m2.advanced.rgb_hue_start == 240
        assert m2.advanced.keyboard_name == "My KB"
        assert m2.advanced.soft_off_enabled is True
        assert m2.advanced.mousekey_enabled is True

    def test_from_dict_with_missing_fields_uses_defaults(self):
        m = ProjectModel.from_dict({"advanced": {}})
        assert m.advanced.nkro_enabled is False
        assert m.advanced.hid_indicators_enabled is True  # défaut opt-in
        assert m.advanced.tapping_term_ms == 200
        assert m.advanced.rgb_on_start is True  # défaut opt-in

    def test_hue_clamp_on_load(self):
        m = ProjectModel.from_dict({"advanced": {"rgb_hue_start": 999}})
        assert m.advanced.rgb_hue_start == 359  # clamped to max


class TestAdvancedOptionsTemplateInjection:
    """Les options sélectionnées finissent bien dans les fichiers générés."""

    def test_zmk_nkro_injects_kconfig(self, tmp_path):
        from modules.build_manager.zmk_template_generator import ZmkTemplateGenerator

        model = ProjectModel()
        model.keyboard.model = "sofle-v2"
        model.keyboard.mcu = "nice_nano_v2"
        model.advanced.nkro_enabled = True
        ZmkTemplateGenerator().generate(model, tmp_path)
        conf = (tmp_path / "config" / "sofle_v2.conf").read_text()
        assert "CONFIG_ZMK_HID_REPORT_TYPE_NKRO=y" in conf

    def test_zmk_passkey_injects_kconfig(self, tmp_path):
        from modules.build_manager.zmk_template_generator import ZmkTemplateGenerator

        model = ProjectModel()
        model.keyboard.model = "sofle-v2"
        model.keyboard.mcu = "nice_nano_v2"
        model.advanced.ble_passkey_entry = True
        ZmkTemplateGenerator().generate(model, tmp_path)
        conf = (tmp_path / "config" / "sofle_v2.conf").read_text()
        assert "CONFIG_ZMK_BLE_PASSKEY_ENTRY=y" in conf

    def test_zmk_keyboard_name_quoted_string(self, tmp_path):
        from modules.build_manager.zmk_template_generator import ZmkTemplateGenerator

        model = ProjectModel()
        model.keyboard.model = "sofle-v2"
        model.keyboard.mcu = "nice_nano_v2"
        model.advanced.keyboard_name = "Sofle Boulot"
        ZmkTemplateGenerator().generate(model, tmp_path)
        conf = (tmp_path / "config" / "sofle_v2.conf").read_text()
        assert 'CONFIG_ZMK_KEYBOARD_NAME="Sofle Boulot"' in conf

    def test_zmk_deep_sleep_min_to_ms(self, tmp_path):
        from modules.build_manager.zmk_template_generator import ZmkTemplateGenerator

        model = ProjectModel()
        model.keyboard.model = "sofle-v2"
        model.keyboard.mcu = "nice_nano_v2"
        model.advanced.deep_sleep_timeout_min = 10
        ZmkTemplateGenerator().generate(model, tmp_path)
        conf = (tmp_path / "config" / "sofle_v2.conf").read_text()
        # 10 min = 600000 ms
        assert "CONFIG_ZMK_IDLE_SLEEP_TIMEOUT=600000" in conf

    def test_zmk_rgb_hue_start_injected(self, tmp_path):
        from modules.build_manager.zmk_template_generator import ZmkTemplateGenerator

        model = ProjectModel()
        model.keyboard.model = "sofle-v2"
        model.keyboard.mcu = "nice_nano_v2"
        model.keyboard.rgb_enabled = True  # nécessaire pour activer le bloc RGB du template
        model.advanced.rgb_hue_start = 120
        ZmkTemplateGenerator().generate(model, tmp_path)
        conf = (tmp_path / "config" / "sofle_v2.conf").read_text()
        assert "CONFIG_ZMK_RGB_UNDERGLOW_HUE_START=120" in conf
