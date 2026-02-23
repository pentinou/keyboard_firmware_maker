# Story 1.2: Sélection du clavier et du microcontrôleur

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a utilisateur (Pentinou ou Alex),
I want to select my keyboard model and MCU from the hardware tab,
so that the application knows which keyboard I have and configures the correct firmware target.

## Acceptance Criteria

1. **Given** je suis dans l'onglet "Matériel"
   **When** j'ouvre le sélecteur de modèle de clavier
   **Then** je vois au minimum : "Sofle v2.1 RGB", "Corne", "Lily58" (FR1)
   **And** les définitions sont chargées depuis les fichiers YAML dans `keyboards/`

2. **Given** j'ai sélectionné un modèle de clavier
   **When** je regarde le sélecteur de MCU
   **Then** je vois les MCU compatibles avec ce modèle (FR2)
   **And** "RP2040" est disponible pour le Sofle v2.1 RGB

3. **Given** je survole un modèle de clavier ou un MCU dans le sélecteur
   **When** je lis l'info-bulle
   **Then** je vois une description contextuelle du matériel (FR5)

4. **Given** j'ai sélectionné "Sofle v2.1 RGB" et "RP2040"
   **When** les sélections sont confirmées
   **Then** le ProjectModel est mis à jour : `keyboard.model = "sofle-v2"`, `keyboard.mcu = "rp2040"`

## Tasks / Subtasks

- [x] Task 1: Ajouter PyYAML à pyproject.toml (AC: 1)
  - [x] 1.1 Ajouter `PyYAML>=6.0` à `[project] dependencies` dans `pyproject.toml`
  - [x] 1.2 Installer `PyYAML` dans l'environnement de dev (`python3 -m pip install --break-system-packages PyYAML`)

- [x] Task 2: Créer les fichiers de définition YAML des claviers (AC: 1, 2, 3)
  - [x] 2.1 Créer `keyboards/sofle-v2.yaml` (Sofle 2.1 RGB — RP2040, OLED: true, RGB: true)
  - [x] 2.2 Créer `keyboards/corne.yaml` (Corne — Pro Micro/Elite-C/RP2040, OLED: true, RGB: false)
  - [x] 2.3 Créer `keyboards/lily58.yaml` (Lily58 — Pro Micro/Elite-C/RP2040, OLED: true, RGB: false)

- [x] Task 3: Créer modules/hardware/keyboard_loader.py — chargement YAML pur Python (AC: 1, 2, 3)
  - [x] 3.1 Définir `@dataclass class McuOption` avec champs `id: str`, `display_name: str`, `description: str`
  - [x] 3.2 Définir `@dataclass class KeyboardDefinition` avec champs `model`, `display_name`, `description`, `mcu_options`, `capabilities` (dict oled/rgb)
  - [x] 3.3 Implémenter `load_keyboard(path: Path) -> KeyboardDefinition` (lecture YAML + construction dataclass)
  - [x] 3.4 Implémenter `load_all_keyboards(keyboards_dir: Path) -> list[KeyboardDefinition]` (glob `*.yaml`, tri alphabétique par `display_name`)
  - [x] 3.5 Valider : aucun import Qt dans `keyboard_loader.py` — testable sans QApplication

- [x] Task 4: Créer modules/hardware/widget.py — HardwareWidget (AC: 1, 2, 3, 4)
  - [x] 4.1 Créer `class HardwareWidget(QWidget)` avec constructeur `__init__(self, model: ProjectModel, parent=None)`
  - [x] 4.2 Charger les définitions via `load_all_keyboards(KEYBOARDS_DIR)` à l'init — pas de reload dynamique
  - [x] 4.3 Ajouter `QComboBox` pour le modèle de clavier ; peupler avec `def.display_name`, `setItemData(..., ToolTipRole)` sur chaque index
  - [x] 4.4 Ajouter `QComboBox` pour le MCU ; peupler en fonction du modèle sélectionné (`mcu_options`), tooltips par MCU
  - [x] 4.5 Connecter `keyboard_combo.currentIndexChanged` → `_on_model_changed()` qui re-peuple `mcu_combo` ET met à jour `self._model.keyboard.model`
  - [x] 4.6 Connecter `mcu_combo.currentIndexChanged` → `_on_mcu_changed()` qui met à jour `self._model.keyboard.mcu`
  - [x] 4.7 Initialiser les combos avec le premier item par défaut (pas de sélection vide si YAML présents)

