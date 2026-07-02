"""Conversion best-effort d'un keymap Vial-QMK vers un keymap ZMK.

Le format Vial est un JSON avec :
  - `layout` : liste de N layers, chaque layer = matrice de bindings QMK
  - `encoder_layout` : liste de N layers, chaque layer = liste d'encodeurs (CCW, CW)

La sortie est un dict compatible avec `KeyboardDefinition.default_keymap_zmk` :
  {"default": [[row 0 bindings], [row 1], ...], "lower": [...], "raise": [...]}

Chaque binding ZMK est une string avec son préfixe (`&kp`, `&trans`, `&mo`, etc.).

Limitations :
- Best-effort sur les keycodes RGB QMK (mapping partiel vers `&rgb_ug RGB_*`)
- Pas de support tap-dance, combo, key-override (QMK avancé) — convertis en `&none`
- KC_CALC, BL_TOGG, QK_CLEAR_EEPROM et autres pas d'équivalent ZMK → `&none`
"""
from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# Références de couche produites par la conversion (MO/TG/TO et LT).
_LAYER_REF_RE = re.compile(r"^&(?:mo|tog|to) (\d+)$")
_LAYER_TAP_RE = re.compile(r"^&lt (\d+) (.+)$")


# Mapping direct QMK keycode → ZMK keycode (sans préfixe).
# Référence : https://zmk.dev/docs/codes/keyboard-keypad
# Pour chaque entrée, le binding final est `&kp <value>`.
_QMK_TO_ZMK_KEY: dict[str, str] = {
    # ── Lettres et chiffres ────────────────────────────────────────────────
    **{f"KC_{c}": c for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"},
    **{f"KC_{i}": f"N{i}" for i in range(10)},
    # ── Modifiers ──────────────────────────────────────────────────────────
    "KC_LSHIFT": "LSHFT", "KC_LSFT": "LSHFT",
    "KC_RSHIFT": "RSHFT", "KC_RSFT": "RSHFT",
    "KC_LCTRL": "LCTRL", "KC_LCTL": "LCTRL",
    "KC_RCTRL": "RCTRL", "KC_RCTL": "RCTRL",
    "KC_LALT": "LALT",
    "KC_RALT": "RALT",
    "KC_LGUI": "LGUI", "KC_LWIN": "LGUI", "KC_LCMD": "LGUI",
    "KC_RGUI": "RGUI", "KC_RWIN": "RGUI", "KC_RCMD": "RGUI",
    # ── Spéciales courantes ────────────────────────────────────────────────
    "KC_ESCAPE": "ESC", "KC_ESC": "ESC",
    "KC_TAB": "TAB",
    "KC_ENTER": "RET", "KC_ENT": "RET",
    "KC_SPACE": "SPACE", "KC_SPC": "SPACE",
    "KC_BSPACE": "BSPC", "KC_BSPC": "BSPC",
    "KC_DELETE": "DEL", "KC_DEL": "DEL",
    "KC_INSERT": "INS", "KC_INS": "INS",
    "KC_CAPS": "CAPS", "KC_CAPSLOCK": "CAPS",
    "KC_HOME": "HOME",
    "KC_END": "END",
    "KC_PGUP": "PG_UP", "KC_PAGE_UP": "PG_UP",
    "KC_PGDN": "PG_DN", "KC_PGDOWN": "PG_DN", "KC_PAGE_DOWN": "PG_DN",
    "KC_UP": "UP",
    "KC_DOWN": "DOWN",
    "KC_LEFT": "LEFT",
    "KC_RIGHT": "RIGHT",
    "KC_PRINT_SCREEN": "PSCRN", "KC_PSCR": "PSCRN",
    "KC_SCROLL_LOCK": "SLCK", "KC_SCRL": "SLCK",
    "KC_PAUSE": "PAUSE_BREAK", "KC_PAUS": "PAUSE_BREAK",
    "KC_APPLICATION": "K_APP", "KC_APP": "K_APP",
    # ── Ponctuation ────────────────────────────────────────────────────────
    "KC_MINUS": "MINUS", "KC_MINS": "MINUS",
    "KC_EQUAL": "EQUAL", "KC_EQL": "EQUAL",
    "KC_LBRACKET": "LBKT", "KC_LBRC": "LBKT",
    "KC_RBRACKET": "RBKT", "KC_RBRC": "RBKT",
    "KC_BSLASH": "BSLH", "KC_BSLS": "BSLH",
    "KC_SCOLON": "SEMI", "KC_SCLN": "SEMI",
    "KC_QUOTE": "SQT", "KC_QUOT": "SQT",
    "KC_GRAVE": "GRAVE", "KC_GRV": "GRAVE",
    "KC_COMMA": "COMMA", "KC_COMM": "COMMA",
    "KC_DOT": "DOT",
    "KC_SLASH": "FSLH", "KC_SLSH": "FSLH",
    # ── Shifted (Vial direct, pour confort) ────────────────────────────────
    "KC_EXCLAIM": "EXCL", "KC_EXLM": "EXCL",
    "KC_AT": "AT_SIGN", "KC_AT_SIGN": "AT_SIGN",
    "KC_HASH": "HASH",
    "KC_DOLLAR": "DLLR", "KC_DLR": "DLLR",
    "KC_PERCENT": "PRCNT", "KC_PERC": "PRCNT",
    "KC_CIRCUMFLEX": "CARET", "KC_CIRC": "CARET",
    "KC_AMPERSAND": "AMPS", "KC_AMPR": "AMPS",
    "KC_ASTERISK": "STAR", "KC_ASTR": "STAR",
    "KC_LEFT_PAREN": "LPAR", "KC_LPRN": "LPAR",
    "KC_RIGHT_PAREN": "RPAR", "KC_RPRN": "RPAR",
    # ── Fonctions F1-F12 ───────────────────────────────────────────────────
    **{f"KC_F{i}": f"F{i}" for i in range(1, 25)},
    # ── Keypad ─────────────────────────────────────────────────────────────
    "KC_KP_PLUS": "KP_PLUS",
    "KC_KP_MINUS": "KP_MINUS",
    "KC_KP_ASTERISK": "KP_MULTIPLY",
    "KC_KP_SLASH": "KP_DIVIDE",
    "KC_KP_EQUAL": "KP_EQUAL",
    "KC_KP_ENTER": "KP_ENTER",
    "KC_KP_DOT": "KP_DOT",
    **{f"KC_KP_{i}": f"KP_N{i}" for i in range(10)},
    "KC_NUMLOCK": "KP_NLCK", "KC_NUM": "KP_NLCK",
    # ── Media / audio ──────────────────────────────────────────────────────
    "KC_AUDIO_MUTE": "C_MUTE", "KC_MUTE": "C_MUTE",
    "KC_AUDIO_VOL_UP": "C_VOL_UP", "KC_VOLU": "C_VOL_UP",
    "KC_AUDIO_VOL_DOWN": "C_VOL_DN", "KC_VOLD": "C_VOL_DN",
    "KC_MEDIA_PLAY_PAUSE": "C_PP", "KC_MPLY": "C_PP",
    "KC_MEDIA_STOP": "C_STOP", "KC_MSTP": "C_STOP",
    "KC_MEDIA_NEXT_TRACK": "C_NEXT", "KC_MNXT": "C_NEXT",
    "KC_MEDIA_PREV_TRACK": "C_PREV", "KC_MPRV": "C_PREV",
    "KC_BRIGHTNESS_UP": "C_BRI_UP", "KC_BRIU": "C_BRI_UP",
    "KC_BRIGHTNESS_DOWN": "C_BRI_DN", "KC_BRID": "C_BRI_DN",
    # ── Calculatrice et autres apps ────────────────────────────────────────
    "KC_CALC": "C_AL_CALC", "KC_CALCULATOR": "C_AL_CALC",
    "KC_MAIL": "C_AL_EMAIL",
    "KC_MY_COMPUTER": "C_AL_MY_COMPUTER", "KC_MYCM": "C_AL_MY_COMPUTER",
    "KC_WWW_HOME": "C_AL_WWW",
    "KC_WWW_BACK": "C_AC_BACK",
    "KC_WWW_FORWARD": "C_AC_FORWARD",
    "KC_WWW_REFRESH": "C_AC_REFRESH",
}


# Mapping QMK RGB underglow → ZMK rgb_ug. Best-effort.
# Référence : https://zmk.dev/docs/keymaps/behaviors/underglow
# ZMK n'a pas autant d'effets RGB que QMK : les modes spécifiques QMK
# (RGB_M_B = breathe, RGB_M_R = rainbow, etc.) sont approximés au mieux par
# `RGB_EFF` (= cycle effect) — l'utilisateur peut alors cycler jusqu'au mode
# voulu. Mieux qu'un `&none` muet.
_QMK_TO_ZMK_RGB: dict[str, str] = {
    "RGB_TOG": "RGB_TOG",
    "RGB_HUI": "RGB_HUI",
    "RGB_HUD": "RGB_HUD",
    "RGB_SAI": "RGB_SAI",
    "RGB_SAD": "RGB_SAD",
    "RGB_VAI": "RGB_BRI",
    "RGB_VAD": "RGB_BRD",
    "RGB_SPI": "RGB_SPI",
    "RGB_SPD": "RGB_SPD",
    "RGB_MOD": "RGB_EFF",
    "RGB_RMOD": "RGB_EFR",
    # Effets QMK spécifiques (RGB_M_*) → fallback sur cycle d'effet
    # (l'utilisateur peut presser plusieurs fois pour atteindre l'effet voulu).
    "RGB_M_P": "RGB_EFF",   # plain (solid)
    "RGB_M_B": "RGB_EFF",   # breathing
    "RGB_M_R": "RGB_EFF",   # rainbow
    "RGB_M_SW": "RGB_EFF",  # swirl
    "RGB_M_SN": "RGB_EFF",  # snake
    "RGB_M_K": "RGB_EFF",   # knight
    "RGB_M_X": "RGB_EFF",   # xmas
    "RGB_M_G": "RGB_EFF",   # gradient
    "RGB_M_T": "RGB_EFF",   # test
    "RGB_M_TW": "RGB_EFF",  # twinkle
    # RGB Matrix (QMK 0.21+) — ZMK n'a pas d'équivalent direct, on mappe
    # comme l'underglow le plus proche.
    "RM_TOGG": "RGB_TOG",
    "RM_NEXT": "RGB_EFF",
    "RM_PREV": "RGB_EFR",
    "RM_HUEU": "RGB_HUI",
    "RM_HUED": "RGB_HUD",
    "RM_SATU": "RGB_SAI",
    "RM_SATD": "RGB_SAD",
    "RM_VALU": "RGB_BRI",
    "RM_VALD": "RGB_BRD",
    "RM_SPDU": "RGB_SPI",
    "RM_SPDD": "RGB_SPD",
}


# System / firmware control
_QMK_TO_ZMK_SYS: dict[str, str] = {
    "QK_BOOT": "&bootloader",
    "RESET": "&bootloader",
    "QK_REBOOT": "&sys_reset",
    "REBOOT": "&sys_reset",
    # BL_TOGG (backlight toggle QMK) — ZMK n'a pas de backlight séparé,
    # on mappe sur le toggle underglow le plus proche fonctionnellement.
    "BL_TOGG": "&rgb_ug RGB_TOG",
    "BL_TOG": "&rgb_ug RGB_TOG",
}


def convert_qmk_keycode_to_zmk(qmk_kc: str) -> str:
    """Convertit un keycode QMK en binding ZMK complet (avec préfixe `&...`).

    Retourne `&none` pour les keycodes inconnus ou sans équivalent ZMK.
    """
    if not isinstance(qmk_kc, str):
        return "&none"
    kc = qmk_kc.strip()
    if not kc:
        return "&none"

    # Trans (héritage layer du dessous)
    if kc in ("KC_TRNS", "KC_TRANSPARENT", "_______"):
        return "&trans"
    # No-op
    if kc in ("KC_NO", "XXXXXXX"):
        return "&none"

    # MO(N) — momentary layer
    if kc.startswith("MO(") and kc.endswith(")"):
        try:
            n = int(kc[3:-1])
            return f"&mo {n}"
        except ValueError:
            return "&none"
    # LT(N, KC) — layer-tap
    if kc.startswith("LT(") and kc.endswith(")"):
        inner = kc[3:-1].split(",")
        if len(inner) == 2:
            try:
                n = int(inner[0].strip())
                inner_kc = inner[1].strip()
                zmk_inner = convert_qmk_keycode_to_zmk(inner_kc)
                # Si zmk_inner commence par "&kp", extraire le keycode pour &lt
                if zmk_inner.startswith("&kp "):
                    return f"&lt {n} {zmk_inner[4:]}"
            except ValueError:
                pass
        return "&none"
    # TG(N) — toggle layer (ZMK : &tog N)
    if kc.startswith("TG(") and kc.endswith(")"):
        try:
            n = int(kc[3:-1])
            return f"&tog {n}"
        except ValueError:
            return "&none"
    # TO(N) — to layer
    if kc.startswith("TO(") and kc.endswith(")"):
        try:
            n = int(kc[3:-1])
            return f"&to {n}"
        except ValueError:
            return "&none"

    # Système / firmware
    if kc in _QMK_TO_ZMK_SYS:
        return _QMK_TO_ZMK_SYS[kc]
    # RGB underglow
    if kc in _QMK_TO_ZMK_RGB:
        return f"&rgb_ug {_QMK_TO_ZMK_RGB[kc]}"
    # Clé standard
    if kc in _QMK_TO_ZMK_KEY:
        return f"&kp {_QMK_TO_ZMK_KEY[kc]}"

    # Inconnu — log et fallback
    logger.debug("QMK keycode sans équivalent ZMK : %s", kc)
    return "&none"


def _normalize_layer_rows(
    qmk_layer: list[list[str]],
    encoder_cols_per_row: dict[int, set[int]] | None = None,
) -> list[list[str]]:
    """Convertit un layer QMK Vial (10 rows × 6 cols pour Sofle split combiné)
    vers le format ZMK 5 rows × N cols utilisées par row.

    Args:
        qmk_layer: matrice Vial (left puis right concaténés en N×6).
        encoder_cols_per_row: pour chaque row, set des col indexes (matrice
            combinée) qui sont des encodeurs et doivent être filtrés.
            Si None, on garde toutes les positions (= comportement legacy).

    Pourquoi filtrer les encodeurs : sur Sofle, la row thumb a 6 touches par
    moitié en QMK (5 thumbs + 1 clic encodeur = KC_MUTE / KC_CALC), mais en
    ZMK le clic encodeur n'est pas dans le keymap (il est géré via le sensor).
    Sans filtrage, la touche SPACE (juste après le slot encodeur) se décale.
    """
    n_rows_qmk = len(qmk_layer)
    if n_rows_qmk == 0:
        return []
    half = n_rows_qmk // 2
    combined = []
    for r in range(half):
        left = qmk_layer[r] if r < n_rows_qmk else []
        right = qmk_layer[r + half] if r + half < n_rows_qmk else []
        full_row = list(left) + list(right)
        # Filtrer les positions encodeur si fournies
        if encoder_cols_per_row and r in encoder_cols_per_row:
            enc_cols = encoder_cols_per_row[r]
            full_row = [kc for c, kc in enumerate(full_row) if c not in enc_cols]
        combined.append(full_row)
    return combined


def convert_vial_to_zmk_keymap(
    vial_data: dict[str, Any],
    layer_names: list[str] | None = None,
    encoder_cols_per_row: dict[int, set[int]] | None = None,
) -> dict[str, list[list[str]]]:
    """Convertit un keymap Vial-QMK complet en keymap ZMK.

    Args:
        vial_data: contenu JSON du fichier Vial (.json export)
        layer_names: noms ZMK des layers dans l'ordre. Défaut: ["default", "lower", "raise", "bluetooth"].
        encoder_cols_per_row: positions encodeur à filtrer par row, pour aligner
            avec le keymap ZMK qui n'inclut pas les clics d'encodeur dans le keymap
            (gérés via sensor-bindings). Construit depuis kb_def.layout côté générateur.

    Returns:
        dict {layer_name: [[bindings row 0], [row 1], ...]} avec bindings ZMK
        sous forme de strings (`&kp ESC`, `&trans`, etc.).
    """
    if layer_names is None:
        layer_names = ["default", "lower", "raise", "bluetooth"]

    qmk_layers = vial_data.get("layout", [])
    result: dict[str, list[list[str]]] = {}
    for idx, name in enumerate(layer_names):
        if idx >= len(qmk_layers):
            break
        qmk_layer = qmk_layers[idx]
        rows_combined = _normalize_layer_rows(qmk_layer, encoder_cols_per_row)
        zmk_rows = []
        for row in rows_combined:
            zmk_rows.append([convert_qmk_keycode_to_zmk(kc) for kc in row])
        result[name] = zmk_rows

    # Le keymap ZMK généré a exactement len(layer_names) couches (0..N-1).
    # Les layers Vial au-delà sont perdus, et toute référence MO/LT/TG/TO
    # vers une couche non générée serait un no-op silencieux au runtime —
    # on la neutralise explicitement pour que le comportement soit prévisible.
    dropped_layers = len(qmk_layers) - len(layer_names)
    if dropped_layers > 0:
        logger.warning(
            "Import Vial : %d layer(s) au-delà de la couche %d ignoré(s) "
            "(le keymap ZMK généré n'a que %d couches).",
            dropped_layers, len(layer_names) - 1, len(layer_names),
        )
    neutralized = _neutralize_out_of_range_layer_refs(result, max_layer=len(layer_names) - 1)
    if neutralized:
        logger.warning(
            "Import Vial : %d binding(s) référençant une couche inexistante "
            "neutralisé(s) (MO/TG/TO → &none, LT → &kp).", neutralized,
        )
    return result


def _neutralize_out_of_range_layer_refs(
    keymap: dict[str, list[list[str]]],
    max_layer: int,
) -> int:
    """Neutralise les bindings pointant vers une couche > max_layer.

    `&mo/&tog/&to N` → `&none` ; `&lt N X` → `&kp X` (le tap est préservé).
    Retourne le nombre de bindings modifiés.
    """
    count = 0
    for rows in keymap.values():
        for row in rows:
            for i, binding in enumerate(row):
                m = _LAYER_REF_RE.match(binding)
                if m and int(m.group(1)) > max_layer:
                    row[i] = "&none"
                    count += 1
                    continue
                m = _LAYER_TAP_RE.match(binding)
                if m and int(m.group(1)) > max_layer:
                    row[i] = f"&kp {m.group(2)}"
                    count += 1
    return count
