"""common.py — détection du format d'un keymap importé et rapport de conversion.

Deux formats sont acceptés à l'import :

- **Vial** (`.vil`, `.json`) — ce qu'exporte vial.rocks. Contient des keycodes
  QMK (`KC_A`, `MO(1)`, …) dans une matrice `layout[couche][ligne][colonne]`.
- **ZMK** (`.keymap`) — le devicetree d'un zmk-config. Contient des bindings
  (`&kp A`, `&mo 1`, …) sous forme de listes plates par couche.

Chaque conversion produit un `ConversionReport` : ce qui a été repris, ce qui a
été abandonné faute d'équivalent, et pourquoi. L'utilisateur voit ce rapport
avant que l'import soit appliqué au projet.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

FORMAT_VIAL = "vial"
FORMAT_ZMK = "zmk"
FORMAT_UNKNOWN = "unknown"


@dataclass
class DroppedBinding:
    """Un binding qui n'a pas pu être converti vers le firmware cible."""

    layer: int
    position: int
    source: str
    reason: str


@dataclass
class ConversionReport:
    """Bilan d'une conversion de keymap entre firmwares."""

    converted: int = 0
    dropped: list[DroppedBinding] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def has_losses(self) -> bool:
        return bool(self.dropped or self.warnings)

    def drop(self, layer: int, position: int, source: str, reason: str) -> None:
        self.dropped.append(DroppedBinding(layer=layer, position=position, source=source, reason=reason))


def detect_format(path: Path, content: str | None = None) -> str:
    """Identifie le format d'un fichier de keymap.

    Le contenu prime sur l'extension : un `.json` peut être n'importe quoi, et
    un keymap ZMK est parfois enregistré sans extension.
    """
    if content is None:
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return FORMAT_UNKNOWN

    stripped = content.lstrip()

    # Vial : JSON avec une clé "layout" (matrice de keycodes par couche)
    if stripped.startswith("{"):
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            return FORMAT_UNKNOWN
        if isinstance(data, dict) and isinstance(data.get("layout"), list):
            return FORMAT_VIAL
        return FORMAT_UNKNOWN

    # ZMK : devicetree contenant un keymap avec des bindings
    if "bindings" in content and ("compatible" in content or "keymap" in content):
        return FORMAT_ZMK

    return FORMAT_UNKNOWN
