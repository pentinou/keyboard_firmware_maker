"""Tests de l'import de keymap multi-format (Vial et ZMK).

Couvre la détection du format, le parseur .keymap ZMK, la conversion
ZMK → QMK et la mise en ordre Vial → LAYOUT() de QMK.
"""
from __future__ import annotations

import json

from modules.keymap_importer.common import (
    FORMAT_UNKNOWN,
    FORMAT_VIAL,
    FORMAT_ZMK,
    ConversionReport,
    detect_format,
)
from modules.keymap_importer.vial_to_qmk import convert_vial_to_qmk_layers
from modules.keymap_importer.zmk_to_qmk import (
    convert_zmk_binding_to_qmk,
    convert_zmk_layers_to_qmk,
    parse_zmk_keymap,
)

ZMK_KEYMAP = """
/ {
    keymap {
        compatible = "zmk,keymap";

        default_layer {
            bindings = <
                &kp ESC   &kp N1  &kp A
                &mo 1     &trans  &kp SPACE
            >;
        };

        lower_layer {
            // couche symboles
            bindings = <
                &kp EXCL  &bt BT_SEL 0  &none
                &to 0     &kp F1        &kp LSHFT
            >;
        };
    };
};
"""


class TestDetectFormat:
    def test_detects_vial_json(self, tmp_path):
        path = tmp_path / "keymap.vil"
        path.write_text(json.dumps({"layout": [[["KC_A"]]], "version": 1}), encoding="utf-8")

        assert detect_format(path) == FORMAT_VIAL

    def test_detects_zmk_keymap(self, tmp_path):
        path = tmp_path / "sofle.keymap"
        path.write_text(ZMK_KEYMAP, encoding="utf-8")

        assert detect_format(path) == FORMAT_ZMK

    def test_json_without_layout_is_unknown(self, tmp_path):
        path = tmp_path / "autre.json"
        path.write_text(json.dumps({"foo": "bar"}), encoding="utf-8")

        assert detect_format(path) == FORMAT_UNKNOWN

    def test_malformed_json_is_unknown(self, tmp_path):
        path = tmp_path / "casse.json"
        path.write_text("{ pas du json", encoding="utf-8")

        assert detect_format(path) == FORMAT_UNKNOWN

    def test_arbitrary_text_is_unknown(self, tmp_path):
        path = tmp_path / "notes.txt"
        path.write_text("mon clavier préféré", encoding="utf-8")

        assert detect_format(path) == FORMAT_UNKNOWN

    def test_content_wins_over_extension(self, tmp_path):
        """Un keymap ZMK enregistré en .json reste détecté comme ZMK."""
        path = tmp_path / "trompeur.json"
        path.write_text(ZMK_KEYMAP, encoding="utf-8")

        assert detect_format(path) == FORMAT_ZMK

    def test_unreadable_file_is_unknown(self, tmp_path):
        assert detect_format(tmp_path / "absent.vil") == FORMAT_UNKNOWN


class TestParseZmkKeymap:
    def test_extracts_layers_in_order(self):
        layers = parse_zmk_keymap(ZMK_KEYMAP)

        assert [layer["name"] for layer in layers] == ["default_layer", "lower_layer"]

    def test_extracts_bindings_with_parameters(self):
        layers = parse_zmk_keymap(ZMK_KEYMAP)

        assert layers[0]["bindings"] == [
            "&kp ESC", "&kp N1", "&kp A", "&mo 1", "&trans", "&kp SPACE",
        ]

    def test_multi_parameter_binding_kept_whole(self):
        layers = parse_zmk_keymap(ZMK_KEYMAP)

        assert "&bt BT_SEL 0" in layers[1]["bindings"]

    def test_comments_are_ignored(self):
        layers = parse_zmk_keymap(ZMK_KEYMAP)

        assert all("couche symboles" not in b for b in layers[1]["bindings"])

    def test_ignores_combos_outside_keymap_node(self):
        content = """
        / {
            combos {
                compatible = "zmk,combos";
                combo_esc { key-positions = <0 1>; bindings = <&kp ESC>; };
            };
            keymap {
                compatible = "zmk,keymap";
                default_layer { bindings = <&kp A &kp B>; };
            };
        };
        """
        layers = parse_zmk_keymap(content)

        assert len(layers) == 1
        assert layers[0]["bindings"] == ["&kp A", "&kp B"]

    def test_empty_content_returns_no_layer(self):
        assert parse_zmk_keymap("") == []


