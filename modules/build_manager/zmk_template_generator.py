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
import re
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

# Mapping MCU id → ZMK board name (HWMv2 qualifier form).
# Les variantes `//zmk` / `/<soc>/zmk` sélectionnent le defconfig ZMK
# (CONFIG_FLASH, CONFIG_NVS, CONFIG_SETTINGS_NVS) requis par Studio/BLE bond.
_ZMK_BOARD_MAP: dict[str, str] = {
    "nice_nano_v2": "nice_nano//zmk",
    "supermini_nrf52840": "nice_nano//zmk",
    "nrfmicro": "nrfmicro/nrf52840/zmk",
}

# Traduction `&pro_micro N` → (port, pin) pour la board `nice_nano//zmk`
# (source : zmk/app/boards/shields/../nice_nano.dts gpio-map).
# Les SuperMini nRF52840 partagent cette table via _ZMK_BOARD_MAP.
_NICE_NANO_PRO_MICRO_TO_NRF: dict[int, tuple[int, int]] = {
    0:  (0, 8),
    1:  (0, 6),
    2:  (0, 17),
    3:  (0, 20),
    4:  (0, 22),
    5:  (0, 24),
    6:  (1, 0),
    7:  (0, 11),
    8:  (1, 4),
    9:  (1, 6),
    10: (0, 9),
    14: (1, 11),
    15: (1, 13),
    16: (0, 10),
    18: (1, 15),
    19: (0, 2),
    20: (0, 29),
    21: (0, 31),
}

_PRO_MICRO_RE = re.compile(r"^\s*&pro_micro\s+(\d+)\s*$")


def _pro_micro_to_nrf_psel(expr: str, mcu: str) -> tuple[int, int] | None:
    """Traduit une expression `&pro_micro N` en couple (port, pin) nRF52.

    Retourne None si le format n'est pas reconnu, si N n'est pas dans la
    table pro_micro du MCU, ou si le MCU n'a pas de table (nrfmicro).
    """
    if mcu not in ("nice_nano_v2", "supermini_nrf52840"):
        return None
    match = _PRO_MICRO_RE.match(expr)
    if not match:
        return None
    return _NICE_NANO_PRO_MICRO_TO_NRF.get(int(match.group(1)))


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


