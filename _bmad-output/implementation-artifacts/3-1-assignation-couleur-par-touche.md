# Story 3.1: Assignation de couleur par touche

Status: done

## Story

As a utilisateur (Pentinou),
I want to assign a specific color to individual keys on a visual keyboard layout,
So that I can create a custom per-key RGB configuration without editing code.

## Acceptance Criteria

1. **Given** je suis dans l'onglet "RGB"
   **When** je vois le layout de mon clavier Sofle
   **Then** un rendu visuel du split clavier (gauche + droite) est affiché avec toutes les touches représentées

2. **Given** je clique sur une touche dans le layout visuel
   **When** je sélectionne une couleur via le color picker
   **Then** la touche change de couleur dans le rendu visuel en moins de 200ms (NFR2, FR11)
   **And** la couleur est stockée dans `rgb.per_key` au format `{"L_r0_c0": "#FF0000"}`

3. **Given** j'ai assigné des couleurs à plusieurs touches
   **When** je sauvegarde le projet
   **Then** toutes les assignations par touche sont persistées dans le fichier JSON

4. **Given** je recharge un projet avec des couleurs par touche
   **When** j'ouvre l'onglet "RGB"
   **Then** le layout visuel affiche les couleurs restaurées sur chaque touche

5. **Given** je change de modèle de clavier (ex: Sofle → Corne)
   **When** je reviens sur l'onglet "RGB"
   **Then** le layout est reconstruit selon les dimensions du nouveau clavier

## Tasks / Subtasks

- [x] Task 1: Étendre KeyboardDefinition avec le champ matrix (AC: 1, 5)
  - [x] 1.1 Ajouter `matrix: dict[str, int]` à `KeyboardDefinition` avec défaut `{"rows": 5, "cols": 6}`
  - [x] 1.2 Mettre à jour `load_keyboard()` pour lire `data.get("matrix", {})`
  - [x] 1.3 Vérifier que les tests existants ne régressent pas

- [x] Task 2: Créer modules/rgb_editor/widget.py — RgbWidget (AC: 1, 2, 4, 5)
  - [x] 2.1 Créer `RgbWidget(QWidget)` avec layout horizontal (deux panneaux gauche/droite)
  - [x] 2.2 `_build_layout()` : crée une grille de QPushButton (KEY_SIZE=36px) selon `rows × cols`
  - [x] 2.3 Nommer les boutons `"L_r{r}_c{c}"` (gauche) et `"R_r{r}_c{c}"` (droite)
  - [x] 2.4 `_on_key_clicked(key_id)` : ouvre `QColorDialog.getColor()` → appelle `_apply_color()`
  - [x] 2.5 `_apply_color(key_id, hex_color)` : met à jour le stylesheet du bouton ET `model.rgb.per_key`
  - [x] 2.6 `_sync_from_model()` : restaure toutes les couleurs depuis `model.rgb.per_key`
  - [x] 2.7 `refresh_layout()` : reconstruit la grille depuis `model.keyboard.model` (changement de clavier)

- [x] Task 3: Intégrer RgbWidget dans MainWindow (AC: 1, 5)
  - [x] 3.1 Remplacer `self._tab_rgb = QWidget()` par `self._tab_rgb = RgbWidget(self._model)`
  - [x] 3.2 Dans `_on_capabilities_changed()` : appeler `self._tab_rgb.refresh_layout()` si RGB activé

- [x] Task 4: Écrire et valider les tests (AC: 1, 2, 3, 4, 5)
  - [x] 4.1 Créer `modules/rgb_editor/tests/__init__.py`
  - [x] 4.2 Créer `modules/rgb_editor/tests/test_widget.py` — tests RgbWidget
  - [x] 4.3 Ajouter tests matrix dans `modules/hardware/tests/test_keyboard_loader.py`
  - [x] 4.4 Vérifier `python3 -m pytest tests/ modules/ -v` — aucune régression

## Dev Notes

### KeyboardDefinition.matrix — extension backward-compatible

```python
@dataclass
class KeyboardDefinition:
    model: str
    display_name: str
    description: str
    mcu_options: list[McuOption] = field(default_factory=list)
    capabilities: dict[str, bool] = field(default_factory=dict)
    matrix: dict[str, int] = field(default_factory=lambda: {"rows": 5, "cols": 6})
```

