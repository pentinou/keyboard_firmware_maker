"""Tests pour le converter Vial-QMK → ZMK."""
from __future__ import annotations

import pytest

from modules.keymap_importer.vial_to_zmk import (
    convert_qmk_keycode_to_zmk,
    convert_vial_to_zmk_keymap,
)


class TestQmkKeycodeConversion:
    """Conversion individuelle de keycodes QMK → bindings ZMK."""

    @pytest.mark.parametrize("qmk,zmk", [
        ("KC_A", "&kp A"),
        ("KC_Z", "&kp Z"),
        ("KC_1", "&kp N1"),
        ("KC_0", "&kp N0"),
        ("KC_ESCAPE", "&kp ESC"),
        ("KC_ESC", "&kp ESC"),
        ("KC_TAB", "&kp TAB"),
        ("KC_ENTER", "&kp RET"),
        ("KC_SPACE", "&kp SPACE"),
        ("KC_LSHIFT", "&kp LSHFT"),
        ("KC_LSFT", "&kp LSHFT"),
        ("KC_LGUI", "&kp LGUI"),
        ("KC_LALT", "&kp LALT"),
        ("KC_BSPACE", "&kp BSPC"),
        ("KC_QUOTE", "&kp SQT"),
        ("KC_SCOLON", "&kp SEMI"),
        ("KC_SLASH", "&kp FSLH"),
        ("KC_LBRACKET", "&kp LBKT"),
        ("KC_RBRACKET", "&kp RBKT"),
        ("KC_BSLASH", "&kp BSLH"),
        ("KC_F1", "&kp F1"),
        ("KC_F12", "&kp F12"),
        ("KC_HOME", "&kp HOME"),
        ("KC_END", "&kp END"),
        ("KC_PGUP", "&kp PG_UP"),
        ("KC_PGDOWN", "&kp PG_DN"),
        ("KC_UP", "&kp UP"),
        ("KC_DELETE", "&kp DEL"),
        ("KC_KP_PLUS", "&kp KP_PLUS"),
        ("KC_KP_EQUAL", "&kp KP_EQUAL"),
        ("KC_MUTE", "&kp C_MUTE"),
        ("KC_VOLU", "&kp C_VOL_UP"),
        ("KC_MPRV", "&kp C_PREV"),
        ("KC_BRID", "&kp C_BRI_DN"),
        ("KC_CALC", "&kp C_AL_CALC"),
        ("KC_APPLICATION", "&kp K_APP"),
        ("KC_MINUS", "&kp MINUS"),
        ("KC_COMMA", "&kp COMMA"),
        ("KC_DOT", "&kp DOT"),
    ])
    def test_standard_keys(self, qmk: str, zmk: str):
        assert convert_qmk_keycode_to_zmk(qmk) == zmk

    @pytest.mark.parametrize("qmk,zmk", [
        ("KC_TRNS", "&trans"),
        ("KC_TRANSPARENT", "&trans"),
        ("_______", "&trans"),
        ("KC_NO", "&none"),
        ("XXXXXXX", "&none"),
    ])
    def test_trans_and_none(self, qmk: str, zmk: str):
        assert convert_qmk_keycode_to_zmk(qmk) == zmk

    @pytest.mark.parametrize("qmk,zmk", [
        ("MO(1)", "&mo 1"),
        ("MO(2)", "&mo 2"),
        ("MO(10)", "&mo 10"),
        ("TG(1)", "&tog 1"),
        ("TO(3)", "&to 3"),
    ])
    def test_layer_behaviors(self, qmk: str, zmk: str):
        assert convert_qmk_keycode_to_zmk(qmk) == zmk

    def test_layer_tap(self):
        """LT(layer, kc) → &lt layer kc"""
        assert convert_qmk_keycode_to_zmk("LT(1, KC_SPACE)") == "&lt 1 SPACE"
        assert convert_qmk_keycode_to_zmk("LT(2,KC_A)") == "&lt 2 A"

    @pytest.mark.parametrize("qmk,zmk", [
        ("QK_BOOT", "&bootloader"),
        ("RESET", "&bootloader"),
        ("QK_REBOOT", "&sys_reset"),
    ])
    def test_system_keys(self, qmk: str, zmk: str):
        assert convert_qmk_keycode_to_zmk(qmk) == zmk

    @pytest.mark.parametrize("qmk,zmk_suffix", [
        ("RGB_TOG", "RGB_TOG"),
        ("RGB_HUI", "RGB_HUI"),
        ("RGB_HUD", "RGB_HUD"),
        ("RGB_SAI", "RGB_SAI"),
        ("RGB_SAD", "RGB_SAD"),
        ("RGB_VAI", "RGB_BRI"),     # QMK VAI = ZMK BRI (brightness up)
        ("RGB_VAD", "RGB_BRD"),
        ("RGB_SPI", "RGB_SPI"),
        ("RGB_SPD", "RGB_SPD"),
        ("RGB_MOD", "RGB_EFF"),     # QMK MOD = ZMK EFF (cycle effect)
        ("RGB_RMOD", "RGB_EFR"),
    ])
    def test_rgb_underglow(self, qmk: str, zmk_suffix: str):
        assert convert_qmk_keycode_to_zmk(qmk) == f"&rgb_ug {zmk_suffix}"

    @pytest.mark.parametrize("qmk,expected", [
        ("BL_TOGG", "&rgb_ug RGB_TOG"),  # backlight → underglow toggle
        ("RGB_M_B", "&rgb_ug RGB_EFF"),  # modes QMK → cycle effect
        ("RGB_M_R", "&rgb_ug RGB_EFF"),
        ("RGB_M_SW", "&rgb_ug RGB_EFF"),
        ("RGB_M_SN", "&rgb_ug RGB_EFF"),
        ("RGB_M_G", "&rgb_ug RGB_EFF"),
        ("RGB_M_X", "&rgb_ug RGB_EFF"),
        ("RM_TOGG", "&rgb_ug RGB_TOG"),  # RGB matrix → underglow
        ("RM_NEXT", "&rgb_ug RGB_EFF"),
        ("RM_PREV", "&rgb_ug RGB_EFR"),
    ])
    def test_qmk_specific_rgb_modes_best_effort(self, qmk: str, expected: str):
        """Modes RGB spécifiques QMK convertis en best-effort ZMK (au lieu de &none muet)."""
        assert convert_qmk_keycode_to_zmk(qmk) == expected

    @pytest.mark.parametrize("qmk", [
        "QK_CLEAR_EEPROM",  # pas d'équivalent ZMK direct
        "UNKNOWN_KC",
    ])
    def test_unknown_keycodes_fallback_to_none(self, qmk: str):
        assert convert_qmk_keycode_to_zmk(qmk) == "&none"

    @pytest.mark.parametrize("invalid", ["", None, 42, []])
    def test_invalid_input(self, invalid):
        assert convert_qmk_keycode_to_zmk(invalid) == "&none"


