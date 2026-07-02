"""Tests pour modules/build_manager/template_generator.py."""
from __future__ import annotations

import pytest

from models.project_model import OledConfig, OledImageItem, OledSideConfig, ProjectModel, RgbConfig, RgbEffect
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
        basic_model.oled.left.layer.enabled = True
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

    def test_rules_mk_mousekey_enabled(self, generator, basic_model, tmp_path):
        basic_model.advanced.mousekey_enabled = True
        generator.generate(basic_model, tmp_path)
        content = (tmp_path / "rules.mk").read_text()
        assert "MOUSEKEY_ENABLE = yes" in content

    def test_rules_mk_mousekey_disabled_by_default(self, generator, basic_model, tmp_path):
        generator.generate(basic_model, tmp_path)
        content = (tmp_path / "rules.mk").read_text()
        assert "MOUSEKEY_ENABLE" not in content

    def test_config_h_mousekey_define_gated_on_enable(self, generator, basic_model, tmp_path):
        # Bug #2 : régler un timing sans activer la feature ne doit RIEN émettre.
        basic_model.advanced.mousekey_delay_ms = 5
        generator.generate(basic_model, tmp_path)
        content = (tmp_path / "config.h").read_text()
        assert "MOUSEKEY_DELAY" not in content
        # Une fois la feature activée, le #define apparaît.
        basic_model.advanced.mousekey_enabled = True
        generator.generate(basic_model, tmp_path)
        content = (tmp_path / "config.h").read_text()
        assert "#define MOUSEKEY_DELAY 5" in content

    def test_config_h_contains_keyboard_model(self, generator, basic_model, tmp_path):
        generator.generate(basic_model, tmp_path)
        content = (tmp_path / "config.h").read_text()
        assert "sofle-v2" in content

    def test_config_h_oled_define_128x32(self, generator, basic_model, tmp_path):
        """config.h doit définir OLED_DISPLAY_128X32 (32×128 px)."""
        basic_model.oled.left.layer.enabled = True
        generator.generate(basic_model, tmp_path)
        content = (tmp_path / "config.h").read_text()
        assert "OLED_DISPLAY_128X32" in content
        assert "OLED_DISPLAY_128X64" not in content

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
        # vial.json may be static (copied) or template-generated
        assert "vial.json.j2" in result or "vial.json" in result

    def test_keymap_c_contains_oled_task_when_oled_enabled(self, generator, basic_model, tmp_path):
        basic_model.oled.left.layer.enabled = True
        generator.generate(basic_model, tmp_path)
        content = (tmp_path / "keymaps" / "default" / "keymap.c").read_text()
        assert "oled_task_user" in content

    def test_keymap_c_uses_is_keyboard_left(self, generator, basic_model, tmp_path):
        """keymap.c doit utiliser is_keyboard_left() pour brancher gauche/droite."""
        basic_model.oled.left.layer.enabled = True
        generator.generate(basic_model, tmp_path)
        content = (tmp_path / "keymaps" / "default" / "keymap.c").read_text()
        assert "is_keyboard_left()" in content

    def test_rules_mk_bootloader_rp2040(self, generator, basic_model, tmp_path):
        basic_model.keyboard.mcu = "rp2040"
        generator.generate(basic_model, tmp_path)
        content = (tmp_path / "rules.mk").read_text()
        assert "BOOTLOADER = rp2040" in content

    def test_rules_mk_bootloader_pro_micro(self, generator, basic_model, tmp_path):
        basic_model.keyboard.mcu = "pro_micro"
        generator.generate(basic_model, tmp_path)
        content = (tmp_path / "rules.mk").read_text()
        assert "BOOTLOADER = caterina" in content

    def test_rules_mk_bootloader_elite_c(self, generator, basic_model, tmp_path):
        basic_model.keyboard.mcu = "elite_c"
        generator.generate(basic_model, tmp_path)
        content = (tmp_path / "rules.mk").read_text()
        assert "BOOTLOADER = atmel-dfu" in content

    def test_rules_mk_wpm_enabled_when_left_wpm(self, generator, basic_model, tmp_path):
        """WPM_ENABLE activé si left.wpm.enabled."""
        basic_model.oled.left.wpm.enabled = True
        generator.generate(basic_model, tmp_path)
        content = (tmp_path / "rules.mk").read_text()
        assert "WPM_ENABLE = yes" in content

    def test_rules_mk_wpm_enabled_when_right_wpm(self, generator, basic_model, tmp_path):
        """WPM_ENABLE activé si right.wpm.enabled."""
        basic_model.oled.right.wpm.enabled = True
        generator.generate(basic_model, tmp_path)
        content = (tmp_path / "rules.mk").read_text()
        assert "WPM_ENABLE = yes" in content

    def test_rules_mk_wpm_enabled_when_katawajojo(self, generator, basic_model, tmp_path):
        """WPM_ENABLE activé si katawajojo_enabled (KatawaJojo utilise WPM)."""
        basic_model.oled.left.katawajojo_enabled = True
        generator.generate(basic_model, tmp_path)
        content = (tmp_path / "rules.mk").read_text()
        assert "WPM_ENABLE = yes" in content

    def test_rules_mk_wpm_enabled_when_luna(self, generator, basic_model, tmp_path):
        """WPM_ENABLE activé si luna_enabled (Luna utilise WPM)."""
        basic_model.oled.left.luna_enabled = True
        generator.generate(basic_model, tmp_path)
        content = (tmp_path / "rules.mk").read_text()
        assert "WPM_ENABLE = yes" in content

    def test_rules_mk_wpm_enabled_when_ocean_dream(self, generator, basic_model, tmp_path):
        """WPM_ENABLE activé si ocean_dream_enabled (Ocean Dream utilise WPM)."""
        basic_model.oled.left.ocean_dream_enabled = True
        generator.generate(basic_model, tmp_path)
        content = (tmp_path / "rules.mk").read_text()
        assert "WPM_ENABLE = yes" in content

    def test_rules_mk_wpm_not_enabled_without_wpm_feature(self, generator, basic_model, tmp_path):
        """WPM_ENABLE non activé si aucun overlay WPM ni animation."""
        basic_model.oled.left.layer.enabled = True
        generator.generate(basic_model, tmp_path)
        content = (tmp_path / "rules.mk").read_text()
        assert "WPM_ENABLE = yes" not in content

    def test_oled_multiframe_left_uses_timer(self, generator, basic_model, tmp_path):
        """Multi-frames OLED gauche : frame_idx incrémenté avec timer."""
        img = OledImageItem(image_path="test.png", frames=[b"\xFF" * 4096, b"\x00" * 4096])
        basic_model.oled.left.images = [img]
        generator.generate(basic_model, tmp_path)
        content = (tmp_path / "keymaps" / "default" / "keymap.c").read_text()
        assert "timer_elapsed32" in content
        assert "left_img0_idx" in content
        assert "left_img0_frame0" in content
        assert "left_img0_frame1" in content

    def test_oled_single_frame_no_timer_overflow(self, generator, basic_model, tmp_path):
        """Avec 1 seule frame gauche, pas de timer (juste oled_write_raw_P direct)."""
        img = OledImageItem(image_path="test.png", frames=[b"\xFF" * 4096])
        basic_model.oled.left.images = [img]
        generator.generate(basic_model, tmp_path)
        content = (tmp_path / "keymaps" / "default" / "keymap.c").read_text()
        assert "left_img0_frame0" in content
        assert "left_img0_timer" not in content  # pas de timer pour 1 frame

    def test_left_overlay_positions_in_keymap(self, generator, basic_model, tmp_path):
        """Les positions col/line des overlays gauche sont dans keymap.c."""
        basic_model.oled.left.layer.enabled = True
        basic_model.oled.left.layer.col = 2
        basic_model.oled.left.layer.line = 5
        generator.generate(basic_model, tmp_path)
        content = (tmp_path / "keymaps" / "default" / "keymap.c").read_text()
        assert "oled_set_cursor(2, 5)" in content

    def test_right_overlay_positions_in_keymap(self, generator, basic_model, tmp_path):
        """Les positions col/line des overlays droit sont dans keymap.c."""
        basic_model.oled.right.caps_lock.enabled = True
        basic_model.oled.right.caps_lock.col = 1
        basic_model.oled.right.caps_lock.line = 3
        generator.generate(basic_model, tmp_path)
        content = (tmp_path / "keymaps" / "default" / "keymap.c").read_text()
        assert "oled_set_cursor(1, 3)" in content


