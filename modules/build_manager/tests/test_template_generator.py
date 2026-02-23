"""Tests pour modules/build_manager/template_generator.py."""
from __future__ import annotations

import pytest

from models.project_model import OledConfig, ProjectModel, RgbConfig, RgbEffect
from modules.build_manager.template_generator import TemplateGenerator, _encode_oled_frames


@pytest.fixture
def generator(tmp_path):
    """TemplateGenerator pointant sur les vrais templates du projet."""
    from pathlib import Path
    templates_dir = Path(__file__).parent.parent.parent.parent / "templates"
    return TemplateGenerator(templates_dir=templates_dir)


@pytest.fixture
def basic_model():
    m = ProjectModel()
    m.keyboard.model = "sofle-v2"
    m.keyboard.mcu = "rp2040"
    return m


class TestTemplateGeneratorGenerate:
    def test_generate_creates_keymap_c(self, generator, basic_model, tmp_path):
        result = generator.generate(basic_model, tmp_path)
        assert (tmp_path / "keymaps" / "default" / "keymap.c").is_file()

    def test_generate_creates_config_h(self, generator, basic_model, tmp_path):
        generator.generate(basic_model, tmp_path)
        assert (tmp_path / "config.h").is_file()

    def test_generate_creates_rules_mk(self, generator, basic_model, tmp_path):
        generator.generate(basic_model, tmp_path)
        assert (tmp_path / "rules.mk").is_file()

    def test_generate_creates_vial_json(self, generator, basic_model, tmp_path):
        generator.generate(basic_model, tmp_path)
        assert (tmp_path / "keymaps" / "default" / "vial.json").is_file()

    def test_rules_mk_contains_mcu(self, generator, basic_model, tmp_path):
        generator.generate(basic_model, tmp_path)
        content = (tmp_path / "rules.mk").read_text()
        assert "RP2040" in content or "rp2040" in content.lower()

    def test_rules_mk_oled_enabled(self, generator, basic_model, tmp_path):
        basic_model.oled.overlays = ["layer"]
        generator.generate(basic_model, tmp_path)
        content = (tmp_path / "rules.mk").read_text()
        assert "OLED_ENABLE = yes" in content

    def test_rules_mk_rgb_enabled(self, generator, basic_model, tmp_path):
        basic_model.rgb.effects = [RgbEffect(type="static")]
        generator.generate(basic_model, tmp_path)
        content = (tmp_path / "rules.mk").read_text()
        assert "RGB_MATRIX_ENABLE = yes" in content

    def test_rules_mk_oled_not_enabled_by_default(self, generator, basic_model, tmp_path):
        generator.generate(basic_model, tmp_path)
        content = (tmp_path / "rules.mk").read_text()
        assert "OLED_ENABLE = yes" not in content

    def test_config_h_contains_keyboard_model(self, generator, basic_model, tmp_path):
        generator.generate(basic_model, tmp_path)
        content = (tmp_path / "config.h").read_text()
        assert "sofle-v2" in content

    def test_vial_json_is_valid_json(self, generator, basic_model, tmp_path):
        import json
        generator.generate(basic_model, tmp_path)
        content = (tmp_path / "keymaps" / "default" / "vial.json").read_text()
        data = json.loads(content)
        assert "matrix" in data
        assert "layouts" in data

    def test_generate_returns_dict_with_all_templates(self, generator, basic_model, tmp_path):
        result = generator.generate(basic_model, tmp_path)
        assert "keymap.c.j2" in result
        assert "config.h.j2" in result
        assert "rules.mk.j2" in result
        assert "vial.json.j2" in result

    def test_keymap_c_contains_oled_task_when_oled_enabled(self, generator, basic_model, tmp_path):
        basic_model.oled.overlays = ["layer"]
        generator.generate(basic_model, tmp_path)
        content = (tmp_path / "keymaps" / "default" / "keymap.c").read_text()
        assert "oled_task_user" in content

    def test_rules_mk_bootloader_rp2040(self, generator, basic_model, tmp_path):
        """M1 — MCU rp2040 → BOOTLOADER = rp2040."""
        basic_model.keyboard.mcu = "rp2040"
        generator.generate(basic_model, tmp_path)
        content = (tmp_path / "rules.mk").read_text()
        assert "BOOTLOADER = rp2040" in content

    def test_rules_mk_bootloader_pro_micro(self, generator, basic_model, tmp_path):
        """M1 — MCU pro_micro → BOOTLOADER = caterina."""
        basic_model.keyboard.mcu = "pro_micro"
        generator.generate(basic_model, tmp_path)
        content = (tmp_path / "rules.mk").read_text()
        assert "BOOTLOADER = caterina" in content

    def test_rules_mk_bootloader_elite_c(self, generator, basic_model, tmp_path):
        """M1 — MCU elite_c → BOOTLOADER = atmel-dfu."""
        basic_model.keyboard.mcu = "elite_c"
        generator.generate(basic_model, tmp_path)
        content = (tmp_path / "rules.mk").read_text()
        assert "BOOTLOADER = atmel-dfu" in content

    def test_oled_multiframe_uses_timer_not_hardcoded_index(self, generator, basic_model, tmp_path):
        """M3 — multi-frames OLED : frame_idx incrémenté avec timer, pas hardcodé à 0."""
        # oled_enabled requiert image_path ou overlays
        basic_model.oled.image_path = "test.png"
        basic_model.oled.frames = [b"\xFF" * 16, b"\x00" * 16]
        generator.generate(basic_model, tmp_path)
        content = (tmp_path / "keymaps" / "default" / "keymap.c").read_text()
        assert "timer_elapsed32" in content
        assert "frame_idx" in content
        # Les deux frames doivent être référencées
        assert "oled_frame_0" in content
        assert "oled_frame_1" in content

    def test_oled_single_frame_no_timer_overflow(self, generator, basic_model, tmp_path):
        """Avec 1 seule frame, le modulo doit être % 1."""
        basic_model.oled.image_path = "test.png"
        basic_model.oled.frames = [b"\xFF" * 16]
        generator.generate(basic_model, tmp_path)
        content = (tmp_path / "keymaps" / "default" / "keymap.c").read_text()
        assert "% 1" in content  # frame_idx = (frame_idx + 1) % 1


class TestEncodeOledFrames:
    def test_empty_frames(self):
        assert _encode_oled_frames([]) == []

    def test_single_byte_frame(self):
        result = _encode_oled_frames([b"\xFF"])
        assert len(result) == 1
        assert "0xFF" in result[0]

    def test_multiple_bytes_frame(self):
        result = _encode_oled_frames([b"\x00\xFF\xAB"])
        assert "0x00" in result[0]
        assert "0xFF" in result[0]
        assert "0xAB" in result[0]

    def test_row_break_every_16_bytes(self):
        data = bytes(range(32))  # 32 bytes → 2 rows of 16
        result = _encode_oled_frames([data])
        assert len(result) == 1
        # Should have a newline-based separator between row 0 and row 1
        assert ",\n" in result[0]
