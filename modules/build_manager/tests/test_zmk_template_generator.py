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

    def test_dtsi_kscan_has_wakeup_source(self, zmk_gen, corne_model, tmp_path):
        """Garde-fou : sans wakeup-source, le firmware compile mais reste bloqué
        au premier deep sleep — régression silencieuse impossible à détecter
        autrement qu'en runtime hardware. Voir zmk_build_gotchas.md §2."""
        zmk_gen.generate(corne_model, tmp_path)
        content = (tmp_path / "config" / "boards" / "shields" / "corne" / "corne.dtsi").read_text()
        assert "wakeup-source" in content

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

    def test_build_yaml_no_studio_snippet_in_ble_mode(self, zmk_gen, corne_model, tmp_path):
        # Studio est désormais en transport BLE par défaut → aucune entrée du
        # build.yaml ne doit avoir le snippet studio-rpc-usb-uart (USB transport).
        import yaml
        zmk_gen.generate(corne_model, tmp_path)
        data = yaml.safe_load((tmp_path / "build.yaml").read_text())
        for entry in data.get("include", []):
            assert "snippet" not in entry, (
                f"Entrée build.yaml ne doit pas avoir de snippet en mode BLE : {entry}"
            )

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


class TestZmkCustomKeymap:
    """Import keymap perso Vial-QMK pour override le default du YAML."""

    @pytest.fixture
    def sofle_with_custom_keymap(self):
        """Sofle ZMK + custom_keymap minimal (un keymap Vial fictif)."""
        m = ProjectModel()
        m.keyboard.model = "sofle-v2"
        m.keyboard.mcu = "nice_nano_v2"
        m.keyboard.use_custom_keymap = True
        # Layer default : 10 rows × 6 cols, KC_A partout pour le layer 0
        m.keyboard.custom_keymap = {
            "layout": [
                # Layer 0 = ESC partout sur left, A partout sur right (pour distinguer)
                [["KC_ESCAPE"] * 6] * 5 + [["KC_A"] * 6] * 5,
            ],
        }
        return m

    def test_custom_keymap_overrides_default(self, zmk_gen, sofle_with_custom_keymap, tmp_path):
        zmk_gen.generate(sofle_with_custom_keymap, tmp_path)
        keymap = (tmp_path / "config" / "boards" / "shields" / "sofle_v2" / "sofle_v2.keymap").read_text()
        # Le default du YAML Sofle commence par "&kp ESC &kp N1 ..." sur row 0.
        # Notre override met ESC partout sur left (=KC_ESCAPE) et A partout sur right.
        # Donc on doit voir "&kp ESC" répété + "&kp A" répété.
        assert "&kp ESC" in keymap
        assert "&kp A" in keymap
        # Et PAS de N1/N2/... qui viennent du YAML default
        # Compter les occurrences de N1 — devrait être ~0 dans default_layer
        # (mais peut-être dans lower/raise qui retombent sur YAML)
        # On vérifie au moins que la première row default a ESC répété
        lines = keymap.split("\n")
        default_section_start = next(i for i, l in enumerate(lines) if "default_layer" in l)
        # Lire les ~7 lignes suivantes (header + 5 rows + footer)
        default_section = "\n".join(lines[default_section_start:default_section_start + 15])
        # Première row du default doit contenir ESC plusieurs fois (pas N1)
        assert default_section.count("&kp ESC") >= 6

    def test_custom_keymap_disabled_uses_yaml_default(self, zmk_gen, sofle_model, tmp_path):
        """Quand use_custom_keymap=False, le YAML default est utilisé même si
        custom_keymap est rempli."""
        sofle_model.keyboard.use_custom_keymap = False
        sofle_model.keyboard.custom_keymap = {"layout": [[["KC_A"] * 6] * 10]}
        zmk_gen.generate(sofle_model, tmp_path)
        keymap = (tmp_path / "config" / "boards" / "shields" / "sofle_v2" / "sofle_v2.keymap").read_text()
        # Le YAML Sofle a "&kp N1" sur row 0 du default → doit être présent
        assert "&kp N1" in keymap

    def test_split_keyboard_has_two_sensor_bindings(self, zmk_gen, sofle_model, tmp_path):
        """Sofle split avec encoder doit générer 2 sensor-bindings par layer
        (sensor 0 = left, sensor 1 = right). Régression KFM 2026-05-18."""
        zmk_gen.generate(sofle_model, tmp_path)
        keymap = (tmp_path / "config" / "boards" / "shields" / "sofle_v2" / "sofle_v2.keymap").read_text()
        # 2 occurrences de &inc_dec_kp par layer × 4 layers (default/lower/raise/bluetooth) = 8
        assert keymap.count("&inc_dec_kp") >= 8
        # Le default layer doit avoir VOL + PG côté droit
        assert "&inc_dec_kp C_VOL_UP C_VOL_DN &inc_dec_kp PG_DN PG_UP" in keymap

    def test_split_dtsi_declares_two_encoders(self, zmk_gen, sofle_model, tmp_path):
        """Sur split, le dtsi doit déclarer right_encoder en plus de left_encoder,
        et la liste des sensors doit les inclure tous les deux."""
        zmk_gen.generate(sofle_model, tmp_path)
        dtsi = (tmp_path / "config" / "boards" / "shields" / "sofle_v2" / "sofle_v2.dtsi").read_text()
        assert "left_encoder:" in dtsi
        assert "right_encoder:" in dtsi
        assert "sensors = <&left_encoder &right_encoder>" in dtsi

    def test_split_overlays_enable_local_encoder(self, zmk_gen, sofle_model, tmp_path):
        """L'overlay gauche active left_encoder, l'overlay droit active right_encoder."""
        zmk_gen.generate(sofle_model, tmp_path)
        left_overlay = (tmp_path / "config" / "boards" / "shields" / "sofle_v2" / "sofle_v2_left.overlay").read_text()
        right_overlay = (tmp_path / "config" / "boards" / "shields" / "sofle_v2" / "sofle_v2_right.overlay").read_text()
        assert "&left_encoder" in left_overlay
        assert "right_encoder" not in left_overlay  # droite pas activée côté gauche
        assert "&right_encoder" in right_overlay
        assert "left_encoder" not in right_overlay

    def test_custom_encoder_layout_uses_vial_bindings(self, zmk_gen, sofle_model, tmp_path):
        """Si custom_keymap contient un encoder_layout Vial, ces bindings doivent
        remplacer les defaults dans les sensor-bindings ZMK."""
        sofle_model.keyboard.use_custom_keymap = True
        sofle_model.keyboard.custom_keymap = {
            "layout": [[["KC_A"] * 6] * 10],
            "encoder_layout": [
                # Layer 0 : left = [VOLD, VOLU], right = [PGDOWN, PGUP]
                [["KC_VOLD", "KC_VOLU"], ["KC_PGDOWN", "KC_PGUP"]],
            ],
        }
        zmk_gen.generate(sofle_model, tmp_path)
        keymap = (tmp_path / "config" / "boards" / "shields" / "sofle_v2" / "sofle_v2.keymap").read_text()
        # CW d'abord dans ZMK : Vial [VOLD, VOLU] (CCW, CW) → ZMK &inc_dec_kp VOLU VOLD
        assert "&inc_dec_kp C_VOL_UP C_VOL_DN &inc_dec_kp PG_UP PG_DN" in keymap

    def test_rgb_bindings_filtered_when_keyboard_no_rgb(self, zmk_gen, corne_model, tmp_path):
        """Régression KFM 2026-05-18 : importer un keymap Vial avec RGB_* dans
        un projet Corne (sans RGB) doit remplacer les `&rgb_ug` par `&none`
        sinon le parser DT plante (header rgb.h absent + symboles non définis)."""
        corne_model.keyboard.use_custom_keymap = True
        corne_model.keyboard.rgb_enabled = False  # Corne sans RGB
        # Keymap avec un binding RGB sur la 1ère touche du lower
        corne_model.keyboard.custom_keymap = {
            "layout": [
                # default
                [["KC_A"] * 6] * 8,
                # lower : RGB_TOG en première position
                [["RGB_TOG", "KC_A", "KC_A", "KC_A", "KC_A", "KC_A"]] + [["KC_A"] * 6] * 7,
            ],
        }
        zmk_gen.generate(corne_model, tmp_path)
        keymap = (tmp_path / "config" / "boards" / "shields" / "corne" / "corne.keymap").read_text()
        # `&rgb_ug` ne doit PAS apparaître dans le keymap final
        assert "&rgb_ug" not in keymap