class TestImagePosition:
    def test_image_set_cursor_left_nonzero(self, generator, basic_model, tmp_path):
        """oled_write_raw_P utilise toujours oled_set_cursor(0, 0) (plein écran)."""
        img = OledImageItem(image_path="test.png", frames=[b"\xFF" * 4096], col=2, line=4)
        basic_model.oled.left.images = [img]
        generator.generate(basic_model, tmp_path)
        content = (tmp_path / "keymaps" / "default" / "keymap.c").read_text()
        assert "oled_set_cursor(0, 0)" in content

    def test_image_set_cursor_right_nonzero(self, generator, basic_model, tmp_path):
        """oled_write_raw_P utilise toujours oled_set_cursor(0, 0) (plein écran)."""
        img = OledImageItem(image_path="test.png", frames=[b"\xFF" * 4096], col=0, line=6)
        basic_model.oled.right.images = [img]
        generator.generate(basic_model, tmp_path)
        content = (tmp_path / "keymaps" / "default" / "keymap.c").read_text()
        assert "oled_set_cursor(0, 0)" in content

    def test_image_set_cursor_left_zero_zero(self, generator, basic_model, tmp_path):
        """oled_set_cursor(0, 0) présent pour image gauche."""
        img = OledImageItem(image_path="test.png", frames=[b"\xFF" * 4096], col=0, line=0)
        basic_model.oled.left.images = [img]
        generator.generate(basic_model, tmp_path)
        content = (tmp_path / "keymaps" / "default" / "keymap.c").read_text()
        assert "oled_set_cursor(0, 0)" in content


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
        assert ",\n" in result[0]


