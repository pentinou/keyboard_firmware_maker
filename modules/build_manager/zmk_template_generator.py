"""zmk_template_generator.py — Génération de la structure zmk-config depuis ProjectModel.

Utilise Jinja2 pour rendre les templates Devicetree (.overlay, .keymap) et Kconfig
(.conf) paramétrés depuis ProjectModel. Aucun import Qt — pur Python (testable).

Structure de sortie dans output_dir/ :
  config/boards/shields/{shield}/
    {shield}.dtsi           (split: shared devicetree include)
    {shield}.overlay        (non-split: standalone overlay)
    {shield}_left.overlay   (split)
    {shield}_right.overlay  (split)
    {shield}.keymap
    {shield}.conf
    {shield}_right.conf     (split)
    Kconfig.shield
    Kconfig.defconfig
  build.yaml
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

from models.project_model import ProjectModel
from modules.hardware.keyboard_loader import KeyboardDefinition, McuPins, load_keyboard

logger = logging.getLogger(__name__)

BASE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).parent.parent.parent))
ZMK_TEMPLATES_DIR = BASE_DIR / "templates" / "zmk"
KEYBOARDS_DIR = BASE_DIR / "keyboards"

# Mapping MCU id → ZMK board name
_ZMK_BOARD_MAP: dict[str, str] = {
    "nice_nano_v2": "nice_nano_v2",
    "supermini_nrf52840": "nice_nano_v2",
    "nrfmicro": "nrfmicro_13",
}


def _load_keyboard_def(model: str) -> KeyboardDefinition | None:
    """Charge la définition de clavier depuis le YAML."""
    yaml_path = KEYBOARDS_DIR / f"{model}.yaml"
    if not yaml_path.exists():
        logger.warning("YAML introuvable : %s", yaml_path)
        return None
    return load_keyboard(yaml_path)


def _format_gpios(pins: list[str], flags: str) -> str:
    """Formate une liste de pins en bloc Devicetree row-gpios/col-gpios."""
    lines = []
    for i, pin in enumerate(pins):
        prefix = "<" if i == 0 else "        , <"
        lines.append(f"{prefix}{pin} {flags}>")
    return "\n".join(lines)


def _get_used_positions(kb_def: KeyboardDefinition) -> set[tuple[int, int]]:
    """Retourne les positions (row, col) utilisées (hors encodeurs) dans la matrice combinée."""
    cols = kb_def.matrix["cols"]
    used: set[tuple[int, int]] = set()

    for key in kb_def.layout.get("left", []):
        if not key.encoder:
            used.add((key.row, key.col))
    for key in kb_def.layout.get("right", []):
        if not key.encoder:
            used.add((key.row, key.col + cols))
    for key in kb_def.layout.get("keys", []):
        if not key.encoder:
            used.add((key.row, key.col))

    return used


def _build_matrix_transform(kb_def: KeyboardDefinition) -> str:
    """Construit le bloc map de la matrix-transform ZMK depuis le layout."""
    rows = kb_def.matrix["rows"]
    cols = kb_def.matrix["cols"]
    total_cols = cols * 2 if kb_def.split else cols

    used_positions = _get_used_positions(kb_def)

    lines = []
    for r in range(rows):
        row_entries = []
        for c in range(total_cols):
            if (r, c) in used_positions:
                row_entries.append(f"RC({r},{c})")
        if row_entries:
            lines.append("            " + "  ".join(row_entries))

    return "\n".join(lines)


def _build_trans_bindings(kb_def: KeyboardDefinition) -> str:
    """Construit une grille de &trans pour toutes les touches du keymap."""
    rows = kb_def.matrix["rows"]
    cols = kb_def.matrix["cols"]
    total_cols = cols * 2 if kb_def.split else cols

    used_positions = _get_used_positions(kb_def)

    lines = []
    for r in range(rows):
        entries = []
        for c in range(total_cols):
            if (r, c) in used_positions:
                entries.append("&trans")
        if entries:
            lines.append("                " + "  ".join(entries))

    return "\n".join(lines)


def _build_physical_layout_keys(kb_def: KeyboardDefinition) -> str:
    """Construit la propriété keys du physical-layout pour ZMK Studio.

    Chaque touche est décrite par &key_physical_attrs w h x y r rx ry
    en centi-key-units (100 = 1u). L'ordre doit correspondre exactement
    au matrix transform et aux bindings du keymap.
    """
    rows = kb_def.matrix["rows"]
    cols = kb_def.matrix["cols"]
    total_cols = cols * 2 if kb_def.split else cols

    left_keys = kb_def.layout.get("left", [])
    right_keys = kb_def.layout.get("right", [])
    single_keys = kb_def.layout.get("keys", [])

    # Map (row, col_combined) → (x, y) en key-units
    position_map: dict[tuple[int, int], tuple[float, float]] = {}

    for key in left_keys:
        if not key.encoder:
            position_map[(key.row, key.col)] = (key.x, key.y)

    # Offset côté droit : largeur max gauche + 1u (touche) + 2u (gap entre moitiés)
    if kb_def.split and left_keys:
        max_left_x = max(k.x for k in left_keys if not k.encoder)
        right_x_offset = max_left_x + 3.0
    else:
        right_x_offset = 0.0

    for key in right_keys:
        if not key.encoder:
            position_map[(key.row, key.col + cols)] = (key.x + right_x_offset, key.y)

    for key in single_keys:
        if not key.encoder:
            position_map[(key.row, key.col)] = (key.x, key.y)

    # Collecter dans l'ordre row-major (même ordre que transform / bindings)
    entries: list[tuple[int, int]] = []
    for r in range(rows):
        for c in range(total_cols):
            if (r, c) in position_map:
                x, y = position_map[(r, c)]
                entries.append((int(round(x * 100)), int(round(y * 100))))

    if not entries:
        return ""

    lines = []
    for i, (x, y) in enumerate(entries):
        prefix = "        keys = " if i == 0 else "             , "
        suffix = ";" if i == len(entries) - 1 else ""
        lines.append(f"{prefix}<&key_physical_attrs 100 100 {x:>5} {y:>5} 0 0 0>{suffix}")

    return "\n".join(lines)


class ZmkTemplateGenerator:
    """Génère les fichiers source ZMK depuis ProjectModel + templates Jinja2."""

    def __init__(self, templates_dir: Path | None = None) -> None:
        self._templates_dir = templates_dir or ZMK_TEMPLATES_DIR

    def generate(self, model: ProjectModel, output_dir: Path) -> dict[str, Path]:
        """Rend tous les templates ZMK et écrit les fichiers dans output_dir.

        Args:
            model: état du projet à sérialiser en config ZMK.
            output_dir: répertoire de destination (créé si absent).

        Returns:
            Dict {description: chemin_fichier_généré}.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        env = Environment(
            loader=FileSystemLoader(str(self._templates_dir)),
            autoescape=False,
            keep_trailing_newline=True,
        )

        context = self._build_context(model)
        shield_name = context["shield_name"]
        split = context["split"]

        # Répertoire du shield
        shield_dir = output_dir / "config" / "boards" / "shields" / shield_name
        shield_dir.mkdir(parents=True, exist_ok=True)

        generated: dict[str, Path] = {}

        if split:
            # Split: .dtsi commun + left/right overlays
            dtsi_path = shield_dir / f"{shield_name}.dtsi"
            dtsi_path.write_text(env.get_template("shield.dtsi.j2").render(context), encoding="utf-8")
            generated["dtsi"] = dtsi_path

            left_path = shield_dir / f"{shield_name}_left.overlay"
            left_path.write_text(env.get_template("shield_left.overlay.j2").render(context), encoding="utf-8")
            generated["left_overlay"] = left_path

            right_path = shield_dir / f"{shield_name}_right.overlay"
            right_path.write_text(env.get_template("shield_right.overlay.j2").render(context), encoding="utf-8")
            generated["right_overlay"] = right_path

            right_conf = shield_dir / f"{shield_name}_right.conf"
            right_conf.write_text(env.get_template("shield_right.conf.j2").render(context), encoding="utf-8")
            generated["right_conf"] = right_conf
        else:
            # Non-split: overlay standalone
            overlay_path = shield_dir / f"{shield_name}.overlay"
            overlay_path.write_text(env.get_template("shield.overlay.j2").render(context), encoding="utf-8")
            generated["overlay"] = overlay_path

        # Fichiers communs
        keymap_path = shield_dir / f"{shield_name}.keymap"
        keymap_path.write_text(env.get_template("shield.keymap.j2").render(context), encoding="utf-8")
        generated["keymap"] = keymap_path

        conf_path = shield_dir / f"{shield_name}.conf"
        conf_path.write_text(env.get_template("shield.conf.j2").render(context), encoding="utf-8")
        generated["conf"] = conf_path

        kconfig_shield = shield_dir / "Kconfig.shield"
        kconfig_shield.write_text(env.get_template("Kconfig.shield.j2").render(context), encoding="utf-8")
        generated["Kconfig.shield"] = kconfig_shield

        kconfig_defconfig = shield_dir / "Kconfig.defconfig"
        kconfig_defconfig.write_text(env.get_template("Kconfig.defconfig.j2").render(context), encoding="utf-8")
        generated["Kconfig.defconfig"] = kconfig_defconfig

        # build.yaml à la racine
        build_yaml = output_dir / "build.yaml"
        build_yaml.write_text(env.get_template("build.yaml.j2").render(context), encoding="utf-8")
        generated["build.yaml"] = build_yaml

        logger.info("ZMK config générée : %d fichiers dans %s", len(generated), output_dir)
        return generated

    def _build_context(self, model: ProjectModel) -> dict[str, Any]:
        """Construit le contexte Jinja2 pour les templates ZMK."""
        kb_def = _load_keyboard_def(model.keyboard.model)
        if kb_def is None:
            raise ValueError(f"Clavier inconnu : {model.keyboard.model}")

        mcu = model.keyboard.mcu or "nice_nano_v2"

        # Extraire les pins du MCU sélectionné
        pins = McuPins()
        for mcu_opt in kb_def.mcu_options:
            if mcu_opt.id == mcu:
                pins = mcu_opt.pins
                break

        shield_name = kb_def.model.replace("-", "_")
        zmk_board = _ZMK_BOARD_MAP.get(mcu, "nice_nano_v2")

        # GPIO flags selon direction diode
        diode_dir = kb_def.diode_direction.lower()
        if diode_dir == "col2row":
            row_flags = "(GPIO_ACTIVE_HIGH | GPIO_PULL_DOWN)"
            col_flags = "GPIO_ACTIVE_HIGH"
        else:
            row_flags = "GPIO_ACTIVE_HIGH"
            col_flags = "(GPIO_ACTIVE_HIGH | GPIO_PULL_DOWN)"

        row_gpios_left = _format_gpios(pins.matrix_rows, row_flags)
        col_gpios_left = _format_gpios(pins.matrix_cols, col_flags)
        # Pour split, les deux moitiés utilisent les mêmes pins (symétrie PCB)
        row_gpios_right = row_gpios_left
        col_gpios_right = col_gpios_left

        # Matrix transform
        matrix_transform_map = _build_matrix_transform(kb_def)

        # Bindings (toutes les touches en &trans)
        trans_bindings = _build_trans_bindings(kb_def)

        # Physical layout pour ZMK Studio
        physical_layout_keys = _build_physical_layout_keys(kb_def)

        # Display
        has_display = bool(model.keyboard.oled_sides)
        # TODO: détecter nice!view vs OLED depuis la config
        display_type = "oled"
        nice_view = False

        # RGB underglow
        rgb_underglow = kb_def.capabilities.get("rgb", False) and model.keyboard.rgb_enabled

        # Encodeur
        encoder_a = pins.encoder_a[0] if pins.encoder_a else ""
        encoder_b = pins.encoder_b[0] if pins.encoder_b else ""

        return {
            "shield_name": shield_name,
            "shield_name_upper": shield_name.upper(),
            "display_name": kb_def.display_name,
            "zmk_board": zmk_board,
            "mcu": mcu,
            "split": kb_def.split,
            "diode_direction_zmk": diode_dir,
            "row_gpios_left": row_gpios_left,
            "col_gpios_left": col_gpios_left,
            "row_gpios_right": row_gpios_right,
            "col_gpios_right": col_gpios_right,
            "matrix_rows_total": kb_def.matrix["rows"] * (2 if kb_def.split else 1),
            "matrix_cols": kb_def.matrix["cols"],
            "matrix_transform_map": matrix_transform_map,
            "default_bindings": trans_bindings,
            "lower_bindings": trans_bindings,
            "raise_bindings": trans_bindings,
            "has_encoder": kb_def.has_encoder,
            "encoder_a": encoder_a,
            "encoder_b": encoder_b,
            "has_display": has_display,
            "display_type": display_type,
            "nice_view": nice_view,
            "rgb_underglow": rgb_underglow,
            "rgb_max_brightness": kb_def.rgb_hw.max_brightness,
            "physical_layout_keys": physical_layout_keys,
        }