class TestZmkBluetoothLayer:
    """Layer Bluetooth tri-layer (LOWER + RAISE → BT_SEL / BT_CLR / OUT_*)."""

    def test_keymap_contains_bluetooth_layer(self, zmk_gen, corne_model, tmp_path):
        zmk_gen.generate(corne_model, tmp_path)
        keymap = (tmp_path / "config" / "boards" / "shields" / "corne" / "corne.keymap").read_text()
        assert "bluetooth_layer" in keymap
        assert 'display-name = "Bluetooth"' in keymap

    def test_bluetooth_layer_has_bt_bindings(self, zmk_gen, corne_model, tmp_path):
        zmk_gen.generate(corne_model, tmp_path)
        keymap = (tmp_path / "config" / "boards" / "shields" / "corne" / "corne.keymap").read_text()
        assert "&bt BT_CLR" in keymap
        assert "&bt BT_SEL 0" in keymap
        assert "&bt BT_SEL 4" in keymap
        assert "&out OUT_USB" in keymap
        assert "&out OUT_BLE" in keymap
        assert "&out OUT_TOG" in keymap

    def test_keymap_has_tri_layer_condition(self, zmk_gen, corne_model, tmp_path):
        """LOWER (layer 1) + RAISE (layer 2) → Bluetooth (layer 3)."""
        zmk_gen.generate(corne_model, tmp_path)
        keymap = (tmp_path / "config" / "boards" / "shields" / "corne" / "corne.keymap").read_text()
        assert 'compatible = "zmk,conditional-layers"' in keymap
        assert "if-layers = <1 2>" in keymap
        assert "then-layer = <3>" in keymap

    def test_keymap_always_includes_outputs_header(self, zmk_gen, corne_model, tmp_path):
        """`<dt-bindings/zmk/outputs.h>` est nécessaire pour `&out OUT_*`."""
        zmk_gen.generate(corne_model, tmp_path)
        keymap = (tmp_path / "config" / "boards" / "shields" / "corne" / "corne.keymap").read_text()
        assert "<dt-bindings/zmk/outputs.h>" in keymap

    def test_raise_layer_contains_bt_bindings_duplicated(self, zmk_gen, corne_model, tmp_path):
        """Les touches BT/OUT doivent être dupliquées dans le raise_layer aux
        premières positions `&trans` libres, pour être accessibles sans
        tri-layer (visible dans ZMK Studio)."""
        zmk_gen.generate(corne_model, tmp_path)
        keymap = (tmp_path / "config" / "boards" / "shields" / "corne" / "corne.keymap").read_text()
        # Isoler la section raise_layer
        raise_idx = keymap.index("raise_layer")
        bluetooth_idx = keymap.index("bluetooth_layer")
        raise_section = keymap[raise_idx:bluetooth_idx]
        # Doit contenir au moins BT_CLR, BT_SEL 0, OUT_USB (= début de la liste)
        assert "&bt BT_CLR" in raise_section
        assert "&bt BT_SEL 0" in raise_section
        assert "&out OUT_USB" in raise_section


