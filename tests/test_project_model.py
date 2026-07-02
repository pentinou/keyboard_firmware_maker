"""Tests for ProjectModel — sérialisation/désérialisation JSON."""
from models.project_model import (
    BuildConfig,
    KeyboardConfig,
    OledConfig,
    OledImageItem,
    OledOverlayItem,
    OledSideConfig,
    ProjectModel,
    RgbConfig,
    RgbEffect,
)


# ─── OledOverlayItem ──────────────────────────────────────────────────────────

def test_oled_overlay_item_defaults():
    item = OledOverlayItem()
    assert item.enabled is False
    assert item.col == 0
    assert item.line == 0


def test_oled_overlay_item_serialization():
    item = OledOverlayItem(enabled=True, col=2, line=5)
    d = item.to_dict()
    assert d == {"enabled": True, "col": 2, "line": 5}


def test_oled_overlay_item_from_dict():
    item = OledOverlayItem.from_dict({"enabled": True, "col": 3, "line": 7})
    assert item.enabled is True
    assert item.col == 3
    assert item.line == 7


def test_oled_overlay_item_from_dict_defaults():
    item = OledOverlayItem.from_dict({})
    assert item.enabled is False
    assert item.col == 0
    assert item.line == 0


# ─── OledSideConfig ───────────────────────────────────────────────────────────

def test_oled_side_config_defaults():
    side = OledSideConfig()
    assert side.images == []
    assert side.layer.enabled is False
    assert side.caps_lock.enabled is False
    assert side.wpm.enabled is False
    assert side.katawajojo_enabled is False
    assert side.katawajojo_line == 13
    assert side.luna_enabled is False
    assert side.luna_line == 13
    assert side.ocean_dream_enabled is False
    assert side.ocean_dream_line == 0


def test_oled_side_config_serialization_excludes_frames():
    """to_dict() doit inclure 'images' (sans frames) et les autres clés."""
    side = OledSideConfig()
    img = OledImageItem(image_path="/tmp/test.png")
    img.frames = [b"\x00\xff"]  # runtime only
    side.images = [img]
    d = side.to_dict()
    assert "images" in d
    assert "frames" not in d["images"][0]  # frames exclus
    assert "image_path" in d["images"][0]
    assert "layer" in d
    assert "caps_lock" in d
    assert "wpm" in d
    assert "katawajojo_enabled" in d
    assert "katawajojo_line" in d
    assert "luna_enabled" in d
    assert "luna_line" in d
    assert "ocean_dream_enabled" in d
    assert "ocean_dream_line" in d


def test_oled_side_config_from_dict():
    """from_dict() avec nouveau format 'images'."""
    d = {
        "images": [{"image_path": "/tmp/test.png", "col": 1, "line": 2}],
        "layer": {"enabled": True, "col": 1, "line": 2},
        "caps_lock": {"enabled": False, "col": 0, "line": 0},
        "wpm": {"enabled": True, "col": 3, "line": 4},
        "katawajojo_enabled": True,
        "katawajojo_line": 10,
        "luna_enabled": True,
        "luna_line": 12,
        "ocean_dream_enabled": True,
        "ocean_dream_line": 0,
    }
    side = OledSideConfig.from_dict(d)
    assert len(side.images) == 1
    assert side.images[0].image_path == "/tmp/test.png"
    assert side.images[0].frames == []  # toujours vide au chargement
    assert side.layer.enabled is True
    assert side.layer.col == 1
    assert side.wpm.enabled is True
    assert side.katawajojo_enabled is True
    assert side.katawajojo_line == 10
    assert side.luna_enabled is True
    assert side.luna_line == 12
    assert side.ocean_dream_enabled is True
    assert side.ocean_dream_line == 0


def test_oled_side_config_migration_luna_to_katawajojo():
    """from_dict() doit migrer l'ancien format luna → katawajojo."""
    d = {
        "luna_enabled": True,
        "luna_line": 10,
    }
    side = OledSideConfig.from_dict(d)
    # Old "luna" was actually katawajojo
    assert side.katawajojo_enabled is True
    assert side.katawajojo_line == 10
    # New luna should be False (not present in old format)
    assert side.luna_enabled is False
    assert side.luna_line == 13