### RgbWidget — structure principale

```python
KEYBOARDS_DIR = Path(__file__).parent.parent.parent / "keyboards"
KEY_SIZE = 36

class RgbWidget(QWidget):
    def __init__(self, model: ProjectModel, parent=None):
        super().__init__(parent)
        self._model = model
        self._key_buttons: dict[str, QPushButton] = {}
        self._setup_ui()
        self._build_layout()
        self._sync_from_model()

    def _build_layout(self) -> None:
        # Clear existing buttons and sub-layouts
        for btn in self._key_buttons.values():
            btn.setParent(None)
        self._key_buttons.clear()
        while self._keys_hbox.count():
            item = self._keys_hbox.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Find current keyboard definition for matrix dims
        kb = self._find_current_keyboard()
        rows = kb.matrix.get("rows", 5) if kb else 5
        cols = kb.matrix.get("cols", 6) if kb else 6

        for side in ("L", "R"):
            frame = QFrame()
            frame.setFrameShape(QFrame.Shape.StyledPanel)
            grid = QGridLayout(frame)
            grid.setSpacing(2)
            for r in range(rows):
                for c in range(cols):
                    key_id = f"{side}_r{r}_c{c}"
                    btn = QPushButton()
                    btn.setFixedSize(KEY_SIZE, KEY_SIZE)
                    btn.setObjectName(key_id)
                    btn.setToolTip(key_id)
                    btn.clicked.connect(lambda checked=False, kid=key_id: self._on_key_clicked(kid))
                    grid.addWidget(btn, r, c)
                    self._key_buttons[key_id] = btn
            self._keys_hbox.addWidget(frame)

    def _find_current_keyboard(self):
        from modules.hardware.keyboard_loader import load_all_keyboards
        keyboards = load_all_keyboards(KEYBOARDS_DIR)
        return next((kb for kb in keyboards if kb.model == self._model.keyboard.model), None)
```

### _apply_color — format couleur

```python
def _apply_color(self, key_id: str, hex_color: str) -> None:
    btn = self._key_buttons.get(key_id)
    if btn:
        btn.setStyleSheet(f"background-color: {hex_color};")
    self._model.rgb.per_key[key_id] = hex_color
```

### refresh_layout — appelé par MainWindow

```python
def refresh_layout(self) -> None:
    """Reconstruit le layout quand le modèle de clavier change."""
    self._build_layout()
    self._sync_from_model()
```

### References

- PRD FR11 : assignation couleur par touche (interface visuelle)
- Architecture §rgb_editor/widget.py : keyboard layout renderer, color picker
- RgbConfig.per_key : dict[str, str] — clés format `"L_r{row}_c{col}"`, valeurs hex #RRGGBB
- Epic 3 Story 3.1 : `_bmad-output/planning-artifacts/epics.md#Story-3.1`

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Story 3.1 implémentée avec succès — 125/125 tests passés, zéro régression (2026-02-22)
- `KeyboardDefinition.matrix` ajouté backward-compatible (défaut `{"rows": 5, "cols": 6}`)
- Sofle: 5×6×2 = 60 boutons, Corne: 4×6×2 = 48 boutons — validés par tests
- `QColorDialog.getColor()` mocké dans les tests (dialog modal non testable autrement)
- `btn.setParent(None)` pour détacher les boutons Qt avant de les supprimer dans `_build_layout`
- `refresh_layout()` appelé par `MainWindow._on_capabilities_changed()` uniquement si RGB activé

### File List

- `modules/hardware/keyboard_loader.py` (modifié — `KeyboardDefinition.matrix` + `load_keyboard()`)
- `modules/rgb_editor/widget.py` (nouveau — RgbWidget, _build_layout, _apply_color, _sync_from_model, refresh_layout)
- `modules/rgb_editor/tests/__init__.py` (nouveau)
- `modules/rgb_editor/tests/test_widget.py` (nouveau — 14 tests RgbWidget)
- `modules/hardware/tests/test_keyboard_loader.py` (modifié — TestKeyboardDefinitionMatrix 4 tests)
- `ui/main_window.py` (modifié — RgbWidget + refresh_layout dans _on_capabilities_changed)
