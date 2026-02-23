# Story 1.3: Détection des capacités et masquage dynamique

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a utilisateur,
I want the application to automatically show or hide sections based on my keyboard's capabilities,
so that I am not confused by options that don't apply to my hardware.

## Acceptance Criteria

1. **Given** j'ai sélectionné "Sofle v2.1 RGB" (`oled: true`, `rgb: true` dans le YAML)
   **When** la sélection est confirmée
   **Then** les onglets "OLED" et "RGB" sont activés et visibles (FR3, FR4)

2. **Given** j'ai sélectionné un clavier sans OLED (`oled: false` dans le YAML)
   **When** la sélection est confirmée
   **Then** l'onglet "OLED" est désactivé (`setTabEnabled(False)`)

3. **Given** j'ai sélectionné un clavier sans RGB (`rgb: false` dans le YAML)
   **When** la sélection est confirmée
   **Then** l'onglet "RGB" est désactivé (`setTabEnabled(False)`)

4. **Given** je change de modèle de clavier
   **When** les capacités du nouveau modèle diffèrent
   **Then** les onglets visibles se mettent à jour dynamiquement sans redémarrage de l'application (FR4)

## Tasks / Subtasks

- [x] Task 1: Ajouter le signal `capabilities_changed` à HardwareWidget (AC: 1, 2, 3, 4)
  - [x] 1.1 Déclarer `capabilities_changed = Signal(dict)` dans `HardwareWidget` (dict = `{"oled": bool, "rgb": bool}`)
  - [x] 1.2 Émettre `self.capabilities_changed.emit(kb.capabilities)` dans `_on_model_changed()` après mise à jour du modèle
  - [x] 1.3 Vérifier que le signal est émis à l'initialisation (premier clavier chargé)

- [x] Task 2: Connecter le signal dans MainWindow et gérer les onglets (AC: 1, 2, 3, 4)
  - [x] 2.1 Dans `_setup_ui()`, connecter `self._tab_hardware.capabilities_changed` → `self._on_capabilities_changed`
  - [x] 2.2 Implémenter `_on_capabilities_changed(self, capabilities: dict) -> None`
  - [x] 2.3 Dans ce slot : appeler `self._tabs.setTabEnabled(1, capabilities.get("oled", False))` pour l'onglet OLED
  - [x] 2.4 Dans ce slot : appeler `self._tabs.setTabEnabled(2, capabilities.get("rgb", False))` pour l'onglet RGB
  - [x] 2.5 Forcer l'état initial après connexion (signal émis avant connexion dans `__init__`)

- [x] Task 3: Écrire les tests (AC: 1, 2, 3, 4)
  - [x] 3.1 Dans `test_widget.py` : tester que `capabilities_changed` est émis lors du changement de clavier (5 tests)
  - [x] 3.2 Dans `test_widget.py` : tester que le signal porte les bonnes capacités pour Sofle et Corne
  - [x] 3.3 Dans `test_main_window.py` : tester que l'onglet OLED est activé quand `oled=True`
  - [x] 3.4 Dans `test_main_window.py` : tester que l'onglet RGB est désactivé quand `rgb=False` (Corne)
  - [x] 3.5 Dans `test_main_window.py` : tester le changement dynamique Sofle→Corne
  - [x] 3.6 Vérifier que tous les tests passent — **50/50 PASSED**

## Dev Notes

### Pattern Signal — HardwareWidget → MainWindow

**Règle fondamentale (Architecture §Communication Patterns) :** toute communication inter-modules via signaux Qt.

```python
# modules/hardware/widget.py — ajout du signal
from PySide6.QtCore import Signal

class HardwareWidget(QWidget):
    capabilities_changed = Signal(dict)   # {"oled": bool, "rgb": bool}
    # snake_case OBLIGATOIRE pour les signaux (project-context.md)

    def _on_model_changed(self, index: int) -> None:
        ...
        self._model.keyboard.model = kb.model
        # Émettre APRÈS mise à jour du modèle, avec les capacités du nouveau clavier
        self.capabilities_changed.emit(kb.capabilities)
```