def test_oled_side_config_from_dict_migration():
    """from_dict() doit migrer l'ancien format (image_path au niveau top) vers images[0]."""
    d = {
        "image_path": "/tmp/test.png",
        "image_col": 2,
        "image_line": 3,
        "image_inverted": True,
        "layer": {"enabled": True, "col": 1, "line": 2},
    }
    side = OledSideConfig.from_dict(d)
    assert len(side.images) == 1
    assert side.images[0].image_path == "/tmp/test.png"
    assert side.images[0].col == 2
    assert side.images[0].line == 3
    assert side.images[0].inverted is True


def test_oled_side_config_from_dict_empty():
    side = OledSideConfig.from_dict({})
    assert side.images == []
    assert side.katawajojo_enabled is False
    assert side.katawajojo_line == 13
    assert side.luna_enabled is False
    assert side.luna_line == 13
    assert side.ocean_dream_enabled is False
    assert side.ocean_dream_line == 0


# ─── OledConfig ───────────────────────────────────────────────────────────────

def test_oled_config_defaults():
    cfg = OledConfig()
    assert isinstance(cfg.left, OledSideConfig)
    assert isinstance(cfg.right, OledSideConfig)
    assert cfg.left.images == []
    assert cfg.right.images == []


def test_oled_config_serialization():
    cfg = OledConfig()
    cfg.left.images = [OledImageItem(image_path="/left.png")]
    cfg.right.images = [OledImageItem(image_path="/right.gif")]
    cfg.left.layer.enabled = True
    d = cfg.to_dict()
    assert "left" in d
    assert "right" in d
    assert d["left"]["images"][0]["image_path"] == "/left.png"
    assert d["right"]["images"][0]["image_path"] == "/right.gif"
    assert d["left"]["layer"]["enabled"] is True


def test_oled_config_from_dict():
    d = {
        "left": {
            "images": [{"image_path": "/left.png"}],
            "katawajojo_enabled": True,
            "katawajojo_line": 11,
            "luna_enabled": True,
            "luna_line": 9,
        },
        "right": {"images": [{"image_path": "/right.gif"}]},
    }
    cfg = OledConfig.from_dict(d)
    assert cfg.left.images[0].image_path == "/left.png"
    assert cfg.left.katawajojo_enabled is True
    assert cfg.left.katawajojo_line == 11
    assert cfg.left.luna_enabled is True
    assert cfg.left.luna_line == 9
    assert cfg.right.images[0].image_path == "/right.gif"


def test_oled_config_migration_old_format():
    """OledConfig.from_dict() ignore silencieusement l'ancien format (overlays, luna_x, luna_y)."""
    old_data = {
        "image_path": "/old.gif",
        "overlays": ["layer", "wpm"],
        "luna_enabled": True,
        "luna_x": 0,
        "luna_y": 106,
    }
    # L'ancien format n'a pas de clés "left"/"right" → defaults
    cfg = OledConfig.from_dict(old_data)
    assert isinstance(cfg.left, OledSideConfig)
    assert isinstance(cfg.right, OledSideConfig)
    # Les anciennes clés sont ignorées silencieusement (pas de left/right)
    assert cfg.left.images == []


# ─── ProjectModel ─────────────────────────────────────────────────────────────

def test_project_model_defaults():
    """ProjectModel doit avoir des valeurs par défaut vides."""
    model = ProjectModel()
    assert model.version == "1.0"
    assert model.keyboard.model == ""
    assert model.keyboard.mcu == ""
    assert isinstance(model.oled, OledConfig)
    assert isinstance(model.oled.left, OledSideConfig)
    assert isinstance(model.oled.right, OledSideConfig)
    assert model.oled.left.images == []
    assert model.oled.left.katawajojo_enabled is False
    assert model.oled.left.luna_enabled is False
    assert model.oled.left.ocean_dream_enabled is False
    assert model.rgb.effects == []
    assert model.rgb.per_key == {}
    assert model.build.vial_qmk_version == ""


