"""Tests pour modules/build_manager/zmk_template_generator.py — ZmkTemplateGenerator."""
from __future__ import annotations

from pathlib import Path

import pytest

from models.project_model import ProjectModel
from modules.build_manager.zmk_template_generator import ZmkTemplateGenerator


@pytest.fixture
def zmk_gen():
    templates_dir = Path(__file__).parent.parent.parent.parent / "templates" / "zmk"
    return ZmkTemplateGenerator(templates_dir=templates_dir)


@pytest.fixture
def corne_model():
    m = ProjectModel()
    m.keyboard.model = "corne"
    m.keyboard.mcu = "nice_nano_v2"
    return m


@pytest.fixture
def sofle_model():
    m = ProjectModel()
    m.keyboard.model = "sofle-v2"
    m.keyboard.mcu = "nice_nano_v2"
    m.keyboard.rgb_enabled = True
    m.keyboard.oled_sides = ["left"]
    return m


class TestZmkGenerateSplitCorne:
    """Corne split avec nice!nano v2."""

    def test_creates_dtsi(self, zmk_gen, corne_model, tmp_path):
        zmk_gen.generate(corne_model, tmp_path)
        assert (tmp_path / "config" / "boards" / "shields" / "corne" / "corne.dtsi").is_file()

    def test_creates_left_overlay(self, zmk_gen, corne_model, tmp_path):
        zmk_gen.generate(corne_model, tmp_path)
        assert (tmp_path / "config" / "boards" / "shields" / "corne" / "corne_left.overlay").is_file()

    def test_creates_right_overlay(self, zmk_gen, corne_model, tmp_path):
        zmk_gen.generate(corne_model, tmp_path)
        assert (tmp_path / "config" / "boards" / "shields" / "corne" / "corne_right.overlay").is_file()

    def test_creates_keymap(self, zmk_gen, corne_model, tmp_path):
        zmk_gen.generate(corne_model, tmp_path)
        assert (tmp_path / "config" / "boards" / "shields" / "corne" / "corne.keymap").is_file()

    def test_creates_conf(self, zmk_gen, corne_model, tmp_path):
        zmk_gen.generate(corne_model, tmp_path)
        assert (tmp_path / "config" / "boards" / "shields" / "corne" / "corne.conf").is_file()

    def test_creates_right_conf(self, zmk_gen, corne_model, tmp_path):
        zmk_gen.generate(corne_model, tmp_path)
        assert (tmp_path / "config" / "boards" / "shields" / "corne" / "corne_right.conf").is_file()

    def test_creates_kconfig_shield(self, zmk_gen, corne_model, tmp_path):
        zmk_gen.generate(corne_model, tmp_path)
        assert (tmp_path / "config" / "boards" / "shields" / "corne" / "Kconfig.shield").is_file()

    def test_creates_kconfig_defconfig(self, zmk_gen, corne_model, tmp_path):
        zmk_gen.generate(corne_model, tmp_path)
        assert (tmp_path / "config" / "boards" / "shields" / "corne" / "Kconfig.defconfig").is_file()

    def test_creates_build_yaml(self, zmk_gen, corne_model, tmp_path):
        zmk_gen.generate(corne_model, tmp_path)
        assert (tmp_path / "build.yaml").is_file()

    def test_dtsi_contains_kscan(self, zmk_gen, corne_model, tmp_path):
        zmk_gen.generate(corne_model, tmp_path)
        content = (tmp_path / "config" / "boards" / "shields" / "corne" / "corne.dtsi").read_text()
        assert "zmk,kscan-gpio-matrix" in content

    def test_dtsi_contains_matrix_transform(self, zmk_gen, corne_model, tmp_path):
        zmk_gen.generate(corne_model, tmp_path)
        content = (tmp_path / "config" / "boards" / "shields" / "corne" / "corne.dtsi").read_text()
        assert "zmk,matrix-transform" in content

    def test_keymap_contains_zmk_keymap(self, zmk_gen, corne_model, tmp_path):
        zmk_gen.generate(corne_model, tmp_path)
        content = (tmp_path / "config" / "boards" / "shields" / "corne" / "corne.keymap").read_text()
        assert "zmk,keymap" in content
        assert "&trans" in content

    def test_left_overlay_includes_dtsi(self, zmk_gen, corne_model, tmp_path):
        zmk_gen.generate(corne_model, tmp_path)
        content = (tmp_path / "config" / "boards" / "shields" / "corne" / "corne_left.overlay").read_text()
        assert '#include "corne.dtsi"' in content

    def test_right_overlay_has_col_offset(self, zmk_gen, corne_model, tmp_path):
        zmk_gen.generate(corne_model, tmp_path)
        content = (tmp_path / "config" / "boards" / "shields" / "corne" / "corne_right.overlay").read_text()
        assert "col-offset" in content

    def test_conf_has_split(self, zmk_gen, corne_model, tmp_path):
        zmk_gen.generate(corne_model, tmp_path)
        content = (tmp_path / "config" / "boards" / "shields" / "corne" / "corne.conf").read_text()
        assert "CONFIG_ZMK_SPLIT=y" in content

    def test_build_yaml_has_nice_nano(self, zmk_gen, corne_model, tmp_path):
        zmk_gen.generate(corne_model, tmp_path)
        content = (tmp_path / "build.yaml").read_text()
        assert "nice_nano_v2" in content

    def test_build_yaml_has_left_right(self, zmk_gen, corne_model, tmp_path):
        zmk_gen.generate(corne_model, tmp_path)
        content = (tmp_path / "build.yaml").read_text()
        assert "corne_left" in content
        assert "corne_right" in content

    def test_left_overlay_has_gpio_pins(self, zmk_gen, corne_model, tmp_path):
        zmk_gen.generate(corne_model, tmp_path)
        content = (tmp_path / "config" / "boards" / "shields" / "corne" / "corne_left.overlay").read_text()
        assert "&pro_micro" in content

    def test_kconfig_shield_split(self, zmk_gen, corne_model, tmp_path):
        zmk_gen.generate(corne_model, tmp_path)
        content = (tmp_path / "config" / "boards" / "shields" / "corne" / "Kconfig.shield").read_text()
        assert "SHIELD_CORNE_LEFT" in content
        assert "SHIELD_CORNE_RIGHT" in content


