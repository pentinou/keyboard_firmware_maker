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
        assert (tmp_path / "config" / "corne.conf").is_file()

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

    def test_matrix_transform_dimensions_match_col_offset_pattern(
        self, zmk_gen, corne_model, tmp_path
    ):
        zmk_gen.generate(corne_model, tmp_path)
        dtsi = (tmp_path / "config" / "boards" / "shields" / "corne" / "corne.dtsi").read_text()
        right = (
            tmp_path / "config" / "boards" / "shields" / "corne" / "corne_right.overlay"
        ).read_text()
        # Corne: 4 rows × 6 cols, split via col-offset=6 on right → transform
        # must declare rows=<4> columns=<12>, NOT rows=<8> columns=<6>.
        assert "rows = <4>" in dtsi
        assert "columns = <12>" in dtsi
        assert "col-offset = <6>" in right

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
        content = (tmp_path / "config" / "corne.conf").read_text()
        assert "CONFIG_ZMK_SPLIT=y" in content

    def test_build_yaml_has_nice_nano(self, zmk_gen, corne_model, tmp_path):
        zmk_gen.generate(corne_model, tmp_path)
        content = (tmp_path / "build.yaml").read_text()
        assert "board: nice_nano//zmk" in content

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

    def test_creates_west_yml(self, zmk_gen, corne_model, tmp_path):
        zmk_gen.generate(corne_model, tmp_path)
        assert (tmp_path / "config" / "west.yml").is_file()

    def test_west_yml_imports_zmk_manifest(self, zmk_gen, corne_model, tmp_path):
        zmk_gen.generate(corne_model, tmp_path)
        content = (tmp_path / "config" / "west.yml").read_text()
        assert "zmkfirmware" in content
        assert "import: app/west.yml" in content
        assert "path: config" in content


