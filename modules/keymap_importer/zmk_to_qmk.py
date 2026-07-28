"""zmk_to_qmk.py — lecture d'un keymap ZMK (.keymap) et conversion vers QMK.

Sens inverse de `vial_to_zmk`. Deux étapes séparées :

1. `parse_zmk_keymap()` extrait les couches et leurs bindings du devicetree.
   Le parseur est volontairement minimal — il cible la forme produite par ZMK
   et par KFM (`keymap { compatible = "zmk,keymap"; layer { bindings = <…> } }`),
   pas le langage devicetree complet.
2. `convert_zmk_layer_to_qmk()` traduit chaque binding en keycode QMK.

Les fonctionnalités propres à ZMK n'ont pas d'équivalent QMK (`&bt`, `&out`,
`&ext_power`, `&studio_unlock`) : elles deviennent `KC_NO` et sont listées dans
le `ConversionReport` plutôt que d'échouer silencieusement.
"""
from __future__ import annotations

import logging
import re

from modules.keymap_importer.common import ConversionReport

logger = logging.getLogger(__name__)

# Table inverse de _QMK_TO_ZMK_KEY. Un keycode ZMK peut avoir plusieurs noms
# QMK ; on choisit la forme canonique courte, celle que Vial affiche.
_ZMK_TO_QMK_KEY: dict[str, str] = {
    **{c: f"KC_{c}" for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"},
    **{f"N{i}": f"KC_{i}" for i in range(10)},
    # Modifiers
    "LSHFT": "KC_LSFT", "RSHFT": "KC_RSFT",
    "LCTRL": "KC_LCTL", "RCTRL": "KC_RCTL",
    "LALT": "KC_LALT", "RALT": "KC_RALT",
    "LGUI": "KC_LGUI", "RGUI": "KC_RGUI",
    # Spéciales
    "ESC": "KC_ESC", "TAB": "KC_TAB", "RET": "KC_ENT", "ENTER": "KC_ENT",
    "SPACE": "KC_SPC", "BSPC": "KC_BSPC", "DEL": "KC_DEL", "INS": "KC_INS",
    "CAPS": "KC_CAPS", "HOME": "KC_HOME", "END": "KC_END",
    "PG_UP": "KC_PGUP", "PG_DN": "KC_PGDN",
    "UP": "KC_UP", "DOWN": "KC_DOWN", "LEFT": "KC_LEFT", "RIGHT": "KC_RGHT",
    "PSCRN": "KC_PSCR", "SLCK": "KC_SCRL", "PAUSE_BREAK": "KC_PAUS",
    "K_APP": "KC_APP",
    # Ponctuation
    "MINUS": "KC_MINS", "EQUAL": "KC_EQL", "LBKT": "KC_LBRC", "RBKT": "KC_RBRC",
    "BSLH": "KC_BSLS", "SEMI": "KC_SCLN", "SQT": "KC_QUOT", "GRAVE": "KC_GRV",
    "COMMA": "KC_COMM", "DOT": "KC_DOT", "FSLH": "KC_SLSH",
    # Shiftées
    "EXCL": "KC_EXLM", "AT": "KC_AT", "HASH": "KC_HASH", "DLLR": "KC_DLR",
    "PRCNT": "KC_PERC", "CARET": "KC_CIRC", "AMPS": "KC_AMPR", "STAR": "KC_ASTR",
    "LPAR": "KC_LPRN", "RPAR": "KC_RPRN", "UNDER": "KC_UNDS", "PLUS": "KC_PLUS",
    "LBRC": "KC_LCBR", "RBRC": "KC_RCBR", "PIPE": "KC_PIPE", "COLON": "KC_COLN",
    "DQT": "KC_DQUO", "TILDE": "KC_TILD", "LT": "KC_LT", "GT": "KC_GT",
    "QMARK": "KC_QUES",
    # Fonctions
    **{f"F{i}": f"KC_F{i}" for i in range(1, 25)},
    # Pavé numérique
    "KP_N0": "KC_P0", "KP_N1": "KC_P1", "KP_N2": "KC_P2", "KP_N3": "KC_P3",
    "KP_N4": "KC_P4", "KP_N5": "KC_P5", "KP_N6": "KC_P6", "KP_N7": "KC_P7",
    "KP_N8": "KC_P8", "KP_N9": "KC_P9",
    "KP_PLUS": "KC_PPLS", "KP_MINUS": "KC_PMNS", "KP_MULTIPLY": "KC_PAST",
    "KP_DIVIDE": "KC_PSLS", "KP_ENTER": "KC_PENT", "KP_DOT": "KC_PDOT",
    "KP_NUM": "KC_NUM",
    # Média / système
    "C_MUTE": "KC_MUTE", "C_VOL_UP": "KC_VOLU", "C_VOL_DN": "KC_VOLD",
    "C_PP": "KC_MPLY", "C_NEXT": "KC_MNXT", "C_PREV": "KC_MPRV",
    "C_STOP": "KC_MSTP",
    "C_BRI_UP": "KC_BRIU", "C_BRI_DN": "KC_BRID",
    "K_CMENU": "KC_APP", "C_AL_CALC": "KC_CALC",
}

# Bindings ZMK sans paramètre, traduisibles tels quels.
_ZMK_SIMPLE_TO_QMK: dict[str, str] = {
    "&trans": "KC_TRNS",
    "&none": "KC_NO",
    "&bootloader": "QK_BOOT",
    "&sys_reset": "QK_RBT",
    "&caps_word": "CW_TOGG",
    "&key_repeat": "QK_REP",
}

# Comportements ZMK sans contrepartie QMK, avec la raison montrée à l'utilisateur.
_ZMK_UNSUPPORTED: dict[str, str] = {
    "&bt": "Bluetooth ZMK — QMK n'a pas de gestion de profils BLE",
    "&out": "Sélection de sortie USB/BLE — propre à ZMK",
    "&ext_power": "Contrôle de l'alimentation externe — propre à ZMK",
    "&studio_unlock": "Déverrouillage ZMK Studio — propre à ZMK",
    "&soft_off": "Extinction logicielle ZMK — pas d'équivalent QMK direct",
    "&rgb_ug": "RGB underglow ZMK — les codes RGB QMK diffèrent",
}

_LAYER_BLOCK_RE = re.compile(
    r"(?P<name>[A-Za-z_][\w-]*)\s*\{[^{}]*?bindings\s*=\s*<(?P<bindings>.*?)>\s*;",
    re.DOTALL,
)
_COMMENT_BLOCK_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
_COMMENT_LINE_RE = re.compile(r"//[^\n]*")
_BINDING_RE = re.compile(r"&\w+(?:\s+(?!&)[^\s&]+)*")


def _strip_comments(text: str) -> str:
    return _COMMENT_LINE_RE.sub("", _COMMENT_BLOCK_RE.sub("", text))


def parse_zmk_keymap(content: str) -> list[dict]:
    """Extrait les couches d'un fichier .keymap ZMK.

    Returns:
        Liste ordonnée de `{"name": str, "bindings": list[str]}`. Vide si le
        fichier ne contient aucun bloc `bindings = <…>` exploitable.
    """
    text = _strip_comments(content)

    # On se limite au nœud keymap quand il est identifiable, pour ne pas
    # ramasser les combos, macros et behaviors qui ont aussi des `bindings`.
    keymap_start = text.find('compatible = "zmk,keymap"')
    if keymap_start != -1:
        text = text[keymap_start:]

    layers: list[dict] = []
    for match in _LAYER_BLOCK_RE.finditer(text):
        raw = match.group("bindings")
        bindings = [b.strip() for b in _BINDING_RE.findall(raw)]
        if not bindings:
            continue
        layers.append({"name": match.group("name"), "bindings": bindings})
    return layers


def convert_zmk_binding_to_qmk(binding: str) -> str | None:
    """Traduit un binding ZMK en keycode QMK.

    Retourne None si le binding n'a pas d'équivalent — l'appelant décide quoi
    en faire (`KC_NO` + entrée dans le rapport).
    """
    if not isinstance(binding, str):
        return None
    b = " ".join(binding.split())
    if not b:
        return None

    if b in _ZMK_SIMPLE_TO_QMK:
        return _ZMK_SIMPLE_TO_QMK[b]

    parts = b.split()
    behavior = parts[0]
    args = parts[1:]

    if behavior == "&kp" and len(args) == 1:
        return _ZMK_TO_QMK_KEY.get(args[0])
    if behavior == "&mo" and len(args) == 1 and args[0].isdigit():
        return f"MO({args[0]})"
    if behavior == "&tog" and len(args) == 1 and args[0].isdigit():
        return f"TG({args[0]})"
    if behavior == "&to" and len(args) == 1 and args[0].isdigit():
        return f"TO({args[0]})"
    if behavior == "&lt" and len(args) == 2 and args[0].isdigit():
        inner = _ZMK_TO_QMK_KEY.get(args[1])
        return f"LT({args[0]}, {inner})" if inner else None
    if behavior == "&mt" and len(args) == 2:
        mod, inner = _ZMK_TO_QMK_KEY.get(args[0]), _ZMK_TO_QMK_KEY.get(args[1])
        # QMK exprime le mod-tap par des macros dédiées (MT() attend un mod brut)
        if mod and inner:
            return f"MT({args[0]}, {inner})"
        return None
    if behavior == "&sk" and len(args) == 1:
        inner = _ZMK_TO_QMK_KEY.get(args[0])
        return f"OSM(MOD_{args[0]})" if inner else None
    if behavior == "&sl" and len(args) == 1 and args[0].isdigit():
        return f"OSL({args[0]})"

    return None


def _unsupported_reason(binding: str) -> str:
    behavior = binding.split()[0] if binding.split() else binding
    if behavior in _ZMK_UNSUPPORTED:
        return _ZMK_UNSUPPORTED[behavior]
    return "Comportement ZMK inconnu ou sans équivalent QMK"


def convert_zmk_layers_to_qmk(
    layers: list[dict],
    report: ConversionReport | None = None,
) -> tuple[list[list[str]], ConversionReport]:
    """Convertit les couches ZMK parsées en couches de keycodes QMK.

    Returns:
        `(couches, rapport)` — chaque couche est une liste plate de keycodes,
        dans l'ordre des bindings ZMK (donc l'ordre du `LAYOUT()` du shield).
    """
    report = report or ConversionReport()
    qmk_layers: list[list[str]] = []

    for layer_idx, layer in enumerate(layers):
        row: list[str] = []
        for pos, binding in enumerate(layer.get("bindings", [])):
            qmk = convert_zmk_binding_to_qmk(binding)
            if qmk is None:
                report.drop(layer_idx, pos, binding, _unsupported_reason(binding))
                row.append("KC_NO")
            else:
                report.converted += 1
                row.append(qmk)
        qmk_layers.append(row)

    return qmk_layers, report
