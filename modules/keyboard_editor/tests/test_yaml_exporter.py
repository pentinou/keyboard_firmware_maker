"""Tests pour yaml_exporter — export YAML round-trip, pur Python sans Qt."""
import pytest

from modules.hardware.keyboard_loader import (
    KeyboardDefinition,
    KeyLayout,
    McuOption,
    McuPins,
    OledHardwareConfig,
    RgbHardwareConfig,
    load_keyboard,
)
from modules.keyboard_editor.yaml_exporter import export_keyboard


def _minimal_mcu() -> McuOption:
    return McuOption(
        id="test_mcu",
        display_name="Test MCU",
        description="MCU de test",
        bootloader="rp2040",
        pins=McuPins(
            matrix_rows=["GP0", "GP1"],
            matrix_cols=["GP2", "GP3", "GP4"],
        ),
    )


def _make_nonsplit_kd() -> KeyboardDefinition:
    return KeyboardDefinition(
        model="my-custom",
        display_name="My Custom",
        description="Test keyboard",
        split=False,
        mcu_options=[_minimal_mcu()],
        capabilities={"oled": False, "rgb": False},
        layout={
            "keys": [
                KeyLayout(row=0, col=0, x=0.0, y=0.0),
                KeyLayout(row=0, col=1, x=1.0, y=0.0),
                KeyLayout(row=1, col=0, x=0.0, y=1.0),
                KeyLayout(row=1, col=1, x=1.0, y=1.0, w=2.0),
            ]
        },
    )


def _make_split_kd() -> KeyboardDefinition:
    return KeyboardDefinition(
        model="my-split",
        display_name="My Split",
        description="Split test keyboard",
        split=True,
        mcu_options=[_minimal_mcu()],
        capabilities={"oled": False, "rgb": False},
        layout={
            "left": [
                KeyLayout(row=0, col=0, x=0.0, y=0.0),
                KeyLayout(row=0, col=1, x=1.0, y=0.0),
            ],
            "right": [
                KeyLayout(row=0, col=0, x=0.0, y=0.0),
                KeyLayout(row=0, col=1, x=1.0, y=0.0),
            ],
        },
    )


def test_export_roundtrip_nonsplit(tmp_path):
    """Round-trip export/reload préserve les champs clés (non-split)."""
    kd = _make_nonsplit_kd()
    dest = tmp_path / "my-custom.yaml"
    export_keyboard(kd, dest)

    assert dest.exists()
    reloaded = load_keyboard(dest)

    assert reloaded.model == "my-custom"
    assert reloaded.display_name == "My Custom"
    assert reloaded.split is False
    assert len(reloaded.layout.get("keys", [])) == 4
    assert reloaded.layout["keys"][3].w == 2.0
    assert reloaded.matrix["rows"] == 2
    assert reloaded.matrix["cols"] == 2
    assert reloaded.mcu_options[0].id == "test_mcu"
    assert reloaded.mcu_options[0].bootloader == "rp2040"
    assert reloaded.mcu_options[0].pins.matrix_rows == ["GP0", "GP1"]


def test_export_roundtrip_split(tmp_path):
    """Round-trip export/reload préserve layout left/right (split)."""
    kd = _make_split_kd()
    dest = tmp_path / "my-split.yaml"
    export_keyboard(kd, dest)

    reloaded = load_keyboard(dest)

    assert reloaded.split is True
    assert len(reloaded.layout.get("left", [])) == 2
    assert len(reloaded.layout.get("right", [])) == 2
    assert reloaded.layout.get("keys", []) == []


def test_export_invalid_model_empty(tmp_path):
    """ValueError levée si model est vide."""
    kd = _make_nonsplit_kd()
    kd.model = ""
    with pytest.raises(ValueError, match="model invalide"):
        export_keyboard(kd, tmp_path / "bad.yaml")


def test_export_invalid_model_uppercase(tmp_path):
    """ValueError levée si model contient des majuscules."""
    kd = _make_nonsplit_kd()
    kd.model = "MyKeyboard"
    with pytest.raises(ValueError, match="model invalide"):
        export_keyboard(kd, tmp_path / "bad.yaml")


def test_export_invalid_model_spaces(tmp_path):
    """ValueError levée si model contient des espaces."""
    kd = _make_nonsplit_kd()
    kd.model = "my keyboard"
    with pytest.raises(ValueError, match="model invalide"):
        export_keyboard(kd, tmp_path / "bad.yaml")


def test_export_with_capabilities(tmp_path):
    """OLED et RGB exportés correctement si activés."""
    kd = _make_nonsplit_kd()
    kd.capabilities = {"oled": True, "rgb": True}
    kd.oled_hw = OledHardwareConfig(driver="ssd1306", rotation=270, display="128X32")
    kd.rgb_hw = RgbHardwareConfig(max_brightness=150)
    dest = tmp_path / "caps.yaml"
    export_keyboard(kd, dest)

    reloaded = load_keyboard(dest)
    assert reloaded.capabilities.get("oled") is True
    assert reloaded.capabilities.get("rgb") is True
    assert reloaded.oled_hw.driver == "ssd1306"
    assert reloaded.rgb_hw.max_brightness == 150


def test_export_matrix_computed(tmp_path):
    """matrix.rows et matrix.cols calculés depuis les positions de touches."""
    kd = _make_nonsplit_kd()
    dest = tmp_path / "matrix.yaml"
    export_keyboard(kd, dest)

    reloaded = load_keyboard(dest)
    # rows: max row=1 → rows=2 ; cols: max col=1 → cols=2
    assert reloaded.matrix["rows"] == 2
    assert reloaded.matrix["cols"] == 2


def test_export_creates_parent_dir(tmp_path):
    """export_keyboard crée le répertoire parent si absent."""
    kd = _make_nonsplit_kd()
    nested = tmp_path / "a" / "b" / "c" / "my-custom.yaml"
    export_keyboard(kd, nested)
    assert nested.exists()


def test_export_yaml_flow_style_keys(tmp_path):
    """Les touches sont exportées en style flow {row: x, col: y, ...}."""
    kd = _make_nonsplit_kd()
    dest = tmp_path / "flow.yaml"
    export_keyboard(kd, dest)

    content = dest.read_text(encoding="utf-8")
    # Les touches doivent être sur une seule ligne avec accolades
    assert "{row: 0, col: 0, x: 0.0, y: 0.0}" in content