class TestZmkStudioLocking:
    """ZMK Studio : locking désactivé pour accès USB sans unlock behavior."""

    def test_conf_disables_studio_locking(self, zmk_gen, corne_model, tmp_path):
        zmk_gen.generate(corne_model, tmp_path)
        content = (tmp_path / "config" / "corne.conf").read_text()
        assert "CONFIG_ZMK_STUDIO_LOCKING=n" in content


class TestZmkDebugLogging:
    """Mode debug logging : émet les logs Zephyr/ZMK sur USB CDC ACM."""

    def test_disabled_by_default(self, zmk_gen, corne_model, tmp_path):
        zmk_gen.generate(corne_model, tmp_path)
        conf = (tmp_path / "config" / "corne.conf").read_text()
        assert "CONFIG_LOG=y" not in conf
        assert "CONFIG_USB_CDC_ACM=y" not in conf

    def test_enabled_when_flag_set(self, zmk_gen, corne_model, tmp_path):
        corne_model.keyboard.debug_logging = True
        zmk_gen.generate(corne_model, tmp_path)
        conf = (tmp_path / "config" / "corne.conf").read_text()
        assert "CONFIG_LOG=y" in conf
        assert "CONFIG_LOG_BACKEND_UART=y" in conf
        assert "CONFIG_USB_CDC_ACM=y" in conf
        assert "CONFIG_UART_CONSOLE=y" in conf

    def test_dtsi_includes_cdc_acm_console_for_log_uart(self, zmk_gen, corne_model, tmp_path):
        """`CONFIG_LOG_BACKEND_UART=y` exige un `zephyr,console` dans le DT,
        sinon erreur compile `__device_dts_ord_DT_CHOSEN_zephyr_console_ORD`.
        On route le console vers USB CDC ACM puisque nice_nano n'a pas d'UART
        hardware exposé."""
        corne_model.keyboard.debug_logging = True
        zmk_gen.generate(corne_model, tmp_path)
        dtsi = (tmp_path / "config" / "boards" / "shields" / "corne" / "corne.dtsi").read_text()
        assert "zephyr,console" in dtsi
        assert "zephyr,cdc-acm-uart" in dtsi

    def test_dtsi_reuses_studio_cdc_when_studio_usb(self, zmk_gen, corne_model, tmp_path):
        """Quand studio_transport=usb + debug_logging, on réutilise le node CDC
        ACM du snippet studio-rpc-usb-uart au lieu de redéclarer un node (qui
        causerait un conflit de symbole DT)."""
        corne_model.keyboard.debug_logging = True
        corne_model.keyboard.zmk_studio_transport = "usb"
        zmk_gen.generate(corne_model, tmp_path)
        dtsi = (tmp_path / "config" / "boards" / "shields" / "corne" / "corne.dtsi").read_text()
        # Pas de redéfinition du node CDC ACM, juste assignation chosen
        assert "kfm_debug_console" not in dtsi
        assert "snippet_studio_rpc_usb_uart" in dtsi


class TestZmkDebugDump:
    """kfm_debug_dump.json : snapshot du contexte de génération pour debug post-mortem."""

    def test_dump_file_generated(self, zmk_gen, corne_model, tmp_path):
        zmk_gen.generate(corne_model, tmp_path)
        dump_path = tmp_path / "kfm_debug_dump.json"
        assert dump_path.is_file()

    def test_dump_contains_project_model(self, zmk_gen, corne_model, tmp_path):
        zmk_gen.generate(corne_model, tmp_path)
        import json
        data = json.loads((tmp_path / "kfm_debug_dump.json").read_text())
        assert data["project_model"]["keyboard"]["model"] == "corne"

    def test_dump_contains_kfm_version_and_timestamp(self, zmk_gen, corne_model, tmp_path):
        zmk_gen.generate(corne_model, tmp_path)
        import json
        data = json.loads((tmp_path / "kfm_debug_dump.json").read_text())
        assert "kfm_version" in data
        assert "generated_at" in data
        # ISO-8601 format check (contains 'T' separator)
        assert "T" in data["generated_at"]

    def test_dump_contains_context_flags(self, zmk_gen, corne_model, tmp_path):
        corne_model.keyboard.debug_logging = True
        zmk_gen.generate(corne_model, tmp_path)
        import json
        data = json.loads((tmp_path / "kfm_debug_dump.json").read_text())
        assert data["split"] is True
        assert data["debug_logging"] is True
        assert data["studio_transport"] == "ble"


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