def test_project_model_serialization():
    """to_dict() doit produire un dict JSON valide avec clés snake_case."""
    model = ProjectModel()
    model.keyboard.model = "sofle-v2"
    model.keyboard.mcu = "rp2040"
    model.oled.left.images = [OledImageItem(image_path="/abs/path/test.gif")]
    model.oled.left.layer.enabled = True
    model.rgb.per_key = {"KEY_A": "#FF0000"}

    data = model.to_dict()

    assert data["version"] == "1.0"
    assert data["keyboard"]["model"] == "sofle-v2"
    assert data["keyboard"]["mcu"] == "rp2040"
    assert data["oled"]["left"]["images"][0]["image_path"] == "/abs/path/test.gif"
    assert data["oled"]["left"]["layer"]["enabled"] is True
    assert data["rgb"]["per_key"] == {"KEY_A": "#FF0000"}


def test_from_dict_null_sub_fields_no_crash():
    """from_dict() avec sous-champs null ne doit pas lever AttributeError."""
    data = {
        "version": "1.0",
        "keyboard": None,
        "oled": None,
        "rgb": None,
        "build": None,
    }
    model = ProjectModel.from_dict(data)
    assert model.keyboard.model == ""
    assert isinstance(model.oled, OledConfig)
    assert model.rgb.effects == []
    assert model.build.vial_qmk_version == ""


def test_rgb_from_dict_null_effects_no_crash():
    """RgbConfig.from_dict() avec effects: null ou elements null → liste vide."""
    cfg = RgbConfig.from_dict({"effects": None, "per_key": {}})
    assert cfg.effects == []
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
    img = OledImageItem(image_path="/tmp/test.png")
    img.frames = [b"\x00\xff", b"\xaa\xbb"]
    model.oled.left.images = [img]
    data = model.to_dict()
    # frames ne doit pas apparaître dans le dict de l'OledImageItem
    assert "frames" not in data["oled"]["left"]["images"][0]
    assert "frames" not in data.get("oled", {}).get("right", {})


def test_oled_luna_serialization():
    """luna/katawajojo/ocean_dream doivent être sérialisés et désérialisés."""
    model = ProjectModel()
    model.oled.left.katawajojo_enabled = True
    model.oled.left.katawajojo_line = 10
    model.oled.left.luna_enabled = True
    model.oled.left.luna_line = 12
    model.oled.right.ocean_dream_enabled = True
    model.oled.right.ocean_dream_line = 0
    data = model.to_dict()
    assert data["oled"]["left"]["katawajojo_enabled"] is True
    assert data["oled"]["left"]["katawajojo_line"] == 10
    assert data["oled"]["left"]["luna_enabled"] is True
    assert data["oled"]["left"]["luna_line"] == 12
    assert data["oled"]["right"]["ocean_dream_enabled"] is True
    assert data["oled"]["right"]["ocean_dream_line"] == 0

    restored = ProjectModel.from_dict(data)
    assert restored.oled.left.katawajojo_enabled is True
    assert restored.oled.left.katawajojo_line == 10
    assert restored.oled.left.luna_enabled is True
    assert restored.oled.left.luna_line == 12
    assert restored.oled.right.ocean_dream_enabled is True
    assert restored.oled.right.ocean_dream_line == 0


# ─── OledImageItem ────────────────────────────────────────────────────────────

def test_oled_image_item_defaults():
    img = OledImageItem()
    assert img.image_path == ""
    assert img.frames == []
    assert img.natural_w == 32
    assert img.natural_h == 128
    assert img.col == 0
    assert img.line == 0
    assert img.inverted is False


def test_oled_image_item_serialization():
    img = OledImageItem(image_path="/tmp/t.png", col=2, line=4, inverted=True, natural_w=20, natural_h=50)
    d = img.to_dict()
    assert d["image_path"] == "/tmp/t.png"
    assert d["col"] == 2
    assert d["line"] == 4
    assert d["inverted"] is True
    assert d["natural_w"] == 20
    assert d["natural_h"] == 50
    assert "frames" not in d


def test_oled_image_item_deserialization():
    img = OledImageItem.from_dict({"image_path": "/p.gif", "col": 1, "line": 3, "inverted": True})
    assert img.image_path == "/p.gif"
    assert img.col == 1
    assert img.line == 3
    assert img.inverted is True
    assert img.frames == []


