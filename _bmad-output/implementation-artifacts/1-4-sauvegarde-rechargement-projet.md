# Story 1.4: Sauvegarde et rechargement de projet

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a utilisateur (Pentinou),
I want to save my configuration and reload it later,
so that I can resume my work without starting from zero after a firmware issue.

## Acceptance Criteria

1. **Given** j'ai configuré ma sélection de clavier
   **When** je clique "Sauvegarder le projet" dans le menu "Fichier"
   **Then** une fenêtre de dialogue `QFileDialog` s'ouvre pour choisir l'emplacement
   **And** la configuration est sauvegardée en JSON valide avec des clés snake_case (FR25)

2. **Given** j'ai sélectionné "Sauvegarder" et que le chemin est choisi
   **When** l'écriture s'effectue
   **Then** elle utilise le pattern atomique (`tmp` + `replace`) — le fichier existant n'est jamais corrompu (NFR7)

3. **Given** un fichier projet `.kfm.json` existe sur le disque
   **When** je clique "Ouvrir un projet" et je le sélectionne
   **Then** l'application charge la configuration et restaure la sélection de clavier (FR26)
   **And** le combo clavier dans l'onglet "Matériel" reflète le modèle chargé

4. **Given** j'ai chargé un projet et modifié la sélection matériel
   **When** je sauvegarde à nouveau
   **Then** la nouvelle configuration remplace l'ancienne atomiquement (FR27)

5. **Given** une erreur d'écriture se produit (disque plein, permissions)
   **When** la sauvegarde échoue
   **Then** le fichier original est intact
   **And** un `QMessageBox.critical()` affiche un message d'erreur lisible

## Tasks / Subtasks

- [x] Task 1: Créer modules/project_manager/file_io.py — sauvegarde/chargement JSON pur Python (AC: 1, 2, 4, 5)
  - [x] 1.1 Implémenter `save_project(model: ProjectModel, path: Path) -> None` avec écriture atomique
  - [x] 1.2 Implémenter `load_project(path: Path) -> ProjectModel` qui lit le JSON et appelle `ProjectModel.from_dict()`
  - [x] 1.3 Valider : aucun import Qt dans `file_io.py` — testable sans QApplication
  - [x] 1.4 Gestion d'erreur : propager les exceptions `OSError`, `json.JSONDecodeError` — jamais les avaler

- [x] Task 2: Ajouter le menu "Fichier" dans MainWindow avec actions Save/Open (AC: 1, 3)
  - [x] 2.1 Ajouter `menu_file = menu_bar.addMenu("Fichier")` **avant** le menu "Aide"
  - [x] 2.2 Ajouter action `save_action = menu_file.addAction("Sauvegarder le projet…")` connectée à `_save_project()`
  - [x] 2.3 Ajouter action `open_action = menu_file.addAction("Ouvrir un projet…")` connectée à `_open_project()`
  - [x] 2.4 Ajouter séparateur et action "Quitter" (`QApplication.quit()`)

- [x] Task 3: Implémenter `_save_project()` dans MainWindow (AC: 1, 2, 5)
  - [x] 3.1 Ouvrir `QFileDialog.getSaveFileName()` avec filtre `"Projet KFM (*.kfm.json)"` et dir par défaut `Path.home()`
  - [x] 3.2 Si l'utilisateur annule (chemin vide) → ne rien faire
  - [x] 3.3 Appeler `save_project(self._model, Path(path))` dans un bloc try/except
  - [x] 3.4 En cas d'erreur `OSError` → afficher `QMessageBox.critical(self, "Erreur", f"Impossible de sauvegarder : {e}")`
  - [x] 3.5 En cas de succès → `logger.info("Projet sauvegardé : %s", path)`

