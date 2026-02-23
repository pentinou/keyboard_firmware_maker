"""Tests for ProjectModel — sérialisation/désérialisation JSON."""
from models.project_model import (
    BuildConfig,
    KeyboardConfig,
    OledConfig,
    ProjectModel,
    RgbConfig,
    RgbEffect,
)


def test_project_model_defaults():
    """ProjectModel doit avoir des valeurs par défaut vides."""
    model = ProjectModel()
    assert model.version == "1.0"
    assert model.keyboard.model == ""
    assert model.keyboard.mcu == ""
    assert model.oled.image_path == ""
    assert model.oled.overlays == []
    assert model.oled.frames == []
    assert model.rgb.effects == []
    assert model.rgb.per_key == {}
    assert model.build.vial_qmk_version == ""


def test_project_model_serialization():
    """to_dict() doit produire un dict JSON valide avec clés snake_case."""
    model = ProjectModel()
    model.keyboard.model = "sofle-v2"
    model.keyboard.mcu = "rp2040"
    model.oled.image_path = "/abs/path/test.gif"
    model.oled.overlays = ["layer", "wpm"]
    model.rgb.per_key = {"KEY_A": "#FF0000"}

    data = model.to_dict()

    assert data["version"] == "1.0"
    assert data["keyboard"]["model"] == "sofle-v2"
    assert data["keyboard"]["mcu"] == "rp2040"
    assert data["oled"]["image_path"] == "/abs/path/test.gif"
    assert data["oled"]["overlays"] == ["layer", "wpm"]
    assert data["rgb"]["per_key"] == {"KEY_A": "#FF0000"}


def test_from_dict_null_sub_fields_no_crash():
    """M1/L2 — from_dict() avec sous-champs null ne doit pas lever AttributeError."""
    data = {
        "version": "1.0",
        "keyboard": None,
        "oled": None,
        "rgb": None,
        "build": None,
    }
    model = ProjectModel.from_dict(data)
    assert model.keyboard.model == ""
    assert model.oled.image_path == ""
    assert model.rgb.effects == []
    assert model.build.vial_qmk_version == ""


def test_rgb_from_dict_null_effects_no_crash():
    """M2/L4 — RgbConfig.from_dict() avec effects: null ou elements null → liste vide."""
    from models.project_model import RgbConfig
    # effects: null
    cfg = RgbConfig.from_dict({"effects": None, "per_key": {}})
    assert cfg.effects == []
    # effects: [null, valid_dict]
    cfg2 = RgbConfig.from_dict({
        "effects": [None, {"type": "static", "color_primary": "#FFFFFF",
                           "color_secondary": "#888888", "fade_ms": 500, "trigger_key": None}],
        "per_key": {},
    })
    assert len(cfg2.effects) == 1
    assert cfg2.effects[0].type == "static"


def test_frames_not_serialized():
    """Les frames OLED (données binaires runtime) ne doivent PAS être sérialisées."""
    model = ProjectModel()
    model.oled.frames = [b"\x00\xff", b"\xaa\xbb"]
    data = model.to_dict()
    assert "frames" not in data.get("oled", {})


def test_project_model_deserialization():
    """from_dict() doit reconstruire un ProjectModel depuis un dict JSON."""
    data = {
        "version": "1.0",
        "keyboard": {"model": "sofle-v2", "mcu": "rp2040"},
        "oled": {"image_path": "/tmp/test.gif", "overlays": ["layer"]},
        "rgb": {
            "effects": [
                {
                    "type": "ripple",
                    "color_primary": "#FF0000",
                    "color_secondary": "#FF8800",
                    "fade_ms": 500,
                    "trigger_key": None,
                }
            ],
            "per_key": {"KEY_A": "#FF0000"},
        },
        "build": {"vial_qmk_version": "0.7.1", "toolchain_version": "13.3.rel1"},
    }
    model = ProjectModel.from_dict(data)

    assert model.keyboard.model == "sofle-v2"
    assert model.keyboard.mcu == "rp2040"
    assert model.oled.image_path == "/tmp/test.gif"
    assert model.oled.overlays == ["layer"]
    assert len(model.rgb.effects) == 1
    assert model.rgb.effects[0].type == "ripple"
    assert model.rgb.effects[0].color_primary == "#FF0000"
    assert model.rgb.per_key == {"KEY_A": "#FF0000"}
    assert model.build.vial_qmk_version == "0.7.1"


def test_project_model_partial_deserialization():
    """from_dict() doit gérer un dict partiel sans lever d'exception."""
    data = {"version": "1.0", "keyboard": {"model": "sofle-v2"}}
    model = ProjectModel.from_dict(data)
    assert model.keyboard.model == "sofle-v2"
    assert model.keyboard.mcu == ""  # valeur par défaut
    assert model.oled.image_path == ""


def test_rgb_effect_serialization():
    """RgbEffect doit se sérialiser avec les clés snake_case attendues."""
    effect = RgbEffect(
        type="ripple",
        color_primary="#FF0000",
        color_secondary="#FF8800",
        fade_ms=750,
        trigger_key="KEY_A",
    )
    model = ProjectModel()
    model.rgb.effects = [effect]
    data = model.to_dict()
    effect_data = data["rgb"]["effects"][0]
    assert effect_data["type"] == "ripple"
    assert effect_data["color_primary"] == "#FF0000"
    assert effect_data["color_secondary"] == "#FF8800"
    assert effect_data["fade_ms"] == 750
    assert effect_data["trigger_key"] == "KEY_A"
