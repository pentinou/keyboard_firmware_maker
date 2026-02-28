"""ProjectModel — état central sérialisable de l'application.

Ce dataclass porte toute la configuration utilisateur (clavier, OLED, RGB, build).
Il est passé par injection de dépendance à chaque widget (jamais en singleton global).
Format JSON : clés snake_case, couleurs hex #RRGGBB, chemins absolus.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class KeyboardConfig:
    """Configuration du matériel sélectionné."""

    model: str = ""
    mcu: str = ""
    oled_sides: list[str] = field(default_factory=list)
    # [] = aucun  |  ["left"] | ["right"] | ["left","right"]

    def to_dict(self) -> dict[str, Any]:
        return {"model": self.model, "mcu": self.mcu, "oled_sides": list(self.oled_sides)}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "KeyboardConfig":
        return cls(
            model=data.get("model", ""),
            mcu=data.get("mcu", ""),
            oled_sides=list(data.get("oled_sides", [])),
        )


@dataclass
class OledOverlayItem:
    """Position d'un overlay (layer, caps lock, WPM) sur l'écran OLED.

    col  : colonne curseur QMK (0–4 pour OLED 32px avec font 6px)
    line : page QMK (0–15 pour OLED 128px / 8)
    """

    enabled: bool = False
    col: int = 0
    line: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {"enabled": self.enabled, "col": self.col, "line": self.line}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OledOverlayItem":
        return cls(
            enabled=bool(data.get("enabled", False)),
            col=int(data.get("col", 0)),
            line=int(data.get("line", 0)),
        )


@dataclass
class OledImageItem:
    """Une image importée sur l'écran OLED avec position et options.

    Note: `frames` est uniquement runtime (données binaires converties).
    Il n'est PAS inclus dans la sérialisation JSON.
    natural_w / natural_h : dimensions du thumbnail OLED en pixels (avant padding).
    """

    image_path: str = ""
    frames: list[bytes] = field(default_factory=list, repr=False)  # runtime only
    delays: list[int] = field(default_factory=list, repr=False)    # runtime only (ms par frame)
    natural_w: int = 32   # largeur thumbnail (pixels OLED)
    natural_h: int = 128  # hauteur thumbnail (pixels OLED)
    col: int = 0          # colonne curseur QMK (0-4)
    line: int = 0         # page QMK (0-15)
    inverted: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "image_path": self.image_path,
            "natural_w": self.natural_w,
            "natural_h": self.natural_h,
            "col": self.col,
            "line": self.line,
            "inverted": self.inverted,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OledImageItem":
        return cls(
            image_path=data.get("image_path", ""),
            natural_w=int(data.get("natural_w", 32)),
            natural_h=int(data.get("natural_h", 128)),
            col=int(data.get("col", 0)),
            line=int(data.get("line", 0)),
            inverted=bool(data.get("inverted", False)),
        )


@dataclass
class OledSideConfig:
    """Configuration OLED d'une moitié du clavier split.

    Note: OledImageItem.frames est uniquement runtime (données binaires converties).
    """

    images: list[OledImageItem] = field(default_factory=list)
    layer: OledOverlayItem = field(default_factory=OledOverlayItem)
    caps_lock: OledOverlayItem = field(default_factory=OledOverlayItem)
    wpm: OledOverlayItem = field(default_factory=OledOverlayItem)
    rgb_mode: OledOverlayItem = field(default_factory=OledOverlayItem)
    katawajojo_enabled: bool = False
    katawajojo_line: int = 13  # page de départ KatawaJojo (13*8=104px, bas de l'écran 128px)
    luna_enabled: bool = False
    luna_line: int = 13  # page de départ Luna (13*8=104px, bas de l'écran 128px)
    ocean_dream_enabled: bool = False
    ocean_dream_line: int = 0  # plein écran
    bongo_enabled: bool = False
    bongo_line: int = 0  # page de départ Bongo Cat (0-15)

    def to_dict(self) -> dict[str, Any]:
        return {
            "images": [img.to_dict() for img in self.images],
            "layer": self.layer.to_dict(),
            "caps_lock": self.caps_lock.to_dict(),
            "wpm": self.wpm.to_dict(),
            "rgb_mode": self.rgb_mode.to_dict(),
            "katawajojo_enabled": self.katawajojo_enabled,
            "katawajojo_line": self.katawajojo_line,
            "luna_enabled": self.luna_enabled,
            "luna_line": self.luna_line,
            "ocean_dream_enabled": self.ocean_dream_enabled,
            "ocean_dream_line": self.ocean_dream_line,
            "bongo_enabled": self.bongo_enabled,
            "bongo_line": self.bongo_line,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OledSideConfig":
        # New format: "images" key (list of OledImageItem dicts)
        if "images" in data and isinstance(data["images"], list):
            images = [OledImageItem.from_dict(d) for d in data["images"] if isinstance(d, dict)]
        # Migration: old format had image_path at top level
        elif data.get("image_path"):
            images = [OledImageItem.from_dict({
                "image_path": data["image_path"],
                "col": int(data.get("image_col", 0)),
                "line": int(data.get("image_line", 0)),
                "inverted": bool(data.get("image_inverted", False)),
            })]
        else:
            images = []
        # Migration: old "luna_enabled" was actually katawajojo
        if "katawajojo_enabled" in data:
            katawajojo_enabled = bool(data.get("katawajojo_enabled", False))
            katawajojo_line = int(data.get("katawajojo_line", 13))
            luna_enabled = bool(data.get("luna_enabled", False))
            luna_line = int(data.get("luna_line", 13))
        else:
            katawajojo_enabled = bool(data.get("luna_enabled", False))
            katawajojo_line = int(data.get("luna_line", 13))
            luna_enabled = False
            luna_line = 13
        return cls(
            images=images,
            layer=OledOverlayItem.from_dict(data.get("layer") or {}),
            caps_lock=OledOverlayItem.from_dict(data.get("caps_lock") or {}),
            wpm=OledOverlayItem.from_dict(data.get("wpm") or {}),
            rgb_mode=OledOverlayItem.from_dict(data.get("rgb_mode") or {}),
            katawajojo_enabled=katawajojo_enabled,
            katawajojo_line=katawajojo_line,
            luna_enabled=luna_enabled,
            luna_line=luna_line,
            ocean_dream_enabled=bool(data.get("ocean_dream_enabled", False)),
            ocean_dream_line=int(data.get("ocean_dream_line", 0)),
            bongo_enabled=bool(data.get("bongo_enabled", False)),
            bongo_line=int(data.get("bongo_line", 0)),
        )


@dataclass
class OledConfig:
    """Configuration OLED split : côté gauche + côté droit indépendants.

    Migration : les anciens champs (image_path, overlays, luna_x, luna_y)
    sont ignorés silencieusement lors du chargement.
    """

    left: OledSideConfig = field(default_factory=OledSideConfig)
    right: OledSideConfig = field(default_factory=OledSideConfig)
    anti_burnin: bool = False
    sleep_enabled: bool = False
    sleep_timeout_s: int = 240

    def to_dict(self) -> dict[str, Any]:
        return {
            "left": self.left.to_dict(),
            "right": self.right.to_dict(),
            "anti_burnin": self.anti_burnin,
            "sleep_enabled": self.sleep_enabled,
            "sleep_timeout_s": self.sleep_timeout_s,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OledConfig":
        # Migration : si l'ancien format (clé "image_path" au niveau racine) est détecté,
        # ignorer silencieusement les anciens champs.
        left_data = data.get("left") or {}
        right_data = data.get("right") or {}
        return cls(
            left=OledSideConfig.from_dict(left_data),
            right=OledSideConfig.from_dict(right_data),
            anti_burnin=bool(data.get("anti_burnin", False)),
            sleep_enabled=bool(data.get("sleep_enabled", False)),
            sleep_timeout_s=int(data.get("sleep_timeout_s", 240)),
        )


@dataclass
class RgbEffect:
    """Définition d'un effet RGB.

    Couleurs stockées en hex #RRGGBB.
    """

    type: str = "static"
    color_primary: str = "#FFFFFF"
    color_secondary: str = "#888888"
    fade_ms: int = 500
    trigger_key: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "color_primary": self.color_primary,
            "color_secondary": self.color_secondary,
            "fade_ms": self.fade_ms,
            "trigger_key": self.trigger_key,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RgbEffect":
        return cls(
            type=data.get("type", "static"),
            color_primary=data.get("color_primary", "#FFFFFF"),
            color_secondary=data.get("color_secondary", "#888888"),
            fade_ms=data.get("fade_ms", 500),
            trigger_key=data.get("trigger_key"),
        )


@dataclass
class RgbConfig:
    """Configuration RGB globale (effets prédéfinis + couleurs par touche)."""

    effects: list[RgbEffect] = field(default_factory=list)
    per_key: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "effects": [e.to_dict() for e in self.effects],
            "per_key": dict(self.per_key),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RgbConfig":
        return cls(
            effects=[RgbEffect.from_dict(e) for e in (data.get("effects") or []) if isinstance(e, dict)],
            per_key=dict(data.get("per_key") or {}),
        )


@dataclass
class BuildConfig:
    """Versions de la toolchain verrouillées pour la reproductibilité."""

    vial_qmk_version: str = ""
    toolchain_version: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "vial_qmk_version": self.vial_qmk_version,
            "toolchain_version": self.toolchain_version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BuildConfig":
        return cls(
            vial_qmk_version=data.get("vial_qmk_version", ""),
            toolchain_version=data.get("toolchain_version", ""),
        )


@dataclass
class ProjectModel:
    """État central sérialisable de keyboard_firmware_maker.

    Passé par injection de dépendance à chaque widget via le constructeur.
    Ne jamais instancier en singleton global.

    Format JSON de sauvegarde (clés snake_case) :
    {
        "version": "1.0",
        "keyboard": {"model": "sofle-v2", "mcu": "rp2040"},
        "oled": {
            "left":  {"images": [{"image_path": "", "col": 0, "line": 0, ...}], "layer": {...}, ...},
            "right": {"images": [], "layer": {...}, ...}
        },
        "rgb": {"effects": [...], "per_key": {"KEY_A": "#FF0000"}},
        "build": {"vial_qmk_version": "0.7.1", "toolchain_version": "13.3.rel1"}
    }
    """

    version: str = "1.0"
    keyboard: KeyboardConfig = field(default_factory=KeyboardConfig)
    oled: OledConfig = field(default_factory=OledConfig)
    rgb: RgbConfig = field(default_factory=RgbConfig)
    build: BuildConfig = field(default_factory=BuildConfig)

    def to_dict(self) -> dict[str, Any]:
        """Sérialise l'état complet en dict JSON-compatible.

        Note: OledSideConfig.frames est exclu (données binaires runtime).
        """
        return {
            "version": self.version,
            "keyboard": self.keyboard.to_dict(),
            "oled": self.oled.to_dict(),
            "rgb": self.rgb.to_dict(),
            "build": self.build.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProjectModel":
        """Reconstruit un ProjectModel depuis un dict JSON.

        Gère les dicts partiels (champs manquants → valeurs par défaut).
        """
        return cls(
            version=data.get("version", "1.0"),
            keyboard=KeyboardConfig.from_dict(data.get("keyboard") or {}),
            oled=OledConfig.from_dict(data.get("oled") or {}),
            rgb=RgbConfig.from_dict(data.get("rgb") or {}),
            build=BuildConfig.from_dict(data.get("build") or {}),
        )
