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

import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

from models.project_model import OledSideConfig, ProjectModel
from modules.hardware.keyboard_loader import KeyboardDefinition, McuPins, load_keyboard
from modules.oled_editor.processor import (
    composite_side_frame,
    composite_side_frames,
    composite_side_frames_per_layer,
    frame_32x128_to_lvgl_128x32,
)

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


def _build_bluetooth_layer_bindings(kb_def: KeyboardDefinition) -> str:
    """Génère le layer Bluetooth : touches `&bt` + `&out` sur les 9 premières
    positions utilisées (en ordre row-major), `&trans` partout ailleurs.

    Layout :
      1. `&bt BT_CLR`     (effacer profil actif)
      2. `&bt BT_SEL 0`   (profil 1)
      3. `&bt BT_SEL 1`   (profil 2)
      4. `&bt BT_SEL 2`   (profil 3)
      5. `&bt BT_SEL 3`   (profil 4)
      6. `&bt BT_SEL 4`   (profil 5)
      7. `&out OUT_USB`   (forcer USB)
      8. `&out OUT_BLE`   (forcer BLE)
      9. `&out OUT_TOG`   (toggle USB/BLE)

    Accès via tri-layer : LOWER + RAISE simultanément → bluetooth_layer actif.
    """
    bt_bindings = [
        "&bt BT_CLR",
        "&bt BT_SEL 0",
        "&bt BT_SEL 1",
        "&bt BT_SEL 2",
        "&bt BT_SEL 3",
        "&bt BT_SEL 4",
        "&out OUT_USB",
        "&out OUT_BLE",
        "&out OUT_TOG",
    ]
    rows = kb_def.matrix["rows"]
    cols = kb_def.matrix["cols"]
    total_cols = cols * 2 if kb_def.split else cols
    used_positions = _get_used_positions(kb_def)

    lines = []
    placed = 0
    for r in range(rows):
        entries = []
        for c in range(total_cols):
            if (r, c) in used_positions:
                if placed < len(bt_bindings):
                    entries.append(bt_bindings[placed])
                    placed += 1
                else:
                    entries.append("&trans")
        if entries:
            lines.append("                " + "  ".join(entries))
    return "\n".join(lines)


# Bindings BT/OUT injectés dans le layer raise (mêmes que le tri-layer Bluetooth)
# pour faciliter l'accès sans avoir à connaître le combo LOWER+RAISE — visible
# aussi dans ZMK Studio qui peut ne pas afficher les conditional_layers.
_BLUETOOTH_BINDINGS_FOR_RAISE = [
    "&bt BT_CLR",
    "&bt BT_SEL 0",
    "&bt BT_SEL 1",
    "&bt BT_SEL 2",
    "&bt BT_SEL 3",
    "&bt BT_SEL 4",
    "&out OUT_USB",
    "&out OUT_BLE",
    "&out OUT_TOG",
]


def _compute_layer_grid(
    kb_def: KeyboardDefinition,
    layer_name: str,
    keymap_override: dict[str, list[list[str]]] | None = None,
) -> list[list[str]]:
    """Retourne la grille `rows × used_cols_par_row` du layer, avec `&trans`
    aux positions non couvertes par le YAML / override."""
    rows = kb_def.matrix["rows"]
    cols = kb_def.matrix["cols"]
    total_cols = cols * 2 if kb_def.split else cols

    used_positions = _get_used_positions(kb_def)
    if keymap_override is not None and layer_name in keymap_override:
        layer_data = keymap_override[layer_name]
    else:
        layer_data = kb_def.default_keymap_zmk.get(layer_name) or []

    grid = []
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
        grid.append(entries)
    return grid


def _inject_bluetooth_into_grid(grid: list[list[str]]) -> list[list[str]]:
    """Remplace les premiers `&trans` (en ordre row-major) du layer raise par
    les bindings BT_CLR / BT_SEL 0..4 / OUT_USB / OUT_BLE / OUT_TOG.

    Mute (`&none`) ou bindings non-trans sont préservés (priorité à ce que
    l'utilisateur a déjà placé). Le tri-layer Bluetooth reste accessible.
    """
    bt = list(_BLUETOOTH_BINDINGS_FOR_RAISE)
    out = [list(row) for row in grid]
    for r in range(len(out)):
        for c in range(len(out[r])):
            if not bt:
                return out
            if out[r][c] == "&trans":
                out[r][c] = bt.pop(0)
    return out