class TestZmkOledCustomScreen:
    """Phase 1 ZMK custom OLED — image-only status screen."""

    @pytest.fixture
    def sofle_with_custom_oled(self):
        from models.project_model import OledImageItem
        m = ProjectModel()
        m.keyboard.model = "sofle-v2"
        m.keyboard.mcu = "nice_nano_v2"
        m.keyboard.oled_sides = ["left"]
        # Image runtime : frame 32×128 toute blanche placée à (0, 0) plein canvas
        white_frame = bytes([0xFF] * (32 * 128))
        img_left = OledImageItem(
            image_path="dummy.png", frames=[white_frame],
            natural_w=32, natural_h=128, col=0, line=0,
        )
        m.oled.left.images.append(img_left)
        return m

    def test_default_keeps_built_in_status_screen(self, zmk_gen, sofle_model, tmp_path):
        """Sans image placée, la conf garde STATUS_SCREEN_BUILT_IN=y (régression)."""
        zmk_gen.generate(sofle_model, tmp_path)
        conf = (tmp_path / "config" / "sofle_v2.conf").read_text()
        assert "CONFIG_ZMK_DISPLAY_STATUS_SCREEN_BUILT_IN=y" in conf
        assert "CONFIG_ZMK_DISPLAY_STATUS_SCREEN_CUSTOM" not in conf

    def test_custom_screen_active_when_image_placed(self, zmk_gen, sofle_with_custom_oled, tmp_path):
        zmk_gen.generate(sofle_with_custom_oled, tmp_path)
        conf = (tmp_path / "config" / "sofle_v2.conf").read_text()
        assert "CONFIG_ZMK_DISPLAY_STATUS_SCREEN_CUSTOM=y" in conf
        assert "CONFIG_ZMK_DISPLAY_STATUS_SCREEN_BUILT_IN" not in conf
        # ZMK active LV_CONF_MINIMAL=y qui désactive le widget image LVGL.
        # On doit forcer LV_USE_IMAGE=y pour disposer de lv_image_create/set_src.
        assert "CONFIG_LV_USE_IMAGE=y" in conf

    def test_use_builtin_screen_forces_builtin_even_with_image(
        self, zmk_gen, sofle_with_custom_oled, tmp_path,
    ):
        """Quand `oled.use_builtin_screen=True`, KFM doit ignorer les images +
        widgets et générer un firmware avec STATUS_SCREEN_BUILT_IN."""
        sofle_with_custom_oled.oled.use_builtin_screen = True
        zmk_gen.generate(sofle_with_custom_oled, tmp_path)
        conf = (tmp_path / "config" / "sofle_v2.conf").read_text()
        assert "CONFIG_ZMK_DISPLAY_STATUS_SCREEN_BUILT_IN=y" in conf
        assert "CONFIG_ZMK_DISPLAY_STATUS_SCREEN_CUSTOM" not in conf
        # status_screen.c ne doit PAS être généré (le canvas est ignoré)
        screen_path = tmp_path / "config" / "boards" / "shields" / "sofle_v2" / "status_screen_left.c"
        assert not screen_path.exists()

    def test_show_battery_percentage_disabled_by_default(self, zmk_gen, sofle_model, tmp_path):
        zmk_gen.generate(sofle_model, tmp_path)
        conf = (tmp_path / "config" / "sofle_v2.conf").read_text()
        assert "CONFIG_ZMK_WIDGET_BATTERY_STATUS_SHOW_PERCENTAGE" not in conf

    def test_show_battery_percentage_enabled_when_flag_set(self, zmk_gen, sofle_model, tmp_path):
        sofle_model.oled.show_battery_percentage = True
        zmk_gen.generate(sofle_model, tmp_path)
        conf = (tmp_path / "config" / "sofle_v2.conf").read_text()
        assert "CONFIG_ZMK_WIDGET_BATTERY_STATUS_SHOW_PERCENTAGE=y" in conf

    def test_status_screen_left_c_generated(self, zmk_gen, sofle_with_custom_oled, tmp_path):
        zmk_gen.generate(sofle_with_custom_oled, tmp_path)
        screen_path = tmp_path / "config" / "boards" / "shields" / "sofle_v2" / "status_screen_left.c"
        assert screen_path.is_file()
        content = screen_path.read_text()
        # LVGL 9 : lv_image_dsc_t / lv_image_create / lv_image_set_src
        # (les alias lv_img_* dans lv_api_map_v8.h ne sont pas inclus par défaut
        # dans les .c générés, donc on écrit la nomenclature v9 native)
        assert "lv_image_dsc_t status_screen_frames[]" in content
        assert "zmk_display_status_screen" in content
        assert "LV_COLOR_FORMAT_I1" in content
        assert "LV_IMAGE_HEADER_MAGIC" in content

    def test_status_screen_right_c_not_generated_without_right_image(
        self, zmk_gen, sofle_with_custom_oled, tmp_path,
    ):
        """Si seul le côté gauche a une image, la moitié droite garde le status screen built-in."""
        zmk_gen.generate(sofle_with_custom_oled, tmp_path)
        right_screen = tmp_path / "config" / "boards" / "shields" / "sofle_v2" / "status_screen_right.c"
        assert not right_screen.exists()

    def test_cmakelists_txt_generated(self, zmk_gen, sofle_with_custom_oled, tmp_path):
        zmk_gen.generate(sofle_with_custom_oled, tmp_path)
        cmake_path = tmp_path / "config" / "boards" / "shields" / "sofle_v2" / "CMakeLists.txt"
        assert cmake_path.is_file()
        content = cmake_path.read_text()
        assert "CONFIG_ZMK_DISPLAY_STATUS_SCREEN_CUSTOM" in content
        assert "status_screen_left.c" in content
        assert "status_screen_right.c" in content  # branche elseif présente même si pas généré

    def test_lvgl_data_size_correct(self, zmk_gen, sofle_with_custom_oled, tmp_path):
        """Le tableau status_screen_img_data doit contenir 520 octets (8 palette + 512 data)."""
        zmk_gen.generate(sofle_with_custom_oled, tmp_path)
        screen_path = tmp_path / "config" / "boards" / "shields" / "sofle_v2" / "status_screen_left.c"
        content = screen_path.read_text()
        # Compte les littéraux 0xNN
        import re
        hex_literals = re.findall(r"0x[0-9A-F]{2}", content)
        # Le data array doit contenir 520 octets ; le reste du fichier (header,
        # palette comments) ne contient pas de 0xNN sauf si on en met dans des commentaires.
        # On teste l'inégalité minimum.
        assert len(hex_literals) >= 520

    def test_image_white_produces_white_data_pattern(self, zmk_gen, sofle_with_custom_oled, tmp_path):
        """Image toute blanche → palette + 512 octets de 0xFF."""
        zmk_gen.generate(sofle_with_custom_oled, tmp_path)
        screen_path = tmp_path / "config" / "boards" / "shields" / "sofle_v2" / "status_screen_left.c"
        content = screen_path.read_text()
        # Doit contenir au moins une suite de plusieurs 0xFF consécutifs
        assert "0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF" in content