```python
# ui/main_window.py — connexion dans _setup_ui()
self._tab_hardware = HardwareWidget(self._model)
self._tab_hardware.capabilities_changed.connect(self._on_capabilities_changed)

def _on_capabilities_changed(self, capabilities: dict) -> None:
    """Met à jour la visibilité des onglets selon les capacités du clavier."""
    self._tabs.setTabEnabled(1, capabilities.get("oled", False))  # OLED
    self._tabs.setTabEnabled(2, capabilities.get("rgb", False))   # RGB
    logger.info("Capacités mises à jour : OLED=%s, RGB=%s",
                capabilities.get("oled"), capabilities.get("rgb"))
```

### Indices des onglets (CRITIQUE — ne pas se tromper)

```python
# ui/main_window.py — ordre défini dans _setup_ui()
self._tabs.addTab(self._tab_hardware, "Matériel")  # index 0
self._tabs.addTab(self._tab_oled, "OLED")          # index 1
self._tabs.addTab(self._tab_rgb, "RGB")            # index 2
self._tabs.addTab(self._tab_build, "Build")        # index 3
```

**⚠️ JAMAIS utiliser des indices en dur dans les tests** — utiliser `findText()` ou stocker les indices comme constantes.

### Ordre des opérations dans _setup_ui() (IMPORTANT)

La connexion du signal doit se faire **après** `addTab()` pour que `setTabEnabled()` fonctionne :

```python
def _setup_ui(self) -> None:
    self._tabs = QTabWidget()
    self.setCentralWidget(self._tabs)

    self._tab_hardware = HardwareWidget(self._model)  # 1. Créer le widget
    self._tab_oled = QWidget()
    self._tab_rgb = QWidget()
    self._tab_build = QWidget()

    self._tabs.addTab(self._tab_hardware, "Matériel")  # 2. Ajouter les tabs
    self._tabs.addTab(self._tab_oled, "OLED")
    self._tabs.addTab(self._tab_rgb, "RGB")
    self._tabs.addTab(self._tab_build, "Build")

    # 3. Connecter le signal APRÈS addTab() pour que setTabEnabled() soit valide
    self._tab_hardware.capabilities_changed.connect(self._on_capabilities_changed)
```

**Alternative propre :** appeler `_on_capabilities_changed` manuellement après la connexion pour l'état initial, si `HardwareWidget.__init__` émet le signal avant la connexion.

### État initial des onglets