- [x] Task 5: Mettre à jour ui/main_window.py — brancher HardwareWidget (AC: 1, 2, 4)
  - [x] 5.1 Importer `HardwareWidget` depuis `modules.hardware.widget`
  - [x] 5.2 Remplacer `self._tab_hardware = QWidget()` par `self._tab_hardware = HardwareWidget(self._model)`
  - [x] 5.3 Vérifier que les 3 autres onglets (OLED, RGB, Build) restent des `QWidget()` vides (pas de régression)

- [x] Task 6: Écrire et valider les tests (AC: 1, 2, 3, 4)
  - [x] 6.1 Créer `modules/hardware/tests/fixtures/test_keyboard.yaml` (clavier fictif minimal pour les tests)
  - [x] 6.2 Créer `modules/hardware/tests/test_keyboard_loader.py` — 15 tests `load_keyboard` et `load_all_keyboards`
  - [x] 6.3 Créer `modules/hardware/tests/test_widget.py` — 15 tests `HardwareWidget` avec pytest-qt (`qtbot`)
  - [x] 6.4 Vérifier que tous les tests passent avec `python3 -m pytest tests/ modules/ -v` — **41/41 PASSED**

## Dev Notes

### Nouvelle Dépendance — PyYAML (IMPORTANT)

**PyYAML n'est pas encore dans `pyproject.toml`** — c'est la première dépendance ajoutée dans Story 1.2.

```toml
# pyproject.toml — à mettre à jour
[project]
dependencies = [
    "PySide6>=6.10.2",
    "Pillow>=10.0",
    "numpy>=1.26",
    "jinja2>=3.1",
    "pyinstaller>=6.0",
    "PyYAML>=6.0",   # ← AJOUT Story 1.2
]
```

Installation dev :
```bash
python3 -m pip install --break-system-packages PyYAML
```

### Format YAML des définitions de claviers (Architecture §Format Patterns)

Chaque fichier dans `keyboards/` respecte ce schéma (kebab-case pour le nom de fichier) :

```yaml
# keyboards/sofle-v2.yaml
model: sofle-v2
display_name: "Sofle v2.1 RGB"
description: "Clavier split 60% avec encodeurs rotatifs, afficheur OLED 128×64 et LEDs RGB addressables per-key."
mcu_options:
  - id: rp2040
    display_name: "RP2040 (Sea Picro / Pro Micro RP2040)"
    description: "Microcontrôleur dual-core ARM Cortex-M0+, 264 KB RAM, 2 MB Flash. Recommandé pour Vial-QMK."
capabilities:
  oled: true
  rgb: true
matrix:
  rows: 5
  cols: 6
oled:
  width: 64
  height: 128
  bits: 1
```

```yaml
# keyboards/corne.yaml
model: corne
display_name: "Corne (crkbd)"
description: "Clavier split 40% compact à 42 touches. Supporte OLED. Pas de RGB per-key nativement."
mcu_options:
  - id: pro_micro
    display_name: "Pro Micro (ATmega32U4)"
    description: "Microcontrôleur classique Arduino compatible QMK. 32 KB Flash."
  - id: elite_c
    display_name: "Elite-C (ATmega32U4)"
    description: "Pro Micro amélioré avec USB-C et pins supplémentaires."
  - id: rp2040
    display_name: "RP2040 (Nice!Nano compatible)"
    description: "Microcontrôleur RP2040 avec plus de mémoire et de performances."
capabilities:
  oled: true
  rgb: false
matrix:
  rows: 4
  cols: 6
```