def _format_grid(grid: list[list[str]]) -> str:
    """Convertit la grille en string ZMK indentée."""
    lines = []
    for row in grid:
        if row:
            lines.append("                " + "  ".join(row))
    return "\n".join(lines)


def _build_layer_bindings(
    kb_def: KeyboardDefinition,
    layer_name: str,
    keymap_override: dict[str, list[list[str]]] | None = None,
    inject_bluetooth: bool = False,
) -> str:
    """Construit les bindings d'un layer.

    Si `keymap_override` contient `layer_name`, ces bindings ont priorité sur
    `kb_def.default_keymap_zmk[layer_name]` (cas import Vial-QMK).

    Si `inject_bluetooth=True`, remplace les premiers `&trans` par les
    behaviors BT/OUT (utile pour le raise_layer : accessibles sans tri-layer).
    """
    grid = _compute_layer_grid(kb_def, layer_name, keymap_override)
    if inject_bluetooth:
        grid = _inject_bluetooth_into_grid(grid)
    return _format_grid(grid)


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


def _side_has_custom_oled(side: OledSideConfig) -> bool:
    """True si la moitié a au moins une image (avec frames) ou un widget ZMK activé.

    Utilisé pour décider si on génère un `status_screen.c` custom pour cette moitié,
    ou si on garde le status screen built-in de ZMK.
    """
    if any(img.frames for img in side.images):
        return True
    return (
        side.zmk_battery.enabled
        or side.zmk_output.enabled
        or side.zmk_layer.enabled
        or side.zmk_peripheral.enabled
    )


# Hauteur typique d'un widget ZMK (icône) en pixels LVGL natifs après rotation.
# Utilisée pour calculer l'offset y depuis le bord supérieur du framebuffer 128×32.
# 12 px suffit pour les icônes battery/output/layer/peripheral natives ZMK.
_WIDGET_LVGL_APPROX_H = 12


def _editor_to_lvgl_pos(col: int, line: int, approx_h: int = _WIDGET_LVGL_APPROX_H) -> tuple[int, int]:
    """Traduit une position éditeur (col, line) → coordonnées LVGL (x, y) après rotation 90° CW.

    Éditeur : 32×128 (vertical), grille 6×8 (col*6, line*8 = pixel coords).
    LVGL natif (SSD1306 horizontal) : 128×32. Rotation 90° CW :
        editor_x = col*6 → contribue à lvgl_y inversé
        editor_y = line*8 → contribue à lvgl_x

    Pour qu'un widget de hauteur approx_h en LVGL tienne dans le framebuffer,
    on offset lvgl_y par `32 - col*6 - approx_h`. Clamping à 0 si négatif.
    """
    lvgl_x = max(0, min(127, line * 8))
    lvgl_y = max(0, 32 - col * 6 - approx_h)
    return lvgl_x, lvgl_y


def _build_widgets_context(side: OledSideConfig, role: str) -> list[dict]:
    """Construit la liste des widgets ZMK à instancier pour une moitié.

    Args:
        side: configuration OLED de la moitié (gauche/droite).
        role: "central" (left en split, ou seule moitié non-split) ou "peripheral" (right en split).

    Returns:
        Liste de dicts {type, x, y, [show_peer]}. Peripheral exclu pour central,
        layer/output exclus pour peripheral (ces widgets dépendent d'événements ZMK
        central-only ou peripheral-only).
    """
    widgets: list[dict] = []
    if side.zmk_battery.enabled:
        x, y = _editor_to_lvgl_pos(side.zmk_battery.col, side.zmk_battery.line)
        # show_peer uniquement valide en central (peripheral n'a pas accès au peer)
        show_peer = bool(side.zmk_battery.show_peer) and role == "central"
        widgets.append({"type": "battery", "x": x, "y": y, "show_peer": show_peer})
    if role == "central":
        if side.zmk_output.enabled:
            x, y = _editor_to_lvgl_pos(side.zmk_output.col, side.zmk_output.line)
            widgets.append({"type": "output", "x": x, "y": y})
        if side.zmk_layer.enabled:
            x, y = _editor_to_lvgl_pos(side.zmk_layer.col, side.zmk_layer.line)
            widgets.append({"type": "layer", "x": x, "y": y})
    if role == "peripheral" and side.zmk_peripheral.enabled:
        x, y = _editor_to_lvgl_pos(side.zmk_peripheral.col, side.zmk_peripheral.line)
        widgets.append({"type": "peripheral", "x": x, "y": y})
    return widgets