def test_oled_image_item_defaults_from_empty_dict():
    img = OledImageItem.from_dict({})
    assert img.col == 0
    assert img.line == 0
    assert img.inverted is False


def test_oled_image_item_roundtrip():
    img = OledImageItem(image_path="/tmp/a.png", col=3, line=7, inverted=True)
    img.frames = [b"\xff"]  # runtime — must not appear in dict
    restored = OledImageItem.from_dict(img.to_dict())
    assert restored.image_path == "/tmp/a.png"
    assert restored.col == 3
    assert restored.line == 7
    assert restored.inverted is True
    assert restored.frames == []  # runtime not serialized


def test_oled_side_config_images_serialization_roundtrip():
    model = ProjectModel()
    model.oled.left.images = [
        OledImageItem(image_path="/a.png", col=4, line=12),
        OledImageItem(image_path="/b.gif", col=1, line=8, inverted=True),
    ]
    model.oled.right.images = []
    data = model.to_dict()
    restored = ProjectModel.from_dict(data)
    assert len(restored.oled.left.images) == 2
    assert restored.oled.left.images[0].image_path == "/a.png"
    assert restored.oled.left.images[0].col == 4
    assert restored.oled.left.images[1].inverted is True
    assert restored.oled.right.images == []


# ─── bongo_enabled / bongo_line ───────────────────────────────────────────────

def test_oled_side_config_bongo_defaults():
    side = OledSideConfig()
    assert side.bongo_enabled is False
    assert side.bongo_line == 0


def test_oled_side_config_bongo_serialization():
    side = OledSideConfig(bongo_enabled=True, bongo_line=5)
    d = side.to_dict()
    assert d["bongo_enabled"] is True
    assert d["bongo_line"] == 5


def test_oled_side_config_bongo_deserialization():
    side = OledSideConfig.from_dict({"bongo_enabled": True, "bongo_line": 8})
    assert side.bongo_enabled is True
    assert side.bongo_line == 8


def test_oled_side_config_bongo_defaults_from_empty_dict():
    side = OledSideConfig.from_dict({})
    assert side.bongo_enabled is False
    assert side.bongo_line == 0


def test_oled_side_config_bongo_roundtrip():
    model = ProjectModel()
    model.oled.right.bongo_enabled = True
    model.oled.right.bongo_line = 3
    data = model.to_dict()
    restored = ProjectModel.from_dict(data)
    assert restored.oled.right.bongo_enabled is True
    assert restored.oled.right.bongo_line == 3
    assert restored.oled.left.bongo_enabled is False


def test_oled_overlay_roundtrip():
    """Les overlays doivent survivre à un cycle to_dict/from_dict."""
    model = ProjectModel()
    model.oled.left.layer.enabled = True
    model.oled.left.layer.col = 2
    model.oled.left.layer.line = 5
    model.oled.right.wpm.enabled = True
    model.oled.right.wpm.col = 1
    model.oled.right.wpm.line = 14

    data = model.to_dict()
    restored = ProjectModel.from_dict(data)

    assert restored.oled.left.layer.enabled is True
    assert restored.oled.left.layer.col == 2
    assert restored.oled.left.layer.line == 5
    assert restored.oled.right.wpm.enabled is True
    assert restored.oled.right.wpm.col == 1
    assert restored.oled.right.wpm.line == 14


