---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
status: 'complete'
completedAt: '2026-02-22'
inputDocuments:
  - '_bmad-output/planning-artifacts/product-brief-keyboard_firmware_maker-2026-02-21.md'
  - '_bmad-output/planning-artifacts/prd.md'
workflowType: 'architecture'
project_name: 'keyboard_firmware_maker'
user_name: 'Pentinou'
date: '2026-02-22'
---

# Architecture Decision Document

_Ce document se construit de manière collaborative à travers une découverte étape par étape. Les sections sont ajoutées au fil des décisions architecturales._

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**
33 FRs organisés en 6 domaines fonctionnels :
- Gestion du Matériel (FR1-FR5) : sélection clavier/MCU, détection capacités,
  masquage dynamique — implique un moteur de définitions de claviers basé sur
  des fichiers YAML, avec rendu UI conditionnel
- Personnalisation OLED (FR6-FR10) : import GIF/PNG/BMP, conversion 1-bit
  64×128px, prévisualisation pixel-perfect, overlay infos système — implique
  un pipeline de traitement d'images avec algorithme de dithering (Floyd-Steinberg)
- Programmation RGB (FR11-FR15) : éditeur visuel par touche, effets prédéfinis
  (ripple, couleur statique), aperçu animé — implique un renderer de layout
  clavier interactif et un moteur d'effets
- Génération Firmware (FR16-FR24) : compilation Vial-QMK embarquée, vérification
  taille mémoire, sortie .uf2, guide de flash illustré — implique un orchestrateur
  de subprocess et un moteur de templates QMK
- Gestion de Projet (FR25-FR28) : sauvegarde/rechargement, modification
  incrémentale — implique un format de fichier projet sérialisable
- Application & Distribution (FR29-FR33) : offline complet, sans privilèges
  administrateur, autonome — contrainte architecturale transversale

**Non-Functional Requirements:**
NFRs critiques pour les décisions d'architecture :
- NFR1 : compilation < 2 minutes → opérations asynchrones obligatoires
- NFR2 : interactions UI < 200ms → opérations lourdes hors du thread UI
- NFR3 : prévisualisation OLED < 500ms → pipeline image optimisé
- NFR4 : démarrage < 5 secondes → chargement paresseux, pas d'init lourde
- NFR5 : pas de crash durant génération → isolation du subprocess de compilation
- NFR7 : sauvegarde sans corruption → écriture atomique obligatoire
- NFR9-11 : Windows 10/11 + Linux (glibc ≥ 2.31) → packaging cross-platform
- NFR13 : définitions claviers en YAML séparés → architecture plugin-like
- NFR15 : toolchain versionnée explicitement → vendoring ou verrouillage de version

**Scale & Complexity:**
- Primary domain : Application desktop avec toolchain de compilation embarquée
- Complexity level : Moyen-Élevé
- Composants architecturaux estimés : 7-8 modules distincts

### Technical Constraints & Dependencies

- **arm-none-eabi-gcc** : compilateur croisé ARM requis pour la compilation QMK —
  doit être distribué avec l'application ou installé par l'utilisateur
- **Vial-QMK** : fork de QMK avec support de la configuration en temps réel —
  version à verrouiller explicitement (NFR15)
- **Format .uf2** : spécification Microsoft UF2 — génération validée obligatoire (NFR6)
- **Format projet** : JSON ou YAML — décision en attente (à trancher en architecture)
- **Framework UI** : non décidé — candidats Python+PySide6/PyQt6, Tauri/Rust,
  Electron — décision critique pour le packaging
- **Cible MVP** : Sofle 2.1 RGB uniquement — pas de généralisation prématurée

### Cross-Cutting Concerns Identified

1. **Asynchronisme** : toutes les opérations longues (compilation, conversion image)
   doivent s'exécuter hors du thread UI avec retour de progression
2. **Cross-platform** : chemins de fichiers, permissions, formats binaires,
   découverte de la toolchain — à abstraire dans une couche platform
