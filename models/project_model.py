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

    def to_dict(self) -> dict[str, Any]:
        return {"model": self.model, "mcu": self.mcu}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "KeyboardConfig":
        return cls(
            model=data.get("model", ""),
            mcu=data.get("mcu", ""),
        )


@dataclass
class OledConfig:
    """Configuration de l'affichage OLED.

    Note: le champ `frames` est uniquement runtime (données binaires converties).
    Il n'est PAS inclus dans la sérialisation JSON.
    """

    image_path: str = ""
    overlays: list[str] = field(default_factory=list)
    frames: list[bytes] = field(default_factory=list, repr=False)  # runtime only

    def to_dict(self) -> dict[str, Any]:
        """Sérialise sans le champ `frames` (données runtime binaires)."""
        return {
            "image_path": self.image_path,
            "overlays": list(self.overlays),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OledConfig":
        return cls(
            image_path=data.get("image_path", ""),
            overlays=list(data.get("overlays") or []),
            frames=[],  # toujours vide au chargement — regénéré à l'import
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
        "oled": {"image_path": "/abs/path.gif", "overlays": ["layer"]},
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

        Note: OledConfig.frames est exclu (données binaires runtime).
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