### Architecture : keyboard_loader.py (pur Python, sans Qt)

```python
# modules/hardware/keyboard_loader.py
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import yaml
import logging

logger = logging.getLogger(__name__)

@dataclass
class McuOption:
    id: str
    display_name: str
    description: str = ""

@dataclass
class KeyboardDefinition:
    model: str
    display_name: str
    description: str
    mcu_options: list[McuOption] = field(default_factory=list)
    capabilities: dict[str, bool] = field(default_factory=dict)

def load_keyboard(path: Path) -> KeyboardDefinition:
    """Charge un fichier YAML et retourne une KeyboardDefinition."""
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    mcu_options = [
        McuOption(
            id=mcu["id"],
            display_name=mcu["display_name"],
            description=mcu.get("description", ""),
        )
        for mcu in data.get("mcu_options", [])
    ]
    return KeyboardDefinition(
        model=data["model"],
        display_name=data["display_name"],
        description=data.get("description", ""),
        mcu_options=mcu_options,
        capabilities=data.get("capabilities", {}),
    )

def load_all_keyboards(keyboards_dir: Path) -> list[KeyboardDefinition]:
    """Charge tous les fichiers *.yaml du répertoire keyboards/, triés par display_name."""
    keyboards = []
    for yaml_path in sorted(keyboards_dir.glob("*.yaml")):
        try:
            keyboards.append(load_keyboard(yaml_path))
        except Exception as e:
            logger.warning("Impossible de charger %s : %s", yaml_path.name, e)
    return sorted(keyboards, key=lambda k: k.display_name)
```

### Architecture : HardwareWidget (widget.py)

**⚠️ Règle absolue** : `widget.py` ne contient QUE la logique Qt (signaux, layouts, combos). Aucun traitement YAML dedans — délégué à `keyboard_loader.py`.

```python
# modules/hardware/widget.py — structure attendue
class HardwareWidget(QWidget):
    def __init__(self, model: ProjectModel, parent=None):
        super().__init__(parent)
        self._model = model
        self._keyboards: list[KeyboardDefinition] = load_all_keyboards(KEYBOARDS_DIR)
        self._setup_ui()
        self._connect_signals()
        self._on_model_changed(0)  # init MCU combo avec le premier clavier

    def _setup_ui(self) -> None:
        # QFormLayout ou QVBoxLayout avec labels + combos
        ...

    def _on_model_changed(self, index: int) -> None:
        # re-peupler mcu_combo avec les MCU du clavier sélectionné
        # mettre à jour self._model.keyboard.model
        ...

    def _on_mcu_changed(self, index: int) -> None:
        # mettre à jour self._model.keyboard.mcu
        ...
```

**Tooltips QComboBox** — utiliser `setItemData(index, description, Qt.ItemDataRole.ToolTipRole)` pour les info-bulles par item.

### Mise à jour MainWindow

```python
# ui/main_window.py — modification dans _setup_ui()
# ✅ Avant (Story 1.1) :
self._tab_hardware = QWidget()

# ✅ Après (Story 1.2) :
from modules.hardware.widget import HardwareWidget
self._tab_hardware = HardwareWidget(self._model)
```

L'import doit être en haut du fichier. Les 3 autres tabs (OLED, RGB, Build) restent `QWidget()` vides.

### Tests — keyboard_loader (sans Qt)

