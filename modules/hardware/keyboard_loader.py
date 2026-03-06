"""keyboard_loader — chargement des définitions de claviers depuis les fichiers YAML.

Module pur Python sans dépendance Qt — testable sans QApplication.
Chaque fichier YAML dans `keyboards/` décrit un modèle de clavier supporté.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


@dataclass
class McuPins:
    """Brochage matériel d'un MCU pour un clavier donné."""

    matrix_rows: list[str] = field(default_factory=list)
    matrix_cols: list[str] = field(default_factory=list)
    encoder_a: list[str] = field(default_factory=list)
    encoder_b: list[str] = field(default_factory=list)
    encoder_a_right: list[str] = field(default_factory=list)
    encoder_b_right: list[str] = field(default_factory=list)
    ws2812: str = ""
    serial_tx: str = ""
    serial_driver: str = ""
    ws2812_driver: str = ""
    encoder_default_pos: str = ""


@dataclass
class McuOption:
    """Description d'un microcontrôleur compatible avec un modèle de clavier."""

    id: str
    display_name: str
    description: str = ""
    bootloader: str = ""
    pins: McuPins = field(default_factory=McuPins)


@dataclass
class KeyLayout:
    """Position physique d'une touche (unités clavier, 1U = 1 touche)."""

    row: int
    col: int
    x: float
    y: float
    encoder: bool = False
    w: float = 1.0  # largeur en unités clavier (1.0 = 1U standard, 2.0 = 2U, etc.)
    h: float = 1.0  # hauteur en unités clavier (1.0 = standard, 1.5 = tall thumb key)


@dataclass
class LayoutVariant:
    """Variante physique d'un layout (ex: standard vs 7U spacebar)."""

    slug: str
    label: str
    keys: list[KeyLayout] = field(default_factory=list)


@dataclass
class OledHardwareConfig:
    """Configuration matérielle OLED depuis le YAML clavier."""

    driver: str = "ssd1306"
    rotation: int = 270
    display: str = "128X32"


@dataclass
class RgbHardwareConfig:
    """Configuration matérielle RGB depuis le YAML clavier."""

    max_brightness: int = 200


@dataclass
class KeyboardDefinition:
    """Définition complète d'un modèle de clavier chargée depuis un fichier YAML."""

    model: str
    display_name: str
    description: str
    mcu_options: list[McuOption] = field(default_factory=list)
    capabilities: dict[str, bool] = field(default_factory=dict)
    matrix: dict[str, int] = field(default_factory=lambda: {"rows": 5, "cols": 6})
    layout: dict[str, list[KeyLayout]] = field(default_factory=dict)
    """Positions physiques des touches par côté ('left'/'right'). Vide si absent."""
    vial_name: str = ""
    """Nom affiché dans Vial (ex: "Sofle"). Vide = utilise model."""
    vial_vid: str = "0xFEED"
    """Vendor ID USB pour Vial."""
    vial_pid: str = "0x0001"
    """Product ID USB pour Vial."""
    diode_direction: str = "COL2ROW"
    layout_macro: str = "LAYOUT"
    has_encoder: bool = False
    split: bool = True
    layout_variants: list[LayoutVariant] = field(default_factory=list)
    oled_hw: OledHardwareConfig = field(default_factory=OledHardwareConfig)
    rgb_hw: RgbHardwareConfig = field(default_factory=RgbHardwareConfig)


def _parse_pins(raw: dict | None) -> McuPins:
    """Parse un bloc 'pins' YAML en McuPins dataclass."""
    if not raw or not isinstance(raw, dict):
        return McuPins()
    return McuPins(
        matrix_rows=raw.get("matrix_rows", []),
        matrix_cols=raw.get("matrix_cols", []),
        encoder_a=raw.get("encoder_a", []),
        encoder_b=raw.get("encoder_b", []),
        encoder_a_right=raw.get("encoder_a_right", []),
        encoder_b_right=raw.get("encoder_b_right", []),
        ws2812=raw.get("ws2812", ""),
        serial_tx=raw.get("serial_tx", ""),
        serial_driver=raw.get("serial_driver", ""),
        ws2812_driver=raw.get("ws2812_driver", ""),
        encoder_default_pos=raw.get("encoder_default_pos", ""),
    )