class TestZmkOledWidgets:
    """Phase 2 ZMK custom OLED — widgets natifs (battery, output, layer, peripheral)."""

    @pytest.fixture
    def sofle_with_widgets_left(self):
        """Sofle avec battery + output + layer placés sur la moitié gauche (central)."""
        m = ProjectModel()
        m.keyboard.model = "sofle-v2"
        m.keyboard.mcu = "nice_nano_v2"
        m.keyboard.oled_sides = ["left"]
        m.oled.left.zmk_battery.enabled = True
        m.oled.left.zmk_battery.col = 0
        m.oled.left.zmk_battery.line = 0
        m.oled.left.zmk_output.enabled = True
        m.oled.left.zmk_output.col = 1
        m.oled.left.zmk_output.line = 4
        m.oled.left.zmk_layer.enabled = True
        m.oled.left.zmk_layer.col = 2
        m.oled.left.zmk_layer.line = 8
        return m

    @pytest.fixture
    def sofle_with_peripheral_right(self):
        """Sofle avec peripheral_status placé sur la moitié droite."""
        m = ProjectModel()
        m.keyboard.model = "sofle-v2"
        m.keyboard.mcu = "nice_nano_v2"
        m.keyboard.oled_sides = ["left", "right"]
        m.oled.right.zmk_peripheral.enabled = True
        m.oled.right.zmk_peripheral.col = 0
        m.oled.right.zmk_peripheral.line = 0
        m.oled.right.zmk_battery.enabled = True
        return m

    def test_widgets_trigger_custom_screen(self, zmk_gen, sofle_with_widgets_left, tmp_path):
        """Activer un widget (sans image) doit basculer en STATUS_SCREEN_CUSTOM."""
        zmk_gen.generate(sofle_with_widgets_left, tmp_path)
        conf = (tmp_path / "config" / "sofle_v2.conf").read_text()
        assert "CONFIG_ZMK_DISPLAY_STATUS_SCREEN_CUSTOM=y" in conf
        assert "CONFIG_ZMK_DISPLAY_STATUS_SCREEN_BUILT_IN" not in conf

    def test_widget_kconfig_flags_enabled(self, zmk_gen, sofle_with_widgets_left, tmp_path):
        zmk_gen.generate(sofle_with_widgets_left, tmp_path)
        conf = (tmp_path / "config" / "sofle_v2.conf").read_text()
        assert "CONFIG_ZMK_WIDGET_BATTERY_STATUS=y" in conf
        assert "CONFIG_ZMK_WIDGET_OUTPUT_STATUS=y" in conf
        assert "CONFIG_ZMK_WIDGET_LAYER_STATUS=y" in conf

    def test_only_required_widget_kconfig_flags_set(self, zmk_gen, sofle_with_widgets_left, tmp_path):
        """Seuls les widgets placés ont leur Kconfig — peripheral n'est pas placé."""
        zmk_gen.generate(sofle_with_widgets_left, tmp_path)
        conf = (tmp_path / "config" / "sofle_v2.conf").read_text()
        assert "CONFIG_ZMK_WIDGET_PERIPHERAL_STATUS" not in conf

    def test_status_screen_left_includes_widget_headers(self, zmk_gen, sofle_with_widgets_left, tmp_path):
        zmk_gen.generate(sofle_with_widgets_left, tmp_path)
        screen = (tmp_path / "config" / "boards" / "shields" / "sofle_v2" / "status_screen_left.c").read_text()
        assert "<zmk/display/widgets/battery_status.h>" in screen
        assert "<zmk/display/widgets/output_status.h>" in screen
        assert "<zmk/display/widgets/layer_status.h>" in screen

    def test_status_screen_left_calls_init_for_each_widget(self, zmk_gen, sofle_with_widgets_left, tmp_path):
        zmk_gen.generate(sofle_with_widgets_left, tmp_path)
        screen = (tmp_path / "config" / "boards" / "shields" / "sofle_v2" / "status_screen_left.c").read_text()
        assert "zmk_widget_battery_status_init" in screen
        assert "zmk_widget_output_status_init" in screen
        assert "zmk_widget_layer_status_init" in screen
        # set_pos doit aussi être appelé pour chaque widget
        assert screen.count("lv_obj_set_pos") == 3

    def test_widget_calls_guarded_by_kconfig_ifdef(self, zmk_gen, sofle_with_widgets_left, tmp_path):
        """Régression KFM 2026-05-12 : sur la peripheral, certains widgets sont
        désactivés par ZMK (dépendance non satisfaite). Sans #ifdef autour des
        appels d'init, le firmware crashe au boot. Vérifier que chaque appel est
        protégé par son Kconfig correspondant."""
        zmk_gen.generate(sofle_with_widgets_left, tmp_path)
        screen = (tmp_path / "config" / "boards" / "shields" / "sofle_v2" / "status_screen_left.c").read_text()
        assert "#ifdef CONFIG_ZMK_WIDGET_BATTERY_STATUS" in screen
        assert "#ifdef CONFIG_ZMK_WIDGET_OUTPUT_STATUS" in screen
        assert "#ifdef CONFIG_ZMK_WIDGET_LAYER_STATUS" in screen
        # Chaque ifdef doit avoir son endif (couples équilibrés)
        assert screen.count("#ifdef CONFIG_ZMK_WIDGET_") == screen.count("#endif") or \
               screen.count("#ifdef CONFIG_ZMK_WIDGET_") <= screen.count("#endif")

    def test_widget_position_translation(self, zmk_gen, sofle_with_widgets_left, tmp_path):
        """Widget battery à (col=0, line=0) éditeur → LVGL (0, 20) après rotation 90° CW.

        Calcul : lvgl_x = line*8 = 0, lvgl_y = max(0, 32 - col*6 - 12) = 20.
        """
        zmk_gen.generate(sofle_with_widgets_left, tmp_path)
        screen = (tmp_path / "config" / "boards" / "shields" / "sofle_v2" / "status_screen_left.c").read_text()
        # battery widget : col=0, line=0
        assert "lv_obj_set_pos(zmk_widget_battery_status_obj(&battery_widget), 0, 20)" in screen
        # output widget : col=1, line=4 → lvgl (32, max(0, 32-6-12)=14)
        assert "lv_obj_set_pos(zmk_widget_output_status_obj(&output_widget), 32, 14)" in screen
        # layer widget : col=2, line=8 → lvgl (64, max(0, 32-12-12)=8)
        assert "lv_obj_set_pos(zmk_widget_layer_status_obj(&layer_widget), 64, 8)" in screen

    def test_peripheral_widget_only_on_right_half(self, zmk_gen, tmp_path):
        """Peripheral activé sur les deux côtés — il ne doit s'instancier QUE côté droit.

        Côté central (gauche), peripheral_status n'a pas de sens (le central
        relie à plusieurs hôtes BLE, pas à un peripheral identifié pour ce widget).
        """
        m = ProjectModel()
        m.keyboard.model = "sofle-v2"
        m.keyboard.mcu = "nice_nano_v2"
        m.keyboard.oled_sides = ["left", "right"]
        m.oled.left.zmk_peripheral.enabled = True   # devrait être ignoré
        m.oled.left.zmk_battery.enabled = True       # pour générer le screen gauche
        m.oled.right.zmk_peripheral.enabled = True   # accepté
        zmk_gen.generate(m, tmp_path)
        conf = (tmp_path / "config" / "sofle_v2.conf").read_text()
        assert "CONFIG_ZMK_WIDGET_PERIPHERAL_STATUS=y" in conf
        right_screen = (tmp_path / "config" / "boards" / "shields" / "sofle_v2" / "status_screen_right.c").read_text()
        assert "zmk_widget_peripheral_status_init" in right_screen
        # Côté gauche (central) : peripheral activé dans le modèle mais filtré au build
        left_screen = (tmp_path / "config" / "boards" / "shields" / "sofle_v2" / "status_screen_left.c").read_text()
        assert "zmk_widget_peripheral_status_init" not in left_screen

    def test_layer_output_excluded_on_peripheral_side(self, zmk_gen, tmp_path):
        """Layer/output ne doivent pas être instanciés côté peripheral même si l'utilisateur les active.

        Ces widgets dépendent d'événements ZMK central-only (zmk_layer_state_changed,
        zmk_endpoints_changed). Les activer côté peripheral compilerait mais ne mettrait
        jamais à jour.
        """
        m = ProjectModel()
        m.keyboard.model = "sofle-v2"
        m.keyboard.mcu = "nice_nano_v2"
        m.keyboard.oled_sides = ["left", "right"]
        m.oled.right.zmk_layer.enabled = True
        m.oled.right.zmk_output.enabled = True
        m.oled.right.zmk_battery.enabled = True  # pour déclencher custom screen côté droit
        zmk_gen.generate(m, tmp_path)
        right_screen_path = tmp_path / "config" / "boards" / "shields" / "sofle_v2" / "status_screen_right.c"
        right_screen = right_screen_path.read_text()
        assert "zmk_widget_layer_status_init" not in right_screen
        assert "zmk_widget_output_status_init" not in right_screen

    def test_image_plus_widgets_combined(self, zmk_gen, tmp_path):
        """Mix image + widget doit générer les deux côté C."""
        from models.project_model import OledImageItem
        m = ProjectModel()
        m.keyboard.model = "sofle-v2"
        m.keyboard.mcu = "nice_nano_v2"
        m.keyboard.oled_sides = ["left"]
        white = bytes([0xFF] * (32 * 128))
        m.oled.left.images.append(OledImageItem(
            image_path="dummy.png", frames=[white],
            natural_w=32, natural_h=128, col=0, line=0,
        ))
        m.oled.left.zmk_battery.enabled = True
        zmk_gen.generate(m, tmp_path)
        screen = (tmp_path / "config" / "boards" / "shields" / "sofle_v2" / "status_screen_left.c").read_text()
        assert "lv_image_dsc_t status_screen_frames[]" in screen  # image
        assert "zmk_widget_battery_status_init" in screen       # widget
        assert "lv_image_create" in screen                        # bg image instantiation
        assert "lv_image_set_src(bg_img" in screen

    def test_static_image_no_animation_code_emitted(self, zmk_gen, tmp_path):
        """Image statique (1 frame) ne doit PAS générer de K_TIMER ni K_WORK."""
        from models.project_model import OledImageItem
        m = ProjectModel()
        m.keyboard.model = "sofle-v2"
        m.keyboard.mcu = "nice_nano_v2"
        m.keyboard.oled_sides = ["left"]
        white = bytes([0xFF] * (32 * 128))
        m.oled.left.images.append(OledImageItem(
            image_path="dummy.png", frames=[white],
            natural_w=32, natural_h=128, col=0, line=0,
        ))
        zmk_gen.generate(m, tmp_path)
        screen = (tmp_path / "config" / "boards" / "shields" / "sofle_v2" / "status_screen_left.c").read_text()
        assert "K_TIMER_DEFINE" not in screen
        assert "K_WORK_DEFINE" not in screen
        assert "status_screen_anim_timer" not in screen
        # Mais le tableau de frames est généré (même avec 1 seule frame)
        assert "lv_image_dsc_t status_screen_frames[]" in screen

    def test_animated_image_emits_timer_and_work(self, zmk_gen, tmp_path):
        """Image multi-frame → K_TIMER_DEFINE + K_WORK_DEFINE + tableau de delays."""
        from models.project_model import OledImageItem
        m = ProjectModel()
        m.keyboard.model = "sofle-v2"
        m.keyboard.mcu = "nice_nano_v2"
        m.keyboard.oled_sides = ["left"]
        # 3 frames distincts → animation
        f0 = bytes([0x00] * (32 * 128))
        f1 = bytes([0xFF] * (32 * 128))
        f2 = bytes([0x80] * (32 * 128))
        m.oled.left.images.append(OledImageItem(
            image_path="anim.gif", frames=[f0, f1, f2],
            delays=[100, 150, 200],
            natural_w=32, natural_h=128, col=0, line=0,
        ))
        zmk_gen.generate(m, tmp_path)
        screen = (tmp_path / "config" / "boards" / "shields" / "sofle_v2" / "status_screen_left.c").read_text()
        assert "K_TIMER_DEFINE(status_screen_anim_timer" in screen
        assert "K_WORK_DEFINE(status_screen_anim_work" in screen
        assert "status_screen_frame_delays_ms[]" in screen
        # Les délais doivent être présents dans le tableau
        assert "100, 150, 200" in screen
        # Le timer doit être démarré dans zmk_display_status_screen()
        assert "k_timer_start(&status_screen_anim_timer" in screen

    def test_animated_emits_n_frame_arrays(self, zmk_gen, tmp_path):
        """3 frames d'animation → 3 tableaux status_screen_frame_N_data + 3 lv_image_dsc_t."""
        from models.project_model import OledImageItem
        m = ProjectModel()
        m.keyboard.model = "sofle-v2"
        m.keyboard.mcu = "nice_nano_v2"
        m.keyboard.oled_sides = ["left"]
        white = bytes([0xFF] * (32 * 128))
        m.oled.left.images.append(OledImageItem(
            image_path="anim.gif", frames=[white, white, white],
            delays=[100, 100, 100],
            natural_w=32, natural_h=128, col=0, line=0,
        ))
        zmk_gen.generate(m, tmp_path)
        screen = (tmp_path / "config" / "boards" / "shields" / "sofle_v2" / "status_screen_left.c").read_text()
        assert "status_screen_frame_0_data[]" in screen
        assert "status_screen_frame_1_data[]" in screen
        assert "status_screen_frame_2_data[]" in screen
        # 3 entrées dans le tableau lv_image_dsc_t status_screen_frames
        # Chaque entrée référence frame_N_data
        assert screen.count(".data = status_screen_frame_") == 3

    def test_no_layer_aware_uses_phase3_path(self, zmk_gen, tmp_path):
        """Aucune image avec layer != -1 → pas de listener ni d'arrays per-layer."""
        from models.project_model import OledImageItem
        m = ProjectModel()
        m.keyboard.model = "sofle-v2"
        m.keyboard.mcu = "nice_nano_v2"
        m.keyboard.oled_sides = ["left"]
        white = bytes([0xFF] * (32 * 128))
        m.oled.left.images.append(OledImageItem(
            image_path="dummy.png", frames=[white],
            natural_w=32, natural_h=128, col=0, line=0, layer=-1,
        ))
        zmk_gen.generate(m, tmp_path)
        screen = (tmp_path / "config" / "boards" / "shields" / "sofle_v2" / "status_screen_left.c").read_text()
        # Pas de listener / subscription / handler de layer dans le path Phase 3.
        # Note : le commentaire d'en-tête mentionne `zmk_layer_state_changed`,
        # on vérifie donc des symboles concrets, pas la chaîne brute.
        assert "ZMK_LISTENER(status_screen_layer" not in screen
        assert "ZMK_SUBSCRIPTION(status_screen_layer" not in screen
        assert "status_screen_layer_work_handler" not in screen
        assert "<zmk/events/layer_state_changed.h>" not in screen
        # Mais le path Phase 3 standard (status_screen_frames[]) est généré
        assert "lv_image_dsc_t status_screen_frames[]" in screen

    def test_layer_aware_emits_listener_and_per_layer_arrays(self, zmk_gen, tmp_path):
        """Image layer=0 + image layer=-1 (global) → path Phase 4 avec listener."""
        from models.project_model import OledImageItem
        m = ProjectModel()
        m.keyboard.model = "sofle-v2"
        m.keyboard.mcu = "nice_nano_v2"
        m.keyboard.oled_sides = ["left"]
        white = bytes([0xFF] * (32 * 128))
        black = bytes([0x00] * (32 * 128))
        m.oled.left.images.append(OledImageItem(
            image_path="global.png", frames=[white],
            natural_w=32, natural_h=128, col=0, line=0, layer=-1,
        ))
        m.oled.left.images.append(OledImageItem(
            image_path="layer0.png", frames=[black],
            natural_w=32, natural_h=128, col=0, line=0, layer=0,
        ))
        zmk_gen.generate(m, tmp_path)
        screen = (tmp_path / "config" / "boards" / "shields" / "sofle_v2" / "status_screen_left.c").read_text()
        # Path Phase 4 : listener + subscription
        assert "ZMK_LISTENER(status_screen_layer" in screen
        assert "ZMK_SUBSCRIPTION(status_screen_layer, zmk_layer_state_changed)" in screen
        # Per-layer arrays
        assert "status_screen_layer_default_frames[]" in screen
        assert "status_screen_layer_0_frames[]" in screen
        # Switch sur la couche active
        assert "zmk_keymap_highest_layer_active" in screen
        assert "case 0:" in screen
        # Pointeurs globaux
        assert "current_frames" in screen
        assert "current_delays" in screen

    def test_layer_aware_does_not_emit_phase3_arrays(self, zmk_gen, tmp_path):
        """En path Phase 4, les arrays Phase 3 (status_screen_frames) ne doivent PAS être émis."""
        from models.project_model import OledImageItem
        m = ProjectModel()
        m.keyboard.model = "sofle-v2"
        m.keyboard.mcu = "nice_nano_v2"
        m.keyboard.oled_sides = ["left"]
        white = bytes([0xFF] * (32 * 128))
        m.oled.left.images.append(OledImageItem(
            image_path="layer0.png", frames=[white],
            natural_w=32, natural_h=128, col=0, line=0, layer=0,
        ))
        zmk_gen.generate(m, tmp_path)
        screen = (tmp_path / "config" / "boards" / "shields" / "sofle_v2" / "status_screen_left.c").read_text()
        # Pas de symbole Phase 3
        assert "static const lv_image_dsc_t status_screen_frames[]" not in screen
        # Mais le symbole Phase 4 default
        assert "status_screen_layer_default_frames[]" in screen

    def test_layer_aware_handles_animated_per_layer(self, zmk_gen, tmp_path):
        """Image layer=0 multi-frame → tableaux delays_ms[] per-layer + timer."""
        from models.project_model import OledImageItem
        m = ProjectModel()
        m.keyboard.model = "sofle-v2"
        m.keyboard.mcu = "nice_nano_v2"
        m.keyboard.oled_sides = ["left"]
        f0 = bytes([0xFF] * (32 * 128))
        f1 = bytes([0x00] * (32 * 128))
        m.oled.left.images.append(OledImageItem(
            image_path="anim_layer0.gif", frames=[f0, f1],
            delays=[100, 200],
            natural_w=32, natural_h=128, col=0, line=0, layer=0,
        ))
        zmk_gen.generate(m, tmp_path)
        screen = (tmp_path / "config" / "boards" / "shields" / "sofle_v2" / "status_screen_left.c").read_text()
        assert "status_screen_layer_0_delays_ms[]" in screen
        assert "100, 200" in screen
        assert "K_TIMER_DEFINE(status_screen_anim_timer" in screen
        assert "K_WORK_DEFINE(status_screen_anim_work" in screen
        # Le timer doit être restart depuis le handler de layer change
        assert "status_screen_layer_work_handler" in screen

    def test_layer_aware_includes_zmk_event_headers(self, zmk_gen, tmp_path):
        from models.project_model import OledImageItem
        m = ProjectModel()
        m.keyboard.model = "sofle-v2"
        m.keyboard.mcu = "nice_nano_v2"
        m.keyboard.oled_sides = ["left"]
        white = bytes([0xFF] * (32 * 128))
        m.oled.left.images.append(OledImageItem(
            image_path="layer1.png", frames=[white],
            natural_w=32, natural_h=128, col=0, line=0, layer=1,
        ))
        zmk_gen.generate(m, tmp_path)
        screen = (tmp_path / "config" / "boards" / "shields" / "sofle_v2" / "status_screen_left.c").read_text()
        assert "<zmk/event_manager.h>" in screen
        assert "<zmk/events/layer_state_changed.h>" in screen
        assert "<zmk/keymap.h>" in screen

    def test_show_peer_battery_central_only(self, zmk_gen, tmp_path):
        """show_peer=True doit s'appliquer côté central et être ignoré côté peripheral."""
        m = ProjectModel()
        m.keyboard.model = "sofle-v2"
        m.keyboard.mcu = "nice_nano_v2"
        m.keyboard.oled_sides = ["left", "right"]
        m.oled.left.zmk_battery.enabled = True
        m.oled.left.zmk_battery.show_peer = True
        m.oled.right.zmk_battery.enabled = True
        m.oled.right.zmk_battery.show_peer = True  # devrait être ignoré
        # Note : Phase 2 MVP traite show_peer dans le contexte mais n'utilise pas
        # encore de helper init différent — la sémantique sera ajoutée si besoin.
        # Test couvre uniquement la non-régression de génération.
        zmk_gen.generate(m, tmp_path)
        # Les deux fichiers doivent être générés sans crash
        left = tmp_path / "config" / "boards" / "shields" / "sofle_v2" / "status_screen_left.c"
        right = tmp_path / "config" / "boards" / "shields" / "sofle_v2" / "status_screen_right.c"
        assert left.is_file()
        assert right.is_file()
