"""Tests pour modules/hardware/keyboard_loader.py.

Ces tests s'exécutent sans Qt (pur Python).
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from modules.hardware.keyboard_loader import KeyboardDefinition, McuOption, load_all_keyboards, load_keyboard

FIXTURES_DIR = Path(__file__).parent / "fixtures"
_KEYBOARDS_DIR = Path(__file__).parents[3] / "keyboards"


@pytest.fixture(scope="module")
def test_kb() -> KeyboardDefinition:
    """Charge le clavier fixture une seule fois pour tous les tests de TestLoadKeyboard."""
    return load_keyboard(FIXTURES_DIR / "test_keyboard.yaml")


class TestLoadKeyboard:
    def test_loads_model_field(self, test_kb):
        assert test_kb.model == "test-kb"

    def test_loads_display_name(self, test_kb):
        assert test_kb.display_name == "Test Keyboard"

    def test_loads_description(self, test_kb):
        assert "test" in test_kb.description.lower()

    def test_loads_mcu_options(self, test_kb):
        assert len(test_kb.mcu_options) == 2
        assert test_kb.mcu_options[0].id == "test_mcu"
        assert test_kb.mcu_options[0].display_name == "Test MCU"

    def test_loads_capabilities(self, test_kb):
        assert test_kb.capabilities.get("oled") is True
        assert test_kb.capabilities.get("rgb") is False

    def test_returns_keyboard_definition_type(self, test_kb):
        assert isinstance(test_kb, KeyboardDefinition)

    def test_mcu_options_are_mcu_option_type(self, test_kb):
        for mcu in test_kb.mcu_options:
            assert isinstance(mcu, McuOption)

    def test_missing_description_defaults_to_empty(self, tmp_path):
        yaml_content = (
            "model: no-desc\n"
            "display_name: No Description KB\n"
            "mcu_options:\n"
            "  - id: mcu1\n"
            "    display_name: MCU1\n"
            "capabilities:\n"
            "  oled: false\n"
            "  rgb: false\n"
        )
        p = tmp_path / "no-desc.yaml"
        p.write_text(yaml_content, encoding="utf-8")
        kb = load_keyboard(p)
        assert kb.description == ""

    def test_no_qt_import_in_module(self):
        """keyboard_loader doit être pur Python — aucun import Qt."""
        import inspect
        import modules.hardware.keyboard_loader as mod
        source = inspect.getsource(mod)
        assert "PySide6" not in source
        assert "PyQt" not in source

    def test_missing_required_field_raises_key_error(self, tmp_path):
        """M2 — load_keyboard() lève KeyError si 'model' ou 'display_name' est absent."""
        p = tmp_path / "missing-model.yaml"
        p.write_text(
            "display_name: No Model KB\nmcu_options: []\ncapabilities: {}\n",
            encoding="utf-8",
        )
        with pytest.raises(KeyError):
            load_keyboard(p)

    def test_null_mcu_options_treated_as_empty(self, tmp_path):
        """M1/L4 — mcu_options: null (clé présente, valeur None) → liste vide sans crash."""
        p = tmp_path / "null-mcu.yaml"
        p.write_text(
            "model: null-mcu\ndisplay_name: Null MCU KB\nmcu_options:\ncapabilities: {}\n",
            encoding="utf-8",
        )
        kb = load_keyboard(p)
        assert kb.mcu_options == []


class TestLoadAllKeyboards:
    def test_loads_from_directory(self, tmp_path):
        shutil.copy(FIXTURES_DIR / "test_keyboard.yaml", tmp_path / "test-kb.yaml")
        keyboards = load_all_keyboards(tmp_path)
        assert len(keyboards) == 1
        assert keyboards[0].model == "test-kb"

    def test_skips_invalid_but_loads_valid(self, tmp_path):
        shutil.copy(FIXTURES_DIR / "test_keyboard.yaml", tmp_path / "test-kb.yaml")
        (tmp_path / "bad.yaml").write_text("invalid: [unclosed", encoding="utf-8")
        keyboards = load_all_keyboards(tmp_path)
        assert len(keyboards) == 1

    def test_sorted_by_display_name(self, tmp_path):
        yaml_z = "model: z-kb\ndisplay_name: Zebra KB\nmcu_options: []\ncapabilities: {oled: false, rgb: false}\n"
        yaml_a = "model: a-kb\ndisplay_name: Alpha KB\nmcu_options: []\ncapabilities: {oled: false, rgb: false}\n"
        (tmp_path / "z-kb.yaml").write_text(yaml_z, encoding="utf-8")
        (tmp_path / "a-kb.yaml").write_text(yaml_a, encoding="utf-8")
        keyboards = load_all_keyboards(tmp_path)
        assert keyboards[0].display_name == "Alpha KB"
        assert keyboards[1].display_name == "Zebra KB"

    def test_empty_directory_returns_empty_list(self, tmp_path):
        keyboards = load_all_keyboards(tmp_path)
        assert keyboards == []

    def test_loads_real_keyboards_dir(self):
        """Test avec les vrais fichiers YAML du projet."""
        if not _KEYBOARDS_DIR.exists():
            pytest.skip("keyboards/ directory not found")
        keyboards = load_all_keyboards(_KEYBOARDS_DIR)
        assert len(keyboards) >= 3
        display_names = [kb.display_name for kb in keyboards]
        assert "Sofle v2.1 RGB" in display_names


@pytest.mark.skipif(not _KEYBOARDS_DIR.exists(), reason="keyboards/ directory not found")
class TestKeyboardDefinitionMatrix:
    def test_sofle_has_matrix_rows(self):
        kb = load_keyboard(_KEYBOARDS_DIR / "sofle-v2.yaml")
        assert kb.matrix.get("rows") == 5

    def test_sofle_has_matrix_cols(self):
        kb = load_keyboard(_KEYBOARDS_DIR / "sofle-v2.yaml")
        assert kb.matrix.get("cols") == 6

    def test_corne_has_4_rows(self):
        kb = load_keyboard(_KEYBOARDS_DIR / "corne.yaml")
        assert kb.matrix.get("rows") == 4

    def test_matrix_has_default_if_missing(self, tmp_path):
        """YAML sans champ matrix → défaut {"rows": 5, "cols": 6}."""
        p = tmp_path / "no-matrix.yaml"
        p.write_text(
            "model: no-matrix\ndisplay_name: No Matrix KB\n"
            "mcu_options: []\ncapabilities: {}\n",
            encoding="utf-8",
        )
        kb = load_keyboard(p)
        assert kb.matrix["rows"] == 5
        assert kb.matrix["cols"] == 6

    def test_matrix_rows_zero_falls_back_to_default(self, tmp_path):
        """M1 — rows: 0 invalide → défaut 5."""
        p = tmp_path / "zero-rows.yaml"
        p.write_text(
            "model: z\ndisplay_name: Z\nmcu_options: []\ncapabilities: {}\n"
            "matrix:\n  rows: 0\n  cols: 6\n",
            encoding="utf-8",
        )
        kb = load_keyboard(p)
        assert kb.matrix["rows"] == 5
        assert kb.matrix["cols"] == 6

    def test_matrix_cols_negative_falls_back_to_default(self, tmp_path):
        """M1 — cols: -1 invalide → défaut 6."""
        p = tmp_path / "neg-cols.yaml"
        p.write_text(
            "model: n\ndisplay_name: N\nmcu_options: []\ncapabilities: {}\n"
            "matrix:\n  rows: 5\n  cols: -1\n",
            encoding="utf-8",
        )
        kb = load_keyboard(p)
        assert kb.matrix["rows"] == 5
        assert kb.matrix["cols"] == 6