class TestKatawaJojoTemplate:
    def test_katawajojo_disabled_no_file(self, generator, basic_model, tmp_path):
        """Sans katawajojo_enabled, le fichier katawajojo.c ne doit pas être généré."""
        basic_model.oled.left.katawajojo_enabled = False
        basic_model.oled.right.katawajojo_enabled = False
        generator.generate(basic_model, tmp_path)
        assert not (tmp_path / "keymaps" / "default" / "katawajojo.c").exists()

    def test_katawajojo_enabled_left_generates_file(self, generator, basic_model, tmp_path):
        """Avec left.katawajojo_enabled, keymaps/default/katawajojo.c doit être généré."""
        basic_model.oled.left.katawajojo_enabled = True
        result = generator.generate(basic_model, tmp_path)
        assert (tmp_path / "keymaps" / "default" / "katawajojo.c").is_file()
        assert "katawajojo.c.j2" in result

    def test_katawajojo_enabled_right_generates_file(self, generator, basic_model, tmp_path):
        """Avec right.katawajojo_enabled, keymaps/default/katawajojo.c doit être généré."""
        basic_model.oled.right.katawajojo_enabled = True
        result = generator.generate(basic_model, tmp_path)
        assert (tmp_path / "keymaps" / "default" / "katawajojo.c").is_file()

    def test_katawajojo_c_contains_sprite_data(self, generator, basic_model, tmp_path):
        """katawajojo.c doit contenir les tableaux PROGMEM."""
        basic_model.oled.left.katawajojo_enabled = True
        generator.generate(basic_model, tmp_path)
        content = (tmp_path / "keymaps" / "default" / "katawajojo.c").read_text()
        assert "katawajojo_sit" in content
        assert "katawajojo_walk" in content
        assert "katawajojo_run" in content
        assert "PROGMEM" in content
        assert "render_katawajojo" in content

    def test_katawajojo_keymap_includes_file(self, generator, basic_model, tmp_path):
        """keymap.c doit inclure katawajojo.c quand katawajojo_enabled."""
        basic_model.oled.left.katawajojo_enabled = True
        generator.generate(basic_model, tmp_path)
        content = (tmp_path / "keymaps" / "default" / "keymap.c").read_text()
        assert '#include "katawajojo.c"' in content

    def test_katawajojo_keymap_calls_render(self, generator, basic_model, tmp_path):
        """keymap.c appelle render_katawajojo(line)."""
        basic_model.oled.left.katawajojo_enabled = True
        basic_model.oled.left.katawajojo_line = 13
        generator.generate(basic_model, tmp_path)
        content = (tmp_path / "keymaps" / "default" / "keymap.c").read_text()
        assert "render_katawajojo(13)" in content

    def test_katawajojo_disabled_keymap_no_render(self, generator, basic_model, tmp_path):
        """Sans katawajojo_enabled, keymap.c ne doit pas appeler render_katawajojo()."""
        basic_model.oled.left.katawajojo_enabled = False
        basic_model.oled.right.katawajojo_enabled = False
        generator.generate(basic_model, tmp_path)
        content = (tmp_path / "keymaps" / "default" / "keymap.c").read_text()
        assert "render_katawajojo" not in content

    def test_katawajojo_enables_oled(self, generator, basic_model, tmp_path):
        """katawajojo_enabled seul doit activer l'OLED."""
        basic_model.oled.left.katawajojo_enabled = True
        generator.generate(basic_model, tmp_path)
        content = (tmp_path / "rules.mk").read_text()
        assert "OLED_ENABLE = yes" in content