class TestConvertBinding:
    def test_simple_keys(self):
        assert convert_zmk_binding_to_qmk("&kp A") == "KC_A"
        assert convert_zmk_binding_to_qmk("&kp N5") == "KC_5"
        assert convert_zmk_binding_to_qmk("&kp SPACE") == "KC_SPC"
        assert convert_zmk_binding_to_qmk("&kp RET") == "KC_ENT"

    def test_transparent_and_none(self):
        assert convert_zmk_binding_to_qmk("&trans") == "KC_TRNS"
        assert convert_zmk_binding_to_qmk("&none") == "KC_NO"

    def test_layer_behaviors(self):
        assert convert_zmk_binding_to_qmk("&mo 2") == "MO(2)"
        assert convert_zmk_binding_to_qmk("&tog 1") == "TG(1)"
        assert convert_zmk_binding_to_qmk("&to 0") == "TO(0)"
        assert convert_zmk_binding_to_qmk("&lt 1 SPACE") == "LT(1, KC_SPC)"

    def test_firmware_keys(self):
        assert convert_zmk_binding_to_qmk("&bootloader") == "QK_BOOT"
        assert convert_zmk_binding_to_qmk("&sys_reset") == "QK_RBT"

    def test_zmk_specific_returns_none(self):
        assert convert_zmk_binding_to_qmk("&bt BT_SEL 0") is None
        assert convert_zmk_binding_to_qmk("&out OUT_TOG") is None
        assert convert_zmk_binding_to_qmk("&ext_power EP_TOG") is None

    def test_unknown_keycode_returns_none(self):
        assert convert_zmk_binding_to_qmk("&kp INEXISTANT") is None

    def test_whitespace_is_normalised(self):
        assert convert_zmk_binding_to_qmk("  &kp    A  ") == "KC_A"

    def test_empty_binding_returns_none(self):
        assert convert_zmk_binding_to_qmk("") is None


class TestConvertLayers:
    def test_converts_and_reports(self):
        layers = parse_zmk_keymap(ZMK_KEYMAP)

        qmk, report = convert_zmk_layers_to_qmk(layers)

        assert qmk[0] == ["KC_ESC", "KC_1", "KC_A", "MO(1)", "KC_TRNS", "KC_SPC"]
        assert report.converted == 11  # 12 bindings - 1 sans équivalent
        assert len(report.dropped) == 1

    def test_dropped_binding_becomes_kc_no(self):
        layers = parse_zmk_keymap(ZMK_KEYMAP)

        qmk, _ = convert_zmk_layers_to_qmk(layers)

        assert qmk[1][1] == "KC_NO"

    def test_report_locates_and_explains_the_loss(self):
        layers = parse_zmk_keymap(ZMK_KEYMAP)

        _, report = convert_zmk_layers_to_qmk(layers)
        dropped = report.dropped[0]

        assert dropped.layer == 1
        assert dropped.position == 1
        assert dropped.source == "&bt BT_SEL 0"
        assert "Bluetooth" in dropped.reason
        assert report.has_losses is True

    def test_clean_conversion_reports_no_loss(self):
        qmk, report = convert_zmk_layers_to_qmk([{"name": "d", "bindings": ["&kp A", "&trans"]}])

        assert qmk == [["KC_A", "KC_TRNS"]]
        assert report.has_losses is False


class TestVialToQmkLayers:
    VIAL = {
        "layout": [
            [["KC_ESC", "KC_A"], ["KC_TAB", "KC_B"]],      # couche 0
            [["KC_F1", "KC_TRNS"], ["KC_NO", "KC_C"]],     # couche 1
        ]
    }
    KEYS = [
        {"matrix_row": 0, "matrix_col": 0},
        {"matrix_row": 0, "matrix_col": 1},
        {"matrix_row": 1, "matrix_col": 0},
        {"matrix_row": 1, "matrix_col": 1},
    ]

    def test_orders_keycodes_like_layout_macro(self):
        layers, report = convert_vial_to_qmk_layers(self.VIAL, self.KEYS)

        assert layers[0] == ["KC_ESC", "KC_A", "KC_TAB", "KC_B"]
        assert layers[1] == ["KC_F1", "KC_TRNS", "KC_NO", "KC_C"]
        assert report.has_losses is False

    def test_missing_position_becomes_transparent(self):
        keys = self.KEYS + [{"matrix_row": 9, "matrix_col": 9}]

        layers, report = convert_vial_to_qmk_layers(self.VIAL, keys)

        assert layers[0][-1] == "KC_TRNS"
        assert report.dropped[0].reason.startswith("Position absente")

    def test_extra_layers_are_reported(self):
        vial = {"layout": self.VIAL["layout"] + [[["KC_Z", "KC_Z"], ["KC_Z", "KC_Z"]]]}

        _, report = convert_vial_to_qmk_layers(vial, self.KEYS, max_layers=2)

        assert any("ignorée" in w for w in report.warnings)

    def test_pads_to_requested_layer_count(self):
        layers, _ = convert_vial_to_qmk_layers(self.VIAL, self.KEYS, max_layers=3)

        assert len(layers) == 2  # le fichier n'en fournit que 2

    def test_empty_vial_data_is_reported(self):
        layers, report = convert_vial_to_qmk_layers({}, self.KEYS)

        assert layers == []
        assert report.warnings

    def test_accepts_existing_report(self):
        report = ConversionReport()
        report.warnings.append("préexistant")

        _, returned = convert_vial_to_qmk_layers(self.VIAL, self.KEYS, report=report)

        assert returned is report
        assert "préexistant" in returned.warnings
