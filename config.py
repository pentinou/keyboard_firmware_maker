"""Configuration globale — chemins de ressources résolus pour PyInstaller.

Ce module expose BASE_DIR et les chemins dérivés.
Utilise sys._MEIPASS quand l'application est packagée par PyInstaller,
ou Path(__file__).parent (racine du projet) en développement.

Usage dans n'importe quel module :
    from config import KEYBOARDS_DIR, TEMPLATES_DIR, ASSETS_DIR
"""
from __future__ import annotations

import sys
from pathlib import Path

# Résolution PyInstaller : _MEIPASS est défini dans un bundle frozen
# En développement, on utilise le répertoire du projet (parent de config.py)
BASE_DIR: Path = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))

KEYBOARDS_DIR: Path = BASE_DIR / "keyboards"
TEMPLATES_DIR: Path = BASE_DIR / "templates"
TOOLCHAIN_DIR: Path = BASE_DIR / "toolchain"
ASSETS_DIR: Path = BASE_DIR / "assets"