class TestNewLunaTemplate:
    def test_luna_disabled_no_luna_c(self, generator, basic_model, tmp_path):
        """Sans luna_enabled, le fichier luna.c ne doit pas être généré."""
        basic_model.oled.left.luna_enabled = False
        basic_model.oled.right.luna_enabled = False
        generator.generate(basic_model, tmp_path)
        assert not (tmp_path / "keymaps" / "default" / "luna.c").exists()

    def test_luna_enabled_left_generates_luna_c(self, generator, basic_model, tmp_path):
        """Avec left.luna_enabled, keymaps/default/luna.c doit être généré."""
        basic_model.oled.left.luna_enabled = True
        result = generator.generate(basic_model, tmp_path)
        assert (tmp_path / "keymaps" / "default" / "luna.c").is_file()
        assert "luna.c.j2" in result

    def test_luna_enabled_right_generates_luna_c(self, generator, basic_model, tmp_path):
        """Avec right.luna_enabled, keymaps/default/luna.c doit être généré."""
        basic_model.oled.right.luna_enabled = True
        result = generator.generate(basic_model, tmp_path)
        assert (tmp_path / "keymaps" / "default" / "luna.c").is_file()

    def test_luna_c_contains_sprite_data(self, generator, basic_model, tmp_path):
        """luna.c doit contenir les tableaux PROGMEM."""
        basic_model.oled.left.luna_enabled = True
        generator.generate(basic_model, tmp_path)
        content = (tmp_path / "keymaps" / "default" / "luna.c").read_text()
        assert "luna_sit" in content
        assert "luna_walk" in content
        assert "luna_run" in content
        assert "PROGMEM" in content
        assert "render_luna" in content

    def test_luna_keymap_includes_luna_c(self, generator, basic_model, tmp_path):
        """keymap.c doit inclure luna.c quand luna_enabled."""
        basic_model.oled.left.luna_enabled = True
        generator.generate(basic_model, tmp_path)
        content = (tmp_path / "keymaps" / "default" / "keymap.c").read_text()
        assert '#include "luna.c"' in content

    def test_luna_keymap_calls_render_luna(self, generator, basic_model, tmp_path):
        """keymap.c appelle render_luna(line)."""
        basic_model.oled.left.luna_enabled = True
        basic_model.oled.left.luna_line = 13
        generator.generate(basic_model, tmp_path)
        content = (tmp_path / "keymaps" / "default" / "keymap.c").read_text()
        assert "render_luna(13)" in content

    def test_luna_disabled_keymap_no_render_luna(self, generator, basic_model, tmp_path):
        """Sans luna_enabled, keymap.c ne doit pas appeler render_luna()."""
        basic_model.oled.left.luna_enabled = False
        basic_model.oled.right.luna_enabled = False
        generator.generate(basic_model, tmp_path)
        content = (tmp_path / "keymaps" / "default" / "keymap.c").read_text()
        assert "render_luna" not in content

    def test_luna_enables_oled(self, generator, basic_model, tmp_path):
        """luna_enabled seul doit activer l'OLED."""
        basic_model.oled.left.luna_enabled = True
        generator.generate(basic_model, tmp_path)
        content = (tmp_path / "rules.mk").read_text()
        assert "OLED_ENABLE = yes" in content


