"""vial_to_qmk.py — keymap Vial → couches prêtes pour le `LAYOUT()` de QMK.

Les keycodes d'un fichier Vial sont déjà du QMK : il n'y a pas de traduction,
seulement une **remise en ordre**. Vial stocke une matrice
`layout[couche][ligne][colonne]`, alors que `keymap.c` attend les touches dans
l'ordre du layout macro, celui de `vial_keys` côté générateur.

Une position matrice absente du fichier importé (clavier plus grand que le
keymap fourni) devient `KC_TRNS` et alimente le rapport de conversion.
"""
from __future__ import annotations

import logging
from typing import Any

from modules.keymap_importer.common import ConversionReport

logger = logging.getLogger(__name__)


def convert_vial_to_qmk_layers(
    vial_data: dict[str, Any],
    vial_keys: list[dict],
    max_layers: int = 3,
    report: ConversionReport | None = None,
) -> tuple[list[list[str]], ConversionReport]:
    """Ordonne les keycodes Vial selon les positions du layout macro.

    Args:
        vial_data: contenu du fichier Vial (clé `layout`).
        vial_keys: touches du layout dans l'ordre de `LAYOUT()`, chacune avec
            `matrix_row` et `matrix_col` (construites par le générateur QMK).
        max_layers: nombre de couches du template `keymap.c`.
        report: rapport à compléter, créé si absent.

    Returns:
        `(couches, rapport)` — `couches[i]` a exactement `len(vial_keys)` entrées.
    """
    report = report or ConversionReport()
    source_layers = vial_data.get("layout") or []

    if not isinstance(source_layers, list) or not source_layers:
        report.warnings.append("Le fichier Vial ne contient aucune couche exploitable.")
        return [], report

    if len(source_layers) > max_layers:
        report.warnings.append(
            f"{len(source_layers) - max_layers} couche(s) au-delà de la couche {max_layers - 1} "
            f"ignorée(s) : le firmware généré en compte {max_layers}."
        )

    qmk_layers: list[list[str]] = []
    for layer_idx in range(min(len(source_layers), max_layers)):
        matrix = source_layers[layer_idx]
        row: list[str] = []
        for pos, key in enumerate(vial_keys):
            kc = _lookup(matrix, key.get("matrix_row"), key.get("matrix_col"))
            if kc is None:
                report.drop(
                    layer_idx, pos,
                    f"({key.get('matrix_row')}, {key.get('matrix_col')})",
                    "Position absente du keymap importé",
                )
                row.append("KC_TRNS")
            else:
                report.converted += 1
                row.append(kc)
        qmk_layers.append(row)

    return qmk_layers, report


def _lookup(matrix: Any, row: Any, col: Any) -> str | None:
    """Lit `matrix[row][col]` en tolérant les matrices tronquées ou mal formées."""
    if not isinstance(matrix, list) or not isinstance(row, int) or not isinstance(col, int):
        return None
    if row < 0 or row >= len(matrix):
        return None
    line = matrix[row]
    if not isinstance(line, list) or col < 0 or col >= len(line):
        return None
    value = line[col]
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()