class TestFullVialKeymapConversion:
    """Conversion d'un keymap Vial complet (le JSON fourni par l'user)."""

    @pytest.fixture
    def user_vial_data(self) -> dict:
        """Le keymap Vial fourni par l'utilisateur (Sofle filaire QMK)."""
        return {
            "version": 1,
            "layout": [
                # Layer 0 : default (10 rows × 6 cols)
                [
                    ["KC_ESCAPE", "KC_1", "KC_2", "KC_3", "KC_4", "KC_5"],
                    ["KC_TAB", "KC_Q", "KC_W", "KC_E", "KC_R", "KC_T"],
                    ["KC_TAB", "KC_A", "KC_S", "KC_D", "KC_F", "KC_G"],
                    ["KC_LSHIFT", "KC_Z", "KC_X", "KC_C", "KC_V", "KC_B"],
                    ["KC_LGUI", "KC_LALT", "KC_LCTRL", "MO(1)", "KC_ENTER", "KC_MUTE"],
                    ["KC_MINUS", "KC_0", "KC_9", "KC_8", "KC_7", "KC_6"],
                    ["KC_BSPACE", "KC_P", "KC_O", "KC_I", "KC_U", "KC_Y"],
                    ["KC_QUOTE", "KC_SCOLON", "KC_L", "KC_K", "KC_J", "KC_H"],
                    ["KC_RSHIFT", "KC_SLASH", "KC_DOT", "KC_COMMA", "KC_M", "KC_N"],
                    ["KC_APPLICATION", "KC_RALT", "KC_RCTRL", "MO(2)", "KC_SPACE", "KC_CALC"],
                ],
                # Layer 1 : lower
                [
                    ["BL_TOGG", "RGB_TOG", "RGB_HUI", "RGB_HUD", "RGB_SAI", "RGB_SAD"],
                    ["RGB_SPI", "RGB_SPD", "KC_TRNS", "KC_TRNS", "KC_TRNS", "KC_PGUP"],
                    ["KC_TRNS", "KC_TRNS", "KC_TRNS", "KC_TRNS", "KC_TRNS", "KC_PGDOWN"],
                    ["KC_TRNS", "KC_KP_PLUS", "KC_MINUS", "KC_KP_EQUAL", "KC_HOME", "KC_END"],
                    ["KC_TRNS", "KC_TRNS", "KC_TRNS", "KC_TRNS", "KC_TRNS", "KC_TRNS"],
                    ["KC_NO", "KC_TRNS", "KC_TRNS", "KC_TRNS", "RGB_VAD", "RGB_VAI"],
                    ["KC_TRNS", "KC_TRNS", "KC_TRNS", "KC_TRNS", "KC_TRNS", "KC_TRNS"],
                    ["KC_TRNS", "KC_TRNS", "KC_TRNS", "KC_TRNS", "KC_TRNS", "KC_TRNS"],
                    ["KC_TRNS", "KC_BSLASH", "KC_TRNS", "KC_TRNS", "KC_RBRACKET", "KC_LBRACKET"],
                    ["KC_TRNS", "KC_TRNS", "KC_TRNS", "KC_TRNS", "KC_TRNS", "KC_TRNS"],
                ],
            ],
        }

    def test_default_layer_present(self, user_vial_data):
        result = convert_vial_to_zmk_keymap(user_vial_data)
        assert "default" in result
        # 10 rows QMK → 5 rows ZMK combinées
        assert len(result["default"]) == 5

    def test_default_layer_row0_combined(self, user_vial_data):
        """Row 0 QMK left = [ESC, 1, 2, 3, 4, 5], right = [-, 0, 9, 8, 7, 6]
        → row 0 ZMK = left + right = 12 bindings."""
        result = convert_vial_to_zmk_keymap(user_vial_data)
        row0 = result["default"][0]
        assert len(row0) == 12
        assert row0[0] == "&kp ESC"
        assert row0[1] == "&kp N1"
        assert row0[5] == "&kp N5"
        assert row0[6] == "&kp MINUS"
        assert row0[7] == "&kp N0"
        assert row0[11] == "&kp N6"

    def test_default_layer_row4_thumbs(self, user_vial_data):
        """Row 4 contient les thumbs + encoder + KC_MUTE / KC_CALC sur les extrêmes."""
        result = convert_vial_to_zmk_keymap(user_vial_data)
        row4 = result["default"][4]
        # left col 3 (4ème position) = MO(1)
        assert row4[3] == "&mo 1"
        # left col 4 = ENTER
        assert row4[4] == "&kp RET"
        # left col 5 = MUTE
        assert row4[5] == "&kp C_MUTE"
        # right col 3 (4ème position, 10ème global) = MO(2)
        assert row4[9] == "&mo 2"
        # right col 5 = CALC
        assert row4[11] == "&kp C_AL_CALC"

    def test_lower_layer_rgb_keys(self, user_vial_data):
        """Layer 1 a des RGB_* qui sont convertis en &rgb_ug RGB_*."""
        result = convert_vial_to_zmk_keymap(user_vial_data)
        assert "lower" in result
        row0 = result["lower"][0]
        # BL_TOGG → &rgb_ug RGB_TOG (best-effort : backlight → underglow toggle)
        assert row0[0] == "&rgb_ug RGB_TOG"
        assert row0[1] == "&rgb_ug RGB_TOG"
        assert row0[2] == "&rgb_ug RGB_HUI"
        assert row0[3] == "&rgb_ug RGB_HUD"
        assert row0[4] == "&rgb_ug RGB_SAI"
        assert row0[5] == "&rgb_ug RGB_SAD"

    def test_lower_layer_trans_preserved(self, user_vial_data):
        """KC_TRNS doit devenir &trans."""
        result = convert_vial_to_zmk_keymap(user_vial_data)
        # Row 2 col 0 = KC_TRNS dans le lower
        assert result["lower"][2][0] == "&trans"

    def test_missing_layers_skipped(self):
        """Si moins de layers que de noms, on ne crée que les présents."""
        vial = {"layout": [
            [["KC_A"] * 6] * 10,  # juste 1 layer
        ]}
        result = convert_vial_to_zmk_keymap(vial)
        assert "default" in result
        assert "lower" not in result

    def test_encoder_columns_filtered(self):
        """Sur Sofle, row 4 a 6 entrées Vial par moitié (5 thumbs + 1 clic
        encodeur). Le clic encodeur doit être filtré pour aligner avec les 10
        positions used de ZMK (sinon SPACE est décalée et disparaît)."""
        # Simuler le row 4 Vial Sofle : 6 entries par moitié
        vial = {
            "layout": [
                [
                    # 4 premières rows (ignorées pour ce test)
                    *([["KC_NO"] * 6] * 4),
                    # Row 4 left : 5 thumbs + 1 clic encodeur (KC_MUTE)
                    ["KC_LGUI", "KC_LALT", "KC_LCTRL", "MO(1)", "KC_ENTER", "KC_MUTE"],
                    # 4 premières rows right (ignorées)
                    *([["KC_NO"] * 6] * 4),
                    # Row 4 right : 5 thumbs + 1 clic encodeur (KC_CALC)
                    ["KC_APPLICATION", "KC_RALT", "KC_RCTRL", "MO(2)", "KC_SPACE", "KC_CALC"],
                ]
            ]
        }
        # Sur Sofle : encodeur left = col 5, encodeur right = col 5+6=11 (matrice combinée)
        encoder_cols_per_row = {4: {5, 11}}
        result = convert_vial_to_zmk_keymap(vial, encoder_cols_per_row=encoder_cols_per_row)
        row4 = result["default"][4]
        # Sans encodeurs : 10 entrées (5 left thumbs + 5 right thumbs)
        assert len(row4) == 10
        # left thumbs
        assert row4[0] == "&kp LGUI"
        assert row4[1] == "&kp LALT"
        assert row4[2] == "&kp LCTRL"
        assert row4[3] == "&mo 1"
        assert row4[4] == "&kp RET"
        # right thumbs (KC_MUTE et KC_CALC sont filtrés)
        assert row4[5] == "&kp K_APP"
        assert row4[6] == "&kp RALT"
        assert row4[7] == "&kp RCTRL"
        assert row4[8] == "&mo 2"
        # SPACE doit être présent !
        assert row4[9] == "&kp SPACE"