class TestOceanDreamTemplate:
    def test_ocean_dream_disabled_no_file(self, generator, basic_model, tmp_path):
        """Sans ocean_dream_enabled, ocean_dream.c ne doit pas être généré."""
        generator.generate(basic_model, tmp_path)
        assert not (tmp_path / "keymaps" / "default" / "ocean_dream.c").exists()

    def test_ocean_dream_enabled_left_generates_file(self, generator, basic_model, tmp_path):
        """Avec left.ocean_dream_enabled, ocean_dream.c doit être généré."""
        basic_model.oled.left.ocean_dream_enabled = True
        result = generator.generate(basic_model, tmp_path)
        assert (tmp_path / "keymaps" / "default" / "ocean_dream.c").is_file()
        assert "ocean_dream.c.j2" in result

    def test_ocean_dream_enabled_right_generates_file(self, generator, basic_model, tmp_path):
        """Avec right.ocean_dream_enabled, ocean_dream.c doit être généré."""
        basic_model.oled.right.ocean_dream_enabled = True
        result = generator.generate(basic_model, tmp_path)
        assert (tmp_path / "keymaps" / "default" / "ocean_dream.c").is_file()

    def test_ocean_dream_c_contains_render_function(self, generator, basic_model, tmp_path):
        """ocean_dream.c doit contenir render_ocean_dream."""
        basic_model.oled.left.ocean_dream_enabled = True
        generator.generate(basic_model, tmp_path)
        content = (tmp_path / "keymaps" / "default" / "ocean_dream.c").read_text()
        assert "render_ocean_dream" in content

    def test_ocean_dream_keymap_includes_file(self, generator, basic_model, tmp_path):
        """keymap.c doit inclure ocean_dream.c quand ocean_dream_enabled."""
        basic_model.oled.left.ocean_dream_enabled = True
        generator.generate(basic_model, tmp_path)
        content = (tmp_path / "keymaps" / "default" / "keymap.c").read_text()
        assert '#include "ocean_dream.c"' in content

    def test_ocean_dream_keymap_calls_render(self, generator, basic_model, tmp_path):
        """keymap.c appelle render_ocean_dream() (pas de paramètre line)."""
        basic_model.oled.left.ocean_dream_enabled = True
        generator.generate(basic_model, tmp_path)
        content = (tmp_path / "keymaps" / "default" / "keymap.c").read_text()
        assert "render_ocean_dream()" in content

    def test_ocean_dream_disabled_keymap_no_render(self, generator, basic_model, tmp_path):
        """Sans ocean_dream_enabled, keymap.c ne doit pas appeler render_ocean_dream()."""
        generator.generate(basic_model, tmp_path)
        content = (tmp_path / "keymaps" / "default" / "keymap.c").read_text()
        assert "render_ocean_dream" not in content

    def test_ocean_dream_enables_oled(self, generator, basic_model, tmp_path):
        """ocean_dream_enabled seul doit activer l'OLED."""
        basic_model.oled.right.ocean_dream_enabled = True
        generator.generate(basic_model, tmp_path)
        content = (tmp_path / "rules.mk").read_text()
        assert "OLED_ENABLE = yes" in content