```python
# modules/hardware/tests/test_keyboard_loader.py
from pathlib import Path
from modules.hardware.keyboard_loader import load_keyboard, load_all_keyboards

FIXTURES_DIR = Path(__file__).parent / "fixtures"

def test_load_keyboard_fields():
    kb = load_keyboard(FIXTURES_DIR / "test_keyboard.yaml")
    assert kb.model == "test-kb"
    assert kb.display_name == "Test Keyboard"
    assert len(kb.mcu_options) >= 1
    assert kb.mcu_options[0].id == "test_mcu"

def test_load_keyboard_capabilities():
    kb = load_keyboard(FIXTURES_DIR / "test_keyboard.yaml")
    assert kb.capabilities.get("oled") is True

def test_load_all_keyboards_returns_list(tmp_path):
    import shutil
    shutil.copy(FIXTURES_DIR / "test_keyboard.yaml", tmp_path / "test-kb.yaml")
    keyboards = load_all_keyboards(tmp_path)
    assert len(keyboards) == 1
    assert keyboards[0].model == "test-kb"

def test_load_all_keyboards_skips_invalid(tmp_path):
    (tmp_path / "bad.yaml").write_text("invalid: [unclosed")
    keyboards = load_all_keyboards(tmp_path)
    assert len(keyboards) == 0  # aucun crash — log warning uniquement
```

### Tests — HardwareWidget (avec pytest-qt)

```python
# modules/hardware/tests/test_widget.py
import pytest
from PySide6.QtWidgets import QComboBox
from models.project_model import ProjectModel
from modules.hardware.widget import HardwareWidget

def test_hardware_widget_keyboard_combo_populated(qtbot):
    model = ProjectModel()
    widget = HardwareWidget(model)
    qtbot.addWidget(widget)
    combo = widget.findChild(QComboBox, "keyboard_combo")
    assert combo is not None
    assert combo.count() >= 3  # au moins Sofle, Corne, Lily58

def test_hardware_widget_updates_model(qtbot):
    model = ProjectModel()
    widget = HardwareWidget(model)
    qtbot.addWidget(widget)
    # La sélection par défaut (index 0) a mis à jour le model
    assert model.keyboard.model != ""
    assert model.keyboard.mcu != ""

def test_hardware_widget_mcu_filtered_by_keyboard(qtbot):
    model = ProjectModel()
    widget = HardwareWidget(model)
    qtbot.addWidget(widget)
    keyboard_combo = widget.findChild(QComboBox, "keyboard_combo")
    mcu_combo = widget.findChild(QComboBox, "mcu_combo")
    # Sélectionner un autre clavier → MCU combo change
    keyboard_combo.setCurrentIndex(1)
    count_kb1 = mcu_combo.count()
    keyboard_combo.setCurrentIndex(0)
    count_kb0 = mcu_combo.count()
    # Les combos ne doivent pas être vides
    assert count_kb0 >= 1
    assert count_kb1 >= 1
```

**Naming des combos** : utiliser `setObjectName("keyboard_combo")` et `setObjectName("mcu_combo")` pour que `findChild` fonctionne dans les tests.

### Fixture YAML minimale

```yaml
# modules/hardware/tests/fixtures/test_keyboard.yaml
model: test-kb
display_name: "Test Keyboard"
description: "Clavier de test minimal pour les tests unitaires."
mcu_options:
  - id: test_mcu
    display_name: "Test MCU"
    description: "MCU de test."
capabilities:
  oled: true
  rgb: false
matrix:
  rows: 4
  cols: 6
```

### Règles Critiques à Respecter

1. **`keyboard_loader.py` = pur Python** — zéro import Qt. Tests sans `qtbot`.
2. **`widget.py` = uniquement Qt** — pas de traitement YAML dedans.
3. **`KEYBOARDS_DIR`** importé depuis `config.py` (pas recalculé dans widget).
4. **Logging** via `logger = logging.getLogger(__name__)` — JAMAIS `print()`.
5. **Pas de `from __future__ import annotations`** si Python 3.11+ (optionnel).
6. **Tri alphabétique** des claviers par `display_name` pour une UI cohérente.
7. **Gestion d'erreur YAML** : si un fichier est invalide, log warning et continuer — jamais de crash sur un YAML corrompu.

