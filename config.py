"""Configuration globale — chemins de ressources résolus pour PyInstaller.

Ce module expose BASE_DIR et les chemins dérivés.
Utilise sys._MEIPASS quand l'application est packagée par PyInstaller,
ou Path(__file__).parent (racine du projet) en développement.

Expose aussi CACHE_DIR et ses sous-répertoires : tout ce que l'application
télécharge ou génère hors du projet vit sous ~/.keyboard_firmware_maker/.

Usage dans n'importe quel module :
    from config import KEYBOARDS_DIR, TEMPLATES_DIR, ASSETS_DIR
    from config import CACHE_DIR, VIAL_QMK_DIR
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

# ── Cache utilisateur ────────────────────────────────────────────────────────
# Contenu téléchargé (vial-qmk, MSYS2, toolchain ARM, workspace ZMK) et données
# créées par l'utilisateur (claviers custom). Jamais dans le répertoire du projet.
CACHE_DIR: Path = Path.home() / ".keyboard_firmware_maker"

VIAL_QMK_DIR: Path = CACHE_DIR / "vial-qmk"
VIAL_QMK_INDEX_FILE: Path = CACHE_DIR / "vial-qmk-index.json"
CUSTOM_KEYBOARDS_DIR: Path = CACHE_DIR / "custom_keyboards"
ZMK_WORKSPACE_DIR: Path = CACHE_DIR / "zmk-workspace"
DOWNLOADED_TOOLCHAIN_DIR: Path = CACHE_DIR / "toolchain" / "windows"
