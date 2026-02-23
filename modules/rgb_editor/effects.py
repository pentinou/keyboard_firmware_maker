# modules/rgb_editor/effects.py
"""Définitions des types d'effets RGB disponibles.

Module pur Python sans dépendance Qt.
"""
from __future__ import annotations

# Chaque entrée : (identifiant snake_case, libellé affiché)
EFFECT_TYPES: tuple[tuple[str, str], ...] = (
    ("static", "Couleur statique uniforme"),
    ("ripple", "Ripple au keystroke"),
)