def _encode_lvgl_bytes_for_c(data: bytes) -> str:
    """Encode des octets en littéraux C `0xNN, 0xNN, ...` regroupés par 16 par ligne.

    Format de sortie compatible avec `static const uint8_t arr[] = { ... };`.
    Le résultat est inséré tel quel dans le template `status_screen.c.j2`.
    """
    chunks: list[str] = []
    for i in range(0, len(data), 16):
        row = data[i : i + 16]
        chunks.append(", ".join(f"0x{b:02X}" for b in row))
    return ",\n    ".join(chunks)


def _build_animation_context(images: list) -> dict:
    """Construit le contexte d'animation pour une moitié (single-layer / Phase 3).

    Retourne un dict avec :
      - `frames` : liste de chaînes hex C (une par frame d'animation, format LVGL 128×32)
      - `delays` : liste de délais en ms entre frames (même longueur que `frames`)
      - `animated` : True si l'animation contient ≥ 2 frames (sinon image statique)
    """
    raw_frames, delays = composite_side_frames(images)
    lvgl_frames = [_encode_lvgl_bytes_for_c(frame_32x128_to_lvgl_128x32(f)) for f in raw_frames]
    return {
        "frames": lvgl_frames,
        "delays": delays,
        "animated": len(lvgl_frames) > 1,
    }


def _build_layered_animation_context(images: list) -> dict:
    """Construit le contexte d'animation par-couche pour Phase 4 (layer-aware).

    Retourne un dict :
      - `layers`: liste de dicts `{layer: int, frames: [hex,...], delays: [ms,...], animated: bool}`
        triés par `layer` croissant (la couche -1 / fallback en premier).
      - `has_layer_aware`: True si au moins une image est assignée à une couche != -1
        (donc plusieurs entrées dans `layers`). Sinon False (Phase 3 path).
    """
    per_layer = composite_side_frames_per_layer(images)
    layers_ctx = []
    for layer_id in sorted(per_layer.keys()):
        raw_frames, delays = per_layer[layer_id]
        lvgl_frames = [_encode_lvgl_bytes_for_c(frame_32x128_to_lvgl_128x32(f)) for f in raw_frames]
        layers_ctx.append({
            "layer": layer_id,
            "frames": lvgl_frames,
            "delays": delays,
            "animated": len(lvgl_frames) > 1,
        })
    return {
        "layers": layers_ctx,
        "has_layer_aware": len(layers_ctx) > 1,
    }


def _extract_kp_keycode(zmk_binding: str) -> str | None:
    """Extrait le keycode pur d'un binding `&kp X` (= "X"). None si pas un &kp."""
    if zmk_binding.startswith("&kp "):
        return zmk_binding[4:].strip()
    return None


# Defaults sensor-bindings par layer pour les claviers split avec 2 encoders.
# Premier élément = left encoder (sensor 0), second = right encoder (sensor 1).
# Format ZMK `&inc_dec_kp <CW> <CCW>` (Clockwise d'abord).
_DEFAULT_SENSOR_BINDINGS: dict[str, tuple[str, str]] = {
    "default": ("&inc_dec_kp C_VOL_UP C_VOL_DN", "&inc_dec_kp PG_DN PG_UP"),
    "lower":   ("&inc_dec_kp PG_UP PG_DN",       "&inc_dec_kp HOME END"),
    "raise":   ("&inc_dec_kp C_BRI_UP C_BRI_DN", "&inc_dec_kp RIGHT LEFT"),
    "bluetooth": ("&inc_dec_kp C_VOL_UP C_VOL_DN", "&inc_dec_kp PG_DN PG_UP"),
}