- [x] Task 4: Implémenter `_open_project()` dans MainWindow (AC: 3, 4)
  - [x] 4.1 Ouvrir `QFileDialog.getOpenFileName()` avec filtre `"Projet KFM (*.kfm.json)"` et dir par défaut `Path.home()`
  - [x] 4.2 Si l'utilisateur annule → ne rien faire
  - [x] 4.3 Appeler `load_project(Path(path))` dans un bloc try/except
  - [x] 4.4 Mettre à jour `self._model` avec les données chargées (remplacer les champs via `from_dict`)
  - [x] 4.5 Synchroniser le combo clavier dans `HardwareWidget` avec `model.keyboard.model` chargé
  - [x] 4.6 En cas d'erreur `(OSError, json.JSONDecodeError, KeyError)` → `QMessageBox.critical()`

- [x] Task 5: Écrire et valider les tests (AC: 1, 2, 3, 4, 5)
  - [x] 5.1 Créer `modules/project_manager/tests/__init__.py`
  - [x] 5.2 Créer `modules/project_manager/tests/test_file_io.py` — tests `save_project` et `load_project`
  - [x] 5.3 Ajouter tests dans `tests/test_main_window.py` pour le menu "Fichier"
  - [x] 5.4 Vérifier que tous les tests passent avec `python3 -m pytest tests/ modules/ -v` (aucune régression)

## Dev Notes

### file_io.py — Implémentation attendue (pur Python, sans Qt)

```python
# modules/project_manager/file_io.py
from __future__ import annotations

import json
import logging
from pathlib import Path

from models.project_model import ProjectModel

logger = logging.getLogger(__name__)


def save_project(model: ProjectModel, path: Path) -> None:
    """Sauvegarde le ProjectModel en JSON avec écriture atomique (NFR7).

    Pattern : écriture dans .tmp → replace() atomique.
    Lève OSError si l'écriture échoue — ne jamais avaler l'exception.
    """
    data = model.to_dict()
    content = json.dumps(data, indent=2, ensure_ascii=False)
    tmp = path.with_suffix(".tmp")
    try:
        tmp.write_text(content, encoding="utf-8")
        tmp.replace(path)
    except OSError:
        # Nettoyer le .tmp si possible
        if tmp.exists():
            tmp.unlink(missing_ok=True)
        raise
    logger.info("Projet sauvegardé : %s", path)


def load_project(path: Path) -> ProjectModel:
    """Charge un ProjectModel depuis un fichier JSON.

    Lève OSError si le fichier est inaccessible.
    Lève json.JSONDecodeError si le JSON est malformé.
    """
    content = path.read_text(encoding="utf-8")
    data = json.loads(content)
    model = ProjectModel.from_dict(data)
    logger.info("Projet chargé : %s", path)
    return model
```

### Menu "Fichier" — Ordre critique dans _setup_menu()

```python
def _setup_menu(self) -> None:
    menu_bar = self.menuBar()

    # Menu Fichier — AVANT Aide
    file_menu = menu_bar.addMenu("Fichier")
    save_action = file_menu.addAction("Sauvegarder le projet…")
    save_action.triggered.connect(self._save_project)
    open_action = file_menu.addAction("Ouvrir un projet…")
    open_action.triggered.connect(self._open_project)
    file_menu.addSeparator()
    quit_action = file_menu.addAction("Quitter")
    quit_action.triggered.connect(QApplication.quit)

    # Menu Aide — inchangé
    help_menu = menu_bar.addMenu("Aide")
    about_action = help_menu.addAction("À propos…")
    about_action.triggered.connect(self._show_about)
```

### Synchronisation combo après chargement (Task 4.5)

Après `load_project()`, le `ProjectModel` est mis à jour mais le `HardwareWidget` n'est pas au courant. Il faut synchroniser le combo :

