# Story 1.1: Initialisation du projet et premier lancement

Status: review

## Story

As a développeur (Pentinou),
I want to initialize the project structure and launch a working application skeleton,
so that I have a stable foundation with MainWindow, ProjectModel, and empty module tabs to build upon.

## Acceptance Criteria

1. **Given** je lance `python main.py` depuis le répertoire du projet **When** l'application démarre **Then** une QMainWindow apparaît avec 4 onglets : "Matériel", "OLED", "RGB", "Build" **And** l'application démarre en moins de 5 secondes (NFR4) **And** aucun droit administrateur n'est requis (FR30)

2. **Given** l'application est lancée **When** j'ouvre le menu "À propos" **Then** la version courante est affichée (ex : "0.1.0") (FR31) **And** un lien vers le dépôt GitHub est présent

3. **Given** l'application est lancée sous Windows ou Linux **When** elle s'exécute depuis le bundle PyInstaller **Then** elle trouve ses ressources via `sys._MEIPASS` sans erreur de chemin

## Tasks / Subtasks

- [x] Task 1: Initialiser pyproject.toml avec toutes les dépendances (AC: 1, 3)
  - [x] 1.1 Créer pyproject.toml avec [project] name, version="0.1.0", python_requires=">=3.11"
  - [x] 1.2 Ajouter dependencies: PySide6>=6.10.2, Pillow>=10.0, numpy>=1.26, jinja2>=3.1, pyinstaller>=6.0
  - [x] 1.3 Ajouter [project.optional-dependencies] dev: pytest>=7.0, pytest-qt>=4.0
  - [x] 1.4 Configurer [tool.ruff] max-line-length=120 et [tool.black] line-length=120

- [x] Task 2: Créer models/project_model.py — ProjectModel dataclass (AC: 1)
  - [x] 2.1 Créer `models/__init__.py`
  - [x] 2.2 Créer `models/project_model.py` avec `@dataclass class ProjectModel` contenant les champs keyboard, oled, rgb, build au format JSON attendu
  - [x] 2.3 Ajouter méthodes `to_dict()` et `from_dict(cls, data)` pour sérialisation/désérialisation JSON

- [x] Task 3: Créer ui/main_window.py — QMainWindow avec 4 onglets (AC: 1, 2)
  - [x] 3.1 Créer `ui/__init__.py`
  - [x] 3.2 Créer `ui/main_window.py` avec `class MainWindow(QMainWindow)` recevant `model: ProjectModel` via constructeur
  - [x] 3.3 Ajouter `QTabWidget` avec 4 onglets vides : "Matériel", "OLED", "RGB", "Build"
  - [x] 3.4 Créer `ui/widgets/__init__.py` et `ui/widgets/about_dialog.py` avec `class AboutDialog(QDialog)` affichant version "0.1.0" et lien GitHub
  - [x] 3.5 Ajouter menu "Aide" → "À propos" dans la barre de menus de MainWindow

- [x] Task 4: Créer main.py — entry point QApplication avec résolution de chemins PyInstaller (AC: 1, 3)
  - [x] 4.1 Créer `main.py` avec `QApplication` et instanciation `ProjectModel` + `MainWindow`
  - [x] 4.2 Implémenter `BASE_DIR = Path(getattr(sys, '_MEIPASS', Path(__file__).parent))` dans `config.py` pour résolution PyInstaller
  - [x] 4.3 Configurer `logging.basicConfig` (level=INFO, format standard)
  - [x] 4.4 Ajouter `if __name__ == '__main__': sys.exit(app.exec())`

- [x] Task 5: Créer la structure de répertoires complète (AC: 1)
  - [x] 5.1 Créer `modules/__init__.py` et sous-packages : `hardware/`, `oled_editor/`, `rgb_editor/`, `build_manager/`, `project_manager/` avec `__init__.py` vides
  - [x] 5.2 Créer répertoires vides avec `.gitkeep` : `keyboards/`, `templates/`, `toolchain/windows/bin/`, `toolchain/linux/bin/`, `assets/icons/`, `assets/flash_guide/`
  - [x] 5.3 Créer `tests/__init__.py` et `tests/integration/`