class TestBongoCatTemplate:
    def test_bongo_disabled_no_bongocat_c(self, generator, basic_model, tmp_path):
        """Sans bongo_enabled, bongocat.c ne doit pas être généré."""
        basic_model.oled.left.bongo_enabled = False
        basic_model.oled.right.bongo_enabled = False
        generator.generate(basic_model, tmp_path)
        assert not (tmp_path / "keymaps" / "default" / "bongocat.c").exists()
        assert not (tmp_path / "keymaps" / "default" / "bongocat.h").exists()

    def test_bongo_enabled_left_generates_bongocat_files(self, generator, basic_model, tmp_path):
        """Avec left.bongo_enabled, bongocat.c et bongocat.h doivent être générés."""
        basic_model.oled.left.bongo_enabled = True
        result = generator.generate(basic_model, tmp_path)
        assert (tmp_path / "keymaps" / "default" / "bongocat.c").is_file()
        assert (tmp_path / "keymaps" / "default" / "bongocat.h").is_file()
        assert "bongocat.c.j2" in result
        assert "bongocat.h.j2" in result

    def test_bongo_enabled_right_generates_bongocat_files(self, generator, basic_model, tmp_path):
        """Avec right.bongo_enabled, bongocat.c et bongocat.h doivent être générés."""
        basic_model.oled.right.bongo_enabled = True
        generator.generate(basic_model, tmp_path)
        assert (tmp_path / "keymaps" / "default" / "bongocat.c").is_file()
        assert (tmp_path / "keymaps" / "default" / "bongocat.h").is_file()

    def test_bongo_keymap_includes_bongocat_c(self, generator, basic_model, tmp_path):
        """keymap.c doit inclure bongocat.c quand bongo_enabled."""
        basic_model.oled.left.bongo_enabled = True
        generator.generate(basic_model, tmp_path)
        content = (tmp_path / "keymaps" / "default" / "keymap.c").read_text()
        assert '#include "bongocat.c"' in content

    def test_bongo_keymap_calls_render_anim_bongocat(self, generator, basic_model, tmp_path):
        """keymap.c appelle render_anim_bongocat() avec oled_set_cursor quand bongo_enabled."""
        basic_model.oled.left.bongo_enabled = True
        basic_model.oled.left.bongo_line = 4
        generator.generate(basic_model, tmp_path)
        content = (tmp_path / "keymaps" / "default" / "keymap.c").read_text()
        assert "render_anim_bongocat()" in content
        assert "oled_set_cursor(0, 4)" in content

    def test_bongo_disabled_keymap_no_render_anim(self, generator, basic_model, tmp_path):
        """Sans bongo_enabled, keymap.c ne doit pas appeler render_anim_bongocat()."""
        basic_model.oled.left.bongo_enabled = False
        basic_model.oled.right.bongo_enabled = False
        generator.generate(basic_model, tmp_path)
        content = (tmp_path / "keymaps" / "default" / "keymap.c").read_text()
        assert "render_anim_bongocat" not in content

    def test_bongo_enables_oled(self, generator, basic_model, tmp_path):
        """bongo_enabled seul doit activer l'OLED."""
        basic_model.oled.right.bongo_enabled = True
        generator.generate(basic_model, tmp_path)
        content = (tmp_path / "rules.mk").read_text()
        assert "OLED_ENABLE = yes" in content

    def test_bongo_enables_wpm(self, generator, basic_model, tmp_path):
        """bongo_enabled doit activer WPM_ENABLE (l'animation réagit au WPM)."""
        basic_model.oled.left.bongo_enabled = True
        generator.generate(basic_model, tmp_path)
        content = (tmp_path / "rules.mk").read_text()
        assert "WPM_ENABLE = yes" in content

    def test_bongocat_c_contains_render_function(self, generator, basic_model, tmp_path):
        """bongocat.c doit contenir render_anim_bongocat."""
        basic_model.oled.left.bongo_enabled = True
        generator.generate(basic_model, tmp_path)
        content = (tmp_path / "keymaps" / "default" / "bongocat.c").read_text()
        assert "render_anim_bongocat" in content
        assert "PROGMEM" in content