```python
def _open_project(self) -> None:
    path, _ = QFileDialog.getOpenFileName(
        self, "Ouvrir un projet", str(Path.home()), "Projet KFM (*.kfm.json)"
    )
    if not path:
        return
    try:
        loaded = load_project(Path(path))
    except (OSError, json.JSONDecodeError, KeyError) as e:
        QMessageBox.critical(self, "Erreur", f"Impossible de charger le projet : {e}")
        return

    # Mettre à jour le modèle partagé (champs par champs pour conserver la référence)
    self._model.keyboard = loaded.keyboard
    self._model.oled = loaded.oled
    self._model.rgb = loaded.rgb
    self._model.build = loaded.build

    # Synchroniser le combo clavier dans HardwareWidget
    self._sync_hardware_widget()
    logger.info("Projet ouvert : %s", path)


def _sync_hardware_widget(self) -> None:
    """Synchronise le combo clavier du HardwareWidget avec model.keyboard.model."""
    combo = self._tab_hardware._keyboard_combo
    for i in range(combo.count()):
        kb = self._tab_hardware._keyboards[i]
        if kb.model == self._model.keyboard.model:
            combo.setCurrentIndex(i)
            break
```

**⚠️ Important :** Ne pas remplacer `self._model` par une nouvelle instance ! Les widgets existants ont une référence au même objet. Mettre à jour les **champs** uniquement.

### Écriture atomique — Pourquoi tmp.replace() ? (NFR7)

```python
# ✅ Atomique — jamais de fichier corrompu
tmp = path.with_suffix(".tmp")
tmp.write_text(content, encoding="utf-8")
tmp.replace(path)  # os.replace() — atomique sur la même partition

# ❌ NON ATOMIQUE — crash pendant écriture = fichier corrompu
path.write_text(content, encoding="utf-8")
```

Sur Linux/Windows, `Path.replace()` appelle `os.rename()` qui est atomique si src et dst sont sur la même partition (le cas ici — `.tmp` dans le même répertoire).

### Tests attendus — file_io.py (sans Qt)

```python
# modules/project_manager/tests/test_file_io.py

def test_save_project_creates_file(tmp_path):
    model = ProjectModel()
    model.keyboard.model = "sofle-v2"
    path = tmp_path / "test.kfm.json"
    save_project(model, path)
    assert path.exists()

def test_save_project_valid_json(tmp_path):
    model = ProjectModel()
    path = tmp_path / "test.kfm.json"
    save_project(model, path)
    data = json.loads(path.read_text())
    assert "keyboard" in data
    assert "version" in data

def test_save_project_snake_case_keys(tmp_path):
    model = ProjectModel()
    path = tmp_path / "test.kfm.json"
    save_project(model, path)
    data = json.loads(path.read_text())
    assert "keyboard" in data          # snake_case
    assert "image_path" in data["oled"]  # snake_case

def test_save_project_no_tmp_file_remains(tmp_path):
    model = ProjectModel()
    path = tmp_path / "test.kfm.json"
    save_project(model, path)
    assert not (tmp_path / "test.tmp").exists()

def test_load_project_roundtrip(tmp_path):
    model = ProjectModel()
    model.keyboard.model = "sofle-v2"
    model.keyboard.mcu = "rp2040"
    path = tmp_path / "test.kfm.json"
    save_project(model, path)
    loaded = load_project(path)
    assert loaded.keyboard.model == "sofle-v2"
    assert loaded.keyboard.mcu == "rp2040"

def test_load_project_missing_file_raises_oserror(tmp_path):
    with pytest.raises(OSError):
        load_project(tmp_path / "nonexistent.kfm.json")

def test_load_project_invalid_json_raises(tmp_path):
    path = tmp_path / "bad.kfm.json"
    path.write_text("not json {{{", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        load_project(path)

def test_save_project_frames_not_serialized(tmp_path):
    """Les frames OLED ne doivent pas apparaître dans le JSON (Story 1.1)."""
    model = ProjectModel()
    model.oled.frames = [b'\x00\xFF']  # données runtime
    path = tmp_path / "test.kfm.json"
    save_project(model, path)
    data = json.loads(path.read_text())
    assert "frames" not in data.get("oled", {})
```

### Tests MainWindow — menu Fichier