class TestZmkGenerateSofleWithRgb:
    """Sofle split avec encoder, OLED et RGB underglow ZMK (SPI3 + WS2812)."""

    def test_conf_enables_rgb_underglow(self, zmk_gen, sofle_model, tmp_path):
        zmk_gen.generate(sofle_model, tmp_path)
        shield = "sofle_v2"
        content = (tmp_path / "config" / f"{shield}.conf").read_text()
        assert "CONFIG_ZMK_RGB_UNDERGLOW=y" in content

    def test_dtsi_emits_ws2812_node(self, zmk_gen, sofle_model, tmp_path):
        zmk_gen.generate(sofle_model, tmp_path)
        dtsi = (tmp_path / "config" / "boards" / "shields" / "sofle_v2" / "sofle_v2.dtsi").read_text()
        assert "led_strip: ws2812@0" in dtsi
        assert 'compatible = "worldsemi,ws2812-spi"' in dtsi

    def test_dtsi_emits_spi3_pinctrl(self, zmk_gen, sofle_model, tmp_path):
        zmk_gen.generate(sofle_model, tmp_path)
        dtsi = (tmp_path / "config" / "boards" / "shields" / "sofle_v2" / "sofle_v2.dtsi").read_text()
        assert "spi3_default" in dtsi
        assert "spi3_sleep" in dtsi
        # sofle-v2.yaml : ws2812 = "&pro_micro 1" → P0.06 sur nice_nano/SuperMini.
        # Validé empiriquement avec firmware blanc fixe sur PCB Sofle v2.1 RGB.
        assert "NRF_PSEL(SPIM_MOSI, 0, 6)" in dtsi

    def test_dtsi_declares_chosen_underglow(self, zmk_gen, sofle_model, tmp_path):
        zmk_gen.generate(sofle_model, tmp_path)
        dtsi = (tmp_path / "config" / "boards" / "shields" / "sofle_v2" / "sofle_v2.dtsi").read_text()
        assert "zmk,underglow = &led_strip" in dtsi

    def test_dtsi_chain_length_from_yaml(self, zmk_gen, sofle_model, tmp_path):
        zmk_gen.generate(sofle_model, tmp_path)
        dtsi = (tmp_path / "config" / "boards" / "shields" / "sofle_v2" / "sofle_v2.dtsi").read_text()
        # sofle-v2.yaml led_count: 36
        assert "chain-length = <36>" in dtsi

    def test_conf_has_encoder(self, zmk_gen, sofle_model, tmp_path):
        zmk_gen.generate(sofle_model, tmp_path)
        shield = "sofle_v2"
        content = (tmp_path / "config" / f"{shield}.conf").read_text()
        assert "CONFIG_EC11=y" in content

    def test_conf_has_display(self, zmk_gen, sofle_model, tmp_path):
        zmk_gen.generate(sofle_model, tmp_path)
        shield = "sofle_v2"
        content = (tmp_path / "config" / f"{shield}.conf").read_text()
        assert "CONFIG_ZMK_DISPLAY=y" in content

    def test_conf_has_battery_widget(self, zmk_gen, sofle_model, tmp_path):
        zmk_gen.generate(sofle_model, tmp_path)
        shield = "sofle_v2"
        content = (tmp_path / "config" / f"{shield}.conf").read_text()
        assert "CONFIG_ZMK_WIDGET_BATTERY_STATUS=y" in content
        assert "CONFIG_ZMK_DISPLAY_STATUS_SCREEN_BUILT_IN=y" in content

    def test_conf_has_split_battery_proxy(self, zmk_gen, sofle_model, tmp_path):
        zmk_gen.generate(sofle_model, tmp_path)
        shield = "sofle_v2"
        content = (tmp_path / "config" / f"{shield}.conf").read_text()
        assert "CONFIG_ZMK_SPLIT_BLE_CENTRAL_BATTERY_LEVEL_PROXY=y" in content
        assert "CONFIG_ZMK_SPLIT_BLE_CENTRAL_BATTERY_LEVEL_FETCHING=y" in content

    def test_conf_no_wpm_widget(self, zmk_gen, sofle_model, tmp_path):
        zmk_gen.generate(sofle_model, tmp_path)
        shield = "sofle_v2"
        content = (tmp_path / "config" / f"{shield}.conf").read_text()
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
        content = (tmp_path / "config" / "corne.conf").read_text()
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
        import re
        zmk_gen.generate(sofle_model, tmp_path)
        shield = "sofle_v2"
        dtsi = (tmp_path / "config" / "boards" / "shields" / shield / f"{shield}.dtsi").read_text()
        keymap = (tmp_path / "config" / "boards" / "shields" / shield / f"{shield}.keymap").read_text()

        phys_count = dtsi.count("key_physical_attrs")
        # Compter tous les bindings du default_layer (chaque binding commence par `&`,
        # ex. &trans, &kp ESC, &lt 1 SPACE). On extrait uniquement le bloc bindings = < ... >;
        start = keymap.index("default_layer")
        bindings_start = keymap.index("bindings = <", start) + len("bindings = <")
        bindings_end = keymap.index(">", bindings_start)
        bindings_block = keymap[bindings_start:bindings_end]
        binding_count = len(re.findall(r"&\w+", bindings_block))

        assert phys_count == binding_count

    def test_sofle_physical_layout_has_right_offset(self, zmk_gen, sofle_model, tmp_path):
        """Les touches droites doivent être décalées vers la droite dans le physical layout."""
        zmk_gen.generate(sofle_model, tmp_path)
        shield = "sofle_v2"
        dtsi = (tmp_path / "config" / "boards" / "shields" / shield / f"{shield}.dtsi").read_text()
        # Le Sofle gauche va jusqu'à x=6.0 (600 centi). Droite offset = 9.0 (900+).
        # Vérifier qu'on a des positions >= 900 centi-key-units
        assert "900" in dtsi or "1000" in dtsi or "1100" in dtsi