def test_project_model_deserialization():
    """from_dict() doit reconstruire un ProjectModel depuis un dict JSON (nouveau format)."""
    data = {
        "version": "1.0",
        "keyboard": {"model": "sofle-v2", "mcu": "rp2040"},
        "oled": {
            "left": {
                "images": [{"image_path": "/tmp/test.gif", "col": 0, "line": 3}],
                "layer": {"enabled": True, "col": 0, "line": 3},
            },
            "right": {},
        },
        "rgb": {
            "effects": [
                {
                    "type": "static",
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
    assert model.oled.left.images[0].image_path == "/tmp/test.gif"
    assert model.oled.left.layer.enabled is True
    assert len(model.rgb.effects) == 1
    assert model.rgb.effects[0].type == "static"
    assert model.rgb.effects[0].color_primary == "#FF0000"
    assert model.rgb.per_key == {"KEY_A": "#FF0000"}
    assert model.build.vial_qmk_version == "0.7.1"


def test_project_model_deserialization_old_format():
    """from_dict() doit migrer l'ancien format (image_path au niveau oled.left)."""
    data = {
        "version": "1.0",
        "oled": {
            "left": {"image_path": "/tmp/test.gif", "image_col": 1, "image_line": 2},
            "right": {},
        },
    }
    model = ProjectModel.from_dict(data)
    assert len(model.oled.left.images) == 1
    assert model.oled.left.images[0].image_path == "/tmp/test.gif"
    assert model.oled.left.images[0].col == 1
    assert model.oled.left.images[0].line == 2


def test_project_model_partial_deserialization():
    """from_dict() doit gérer un dict partiel sans lever d'exception."""
    data = {"version": "1.0", "keyboard": {"model": "sofle-v2"}}
    model = ProjectModel.from_dict(data)
    assert model.keyboard.model == "sofle-v2"
    assert model.keyboard.mcu == ""
    assert model.oled.left.images == []


def test_rgb_effect_serialization():
    """RgbEffect doit se sérialiser avec les clés snake_case attendues."""
    effect = RgbEffect(
        type="static",
        color_primary="#FF0000",
        color_secondary="#FF8800",
        fade_ms=750,
        trigger_key="KEY_A",
    )
    model = ProjectModel()
    model.rgb.effects = [effect]
    data = model.to_dict()
    effect_data = data["rgb"]["effects"][0]
    assert effect_data["type"] == "static"
    assert effect_data["color_primary"] == "#FF0000"
    assert effect_data["color_secondary"] == "#FF8800"
    assert effect_data["fade_ms"] == 750
    assert effect_data["trigger_key"] == "KEY_A"


# ─────────────────────────── Désérialisation défensive (2026-07-02) ──

def test_from_dict_survives_corrupted_int_values():
    """Un projet JSON corrompu (ints remplacés par des strings/None/listes)
    doit charger avec les défauts, pas échouer en bloc."""
    data = {
        "version": "1.0",
        "keyboard": {"model": "sofle-v2", "mcu": "rp2040"},
        "oled": {
            "left": {
                "images": [{"image_path": "x.png", "col": "abc", "line": None}],
                "layer": {"enabled": True, "col": [], "line": "12"},
                "katawajojo_enabled": True,
                "katawajojo_line": "pas-un-nombre",
                "bongo_line": None,
                "zmk_battery": {"enabled": True, "col": "oops", "line": 2},
            },
            "sleep_timeout_s": "beaucoup",
        },
        "rgb": {
            "effects": [{"type": "static", "fade_ms": "vite", "speed": "999"}],
            "custom_effects": [{
                "name": "Vague",
                "tracks": [{
                    "keys_offset": [{"dr": "1", "dc": None}],
                    "steps": [{"time_ms": "0", "hold_ms": [], "fade_ms": "200"}],
                }],
            }],
        },
        "advanced": {"tapping_term_ms": "abc", "mousekey_max_speed": None},
    }
    model = ProjectModel.from_dict(data)
    # Valeurs corrompues → défauts
    assert model.oled.left.images[0].col == 0
    assert model.oled.left.layer.line == 12          # "12" numérique converti
    assert model.oled.left.katawajojo_line == 13
    assert model.oled.left.bongo_line == 0
    assert model.oled.left.zmk_battery.col == 0
    assert model.oled.sleep_timeout_s == 240
    assert model.rgb.effects[0].fade_ms == 500
    assert model.rgb.effects[0].speed == 255          # "999" converti puis clampé
    assert model.advanced.tapping_term_ms == 200
    assert model.advanced.mousekey_max_speed == 10
    # Les offsets/steps produisent des ints (sinon C invalide à la génération)
    off = model.rgb.custom_effects[0].tracks[0].keys_offset[0]
    assert off.dr == 1 and off.dc == 0
    step = model.rgb.custom_effects[0].tracks[0].steps[0]
    assert step.hold_ms == 0 and step.fade_ms == 200