class TestImageInversion:
    def test_inverted_frames_xor_ff(self):
        """_invert_frames doit XOR les pixels de contenu avec 0xFF, fond intact."""
        from modules.build_manager.template_generator import _invert_frames
        # Full 32×128 frame: nat_w=32, nat_h=128 → tout inversé
        frame = bytes([0x00, 0xFF, 0xAB] + [0x00] * (32 * 128 - 3))
        result = _invert_frames([frame], nat_w=32, nat_h=128)
        assert result[0][0] == 0xFF
        assert result[0][1] == 0x00
        assert result[0][2] == 0x54
        # Bounded: nat_w=4, nat_h=1, crop_x=(32-4)//2=14 → only cols 14..17 of row 0 inverted
        frame2 = bytes([0x00] * (32 * 128))
        result2 = _invert_frames([frame2], nat_w=4, nat_h=1)
        # Cols 14-17 of row 0 should be 0xFF, rest 0x00
        assert result2[0][14] == 0xFF
        assert result2[0][17] == 0xFF
        assert result2[0][13] == 0x00
        assert result2[0][18] == 0x00
        assert result2[0][32] == 0x00  # row 1 untouched

    def test_inverted_frames_encoded_in_keymap(self, generator, basic_model, tmp_path):
        """Avec inverted=True, les frames encodées doivent être inversées (XOR 0xFF)."""
        img = OledImageItem(image_path="test.png", frames=[bytes([0x00] * 4096)], inverted=True)
        basic_model.oled.left.images = [img]
        generator.generate(basic_model, tmp_path)
        content = (tmp_path / "keymaps" / "default" / "keymap.c").read_text()
        # 0x00 inversé → pixels blancs → frame_to_qmk_bytes produit 0xFF
        assert "0xFF" in content

    def test_non_inverted_frames_not_changed(self, generator, basic_model, tmp_path):
        """Sans inverted, les frames doivent rester telles quelles."""
        img = OledImageItem(image_path="test.png", frames=[bytes([0x00] * 4096)], inverted=False)
        basic_model.oled.left.images = [img]
        generator.generate(basic_model, tmp_path)
        content = (tmp_path / "keymaps" / "default" / "keymap.c").read_text()
        assert "0x00" in content


class TestTimelineEffectBrightnessScaling:
    """Les effets custom doivent respecter la luminosité utilisateur.

    Bug 2026-07-02 : les couleurs brutes (255) envoyées à rgb_matrix_set_color
    contournaient RGB_MATRIX_MAXIMUM_BRIGHTNESS et les touches RGB_VAI/VAD.
    Une vague multi-rangées à pleine puissance dépassait le budget courant
    USB → chute du rail 5V → firmware gelé en pleine animation.
    """

    def _model_with_wave_effect(self) -> ProjectModel:
        from models.project_model import CustomEffect, EffectStep, EffectTrack, KeyOffset

        m = ProjectModel()
        m.keyboard.model = "sofle-v2"
        m.keyboard.mcu = "rp2040"
        m.rgb.custom_effects = [CustomEffect(
            name="Vague nettoyage",
            effect_type="reactive",
            tracks=[EffectTrack(
                name="Rangée -1",
                target_mode="relative",
                keys_offset=[KeyOffset(dr=-1, dc=0)],
                steps=[EffectStep(time_ms=200, color="#FFFFFF",
                                  hold_ms=100, fade_ms=400, color_to="#000000")],
            )],
        )]
        return m

    def test_set_color_scaled_by_current_brightness(self, generator, tmp_path):
        generator.generate(self._model_with_wave_effect(), tmp_path)
        inc = (tmp_path / "keymaps" / "default" / "rgb_matrix_user.inc").read_text()
        assert "rgb_matrix_config.hsv.v" in inc
        # Plus aucun envoi de couleur brute non mise à l'échelle
        assert "rgb_matrix_set_color(i, _r, _g, _b);" not in inc
        assert "(uint16_t)_r * _v / 255" in inc

    def test_config_h_still_caps_max_brightness(self, generator, tmp_path):
        model = self._model_with_wave_effect()
        model.rgb.effects = [RgbEffect(type="static")]
        generator.generate(model, tmp_path)
        config = (tmp_path / "config.h").read_text()
        assert "#define RGB_MATRIX_MAXIMUM_BRIGHTNESS 200" in config