class TestZmkOledDevicetree:
    """OLED : bloc devicetree ssd1306 sur I2C et chosen zephyr,display."""

    def test_dtsi_has_i2c_display_node(self, zmk_gen, sofle_model, tmp_path):
        zmk_gen.generate(sofle_model, tmp_path)
        shield = "sofle_v2"
        dtsi = (tmp_path / "config" / "boards" / "shields" / shield / f"{shield}.dtsi").read_text()
        assert "&pro_micro_i2c" in dtsi
        assert "ssd1306@3c" in dtsi
        assert 'compatible = "solomon,ssd1306fb"' in dtsi
        assert "reg = <0x3c>" in dtsi

    def test_dtsi_has_display_dimensions(self, zmk_gen, sofle_model, tmp_path):
        zmk_gen.generate(sofle_model, tmp_path)
        shield = "sofle_v2"
        dtsi = (tmp_path / "config" / "boards" / "shields" / shield / f"{shield}.dtsi").read_text()
        # Sofle v2 : display "128X32" → width=128, height=32, multiplex=31
        assert "width = <128>" in dtsi
        assert "height = <32>" in dtsi
        assert "multiplex-ratio = <31>" in dtsi

    def test_dtsi_chosen_references_oled(self, zmk_gen, sofle_model, tmp_path):
        zmk_gen.generate(sofle_model, tmp_path)
        shield = "sofle_v2"
        dtsi = (tmp_path / "config" / "boards" / "shields" / shield / f"{shield}.dtsi").read_text()
        assert "zephyr,display = &oled" in dtsi

    def test_dtsi_no_display_when_not_configured(self, zmk_gen, corne_model, tmp_path):
        """Corne sans oled_sides configuré → pas de bloc OLED généré."""
        zmk_gen.generate(corne_model, tmp_path)
        dtsi = (tmp_path / "config" / "boards" / "shields" / "corne" / "corne.dtsi").read_text()
        assert "ssd1306@3c" not in dtsi
        assert "zephyr,display" not in dtsi

    def test_32px_display_has_com_sequential(self, zmk_gen, sofle_model, tmp_path):
        """OLED 128x32 nécessite com-sequential (pas com-alternative)."""
        zmk_gen.generate(sofle_model, tmp_path)
        shield = "sofle_v2"
        dtsi = (tmp_path / "config" / "boards" / "shields" / shield / f"{shield}.dtsi").read_text()
        assert "com-sequential" in dtsi


class TestZmkStudioLocking:
    """ZMK Studio : locking désactivé pour accès USB sans unlock behavior."""

    def test_conf_disables_studio_locking(self, zmk_gen, corne_model, tmp_path):
        zmk_gen.generate(corne_model, tmp_path)
        content = (tmp_path / "config" / "corne.conf").read_text()
        assert "CONFIG_ZMK_STUDIO_LOCKING=n" in content


class TestZmkMcuMapping:
    """Vérifie que différents MCUs génèrent le bon board ZMK."""

    def test_nrfmicro_board(self, zmk_gen, tmp_path):
        m = ProjectModel()
        m.keyboard.model = "corne"
        m.keyboard.mcu = "nrfmicro"
        zmk_gen.generate(m, tmp_path)
        content = (tmp_path / "build.yaml").read_text()
        assert "board: nrfmicro" in content

    def test_supermini_board(self, zmk_gen, tmp_path):
        m = ProjectModel()
        m.keyboard.model = "corne"
        m.keyboard.mcu = "supermini_nrf52840"
        zmk_gen.generate(m, tmp_path)
        content = (tmp_path / "build.yaml").read_text()
        assert "board: nice_nano//zmk" in content

    def test_nrfmicro_board_qualifier(self, zmk_gen, tmp_path):
        m = ProjectModel()
        m.keyboard.model = "corne"
        m.keyboard.mcu = "nrfmicro"
        zmk_gen.generate(m, tmp_path)
        content = (tmp_path / "build.yaml").read_text()
        assert "board: nrfmicro/nrf52840/zmk" in content

    def test_unknown_mcu_raises(self, zmk_gen, tmp_path):
        m = ProjectModel()
        m.keyboard.model = "corne"
        m.keyboard.mcu = "esp32c3_devkit"  # non supporté
        with pytest.raises(ValueError, match="non supporté"):
            zmk_gen.generate(m, tmp_path)


class TestZmkRgbUnderglowGuards:
    """Cas où RGB underglow doit rester désactivé."""

    def test_corne_no_rgb_block(self, zmk_gen, corne_model, tmp_path):
        zmk_gen.generate(corne_model, tmp_path)
        dtsi = (tmp_path / "config" / "boards" / "shields" / "corne" / "corne.dtsi").read_text()
        assert "ws2812@0" not in dtsi
        assert "zmk,underglow" not in dtsi
        conf = (tmp_path / "config" / "corne.conf").read_text()
        assert "CONFIG_ZMK_RGB_UNDERGLOW" not in conf

    def test_nrfmicro_rgb_disabled(self, zmk_gen, tmp_path):
        # nrfmicro n'a pas de table pro_micro → RGB désactivé même si YAML le demande
        m = ProjectModel()
        m.keyboard.model = "sofle-v2"
        m.keyboard.mcu = "nrfmicro"
        zmk_gen.generate(m, tmp_path)
        dtsi = (tmp_path / "config" / "boards" / "shields" / "sofle_v2" / "sofle_v2.dtsi").read_text()
        assert "ws2812@0" not in dtsi
        conf = (tmp_path / "config" / "sofle_v2.conf").read_text()
        assert "CONFIG_ZMK_RGB_UNDERGLOW" not in conf