class TestZmkGenerateSofleWithRgb:
    """Sofle split avec encoder et RGB underglow."""

    def test_conf_has_rgb_underglow(self, zmk_gen, sofle_model, tmp_path):
        zmk_gen.generate(sofle_model, tmp_path)
        shield = "sofle_v2"
        content = (tmp_path / "config" / "boards" / "shields" / shield / f"{shield}.conf").read_text()
        assert "CONFIG_ZMK_RGB_UNDERGLOW=y" in content

    def test_conf_has_encoder(self, zmk_gen, sofle_model, tmp_path):
        zmk_gen.generate(sofle_model, tmp_path)
        shield = "sofle_v2"
        content = (tmp_path / "config" / "boards" / "shields" / shield / f"{shield}.conf").read_text()
        assert "CONFIG_EC11=y" in content

    def test_conf_has_display(self, zmk_gen, sofle_model, tmp_path):
        zmk_gen.generate(sofle_model, tmp_path)
        shield = "sofle_v2"
        content = (tmp_path / "config" / "boards" / "shields" / shield / f"{shield}.conf").read_text()
        assert "CONFIG_ZMK_DISPLAY=y" in content

    def test_conf_has_battery_widget(self, zmk_gen, sofle_model, tmp_path):
        zmk_gen.generate(sofle_model, tmp_path)
        shield = "sofle_v2"
        content = (tmp_path / "config" / "boards" / "shields" / shield / f"{shield}.conf").read_text()
        assert "CONFIG_ZMK_WIDGET_BATTERY_STATUS=y" in content
        assert "CONFIG_ZMK_DISPLAY_STATUS_SCREEN_BUILT_IN=y" in content

    def test_conf_has_split_battery_proxy(self, zmk_gen, sofle_model, tmp_path):
        zmk_gen.generate(sofle_model, tmp_path)
        shield = "sofle_v2"
        content = (tmp_path / "config" / "boards" / "shields" / shield / f"{shield}.conf").read_text()
        assert "CONFIG_ZMK_SPLIT_BLE_CENTRAL_BATTERY_LEVEL_PROXY=y" in content
        assert "CONFIG_ZMK_SPLIT_BLE_CENTRAL_BATTERY_LEVEL_FETCHING=y" in content

    def test_conf_no_wpm_widget(self, zmk_gen, sofle_model, tmp_path):
        zmk_gen.generate(sofle_model, tmp_path)
        shield = "sofle_v2"
        content = (tmp_path / "config" / "boards" / "shields" / shield / f"{shield}.conf").read_text()
        assert "WPM" not in content

    def test_dtsi_has_encoder(self, zmk_gen, sofle_model, tmp_path):
        zmk_gen.generate(sofle_model, tmp_path)
        shield = "sofle_v2"
        content = (tmp_path / "config" / "boards" / "shields" / shield / f"{shield}.dtsi").read_text()
        assert "alps,ec11" in content

    def test_keymap_has_sensor_bindings(self, zmk_gen, sofle_model, tmp_path):
        zmk_gen.generate(sofle_model, tmp_path)
        shield = "sofle_v2"
        content = (tmp_path / "config" / "boards" / "shields" / shield / f"{shield}.keymap").read_text()
        assert "sensor-bindings" in content


