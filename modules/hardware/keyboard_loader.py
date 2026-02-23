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
class McuOption:
    """Description d'un microcontrôleur compatible avec un modèle de clavier."""

    id: str
    display_name: str
    description: str = ""


@dataclass
class KeyboardDefinition:
    """Définition complète d'un modèle de clavier chargée depuis un fichier YAML."""

    model: str
    display_name: str
    description: str
    mcu_options: list[McuOption] = field(default_factory=list)
    capabilities: dict[str, bool] = field(default_factory=dict)
    matrix: dict[str, int] = field(default_factory=lambda: {"rows": 5, "cols": 6})


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

    return KeyboardDefinition(
        model=data["model"],
        display_name=data["display_name"],
        description=data.get("description", ""),
        mcu_options=mcu_options,
        capabilities=data.get("capabilities", {}),
        matrix={"rows": rows, "cols": cols},
    )


def load_all_keyboards(keyboards_dir: Path) -> list[KeyboardDefinition]:
    """Charge tous les fichiers *.yaml du répertoire keyboards/.

    Les claviers invalides sont ignorés (log warning) sans interrompre le chargement.

    Args:
        keyboards_dir: Répertoire contenant les fichiers YAML de définition.

    Returns:
        Liste de KeyboardDefinition triée alphabétiquement par display_name.
    """
    keyboards: list[KeyboardDefinition] = []

    for yaml_path in sorted(keyboards_dir.glob("*.yaml")):
        try:
            keyboards.append(load_keyboard(yaml_path))
        except Exception as exc:
            logger.warning("Impossible de charger %s : %s", yaml_path.name, exc)

    return sorted(keyboards, key=lambda kb: kb.display_name)