3. **Gestion d'état du projet** : état sérialisable à tout moment, récupération
   après erreur de compilation sans perte de configuration
4. **Isolation des processus** : le subprocess arm-none-eabi-gcc doit être
   isolé — un échec de compilation ne doit pas corrompre l'état de l'application
5. **Extensibilité** : le moteur de définitions claviers doit permettre l'ajout
   d'un nouveau modèle sans modifier le code source (NFR13)

## Starter Template Evaluation

### Primary Technology Domain

Application desktop native — offline, cross-platform (Windows + Linux).
Aucun starter unique dominant pour Python+PySide6 ; le projet sera initialisé
avec pyproject.toml + structure modulaire standard.

### Starter Options Considered

| Framework | Version | Verdict |
|---|---|---|
| Python + PySide6 | 6.10.2 (fév. 2026) | ✅ Sélectionné |
| Tauri v2 (Rust + WebView) | 2.10.x | ❌ Rust non maîtrisé, image processing faible |
| Electron | 40.4.1 | ❌ JS non maîtrisé, binaire ~200MB |

### Selected Stack: Python + PySide6 6.10

**Rationale :**
- Python maîtrisé par Pentinou — pas de courbe d'apprentissage sur le langage
- PIL/Pillow + NumPy : pipeline 1-bit dithering natif et performant (NFR3 : <500ms)
- subprocess : gestion arm-none-eabi-gcc triviale, isolation robuste (NFR5)
- PySide6 6.x : Qt6 stable, widgets riches, QThread pour async (NFR2 : <200ms)
- PyInstaller : packaging .exe Windows + AppImage Linux éprouvé

**Initialization:**
```bash
python -m venv .venv && source .venv/bin/activate  # Linux
# ou .venv\Scripts\activate                          # Windows
pip install PySide6 Pillow numpy PyInstaller
```

**Architectural Decisions Established by Stack:**

- **Language :** Python 3.11+
- **UI Framework :** PySide6 (Qt6) — widgets natifs, QThread pour async
- **Image Processing :** Pillow + NumPy (dithering Floyd-Steinberg)
- **Async :** QThread / QRunnable — jamais bloquer le thread principal Qt
- **Packaging :** PyInstaller (Windows .exe + Linux AppImage)
- **Format projet :** JSON (stdlib json, aucune dépendance externe)
- **Tests :** pytest + pytest-qt

## Core Architectural Decisions

### Decision Priority Analysis