```python
def test_main_window_has_file_menu(qtbot):
    model = ProjectModel()
    window = MainWindow(model)
    qtbot.addWidget(window)
    menu_bar = window.menuBar()
    menus = [menu_bar.actions()[i].text() for i in range(len(menu_bar.actions()))]
    assert "Fichier" in menus

def test_file_menu_has_save_action(qtbot):
    model = ProjectModel()
    window = MainWindow(model)
    qtbot.addWidget(window)
    # Trouver le menu Fichier et ses actions
    file_menu = next(a.menu() for a in window.menuBar().actions() if a.text() == "Fichier")
    action_texts = [a.text() for a in file_menu.actions() if not a.isSeparator()]
    assert any("Sauvegarder" in t for t in action_texts)

def test_file_menu_has_open_action(qtbot):
    model = ProjectModel()
    window = MainWindow(model)
    qtbot.addWidget(window)
    file_menu = next(a.menu() for a in window.menuBar().actions() if a.text() == "Fichier")
    action_texts = [a.text() for a in file_menu.actions() if not a.isSeparator()]
    assert any("Ouvrir" in t for t in action_texts)
```

### Apprentissages Stories 1.1-1.3

- `python3 -m pytest tests/ modules/ -v` pour lancer tous les tests
- Signal émis avant connexion → init manuelle requise (pattern découvert en 1.3)
- Corne est alphabétiquement premier (index 0) → prendre en compte dans les tests
- `blockSignals(True/False)` pour éviter signaux en cascade
- Aucun import Qt dans les modules pur Python (`file_io.py`, `keyboard_loader.py`)
- `QApplication` doit être importé de `PySide6.QtWidgets` pour `quit()`

### Project Structure Notes

**Fichiers à créer :**
```
modules/project_manager/
├── file_io.py                       # NOUVEAU (pur Python — save_project, load_project)
└── tests/
    ├── __init__.py                  # NOUVEAU
    └── test_file_io.py              # NOUVEAU
```

**Fichiers à modifier :**
```
ui/main_window.py                   # Menu "Fichier" + _save_project() + _open_project() + _sync_hardware_widget()
tests/test_main_window.py           # Tests menu Fichier
```

**Fichiers non touchés (régression à éviter) :**
```
modules/hardware/*, models/project_model.py, keyboards/*.yaml
tests/test_project_model.py, tests/test_about_dialog.py
ui/widgets/about_dialog.py
```

### References

- Architecture §Process Patterns : écriture atomique `tmp.replace(path)` — `_bmad-output/planning-artifacts/architecture.md#Process-Patterns`
- Architecture §Requirements→Structure Mapping : FR25-FR27 → `modules/project_manager/file_io.py`
- Architecture §Format Patterns : JSON snake_case, couleurs hex #RRGGBB, chemins absolus
- PRD FR25 (sauvegarde), FR26 (rechargement), FR27 (modification incrémentale) — `_bmad-output/planning-artifacts/prd.md`
- NFR7 : sauvegarde sans corruption — écriture atomique obligatoire
- Epic 1 Story 1.4 : `_bmad-output/planning-artifacts/epics.md#Story-1.4`
- Project Context : règle atomic write, no Qt dans processors, logging stdlib — `_bmad-output/project-context.md`

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Story 1.4 implémentée avec succès — 63/63 tests passés, zéro régression (2026-02-22)
- Piège PySide6 : `next(a.menu() for a in ...)` crée un objet temporaire QMenu qui peut être libéré avant usage. Fix : stocker d'abord la référence à l'action puis appeler `.menu()` sur la référence stockée.
- Menu "Fichier" placé avant "Aide" dans `_setup_menu()` — ordre confirmé par les tests.
- Écriture atomique via `.with_suffix(".tmp") + .replace()` — nettoyage du .tmp en cas d'OSError.

### File List

- `modules/project_manager/file_io.py` (nouveau — save_project + load_project, écriture atomique, pur Python)
- `modules/project_manager/tests/__init__.py` (nouveau — package tests)
- `modules/project_manager/tests/test_file_io.py` (nouveau — 10 tests file_io)
- `ui/main_window.py` (modifié — menu "Fichier" + _save_project + _open_project + _sync_hardware_widget)
- `tests/test_main_window.py` (modifié — 3 tests menu Fichier ajoutés)
