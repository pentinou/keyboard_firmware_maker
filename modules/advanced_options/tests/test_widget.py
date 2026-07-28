"""Tests du widget AdvancedOptionsWidget."""
from __future__ import annotations

from unittest.mock import patch

from PySide6.QtWidgets import QCheckBox, QLabel, QLineEdit, QPushButton, QSpinBox

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

    def test_qmk_mode_disables_options_without_qmk_mapping(self, qtbot):
        """Les options sans mapping dans le générateur QMK sont grisées en QMK.

        `keyboard_name` (CONFIG_ZMK_KEYBOARD_NAME), `hid_indicators` et
        `usb_boot_protocol` n'ont aucune traduction côté template QMK : les
        laisser actives faisait croire à un réglage qui n'était jamais appliqué.
        """
        model = ProjectModel()
        widget = AdvancedOptionsWidget(model)
        qtbot.addWidget(widget)
        widget.set_firmware("qmk")

        assert widget.findChild(QLineEdit, "adv_keyboard_name").isEnabled() is False
        assert widget.findChild(QCheckBox, "adv_hid_indicators_enabled").isEnabled() is False
        assert widget.findChild(QCheckBox, "adv_usb_boot_protocol").isEnabled() is False

    def test_zmk_mode_enables_options_without_qmk_mapping(self, qtbot):
        model = ProjectModel()
        widget = AdvancedOptionsWidget(model)
        qtbot.addWidget(widget)
        widget.set_firmware("zmk")

        assert widget.findChild(QLineEdit, "adv_keyboard_name").isEnabled() is True
        assert widget.findChild(QCheckBox, "adv_hid_indicators_enabled").isEnabled() is True
        assert widget.findChild(QCheckBox, "adv_usb_boot_protocol").isEnabled() is True

    def test_common_options_enabled_both_firmwares(self, qtbot):
        model = ProjectModel()
        widget = AdvancedOptionsWidget(model)
        qtbot.addWidget(widget)

        for firmware in ("qmk", "zmk"):
            widget.set_firmware(firmware)
            assert widget.findChild(QCheckBox, "adv_nkro_enabled").isEnabled() is True
            assert widget.findChild(QCheckBox, "adv_tap_dance_enabled").isEnabled() is True


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

    def test_zmk_keyboard_name_quotes_and_backslashes_stripped(self, tmp_path):
        """Un guillemet ou antislash dans le nom casserait la syntaxe Kconfig."""
        from modules.build_manager.zmk_template_generator import ZmkTemplateGenerator

        model = ProjectModel()
        model.keyboard.model = "sofle-v2"
        model.keyboard.mcu = "nice_nano_v2"
        model.advanced.keyboard_name = 'So"fle\\ KB'
        ZmkTemplateGenerator().generate(model, tmp_path)
        conf = (tmp_path / "config" / "sofle_v2.conf").read_text()
        assert 'CONFIG_ZMK_KEYBOARD_NAME="Sofle KB"' in conf

    def test_zmk_keyboard_name_truncated_to_16_chars(self, tmp_path):
        """ZMK limite le nom d'advertising BLE à 16 caractères."""
        from modules.build_manager.zmk_template_generator import ZmkTemplateGenerator

        model = ProjectModel()
        model.keyboard.model = "sofle-v2"
        model.keyboard.mcu = "nice_nano_v2"
        model.advanced.keyboard_name = "A" * 30  # projet ancien / JSON édité à la main
        ZmkTemplateGenerator().generate(model, tmp_path)
        conf = (tmp_path / "config" / "sofle_v2.conf").read_text()
        assert f'CONFIG_ZMK_KEYBOARD_NAME="{"A" * 16}"' in conf

    def test_keyboard_name_field_limited_to_16_chars(self, qtbot):
        """La QLineEdit doit refléter la limite BLE ZMK de 16 caractères."""
        model = ProjectModel()
        widget = AdvancedOptionsWidget(model)
        qtbot.addWidget(widget)
        line = widget.findChild(QLineEdit, "adv_keyboard_name")
        assert line.maxLength() == 16

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