### Apprentissages de la Story 1.1

- `python3 -m pip install --break-system-packages` requis sur ce système WSL2 (pas de venv disponible sans `apt`)
- Tests lancés avec `python3 -m pytest tests/ modules/ -v`
- `config.py` à la racine expose `KEYBOARDS_DIR = BASE_DIR / "keyboards"` — déjà disponible
- `modules/hardware/tests/__init__.py` déjà créé (Story 1.1)

### Project Structure Notes

**Fichiers à créer :**
```
keyboards/
├── sofle-v2.yaml                    # NOUVEAU
├── corne.yaml                       # NOUVEAU
└── lily58.yaml                      # NOUVEAU

modules/hardware/
├── keyboard_loader.py               # NOUVEAU (pur Python, sans Qt)
├── widget.py                        # NOUVEAU (HardwareWidget)
└── tests/
    ├── fixtures/
    │   └── test_keyboard.yaml       # NOUVEAU (fixture test)
    ├── test_keyboard_loader.py      # NOUVEAU
    └── test_widget.py               # NOUVEAU
```

**Fichiers à modifier :**
```
pyproject.toml                       # Ajouter PyYAML>=6.0
ui/main_window.py                    # Remplacer QWidget() par HardwareWidget(model)
```

**Fichiers non touchés (régression à éviter) :**
```
main.py, config.py, models/project_model.py
ui/widgets/about_dialog.py
tests/test_*.py (Story 1.1)
```

### References

- Architecture §Format Patterns : `_bmad-output/planning-artifacts/architecture.md#Format-Patterns` (schéma YAML clavier)
- Architecture §Structure Patterns : `_bmad-output/planning-artifacts/architecture.md#Structure-Patterns` (séparation widget/loader)
- Architecture §Requirements→Structure Mapping : FR1→`hardware/widget.py`, FR2→`hardware/widget.py`, FR3→`hardware/keyboard_loader.py`, FR5→`hardware/widget.py`
- Architecture §Project Directory : `modules/hardware/keyboard_loader.py` (FR3), `modules/hardware/widget.py` (FR1-FR4)
- PRD FR1, FR2, FR5 : `_bmad-output/planning-artifacts/prd.md`
- Epic 1 Story 1.2 : `_bmad-output/planning-artifacts/epics.md#Story-1.2`
- Project Context : `_bmad-output/project-context.md` (règles snake_case signaux, pur Python processor, QThread > 50ms)
- PyYAML 6.x docs : https://pyyaml.org/wiki/PyYAMLDocumentation (yaml.safe_load — jamais yaml.load)

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Story 1.2 implémentée avec succès — 41/41 tests passés, zéro régression (2026-02-22)
- `keyboard_loader.py` pur Python confirmé (test `test_no_qt_import_in_module` PASSED)
- `blockSignals(True/False)` utilisé dans `_on_model_changed` pour éviter les signaux MCU en cascade lors du rechargement du combo
- `setItemData(idx, description, Qt.ItemDataRole.ToolTipRole)` utilisé pour les tooltips par item (testé et fonctionnel)
- PyYAML ajouté à `pyproject.toml` et installé via `--break-system-packages` (WSL2 sans venv)

### File List

- `pyproject.toml` (modifié — ajout PyYAML>=6.0)
- `keyboards/sofle-v2.yaml` (nouveau)
- `keyboards/corne.yaml` (nouveau)
- `keyboards/lily58.yaml` (nouveau)
- `modules/hardware/keyboard_loader.py` (nouveau)
- `modules/hardware/widget.py` (nouveau)
- `modules/hardware/tests/fixtures/test_keyboard.yaml` (nouveau)
- `modules/hardware/tests/test_keyboard_loader.py` (nouveau)
- `modules/hardware/tests/test_widget.py` (nouveau)
- `ui/main_window.py` (modifié — HardwareWidget remplace QWidget() pour l'onglet Matériel)