def _build_sensor_bindings_for_layer(
    layer_name: str,
    layer_idx: int,
    custom_encoder_layout: list | None,
    split: bool,
) -> str:
    """Retourne le string `sensor-bindings = <...>` pour un layer.

    Si `custom_encoder_layout` (depuis Vial) est fourni et contient ce layer,
    convertit les keycodes QMK → ZMK pour produire les `&inc_dec_kp`.
    Sinon, fallback sur les defaults `_DEFAULT_SENSOR_BINDINGS`.

    Format Vial : `encoder_layout[layer][encoder_idx] = [CCW_kc, CW_kc]`.
    Format ZMK : `&inc_dec_kp <CW> <CCW>` (inversé).
    """
    from modules.keymap_importer.vial_to_zmk import convert_qmk_keycode_to_zmk

    def _kc_to_inc_dec_arg(qmk_kc: str) -> str:
        """QMK keycode → keycode ZMK utilisable dans `&inc_dec_kp` (sans préfixe)."""
        zmk = convert_qmk_keycode_to_zmk(qmk_kc)
        kp = _extract_kp_keycode(zmk)
        return kp or "C_VOL_UP"  # fallback peu impactant si pas mappable

    if custom_encoder_layout and layer_idx < len(custom_encoder_layout):
        encoders = custom_encoder_layout[layer_idx]  # [[CCW_L, CW_L], [CCW_R, CW_R]]
        bindings = []
        for enc_idx in range(2 if split else 1):
            if enc_idx >= len(encoders):
                break
            ccw, cw = encoders[enc_idx][0], encoders[enc_idx][1]
            cw_zmk = _kc_to_inc_dec_arg(cw)
            ccw_zmk = _kc_to_inc_dec_arg(ccw)
            bindings.append(f"&inc_dec_kp {cw_zmk} {ccw_zmk}")
        if bindings:
            return " ".join(bindings)

    # Fallback defaults
    defaults = _DEFAULT_SENSOR_BINDINGS.get(layer_name, _DEFAULT_SENSOR_BINDINGS["default"])
    return defaults[0] + (" " + defaults[1] if split else "")