**Décisions critiques (bloquantes pour l'implémentation) :**
- Architecture interne Qt : Signals/Slots + modules domaine + ProjectModel central
- Stratégie toolchain ARM : binaires vendorés + fallback instructions intégrées
- Génération QMK : Jinja2 templates

**Décisions importantes (façonnent l'architecture) :**
- CI/CD : GitHub Actions matrix build (Windows + Linux)

**Décisions déférées (post-MVP) :**
- Support macOS (runner macOS GitHub Actions en v2)
- Notification de mise à jour optionnelle (v2)

---

### Architecture Interne

**Pattern : Qt Signals/Slots + Modules Domaine + ProjectModel central**

L'application est organisée en modules domaine indépendants communicant via
les signaux Qt natifs. Un objet `ProjectModel` central porte l'état sérialisable.

```
keyboard_firmware_maker/
├── main.py                    # Entry point, QApplication
├── models/
│   └── project_model.py       # ProjectModel — état central sérialisable (JSON)
├── modules/
│   ├── hardware/              # Sélection clavier/MCU, définitions YAML
│   ├── oled_editor/           # Import image, dithering, prévisualisation
│   ├── rgb_editor/            # Éditeur visuel, effets, aperçu animé
│   ├── build_manager/         # Orchestration subprocess, génération templates
│   └── flash_guide/           # Guide illustré, export .uf2
├── ui/
│   ├── main_window.py         # QMainWindow, onglets principaux
│   └── widgets/               # Widgets Qt réutilisables
├── keyboards/                 # Définitions YAML par modèle (sofle_v2.yaml, etc.)
├── templates/                 # Templates Jinja2 QMK (.c.j2, .h.j2)
├── toolchain/                 # Binaires arm-none-eabi-gcc pré-compilés (vendorés)
│   ├── windows/
│   └── linux/
└── tests/
    └── ...                    # pytest + pytest-qt
```

**Règles de communication :**
- L'UI émet des signaux Qt → les modules domaine réagissent
- Les modules domaine mettent à jour `ProjectModel` → l'UI se met à jour via signaux
- Jamais d'import circulaire entre modules domaine
- `ProjectModel` est un dataclass Python pur, sans dépendance Qt (testable unitairement)

---

### Stratégie Toolchain ARM

**MVP : Binaires arm-none-eabi-gcc pré-compilés vendorés + fallback instructions**

- Les binaires ARM officiels (ARM Developer Tools) sont inclus dans
  `toolchain/windows/` et `toolchain/linux/` (ou téléchargés au premier
  lancement depuis les GitHub Releases du projet)
- PyInstaller les inclut automatiquement dans le bundle final
- `build_manager` détecte la plateforme et résout le chemin du gcc embarqué
- **Fallback :** si les binaires embarqués sont absents ou incompatibles,
  l'app affiche des instructions claires pour installer `arm-none-eabi-gcc`
  localement (FR32) et détecte l'installation système via
  `which arm-none-eabi-gcc` (Linux) / `where arm-none-eabi-gcc` (Windows)
- La version de la toolchain est versionnée explicitement dans
  `toolchain/version.txt` (NFR15)

---

### Génération des Templates QMK

**Jinja2 — Templates `.c.j2` par fichier QMK généré**

- Un template Jinja2 par fichier QMK : `keymap.c.j2`, `config.h.j2`,
  `rules.mk.j2`, `vial.json.j2`
- Les templates sont paramétrés depuis `ProjectModel`
  (layout, OLED frames, RGB effects, MCU cible)
- Chaque définition de clavier (YAML) peut surcharger ou étendre
  les templates de base
- Version Vial-QMK verrouillée dans la config de build (NFR15)
- **Dépendance :** `jinja2` (pip)

---

### Infrastructure & CI/CD

**GitHub Actions — Matrix Build Windows + Linux**

- `release.yml` : déclenché sur tag `v*.*.*`
- Matrix : `[windows-latest, ubuntu-20.04]`
- Chaque runner : `pip install`, `pyinstaller --onefile`, upload artifact
- Release GitHub automatique avec `.exe` et `.AppImage` en assets
- `test.yml` : tests unitaires sur chaque push (pytest, cross-platform)

## Implementation Patterns & Consistency Rules

### Naming Patterns

**Code Python — snake_case universel :**
- Modules, fichiers, variables, fonctions : `snake_case`
  - ✅ `oled_editor.py`, `build_manager.py`, `project_model.py`
  - ❌ `OledEditor.py`, `buildManager.py`
- Classes Qt et dataclasses : `PascalCase`
  - ✅ `class OledEditor(QWidget)`, `class ProjectModel`
- Constantes : `UPPER_SNAKE_CASE`
  - ✅ `MAX_OLED_WIDTH = 64`, `DEFAULT_RIPPLE_COLOR`

**Signaux Qt — snake_case avec suffixe descriptif :**
- Pattern : `noun_verb` ou `noun_changed`
  - ✅ `oled_image_changed = Signal(QPixmap)`
  - ✅ `build_started = Signal()`
  - ✅ `build_progress_updated = Signal(int)`  # 0-100
  - ✅ `build_failed = Signal(str)`  # message d'erreur lisible
  - ❌ `oledImageChanged`, `buildStarted`

**Fichiers YAML claviers :** kebab-case — `sofle-v2.yaml`, `corne.yaml`
**Templates Jinja2 :** même nom que le fichier QMK généré — `keymap.c.j2`, `config.h.j2`

---

### Structure Patterns

**Chaque module domaine = package avec séparation UI / logique :**
```
modules/oled_editor/
├── __init__.py          # exports publics du module
├── widget.py            # QWidget principal (UI uniquement)
├── processor.py         # logique métier pure (sans Qt, testable)
└── tests/
    ├── test_processor.py
    └── test_widget.py   # pytest-qt
```

**Règle absolue :**
- `widget.py` : uniquement Qt (signaux, widgets, layouts)
- `processor.py` : uniquement logique Python pure (conversion, calcul, génération)
- Tests co-localisés dans `modules/<name>/tests/`
- Tests d'intégration uniquement dans `tests/integration/`

---

### Format Patterns

**Format projet JSON — schéma standardisé (clés snake_case) :**
```json
{
  "version": "1.0",
  "keyboard": { "model": "sofle-v2", "mcu": "rp2040" },
  "oled": {
    "image_path": "/path/to/image.gif",
    "overlays": ["layer", "wpm"]
  },
  "rgb": {
    "effects": [{
      "type": "ripple",
      "trigger_key": null,
      "color_primary": "#FF0000",
      "color_secondary": "#FF8800",
      "fade_ms": 500
    }],
    "per_key": {}
  },
  "build": {
    "vial_qmk_version": "0.7.1",
    "toolchain_version": "13.3.rel1"
  }
}
```
- Couleurs : hex string `#RRGGBB`
- Chemins : absolus (résolus à la sauvegarde)

**Format définition clavier YAML :**
```yaml
model: sofle-v2
display_name: "Sofle v2.1 RGB"
mcu: rp2040
split: true
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

---

### Communication Patterns

**Règle fondamentale : toute communication inter-modules via signaux Qt**
- Un module n'appelle JAMAIS directement un widget d'un autre module
- Un widget n'appelle JAMAIS directement la logique d'un autre module
- Communication cross-module uniquement via `MainWindow` ou `ProjectModel`

**Pattern tâche longue — QThread obligatoire pour tout traitement > 50ms :**
```python
class BuildWorker(QThread):
    progress = Signal(int)   # 0-100
    log_line = Signal(str)   # ligne de log QMK
    success  = Signal(str)   # chemin du .uf2
    error    = Signal(str)   # message d'erreur humanisé
```

**Pas d'`asyncio`** — Qt event loop + QThread exclusivement.

---

### Process Patterns

**Gestion d'erreurs — signal `error = Signal(str)`, jamais d'exception non catchée :**
```python
# ✅ Correct
try:
    result = self._process_image(path)
except (OSError, ValueError) as e:
    self.error.emit(f"Impossible d'ouvrir l'image : {e}")
    return
```

**Messages d'erreur — lisibles, sans jargon technique :**
- ✅ `"L'image est trop petite (minimum 64×128px)"`
- ❌ `"ValueError: image size (32, 32) < (64, 128)"`

**Injection de dépendance pour ProjectModel :**
```python
# ✅ Correct
class OledEditor(QWidget):
    def __init__(self, model: ProjectModel, parent=None): ...

# ❌ Interdit
model = get_project_model()  # singleton global
```

**Écriture atomique des fichiers projet (NFR7) :**
```python
tmp = path.with_suffix('.tmp')
tmp.write_text(json.dumps(data, indent=2))
tmp.replace(path)
```

**Logging — `logging` stdlib, `print()` interdit :**
```python
logger = logging.getLogger(__name__)
logger.debug("...")   # développement
logger.info("...")    # événements normaux
logger.error("...")   # erreurs récupérables
```

---

### Enforcement Guidelines — Tout agent DOIT :

- Utiliser `snake_case` pour les signaux Qt (pas camelCase)
- Séparer logique métier (`processor.py`) et UI (`widget.py`) dans chaque module
- Passer `ProjectModel` par injection de dépendance au constructeur
- Émettre `error = Signal(str)` pour toutes les erreurs utilisateur
- Utiliser QThread pour tout subprocess ou traitement > 50ms
- Co-localiser les tests dans `modules/<name>/tests/`
- Utiliser l'écriture atomique pour tout fichier projet
- Logger via `logging.getLogger(__name__)`, jamais `print()`

## Project Structure & Boundaries

### Complete Project Directory Structure

```
keyboard_firmware_maker/
├── main.py                          # FR29-FR31 : entry point, QApplication, version
├── pyproject.toml                   # dépendances : PySide6, Pillow, numpy, jinja2, pytest
├── requirements.txt                 # généré depuis pyproject.toml
├── keyboard_firmware_maker.spec     # PyInstaller spec (Windows .exe + Linux AppImage)
├── README.md
├── CHANGELOG.md
├── .gitignore
│
├── .github/
│   └── workflows/
│       ├── test.yml                 # pytest sur chaque push (ubuntu + windows)
│       └── release.yml              # matrix build → .exe + .AppImage sur tag v*.*.*
│
├── keyboards/                       # NFR13 : définitions YAML extensibles
│   ├── sofle-v2.yaml                # Sofle 2.1 RGB (cible MVP)
│   ├── corne.yaml
│   └── lily58.yaml
│
├── templates/                       # Templates Jinja2 QMK
│   ├── keymap.c.j2
│   ├── config.h.j2
│   ├── rules.mk.j2
│   └── vial.json.j2
│
├── toolchain/                       # Binaires arm-none-eabi-gcc vendorés
│   ├── version.txt                  # NFR15 : version verrouillée ex. "13.3.rel1"
│   ├── windows/
│   │   └── bin/
│   │       └── arm-none-eabi-gcc.exe
│   └── linux/
│       └── bin/
│           └── arm-none-eabi-gcc
│
├── models/
│   └── project_model.py             # FR25-FR27 : ProjectModel dataclass, sérialisation JSON
│
├── modules/
│   │
│   ├── hardware/                    # FR1-FR5
│   │   ├── __init__.py
│   │   ├── widget.py                # FR1-FR4 : QWidget sélection clavier/MCU, info-bulles
│   │   ├── keyboard_loader.py       # FR3 : chargement YAML + détection capacités
│   │   └── tests/
│   │       ├── test_keyboard_loader.py
│   │       └── fixtures/
│   │           └── test_keyboard.yaml
│   │
│   ├── oled_editor/                 # FR6-FR10
│   │   ├── __init__.py
│   │   ├── widget.py                # FR8-FR10 : prévisualisation QLabel, overlay config
│   │   ├── processor.py             # FR7 : conversion 1-bit, Floyd-Steinberg, GIF frames
│   │   └── tests/
│   │       ├── test_processor.py    # test dithering, conversion, GIF parsing
│   │       └── test_widget.py       # pytest-qt
│   │
│   ├── rgb_editor/                  # FR11-FR15
│   │   ├── __init__.py
│   │   ├── widget.py                # FR11-FR14 : keyboard layout renderer, color picker
│   │   ├── effect_preview.py        # FR15 : aperçu animé (QTimer)
│   │   ├── effects.py               # définitions effets (ripple, static, etc.)
│   │   └── tests/
│   │       ├── test_effects.py
│   │       └── test_widget.py
│   │
│   ├── build_manager/               # FR16-FR24
│   │   ├── __init__.py
│   │   ├── widget.py                # FR20-FR23 : progress bar, log, guide flash
│   │   ├── builder.py               # FR16-FR19 : QThread, subprocess gcc, .uf2
│   │   ├── template_generator.py    # génération Jinja2 → code QMK source
│   │   ├── toolchain.py             # détection toolchain (vendorée + fallback système)
│   │   ├── uf2_validator.py         # NFR6 : validation format UF2
│   │   └── tests/
│   │       ├── test_builder.py
│   │       ├── test_template_generator.py
│   │       └── test_toolchain.py
│   │
│   └── project_manager/             # FR25-FR28
│       ├── __init__.py
│       ├── file_io.py               # sauvegarde atomique + rechargement JSON
│       └── tests/
│           └── test_file_io.py
│
├── ui/
│   ├── main_window.py               # QMainWindow, onglets, injection ProjectModel
│   └── widgets/
│       ├── flash_guide_dialog.py    # FR23, FR33 : guide illustré étape par étape
│       └── about_dialog.py          # FR31 : version + liens GitHub
│
├── assets/
│   ├── icons/
│   │   └── app_icon.png
│   └── flash_guide/
│       └── *.png                    # visuels guide de flash (bouton BOOT, RPI-RP2...)
│
├── tests/
│   └── integration/
│       └── test_full_workflow.py    # workflow complet : config → build → .uf2
│
└── dist/                            # généré par PyInstaller (gitignored)
    ├── keyboard_firmware_maker.exe
    └── keyboard_firmware_maker.AppImage
```

### Architectural Boundaries

**Module → ProjectModel (flux de données) :**
```
hardware/        → écrit keyboard.model, keyboard.mcu
oled_editor/     → écrit oled.image_path, oled.overlays
rgb_editor/      → écrit rgb.effects, rgb.per_key
build_manager/   → lit tout ProjectModel → génère code QMK
project_manager/ → sérialise/désérialise ProjectModel ↔ JSON
```

**Flux principal (signal-driven) :**
```
[Action utilisateur]
      ↓ Signal Qt
[Module widget]
      ↓ appel
[Module processor / builder]
      ↓ met à jour
[ProjectModel]
      ↓ Signal model_changed
[MainWindow → redistribue aux widgets concernés]
```

**Frontière subprocess (build_manager/builder.py) :**
```
BuildWorker(QThread)
      ↓ subprocess.Popen(arm-none-eabi-gcc ...)
      ↓ capture stdout/stderr ligne par ligne
      ↓ emit log_line(str)     → widget log en temps réel
      ↓ emit progress(int)     → barre de progression
      ↓ emit success(str)      → chemin .uf2 généré
      ↓ emit error(str)        → message d'erreur humanisé
```

### Requirements → Structure Mapping

| FR | Fichier principal |
|---|---|
| FR1-FR2 | `modules/hardware/widget.py` |
| FR3-FR4 | `modules/hardware/keyboard_loader.py` |
| FR5 | `modules/hardware/widget.py` (info-bulles Qt) |
| FR6-FR7 | `modules/oled_editor/processor.py` |
| FR8-FR9 | `modules/oled_editor/widget.py` |
| FR10 | `modules/oled_editor/widget.py` (overlay config) |
| FR11-FR14 | `modules/rgb_editor/widget.py` + `effects.py` |
| FR15 | `modules/rgb_editor/effect_preview.py` |
| FR16-FR19 | `modules/build_manager/builder.py` + `template_generator.py` |
| FR20-FR22 | `modules/build_manager/widget.py` + `builder.py` |
| FR23 | `ui/widgets/flash_guide_dialog.py` + `assets/flash_guide/` |
| FR24 | `templates/vial.json.j2` + `modules/build_manager/template_generator.py` |
| FR25-FR27 | `modules/project_manager/file_io.py` + `models/project_model.py` |
| FR28 | `modules/build_manager/widget.py` (export dialog) |
| FR29 | Tous modules (offline by design, aucun appel réseau) |
| FR30 | `main.py` (pas d'élévation de privilèges) |
| FR31 | `ui/widgets/about_dialog.py` |
| FR32 | `modules/build_manager/toolchain.py` (détection + instructions) |
| FR33 | `ui/widgets/flash_guide_dialog.py` |

## Architecture Validation Results

### Coherence Validation ✅

**Decision Compatibility :**
- Python 3.11 + PySide6 6.10 : compatibles, PySide6 supporte Python 3.9+
- Pillow + NumPy + PySide6 : ImageQt gère la conversion PIL→QPixmap nativement,
  aucun conflit de dépendances
- Jinja2 + PyInstaller : templates .j2 inclus via --add-data dans le .spec
- QThread + subprocess : pattern natif Python/Qt, aucun conflit
- pytest-qt + PySide6 : support officiel, version alignée
- GitHub Actions + PyInstaller matrix : combinaison éprouvée en production

**Pattern Consistency :** ✅
Les patterns snake_case signaux, séparation widget/processor, injection
ProjectModel et QThread pour async sont cohérents avec PySide6 et les
bonnes pratiques Qt.

**Structure Alignment :** ✅
La structure en modules domaine est directement dérivée des 6 catégories
FR du PRD. Aucune friction entre décisions et structure.

---

### Requirements Coverage Validation ✅

**Functional Requirements : 33/33 couverts**
Chaque FR est mappé à un fichier spécifique dans la structure projet.

**Non-Functional Requirements : 15/15 adressés**

| NFR | Couverture architecturale |
|---|---|
| NFR1 < 2min compilation | QThread + subprocess non-bloquant |
| NFR2 < 200ms UI | Toutes opérations lourdes hors thread Qt |
| NFR3 < 500ms OLED preview | processor.py optimisé NumPy |
| NFR4 < 5s démarrage | Chargement YAML lazy, pas d'init lourde |
| NFR5 no crash | BuildWorker isolé, try/except complet |
| NFR6 UF2 valide | uf2_validator.py avant export |
| NFR7 save atomique | file_io.py tmp+replace pattern |
| NFR8 récupérable | BuildWorker émet error signal, app continue |
| NFR9-11 Windows/Linux | PyInstaller matrix GitHub Actions |
| NFR12 Vial-QMK compat | Version fixe dans vial_qmk_manager.py |
| NFR13 YAML extensible | keyboards/ folder, code sans modification |
| NFR14 code documenté | Enforced via patterns (docstrings, typing) |
| NFR15 toolchain versionnée | toolchain/version.txt + vial_qmk_manager.py |

---

### Gaps Identified & Resolved

**Gap 1 — Source Vial-QMK [RÉSOLU — Option B] :**
`modules/build_manager/vial_qmk_manager.py` gère le téléchargement unique
d'un zip Vial-QMK (version SHA verrouillée), extraction dans
`~/.keyboard_firmware_maker/vial-qmk/`. Dialog de progression au premier
lancement. Offline complet ensuite (NFR29 respecté après init).

**Gap 2 — PyInstaller path resolution [DOCUMENTÉ] :**
```python
import sys
from pathlib import Path
BASE_DIR = Path(getattr(sys, '_MEIPASS', Path(__file__).parent.parent.parent))
KEYBOARDS_DIR = BASE_DIR / 'keyboards'
TOOLCHAIN_DIR = BASE_DIR / 'toolchain'
```
Le .spec PyInstaller inclut :
```python
datas=[
    ('keyboards/', 'keyboards/'),
    ('templates/', 'templates/'),
    ('toolchain/', 'toolchain/'),
    ('assets/', 'assets/'),
]
```

**Gap 3 — Pipeline OLED frames → tableaux C [CLARIFIÉ] :**
- `oled_editor/processor.py` : GIF → frames PIL → bitmaps NumPy 1-bit
  → `List[bytes]` stocké dans `ProjectModel.oled.frames`
- `build_manager/template_generator.py` : encode `oled.frames` en
  tableaux C `uint8_t frame_N[] = {0x00, ...}` injectés dans `keymap.c.j2`

**Structure mise à jour :** `modules/build_manager/vial_qmk_manager.py` ajouté.

---

### Architecture Completeness Checklist

**✅ Requirements Analysis**
- [x] Contexte projet analysé (33 FRs, 15 NFRs)
- [x] Complexité évaluée (Moyen-Élevé)
- [x] Contraintes techniques identifiées (toolchain ARM, cross-platform)
- [x] Préoccupations transversales mappées (async, état, isolation)

**✅ Architectural Decisions**
- [x] Stack technique : Python 3.11 + PySide6 6.10
- [x] Image processing : Pillow + NumPy
- [x] Async : QThread / QRunnable
- [x] Packaging : PyInstaller (.exe + AppImage)
- [x] Toolchain ARM : binaires vendorés + fallback système
- [x] Vial-QMK source : cache local, téléchargement unique au premier lancement
- [x] Génération QMK : Jinja2 templates
- [x] CI/CD : GitHub Actions matrix (Windows + Linux)

**✅ Implementation Patterns**
- [x] Conventions de nommage (snake_case signaux, PascalCase classes)
- [x] Séparation widget.py / processor.py dans chaque module
- [x] Injection ProjectModel (pas de singleton)
- [x] Error handling (Signal str, messages lisibles)
- [x] Async (QThread obligatoire > 50ms)
- [x] Atomic writes (tmp+replace)
- [x] Logging (stdlib logging, pas de print)

**✅ Project Structure**
- [x] Arborescence complète définie
- [x] Tous les FRs mappés à des fichiers spécifiques
- [x] Frontières de communication documentées
- [x] Points d'intégration (subprocess, signal boundaries) définis

---

### Architecture Readiness Assessment

**Statut global : ✅ PRÊT POUR L'IMPLÉMENTATION**
**Niveau de confiance : Élevé**

**Points forts :**
- Architecture modulaire directement dérivée des FRs — aucune abstraction inutile
- Séparation widget/processor garantit la testabilité de la logique métier
- Patterns explicites pour tous les points de friction potentiels
- Stack technique maîtrisée (Python/Qt) — courbe d'apprentissage nulle pour Pentinou

**Évolutions futures (post-MVP) :**
- Support macOS : runner macOS dans release.yml + binaire toolchain macOS
- Import code C RGB (v2) : nouveau module `modules/rgb_code_importer/`
- BT/ZMK (v3) : architecture différente, projet séparé recommandé

---

### Implementation Handoff

**Directives pour les agents IA :**
- Utiliser snake_case pour tous les signaux Qt (pas camelCase)
- Séparer systématiquement widget.py et processor.py dans chaque module
- Passer ProjectModel par injection de dépendance au constructeur
- Utiliser QThread pour tout subprocess ou traitement > 50ms
- Résoudre les chemins via `sys._MEIPASS` dans un bundle PyInstaller
- Co-localiser les tests dans `modules/<name>/tests/`

**Première priorité d'implémentation :**
```bash
python -m venv .venv && source .venv/bin/activate
pip install PySide6 Pillow numpy jinja2 pytest pytest-qt
# Story 1 : squelette MainWindow + ProjectModel + onglets vides
```

---

## Architecture Completion Summary

**Architecture Decision Workflow : COMPLETED ✅**
**Steps Completed :** 8
**Date :** 2026-02-22
**Document :** `_bmad-output/planning-artifacts/architecture.md`

### Final Deliverables

- 8 décisions architecturales majeures documentées avec versions
- 8 patterns d'implémentation définis pour la consistance entre agents
- 7 composants architecturaux spécifiés (modules domaine)
- 33 FRs + 15 NFRs entièrement couverts et mappés
- 3 gaps identifiés et résolus durant la validation

### Quality Assurance Checklist

**✅ Architecture Coherence**
- [x] Toutes les décisions sont compatibles entre elles
- [x] Stack Python 3.11 + PySide6 6.10 + Pillow + Jinja2 + PyInstaller validée
- [x] Patterns alignés avec les décisions technologiques

**✅ Requirements Coverage**
- [x] 33/33 FRs couverts, mappés à des fichiers spécifiques
- [x] 15/15 NFRs adressés architecturalement
- [x] Préoccupations transversales (async, atomic write, path resolution) documentées

**✅ Implementation Readiness**
- [x] Décisions spécifiques et actionnables
- [x] Patterns prévenant les conflits entre agents IA
- [x] Structure complète et non-ambiguë
- [x] Exemples de code fournis pour les patterns critiques

---

**Architecture Status : READY FOR IMPLEMENTATION ✅**

**Document Maintenance :** Mettre à jour ce document lors de décisions techniques majeures prises durant l'implémentation.