def _build_layer_bindings(kb_def: KeyboardDefinition, layer_name: str) -> str:
    """Construit les bindings d'un layer.

    Si `kb_def.default_keymap_zmk[layer_name]` est défini, utilise ces bindings
    en ordre row-major (chaque ligne YAML = une ligne de la matrice combinée).
    Les positions non couvertes (YAML plus court que la matrice) retombent sur &trans.
    Aucune entrée pour ce layer → grille complète de &trans.
    """
    rows = kb_def.matrix["rows"]
    cols = kb_def.matrix["cols"]
    total_cols = cols * 2 if kb_def.split else cols

    used_positions = _get_used_positions(kb_def)
    layer_data = kb_def.default_keymap_zmk.get(layer_name) or []

    lines = []
    for r in range(rows):
        entries = []
        row_bindings = layer_data[r] if r < len(layer_data) else []
        idx = 0
        for c in range(total_cols):
            if (r, c) in used_positions:
                if idx < len(row_bindings):
                    entries.append(str(row_bindings[idx]))
                else:
                    entries.append("&trans")
                idx += 1
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

        # User conf à la racine de config/ (chargé par post_boards_shields.cmake de ZMK
        # via candidate ${ZMK_CONFIG}/<shield_dir_name>.conf). Zephyr ne charge
        # dans boards/shields/X/ QUE les fichiers nommés exactement <SHIELD>.conf,
        # donc le fichier commun doit vivre à la racine.
        conf_path = output_dir / "config" / f"{shield_name}.conf"
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

        # config/west.yml — manifest pour `west init -l config` (compilation locale)
        west_yml = output_dir / "config" / "west.yml"
        west_yml.write_text(env.get_template("west.yml.j2").render(context), encoding="utf-8")
        generated["west.yml"] = west_yml

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
        if mcu not in _ZMK_BOARD_MAP:
            raise ValueError(
                f"MCU '{mcu}' non supporté pour la compilation ZMK. "
                f"MCUs supportés : {sorted(_ZMK_BOARD_MAP.keys())}. "
                f"Ajoutez-le à _ZMK_BOARD_MAP dans zmk_template_generator.py "
                f"avec le nom de board HWMv2 correspondant."
            )
        zmk_board = _ZMK_BOARD_MAP[mcu]

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

        # Bindings par layer (depuis YAML default_keymap_zmk, fallback &trans)
        default_bindings = _build_layer_bindings(kb_def, "default")
        lower_bindings = _build_layer_bindings(kb_def, "lower")
        raise_bindings = _build_layer_bindings(kb_def, "raise")

        # Physical layout pour ZMK Studio
        physical_layout_keys = _build_physical_layout_keys(kb_def)

        # Display
        has_display = bool(model.keyboard.oled_sides)
        # TODO: détecter nice!view vs OLED depuis la config
        display_type = "oled"
        nice_view = False

        # Paramètres OLED devicetree (ex: display="128X32" → width=128, height=32)
        oled_driver = kb_def.oled_hw.driver
        display_str = (kb_def.oled_hw.display or "128X32").lower()
        w_part, _, h_part = display_str.partition("x")
        try:
            oled_width = int(w_part)
            oled_height = int(h_part)
        except ValueError:
            oled_width, oled_height = 128, 32
        oled_multiplex = max(oled_height - 1, 0)

        # RGB underglow — activé si user rgb_enabled + capability + ws2812 pin
        # + led_count > 0 + MCU avec table pro_micro connue. Sinon désactivé
        # (build casse sinon : src/rgb_underglow.c : #error "zmk,underglow chosen node…").
        rgb_underglow = False
        ws2812_port = 0
        ws2812_pin = 0
        ws2812_chain_length = 0
        if (
            model.keyboard.rgb_enabled
            and kb_def.capabilities.get("rgb", False)
            and pins.ws2812
            and kb_def.rgb_hw.led_count > 0
        ):
            port_pin = _pro_micro_to_nrf_psel(pins.ws2812, mcu)
            if port_pin is None:
                logger.warning(
                    "RGB underglow désactivé : ws2812 pin '%s' non traduisible "
                    "en NRF_PSEL pour le MCU '%s'", pins.ws2812, mcu,
                )
            else:
                rgb_underglow = True
                ws2812_port, ws2812_pin = port_pin
                ws2812_chain_length = kb_def.rgb_hw.led_count

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
            "matrix_rows_total": kb_def.matrix["rows"],
            "matrix_cols": kb_def.matrix["cols"],
            "matrix_cols_total": kb_def.matrix["cols"] * (2 if kb_def.split else 1),
            "matrix_transform_map": matrix_transform_map,
            "default_bindings": default_bindings,
            "lower_bindings": lower_bindings,
            "raise_bindings": raise_bindings,
            "has_encoder": kb_def.has_encoder,
            "encoder_a": encoder_a,
            "encoder_b": encoder_b,
            "has_display": has_display,
            "display_type": display_type,
            "nice_view": nice_view,
            "oled_driver": oled_driver,
            "oled_width": oled_width,
            "oled_height": oled_height,
            "oled_multiplex": oled_multiplex,
            "rgb_underglow": rgb_underglow,
            "ws2812_port": ws2812_port,
            "ws2812_pin": ws2812_pin,
            "ws2812_chain_length": ws2812_chain_length,
            # ZMK cappe ZMK_RGB_UNDERGLOW_BRT_MAX à [0, 100] (pourcent), pas 0-255 comme QMK
            "rgb_max_brightness": min(max(kb_def.rgb_hw.max_brightness, 0), 100),
            "physical_layout_keys": physical_layout_keys,
        }