Au démarrage sans clavier sélectionné, les onglets OLED et RGB doivent être **désactivés par défaut**.
`HardwareWidget.__init__` appelle `_on_model_changed(0)` qui émet `capabilities_changed` → mais ce signal est émis AVANT que `MainWindow` ne connecte le slot (car `_setup_ui` crée le widget avant d'addTab et de connecter).

**Solution :** Dans `MainWindow._setup_ui()`, après la connexion du signal, appeler explicitement :
```python
# Forcer l'état initial basé sur le premier clavier chargé
if self._tab_hardware._keyboards:
    first_kb = self._tab_hardware._keyboards[self._tab_hardware._keyboard_combo.currentIndex()]
    self._on_capabilities_changed(first_kb.capabilities)
```

Ou plus simplement, initialiser les onglets OLED et RGB comme **désactivés** par défaut et laisser le signal les activer :
```python
self._tabs.setTabEnabled(1, False)  # OLED — désactivé par défaut
self._tabs.setTabEnabled(2, False)  # RGB — désactivé par défaut
# Puis connecter le signal → il sera déclenché au prochain changement
# ET appeler manuellement pour l'état initial
```

### Apprentissages Stories 1.1 & 1.2

- `python3 -m pytest tests/ modules/ -v` pour lancer tous les tests
- `blockSignals(True/False)` à utiliser si rechargement MCU combo déclenche des signaux en cascade
- `setItemData(..., ToolTipRole)` pour les tooltips
- `qtbot.waitSignal(signal, timeout=1000)` pour tester l'émission de signaux Qt
- `setObjectName()` sur les widgets pour les retrouver avec `findChild()`

### Tests — Patterns attendus

```python
# modules/hardware/tests/test_widget.py — nouveaux tests
def test_capabilities_changed_signal_emitted(qtbot):
    model = ProjectModel()
    widget = HardwareWidget(model)
    qtbot.addWidget(widget)
    keyboard_combo = widget.findChild(QComboBox, "keyboard_combo")
    # Changer de clavier → signal doit être émis
    with qtbot.waitSignal(widget.capabilities_changed, timeout=1000) as blocker:
        keyboard_combo.setCurrentIndex((keyboard_combo.currentIndex() + 1) % keyboard_combo.count())
    assert isinstance(blocker.args[0], dict)
    assert "oled" in blocker.args[0]
    assert "rgb" in blocker.args[0]

def test_sofle_capabilities_oled_and_rgb_true(qtbot):
    model = ProjectModel()
    widget = HardwareWidget(model)
    qtbot.addWidget(widget)
    keyboard_combo = widget.findChild(QComboBox, "keyboard_combo")
    sofle_index = next(i for i in range(keyboard_combo.count()) if "Sofle" in keyboard_combo.itemText(i))
    with qtbot.waitSignal(widget.capabilities_changed, timeout=1000) as blocker:
        keyboard_combo.setCurrentIndex(sofle_index)
    caps = blocker.args[0]
    assert caps.get("oled") is True
    assert caps.get("rgb") is True
```

```python
# tests/test_main_window.py — nouveaux tests
def test_oled_tab_enabled_for_sofle(qtbot):
    model = ProjectModel()
    window = MainWindow(model)
    qtbot.addWidget(window)
    tabs = window._tabs
    keyboard_combo = window._tab_hardware.findChild(QComboBox, "keyboard_combo")
    sofle_index = next(i for i in range(keyboard_combo.count()) if "Sofle" in keyboard_combo.itemText(i))
    keyboard_combo.setCurrentIndex(sofle_index)
    assert tabs.isTabEnabled(1) is True   # OLED
    assert tabs.isTabEnabled(2) is True   # RGB

def test_rgb_tab_disabled_for_corne(qtbot):
    model = ProjectModel()
    window = MainWindow(model)
    qtbot.addWidget(window)
    tabs = window._tabs
    keyboard_combo = window._tab_hardware.findChild(QComboBox, "keyboard_combo")
    corne_index = next(i for i in range(keyboard_combo.count()) if "Corne" in keyboard_combo.itemText(i))
    keyboard_combo.setCurrentIndex(corne_index)
    assert tabs.isTabEnabled(2) is False  # RGB désactivé
    assert tabs.isTabEnabled(1) is True   # OLED toujours actif
```

### Project Structure Notes

**Fichiers modifiés uniquement (aucun nouveau fichier) :**
```
modules/hardware/widget.py        # Ajouter Signal capabilities_changed + emit dans _on_model_changed
ui/main_window.py                 # Connecter signal + implémenter _on_capabilities_changed + init tabs
modules/hardware/tests/test_widget.py    # Ajouter tests signal
tests/test_main_window.py         # Ajouter tests tab enable/disable
```

**Fichiers non touchés (régression à éviter) :**
```
keyboard_loader.py, keyboards/*.yaml, models/project_model.py
tests/test_project_model.py, tests/test_about_dialog.py
ui/widgets/about_dialog.py
```

### References

- Architecture §Communication Patterns : signaux inter-modules, snake_case obligatoire
- Architecture §Requirements→Structure Mapping : FR3-FR4 → `hardware/keyboard_loader.py` + `ui/main_window.py`
- PRD FR3 : détection automatique capacités
- PRD FR4 : masquage dynamique des sections
- Epic 1 Story 1.3 : `_bmad-output/planning-artifacts/epics.md#Story-1.3`
- Project Context : règle snake_case signaux, `Signal(dict)` pour données structurées
- PySide6 QTabWidget : `setTabEnabled(index, bool)` — Qt 6.x

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Story 1.3 implémentée avec succès — 50/50 tests passés, zéro régression (2026-02-22)
- Piège découvert : `capabilities_changed` émis pendant `HardwareWidget.__init__` AVANT que `MainWindow` connecte le slot → état initial incorrect. Fix : appel manuel de `_on_capabilities_changed` après connexion en lisant `_keyboards[currentIndex()].capabilities`
- Piège test : Corne alphabétiquement premier (index 0) → `setCurrentIndex(0)` sans changement n'émet pas de signal. Fix : passer à un autre index d'abord dans le test
- `setTabEnabled(False)` choisi plutôt que `removeTab()` : tab reste visible mais grisé, plus cohérent UX et réversible

### File List

- `modules/hardware/widget.py` (modifié — Signal `capabilities_changed` + emit dans `_on_model_changed`)
- `ui/main_window.py` (modifié — connexion signal + `_on_capabilities_changed` + init état onglets)
- `modules/hardware/tests/test_widget.py` (modifié — ajout `TestCapabilitiesSignal` avec 5 tests)
- `tests/test_main_window.py` (modifié — ajout 4 tests tab enable/disable)