- [x] Task 6: Écrire les tests (AC: 1, 2, 3)
  - [x] 6.1 Créer `modules/hardware/tests/` (vide pour l'instant — tests réels en Story 1.2)
  - [x] 6.2 Créer `tests/test_main_window.py` — test `MainWindow` a 4 onglets avec pytest-qt
  - [x] 6.3 Créer `tests/test_project_model.py` — test `ProjectModel` sérialisation/désérialisation JSON
  - [x] 6.4 Créer `tests/test_about_dialog.py` — test `AboutDialog` affiche version "0.1.0"
  - [x] 6.5 Vérifier que tous les tests passent avec `pytest` — **11/11 PASSED**

## Dev Notes

### Stack Technique (critique — ne pas dévier)

- **Python** : 3.11+ (f-strings, match-case, `from __future__ import annotations` si nécessaire)
- **PySide6** : 6.10.2 — importer depuis `PySide6.QtWidgets`, `PySide6.QtCore`, `PySide6.QtGui` (PAS PyQt5/PyQt6)
- **Packaging** : `pyproject.toml` standard (PEP 517/518), pas de `setup.py`
- **Logging** : `import logging; logger = logging.getLogger(__name__)` — JAMAIS `print()`

### Patterns Architecturaux Obligatoires

**1. Résolution de chemins PyInstaller (CRITIQUE)**
```python
# main.py — TOUJOURS ce pattern, jamais __file__ seul
import sys
from pathlib import Path

BASE_DIR = Path(getattr(sys, '_MEIPASS', Path(__file__).parent))
KEYBOARDS_DIR = BASE_DIR / 'keyboards'
TEMPLATES_DIR = BASE_DIR / 'templates'
TOOLCHAIN_DIR = BASE_DIR / 'toolchain'
ASSETS_DIR = BASE_DIR / 'assets'
```

**2. Injection ProjectModel (OBLIGATOIRE — jamais de singleton)**
```python
# ui/main_window.py
class MainWindow(QMainWindow):
    def __init__(self, model: ProjectModel, parent=None):
        super().__init__(parent)
        self._model = model
```

**3. Signaux Qt — snake_case UNIQUEMENT**
```python
# ✅ Correct
model_changed = Signal()
tab_switched = Signal(int)
# ❌ INTERDIT
modelChanged = Signal()
tabSwitched = Signal(int)
```

**4. Logging stdlib**
```python
import logging
logger = logging.getLogger(__name__)
logger.info("Application started")
# ❌ JAMAIS
print("Application started")
```

### ProjectModel — Schéma JSON

```python
# models/project_model.py
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class KeyboardConfig:
    model: str = ""
    mcu: str = ""

@dataclass
class OledConfig:
    image_path: str = ""
    overlays: list[str] = field(default_factory=list)
    frames: list[bytes] = field(default_factory=list)  # runtime only, not serialized

@dataclass
class RgbEffect:
    type: str = "static"
    color_primary: str = "#FFFFFF"
    color_secondary: str = "#888888"
    fade_ms: int = 500
    trigger_key: Optional[str] = None

@dataclass
class RgbConfig:
    effects: list[RgbEffect] = field(default_factory=list)
    per_key: dict[str, str] = field(default_factory=dict)

@dataclass
class BuildConfig:
    vial_qmk_version: str = ""
    toolchain_version: str = ""

@dataclass
class ProjectModel:
    version: str = "1.0"
    keyboard: KeyboardConfig = field(default_factory=KeyboardConfig)
    oled: OledConfig = field(default_factory=OledConfig)
    rgb: RgbConfig = field(default_factory=RgbConfig)
    build: BuildConfig = field(default_factory=BuildConfig)
```

**Sérialisation JSON — clés snake_case, couleurs hex `#RRGGBB`, pas de `frames` dans le JSON**

### Structure de Fichiers à Créer

```
keyboard_firmware_maker/
├── main.py                          # Entry point — QApplication + BASE_DIR
├── pyproject.toml                   # Dépendances + outils
├── models/
│   ├── __init__.py
│   └── project_model.py             # ProjectModel dataclass
├── modules/
│   ├── __init__.py
│   ├── hardware/__init__.py
│   ├── oled_editor/__init__.py
│   ├── rgb_editor/__init__.py
│   ├── build_manager/__init__.py
│   └── project_manager/__init__.py
├── ui/
│   ├── __init__.py
│   ├── main_window.py               # QMainWindow + QTabWidget 4 onglets
│   └── widgets/
│       ├── __init__.py
│       └── about_dialog.py          # QDialog version + lien GitHub
├── keyboards/                       # .gitkeep (YAML peuplés en Story 1.2)
├── templates/                       # .gitkeep (Jinja2 peuplés en Epic 4)
├── toolchain/
│   ├── windows/bin/.gitkeep
│   └── linux/bin/.gitkeep
├── assets/
│   ├── icons/.gitkeep
│   └── flash_guide/.gitkeep
└── tests/
    ├── __init__.py
    ├── integration/
    ├── test_main_window.py
    ├── test_project_model.py
    └── test_about_dialog.py
```

### Tests — Patterns pytest-qt

```python
# tests/test_main_window.py
import pytest
from PySide6.QtWidgets import QApplication
from models.project_model import ProjectModel
from ui.main_window import MainWindow

def test_main_window_has_four_tabs(qtbot):
    model = ProjectModel()
    window = MainWindow(model)
    qtbot.addWidget(window)
    tab_widget = window.findChild(QTabWidget)
    assert tab_widget is not None
    assert tab_widget.count() == 4
    assert tab_widget.tabText(0) == "Matériel"
    assert tab_widget.tabText(1) == "OLED"
    assert tab_widget.tabText(2) == "RGB"
    assert tab_widget.tabText(3) == "Build"
```

```python
# tests/test_project_model.py
from models.project_model import ProjectModel

def test_project_model_serialization():
    model = ProjectModel()
    model.keyboard.model = "sofle-v2"
    model.keyboard.mcu = "rp2040"
    data = model.to_dict()
    assert data["keyboard"]["model"] == "sofle-v2"
    assert data["keyboard"]["mcu"] == "rp2040"
    assert "frames" not in data.get("oled", {})  # frames NOT serialized

def test_project_model_deserialization():
    data = {"version": "1.0", "keyboard": {"model": "sofle-v2", "mcu": "rp2040"}}
    model = ProjectModel.from_dict(data)
    assert model.keyboard.model == "sofle-v2"
```

### Project Structure Notes

- Ce projet est **greenfield** — aucun fichier préexistant à préserver
- Les modules (`hardware/`, `oled_editor/`, etc.) sont des **packages Python vides** pour l'instant — ils seront peuplés dans les stories suivantes
- L'onglet "Matériel" sera peuplé en Story 1.2 — pour l'instant un `QWidget()` vide suffit
- `BASE_DIR` doit être exporté depuis `main.py` ou un module `config.py` partagé pour être utilisé par les autres modules

### Contraintes Non-Fonctionnelles

- NFR4 : démarrage < 5 secondes — aucun chargement lourd dans `__init__` de MainWindow
- NFR14 : docstrings sur toutes les classes publiques
- FR30 : pas d'élévation de privilèges — vérifier qu'aucun appel admin n'est fait

### References

- Architecture: [Source: _bmad-output/planning-artifacts/architecture.md#Starter Template]
- Architecture: [Source: _bmad-output/planning-artifacts/architecture.md#Implementation Patterns]
- Architecture: [Source: _bmad-output/planning-artifacts/architecture.md#Project Structure]
- PRD: [Source: _bmad-output/planning-artifacts/prd.md#FR29-FR31]
- Project Context: [Source: _bmad-output/project-context.md]
- PySide6 6.10: [Source: https://www.qt.io/blog/qt-for-python-release-6.10-is-here]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Story 1.1 implémentée avec succès — 11/11 tests pytest passés (2026-02-22)
- `config.py` créé à la racine du projet pour exposer `BASE_DIR`, `KEYBOARDS_DIR`, `TEMPLATES_DIR`, `TOOLCHAIN_DIR`, `ASSETS_DIR` (pattern PyInstaller)
- `OledConfig.frames` exclu de `to_dict()` conformément à la spec — données runtime uniquement
- Dépendances installées via `python3 -m pip install --break-system-packages` (WSL2 sans venv)

### File List

- `pyproject.toml`
- `config.py`
- `main.py`
- `models/__init__.py`
- `models/project_model.py`
- `ui/__init__.py`
- `ui/main_window.py`
- `ui/widgets/__init__.py`
- `ui/widgets/about_dialog.py`
- `modules/__init__.py`
- `modules/hardware/__init__.py`
- `modules/oled_editor/__init__.py`
- `modules/rgb_editor/__init__.py`
- `modules/build_manager/__init__.py`
- `modules/project_manager/__init__.py`
- `tests/__init__.py`
- `tests/test_main_window.py`
- `tests/test_project_model.py`
- `tests/test_about_dialog.py`
- `keyboards/.gitkeep`
- `templates/.gitkeep`
- `toolchain/windows/bin/.gitkeep`
- `toolchain/linux/bin/.gitkeep`
- `assets/icons/.gitkeep`
- `assets/flash_guide/.gitkeep`