class TestKeymapImportSection:
    """Import d'un keymap vial.rocks ou ZMK — première section de l'onglet.

    Le bloc vivait dans l'onglet Matériel et n'était visible qu'en ZMK ; il est
    désormais unique, ici, et fonctionne pour les deux firmwares.
    """

    @staticmethod
    def _vial_file(tmp_path, layers=1):
        import json
        path = tmp_path / "penti.vil"
        path.write_text(json.dumps({"layout": [[["KC_A", "KC_B"]]] * layers}), encoding="utf-8")
        return path

    @staticmethod
    def _zmk_file(tmp_path):
        path = tmp_path / "sofle.keymap"
        path.write_text(
            '/ { keymap { compatible = "zmk,keymap";\n'
            '  default_layer { bindings = < &kp ESC &kp A &bt BT_SEL 0 >; };\n'
            '}; };\n',
            encoding="utf-8",
        )
        return path

    @staticmethod
    def _import(widget, path, confirm=True):
        from PySide6.QtWidgets import QMessageBox
        answer = QMessageBox.StandardButton.Ok if confirm else QMessageBox.StandardButton.Cancel
        with patch("modules.advanced_options.widget.QFileDialog.getOpenFileName",
                   return_value=(str(path), "")), \
             patch("modules.advanced_options.widget.QMessageBox.question", return_value=answer) as question, \
             patch("modules.advanced_options.widget.QMessageBox.information"), \
             patch("modules.advanced_options.widget.QMessageBox.warning") as warning, \
             patch("modules.advanced_options.widget.QMessageBox.critical") as critical, \
             patch.object(QMessageBox, "exec", return_value=0):
            widget._on_import_keymap_clicked()
        return question, warning, critical

    def test_section_is_present(self, qtbot):
        widget = AdvancedOptionsWidget(ProjectModel())
        qtbot.addWidget(widget)

        assert widget.findChild(QCheckBox, "adv_use_custom_keymap") is not None
        assert widget.findChild(QPushButton, "adv_keymap_import_btn") is not None

    def test_import_button_follows_checkbox(self, qtbot):
        model = ProjectModel()
        widget = AdvancedOptionsWidget(model)
        qtbot.addWidget(widget)
        btn = widget.findChild(QPushButton, "adv_keymap_import_btn")
        assert btn.isEnabled() is False

        widget.findChild(QCheckBox, "adv_use_custom_keymap").setChecked(True)

        assert btn.isEnabled() is True
        assert model.keyboard.use_custom_keymap is True

    def test_vial_import_on_qmk_needs_no_warning(self, qtbot, tmp_path):
        model = ProjectModel()
        widget = AdvancedOptionsWidget(model)
        qtbot.addWidget(widget)
        widget.set_firmware("qmk")

        question, _, _ = self._import(widget, self._vial_file(tmp_path))

        question.assert_not_called()
        assert model.keyboard.custom_keymap["layout"]
        assert model.keyboard.use_custom_keymap is True

    def test_vial_import_on_zmk_warns_about_cross_format(self, qtbot, tmp_path):
        model = ProjectModel()
        widget = AdvancedOptionsWidget(model)
        qtbot.addWidget(widget)
        widget.set_firmware("zmk")

        question, _, _ = self._import(widget, self._vial_file(tmp_path))

        question.assert_called_once()

    def test_zmk_import_on_qmk_warns_and_stores_layers(self, qtbot, tmp_path):
        model = ProjectModel()
        widget = AdvancedOptionsWidget(model)
        qtbot.addWidget(widget)
        widget.set_firmware("qmk")

        question, _, _ = self._import(widget, self._zmk_file(tmp_path))

        question.assert_called_once()
        assert model.keyboard.custom_keymap["zmk_layers"][0]["bindings"][0] == "&kp ESC"

    def test_cancelling_the_warning_leaves_model_untouched(self, qtbot, tmp_path):
        model = ProjectModel()
        widget = AdvancedOptionsWidget(model)
        qtbot.addWidget(widget)
        widget.set_firmware("qmk")

        self._import(widget, self._zmk_file(tmp_path), confirm=False)

        assert model.keyboard.custom_keymap is None
        assert model.keyboard.use_custom_keymap is False

    def test_unknown_format_is_rejected(self, qtbot, tmp_path):
        model = ProjectModel()
        widget = AdvancedOptionsWidget(model)
        qtbot.addWidget(widget)
        path = tmp_path / "notes.txt"
        path.write_text("juste du texte", encoding="utf-8")

        _, warning, _ = self._import(widget, path)

        warning.assert_called_once()
        assert model.keyboard.custom_keymap is None

    def test_status_label_reports_source_and_layers(self, qtbot, tmp_path):
        model = ProjectModel()
        widget = AdvancedOptionsWidget(model)
        qtbot.addWidget(widget)
        widget.set_firmware("qmk")

        self._import(widget, self._vial_file(tmp_path, layers=3))

        status = widget.findChild(QLabel, "adv_keymap_status").text()
        assert "3" in status

    def test_reload_from_model_restores_status(self, qtbot, tmp_path):
        model = ProjectModel()
        model.keyboard.use_custom_keymap = True
        model.keyboard.custom_keymap = {"layout": [[["KC_A"]]] * 2}
        widget = AdvancedOptionsWidget(model)
        qtbot.addWidget(widget)

        widget.reload_from_model()

        assert widget.findChild(QCheckBox, "adv_use_custom_keymap").isChecked() is True
        assert "2" in widget.findChild(QLabel, "adv_keymap_status").text()


class TestTooltips:
    """Chaque option porte une explication avec un exemple concret."""

    def test_every_declared_field_has_a_tooltip(self, qtbot):
        from PySide6.QtWidgets import QWidget

        from modules.advanced_options.widget import ADVANCED_TOOLTIP_FIELDS
        widget = AdvancedOptionsWidget(ProjectModel())
        qtbot.addWidget(widget)

        missing = [
            name for name in ADVANCED_TOOLTIP_FIELDS
            if not (widget.findChild(QWidget, name) or QWidget()).toolTip()
        ]

        assert not missing, f"champs sans infobulle : {missing}"

    def test_tooltip_contains_an_example(self, qtbot):
        widget = AdvancedOptionsWidget(ProjectModel())
        qtbot.addWidget(widget)

        tip = widget.findChild(QCheckBox, "adv_nkro_enabled").toolTip()

        assert "Exemple" in tip

    def test_greying_prepends_notice_without_losing_explanation(self, qtbot):
        widget = AdvancedOptionsWidget(ProjectModel())
        qtbot.addWidget(widget)
        passkey = widget.findChild(QCheckBox, "adv_ble_passkey_entry")

        widget.set_firmware("qmk")
        tip = passkey.toolTip()

        assert tip.startswith("ZMK")
        assert "Exemple" in tip

    def test_explanation_restored_when_option_applies(self, qtbot):
        widget = AdvancedOptionsWidget(ProjectModel())
        qtbot.addWidget(widget)
        passkey = widget.findChild(QCheckBox, "adv_ble_passkey_entry")

        widget.set_firmware("qmk")
        widget.set_firmware("zmk")
        tip = passkey.toolTip()

        assert not tip.startswith("ZMK uniquement")
        assert "Exemple" in tip