def load_keyboard(path: Path) -> KeyboardDefinition:
    """Charge un fichier YAML de définition de clavier et retourne un KeyboardDefinition.

    Args:
        path: Chemin absolu vers le fichier YAML.

    Returns:
        KeyboardDefinition rempli depuis le YAML.

    Raises:
        yaml.YAMLError: Si le fichier YAML est malformé.
        KeyError: Si des champs obligatoires (model, display_name) sont absents.
    """
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)

    mcu_options = [
        McuOption(
            id=mcu["id"],
            display_name=mcu["display_name"],
            description=mcu.get("description", ""),
            bootloader=mcu.get("bootloader", ""),
            pins=_parse_pins(mcu.get("pins", {})),
        )
        for mcu in (data.get("mcu_options") or [])
    ]

    raw_matrix = data.get("matrix", {})
    rows = raw_matrix.get("rows", 5) if isinstance(raw_matrix, dict) else 5
    cols = raw_matrix.get("cols", 6) if isinstance(raw_matrix, dict) else 6
    if not isinstance(rows, int) or rows <= 0:
        logger.warning("Valeur 'rows' invalide (%r) dans %s — défaut 5", rows, path.name)
        rows = 5
    if not isinstance(cols, int) or cols <= 0:
        logger.warning("Valeur 'cols' invalide (%r) dans %s — défaut 6", cols, path.name)
        cols = 6

    raw_layout = data.get("layout", {})
    layout: dict[str, list[KeyLayout]] = {}
    for side in ("left", "right", "keys"):
        keys = raw_layout.get(side, [])
        if isinstance(keys, list):
            layout[side] = [
                KeyLayout(
                    row=int(k["row"]),
                    col=int(k["col"]),
                    x=float(k["x"]),
                    y=float(k["y"]),
                    encoder=bool(k.get("encoder", False)),
                    w=float(k.get("w", 1.0)),
                    h=float(k.get("h", 1.0)),
                )
                for k in keys
                if isinstance(k, dict)
            ]

    raw_variants = data.get("layout_variants", []) or []
    seen_slugs: set[str] = set()
    layout_variants: list[LayoutVariant] = []
    for v in raw_variants:
        if not isinstance(v, dict):
            continue
        slug = str(v.get("slug", ""))
        if slug in seen_slugs:
            logger.warning(
                "Slug dupliqué '%s' dans %s — première occurrence conservée", slug, path.name
            )
            continue
        seen_slugs.add(slug)
        variant_keys = [
            KeyLayout(
                row=int(k["row"]),
                col=int(k["col"]),
                x=float(k["x"]),
                y=float(k["y"]),
                encoder=bool(k.get("encoder", False)),
                w=float(k.get("w", 1.0)),
                h=float(k.get("h", 1.0)),
            )
            for k in (v.get("keys", []) or [])
            if isinstance(k, dict)
        ]
        layout_variants.append(LayoutVariant(
            slug=slug,
            label=str(v.get("label", "")),
            keys=variant_keys,
        ))

    if bool(data.get("split", True)) and layout_variants:
        logger.warning(
            "layout_variants ignoré pour clavier split '%s' — non supporté en génération",
            data.get("model", path.name),
        )

    # Parse OLED hardware config
    raw_oled = data.get("oled", {})
    oled_hw = OledHardwareConfig(
        driver=raw_oled.get("driver", "ssd1306") if isinstance(raw_oled, dict) else "ssd1306",
        rotation=raw_oled.get("rotation", 270) if isinstance(raw_oled, dict) else 270,
        display=raw_oled.get("display", "128X32") if isinstance(raw_oled, dict) else "128X32",
    )

    # Parse RGB hardware config
    raw_rgb = data.get("rgb", {})
    rgb_hw = RgbHardwareConfig(
        max_brightness=raw_rgb.get("max_brightness", 200) if isinstance(raw_rgb, dict) else 200,
    )

    return KeyboardDefinition(
        model=data["model"],
        display_name=data["display_name"],
        description=data.get("description", ""),
        mcu_options=mcu_options,
        capabilities=data.get("capabilities", {}),
        matrix={"rows": rows, "cols": cols},
        layout=layout,
        vial_name=data.get("vial_name", ""),
        vial_vid=data.get("vial_vid", "0xFEED"),
        vial_pid=data.get("vial_pid", "0x0001"),
        diode_direction=data.get("diode_direction", "COL2ROW"),
        layout_macro=data.get("layout_macro", "LAYOUT"),
        has_encoder=bool(data.get("has_encoder", False)),
        split=bool(data.get("split", True)),
        layout_variants=layout_variants,
        oled_hw=oled_hw,
        rgb_hw=rgb_hw,
    )


def load_all_keyboards(
    keyboards_dir: Path,
    custom_dir: Path | None = None,
) -> list[KeyboardDefinition]:
    """Charge tous les fichiers *.yaml depuis keyboards_dir et custom_dir.

    Les claviers invalides sont ignorés (log warning) sans interrompre le chargement.
    Les claviers custom apparaissent après les prédéfinis dans la liste.

    Args:
        keyboards_dir: Répertoire contenant les fichiers YAML prédéfinis.
        custom_dir: Répertoire optionnel des claviers custom utilisateur.

    Returns:
        Liste de KeyboardDefinition triée alphabétiquement par display_name.
    """
    predefined: list[KeyboardDefinition] = []
    for yaml_path in sorted(
        p for p in keyboards_dir.glob("*.yaml") if not p.name.startswith("_")
    ):
        try:
            predefined.append(load_keyboard(yaml_path))
        except Exception as exc:
            logger.warning("Impossible de charger %s : %s", yaml_path.name, exc)

    customs: list[KeyboardDefinition] = []
    if custom_dir is not None and custom_dir.is_dir():
        for yaml_path in sorted(
            p for p in custom_dir.glob("*.yaml") if not p.name.startswith("_")
        ):
            try:
                customs.append(load_keyboard(yaml_path))
            except Exception as exc:
                logger.warning("Impossible de charger custom %s : %s", yaml_path.name, exc)

    # Prédéfinis triés alphabétiquement d'abord, puis customs triés alphabétiquement
    return sorted(predefined, key=lambda kb: kb.display_name) + sorted(customs, key=lambda kb: kb.display_name)