def _kfm_version() -> str:
    """Lit la version KFM depuis _version.py (source de vérité), sinon 'dev'."""
    try:
        from _version import __version__  # type: ignore[import-not-found]
        return str(__version__)
    except (ImportError, AttributeError):
        return "dev"


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

        # OLED custom status screen (Phase 1) — image plein écran générée par KFM.
        # CMakeLists.txt du shield + status_screen[_left|_right].c selon split.
        # Le CMakeLists est aussi requis quand `anti_burnin` est actif (compile
        # kfm_anti_burnin.c indépendamment du custom_screen).
        needs_cmakelists = bool(context["oled_custom_screen"] or context["anti_burnin"])
        if needs_cmakelists:
            cmake_path = shield_dir / "CMakeLists.txt"
            cmake_path.write_text(env.get_template("CMakeLists.txt.j2").render(context), encoding="utf-8")
            generated["CMakeLists.txt"] = cmake_path

        if context["anti_burnin"] and context["has_display"]:
            anti_burnin_path = shield_dir / "kfm_anti_burnin.c"
            anti_burnin_path.write_text(
                env.get_template("kfm_anti_burnin.c.j2").render(context), encoding="utf-8"
            )
            generated["kfm_anti_burnin.c"] = anti_burnin_path

        if context["oled_custom_screen"]:
            screen_template = env.get_template("status_screen.c.j2")
            if split:
                if context["oled_custom_left"]:
                    left_screen = shield_dir / "status_screen_left.c"
                    left_ctx = {
                        **context,
                        "oled_animation": context["oled_animation_left"],
                        "oled_layered": context["oled_layered_left"],
                        "oled_has_image": context["oled_has_image_left"],
                        "oled_widgets": context["oled_widgets_left"],
                        "oled_side": "left",
                    }
                    left_screen.write_text(screen_template.render(left_ctx), encoding="utf-8")
                    generated["status_screen_left.c"] = left_screen
                if context["oled_custom_right"]:
                    right_screen = shield_dir / "status_screen_right.c"
                    right_ctx = {
                        **context,
                        "oled_animation": context["oled_animation_right"],
                        "oled_layered": context["oled_layered_right"],
                        "oled_has_image": context["oled_has_image_right"],
                        "oled_widgets": context["oled_widgets_right"],
                        "oled_side": "right",
                    }
                    right_screen.write_text(screen_template.render(right_ctx), encoding="utf-8")
                    generated["status_screen_right.c"] = right_screen
            else:
                screen_path = shield_dir / "status_screen.c"
                screen_ctx = {
                    **context,
                    "oled_animation": context["oled_animation_left"],
                    "oled_layered": context["oled_layered_left"],
                    "oled_has_image": context["oled_has_image_left"],
                    "oled_widgets": context["oled_widgets_left"],
                    "oled_side": "single",
                }
                screen_path.write_text(screen_template.render(screen_ctx), encoding="utf-8")
                generated["status_screen.c"] = screen_path

        # build.yaml à la racine
        build_yaml = output_dir / "build.yaml"
        build_yaml.write_text(env.get_template("build.yaml.j2").render(context), encoding="utf-8")
        generated["build.yaml"] = build_yaml

        # config/west.yml — manifest pour `west init -l config` (compilation locale)
        west_yml = output_dir / "config" / "west.yml"
        west_yml.write_text(env.get_template("west.yml.j2").render(context), encoding="utf-8")
        generated["west.yml"] = west_yml

        # kfm_debug_dump.json — snapshot du contexte de génération pour debug post-mortem.
        # Permet à l'utilisateur ou à un agent IA de comprendre ce qui a été généré
        # SANS avoir à re-deviner depuis l'UI : version KFM, timestamp, ProjectModel
        # sérialisé, liste des fichiers, état des features critiques (custom screen,
        # widgets actifs, debug_logging, etc.). Lire AVANT de debug un firmware.
        debug_dump = {
            "kfm_version": _kfm_version(),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "output_dir": str(output_dir),
            "project_model": model.to_dict(),
            "shield_name": context.get("shield_name"),
            "shield_name_upper": context.get("shield_name_upper"),
            "split": context.get("split"),
            "has_display": context.get("has_display"),
            "has_encoder": context.get("has_encoder"),
            "rgb_underglow": context.get("rgb_underglow"),
            "studio_transport": context.get("studio_transport"),
            "debug_logging": context.get("debug_logging"),
            "show_battery_percentage": context.get("show_battery_percentage"),
            "oled_custom_screen": context.get("oled_custom_screen"),
            "oled_has_image_left": context.get("oled_has_image_left"),
            "oled_has_image_right": context.get("oled_has_image_right"),
            "oled_widgets_left": context.get("oled_widgets_left"),
            "oled_widgets_right": context.get("oled_widgets_right"),
            "idle_sleep_ms": context.get("idle_sleep_ms"),
            "generated_files": {k: str(v) for k, v in generated.items()},
        }
        dump_path = output_dir / "kfm_debug_dump.json"
        dump_path.write_text(json.dumps(debug_dump, indent=2, default=str), encoding="utf-8")
        generated["kfm_debug_dump.json"] = dump_path

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
        # Si l'utilisateur a importé un keymap perso via UI, on convertit le
        # JSON Vial → bindings ZMK et on l'utilise comme override des layers
        # default/lower/raise (le bluetooth_layer reste généré à part).
        keymap_override = None
        if model.keyboard.use_custom_keymap and model.keyboard.custom_keymap:
            try:
                from modules.keymap_importer.vial_to_zmk import convert_vial_to_zmk_keymap
                # Construire les positions encodeur par row pour que le converter
                # filtre les entrées Vial correspondantes (sinon décalage des
                # bindings après chaque position encodeur — bug touche SPACE).
                cols = kb_def.matrix["cols"]
                encoder_cols_per_row: dict[int, set[int]] = {}
                for key in kb_def.layout.get("left", []):
                    if key.encoder:
                        encoder_cols_per_row.setdefault(key.row, set()).add(key.col)
                for key in kb_def.layout.get("right", []):
                    if key.encoder:
                        encoder_cols_per_row.setdefault(key.row, set()).add(key.col + cols)
                keymap_override = convert_vial_to_zmk_keymap(
                    model.keyboard.custom_keymap,
                    encoder_cols_per_row=encoder_cols_per_row or None,
                )
                # Si le clavier cible n'a pas de RGB underglow (ex: Corne) mais
                # le keymap importé vient d'un clavier qui en avait (ex: Sofle),
                # les `&rgb_ug RGB_*` se retrouvent dans le keymap → erreur DT
                # parse car le header `<dt-bindings/zmk/rgb.h>` n'est pas inclus
                # ET undefined reference au link sur `&rgb_ug`. On les remplace
                # par `&none` pour permettre la compilation.
                kb_has_rgb = bool(model.keyboard.rgb_enabled) and kb_def.capabilities.get("rgb", False)
                if not kb_has_rgb:
                    rgb_count = 0
                    for layer_name, rows in keymap_override.items():
                        for r, row in enumerate(rows):
                            for c, binding in enumerate(row):
                                if binding.startswith("&rgb_ug"):
                                    rows[r][c] = "&none"
                                    rgb_count += 1
                    if rgb_count:
                        logger.warning(
                            "ZMK : %d bindings &rgb_ug remplacés par &none "
                            "(clavier %s sans RGB)", rgb_count, model.keyboard.model,
                        )
                logger.info(
                    "ZMK : custom keymap importé (%d layers convertis depuis Vial, encodeurs filtrés : %s)",
                    len(keymap_override), encoder_cols_per_row,
                )
            except Exception as exc:
                logger.error("Échec conversion Vial → ZMK : %s, fallback default YAML", exc)
                keymap_override = None

        default_bindings = _build_layer_bindings(kb_def, "default", keymap_override)
        lower_bindings = _build_layer_bindings(kb_def, "lower", keymap_override)
        # raise_layer : on injecte les BT/OUT aux premiers &trans pour que les
        # touches de gestion BLE soient accessibles facilement (visible dans
        # ZMK Studio même si le conditional_layer Bluetooth ne l'est pas).
        raise_bindings = _build_layer_bindings(
            kb_def, "raise", keymap_override, inject_bluetooth=True,
        )
        bluetooth_bindings = _build_bluetooth_layer_bindings(kb_def)

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

        # Idle sleep timeout (en ms). Priorité :
        # 1. OledConfig.sleep_enabled + sleep_timeout_s (legacy, override explicite)
        # 2. AdvancedOptionsConfig.deep_sleep_timeout_min (Options avancées, défaut 4 min)
        # Cap à 1 min minimum pour éviter un clavier qui dort instantanément.
        if model.oled.sleep_enabled and model.oled.sleep_timeout_s > 0:
            idle_sleep_ms = max(60_000, model.oled.sleep_timeout_s * 1000)
        else:
            idle_sleep_ms = max(60_000, model.advanced.deep_sleep_timeout_min * 60_000)

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
            "bluetooth_bindings": bluetooth_bindings,
            # Sensor bindings par layer (encodeurs). Split → 2 bindings,
            # non-split → 1. Si custom_keymap a un encoder_layout, on l'utilise.
            "default_sensor_bindings": _build_sensor_bindings_for_layer(
                "default", 0,
                model.keyboard.custom_keymap.get("encoder_layout") if (
                    model.keyboard.use_custom_keymap and model.keyboard.custom_keymap
                ) else None,
                kb_def.split,
            ),
            "lower_sensor_bindings": _build_sensor_bindings_for_layer(
                "lower", 1,
                model.keyboard.custom_keymap.get("encoder_layout") if (
                    model.keyboard.use_custom_keymap and model.keyboard.custom_keymap
                ) else None,
                kb_def.split,
            ),
            "raise_sensor_bindings": _build_sensor_bindings_for_layer(
                "raise", 2,
                model.keyboard.custom_keymap.get("encoder_layout") if (
                    model.keyboard.use_custom_keymap and model.keyboard.custom_keymap
                ) else None,
                kb_def.split,
            ),
            "bluetooth_sensor_bindings": _build_sensor_bindings_for_layer(
                "bluetooth", 3,
                model.keyboard.custom_keymap.get("encoder_layout") if (
                    model.keyboard.use_custom_keymap and model.keyboard.custom_keymap
                ) else None,
                kb_def.split,
            ),
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
            "oled_shares_ext_power": bool(kb_def.rgb_hw.oled_shares_ext_power),
            "anti_burnin": bool(model.oled.anti_burnin),
            # ── Options avancées (onglet KFM "Options avancées") ──────────────
            "adv_keyboard_name": str(model.advanced.keyboard_name).strip(),
            "adv_nkro_enabled": bool(model.advanced.nkro_enabled),
            "adv_hid_indicators_enabled": bool(model.advanced.hid_indicators_enabled),
            "adv_usb_boot_protocol": bool(model.advanced.usb_boot_protocol),
            "adv_ble_passkey_entry": bool(model.advanced.ble_passkey_entry),
            "adv_battery_report_interval_s": (
                int(model.advanced.battery_report_interval_s)
                if model.advanced.battery_report_interval_s != 60 else 0
            ),
            "adv_soft_off_enabled": bool(model.advanced.soft_off_enabled),
            "adv_tap_dance_enabled": bool(model.advanced.tap_dance_enabled),
            "adv_sticky_key_enabled": bool(model.advanced.sticky_key_enabled),
            "adv_rgb_hue_start": int(model.advanced.rgb_hue_start),
            "adv_rgb_on_start": bool(model.advanced.rgb_on_start),
            "adv_rgb_auto_off_idle": bool(model.advanced.rgb_auto_off_idle),
            "adv_rgb_auto_off_usb": bool(model.advanced.rgb_auto_off_usb),
            "adv_pointing_enabled": bool(model.advanced.pointing_enabled),
            "adv_pointing_smooth_scroll": bool(model.advanced.pointing_smooth_scroll),
            "physical_layout_keys": physical_layout_keys,
            "idle_sleep_ms": idle_sleep_ms,
            "studio_transport": (
                model.keyboard.zmk_studio_transport
                if model.keyboard.zmk_studio_transport in ("ble", "usb")
                else "ble"
            ),
            "debug_logging": bool(model.keyboard.debug_logging),
            "show_battery_percentage": bool(model.oled.show_battery_percentage),
            # OLED custom screen (Phase 1 — image-only) : si au moins une image
            # est placée par l'utilisateur sur le canvas, on bascule de
            # STATUS_SCREEN_BUILT_IN vers STATUS_SCREEN_CUSTOM dans shield.conf
            # et on génère un (ou deux pour split) status_screen.c qui affiche
            # le composite plein écran en LVGL INDEXED_1BIT.
            # Si use_builtin_screen est coché, on force STATUS_SCREEN_BUILT_IN
            # quoi qu'il y ait dans le canvas — l'utilisateur a explicitement
            # choisi le screen natif ZMK.
            "oled_custom_screen": (
                has_display
                and not model.oled.use_builtin_screen
                and (
                    _side_has_custom_oled(model.oled.left)
                    or (kb_def.split and _side_has_custom_oled(model.oled.right))
                )
            ),
            "oled_custom_left": (
                has_display
                and not model.oled.use_builtin_screen
                and _side_has_custom_oled(model.oled.left)
            ),
            "oled_custom_right": (
                has_display
                and not model.oled.use_builtin_screen
                and kb_def.split
                and _side_has_custom_oled(model.oled.right)
            ),
            # Phase 3 — animation multi-frames LVGL : retourne {frames, delays, animated}
            # par côté. Pour les écrans sans image (widgets seuls), `animated=False` et la
            # liste contient un seul frame noir — affiché en background mais inoffensif.
            "oled_animation_left": (
                _build_animation_context(model.oled.left.images)
                if has_display and _side_has_custom_oled(model.oled.left)
                else {"frames": [], "delays": [], "animated": False}
            ),
            "oled_animation_right": (
                _build_animation_context(model.oled.right.images)
                if has_display and kb_def.split and _side_has_custom_oled(model.oled.right)
                else {"frames": [], "delays": [], "animated": False}
            ),
            # Phase 4 — animation par-couche : si au moins une image a layer != -1,
            # on bascule vers le pipeline layer-aware avec listener
            # zmk_layer_state_changed et arrays par-couche.
            "oled_layered_left": (
                _build_layered_animation_context(model.oled.left.images)
                if has_display and _side_has_custom_oled(model.oled.left)
                else {"layers": [], "has_layer_aware": False}
            ),
            "oled_layered_right": (
                _build_layered_animation_context(model.oled.right.images)
                if has_display and kb_def.split and _side_has_custom_oled(model.oled.right)
                else {"layers": [], "has_layer_aware": False}
            ),
            # Phase 2 — widgets ZMK natifs par côté.
            # En non-split, "left" est la seule moitié = central. En split, gauche = central,
            # droite = peripheral. Les widgets sont instanciés via `zmk_widget_*_init` côté C.
            "oled_widgets_left": _build_widgets_context(model.oled.left, "central"),
            "oled_widgets_right": (
                _build_widgets_context(model.oled.right, "peripheral") if kb_def.split else []
            ),
            # Flag image-only séparé pour le template (permet un `if` distinct du flag widgets)
            "oled_has_image_left": (
                has_display and any(img.frames for img in model.oled.left.images)
            ),
            "oled_has_image_right": (
                has_display and kb_def.split
                and any(img.frames for img in model.oled.right.images)
            ),
        }