class TestZmkStudioSupport:
    """ZMK Studio : physical layout, config et snippet."""

    def test_conf_has_studio_enabled(self, zmk_gen, corne_model, tmp_path):
        zmk_gen.generate(corne_model, tmp_path)
        content = (tmp_path / "config" / "boards" / "shields" / "corne" / "corne.conf").read_text()
        assert "CONFIG_ZMK_STUDIO=y" in content

    def test_dtsi_has_physical_layout(self, zmk_gen, corne_model, tmp_path):
        zmk_gen.generate(corne_model, tmp_path)
        content = (tmp_path / "config" / "boards" / "shields" / "corne" / "corne.dtsi").read_text()
        assert "zmk,physical-layout" in content
        assert "key_physical_attrs" in content

    def test_dtsi_has_physical_layouts_include(self, zmk_gen, corne_model, tmp_path):
        zmk_gen.generate(corne_model, tmp_path)
        content = (tmp_path / "config" / "boards" / "shields" / "corne" / "corne.dtsi").read_text()
        assert "#include <physical_layouts.dtsi>" in content

    def test_chosen_uses_physical_layout(self, zmk_gen, corne_model, tmp_path):
        zmk_gen.generate(corne_model, tmp_path)
        content = (tmp_path / "config" / "boards" / "shields" / "corne" / "corne.dtsi").read_text()
        assert "zmk,physical-layout = &physical_layout0" in content
        # chosen ne doit PAS contenir zmk,matrix-transform (c'est le physical-layout qui le référence)
        chosen_start = content.index("chosen {")
        chosen_end = content.index("};", chosen_start)
        chosen_block = content[chosen_start:chosen_end]
        assert "zmk,matrix-transform" not in chosen_block

    def test_physical_layout_references_transform(self, zmk_gen, corne_model, tmp_path):
        zmk_gen.generate(corne_model, tmp_path)
        content = (tmp_path / "config" / "boards" / "shields" / "corne" / "corne.dtsi").read_text()
        assert "transform = <&default_transform>" in content
        assert "kscan = <&kscan0>" in content

    def test_build_yaml_has_studio_snippet(self, zmk_gen, corne_model, tmp_path):
        zmk_gen.generate(corne_model, tmp_path)
        content = (tmp_path / "build.yaml").read_text()
        assert "studio-rpc-usb-uart" in content

    def test_physical_layout_key_count_matches_bindings(self, zmk_gen, sofle_model, tmp_path):
        """Le nombre de keys dans le physical layout doit correspondre aux bindings du keymap."""
        zmk_gen.generate(sofle_model, tmp_path)
        shield = "sofle_v2"
        dtsi = (tmp_path / "config" / "boards" / "shields" / shield / f"{shield}.dtsi").read_text()
        keymap = (tmp_path / "config" / "boards" / "shields" / shield / f"{shield}.keymap").read_text()

        phys_count = dtsi.count("key_physical_attrs")
        # Compter les &trans dans le default_layer (premier layer)
        # Extraire le bloc default_layer
        start = keymap.index("default_layer")
        end = keymap.index("};", start)
        layer_block = keymap[start:end]
        trans_count = layer_block.count("&trans")

        assert phys_count == trans_count

    def test_sofle_physical_layout_has_right_offset(self, zmk_gen, sofle_model, tmp_path):
        """Les touches droites doivent être décalées vers la droite dans le physical layout."""
        zmk_gen.generate(sofle_model, tmp_path)
        shield = "sofle_v2"
        dtsi = (tmp_path / "config" / "boards" / "shields" / shield / f"{shield}.dtsi").read_text()
        # Le Sofle gauche va jusqu'à x=6.0 (600 centi). Droite offset = 9.0 (900+).
        # Vérifier qu'on a des positions >= 900 centi-key-units
        assert "900" in dtsi or "1000" in dtsi or "1100" in dtsi


class TestZmkMcuMapping:
    """Vérifie que différents MCUs génèrent le bon board ZMK."""

    def test_nrfmicro_board(self, zmk_gen, tmp_path):
        m = ProjectModel()
        m.keyboard.model = "corne"
        m.keyboard.mcu = "nrfmicro"
        zmk_gen.generate(m, tmp_path)
        content = (tmp_path / "build.yaml").read_text()
        assert "nrfmicro_13" in content

    def test_supermini_board(self, zmk_gen, tmp_path):
        m = ProjectModel()
        m.keyboard.model = "corne"
        m.keyboard.mcu = "supermini_nrf52840"
        zmk_gen.generate(m, tmp_path)
        content = (tmp_path / "build.yaml").read_text()
        assert "nice_nano_v2" in content
