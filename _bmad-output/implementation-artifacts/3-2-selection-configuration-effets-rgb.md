# Story 3.2: Sélection et configuration des effets RGB

Status: done

## Story

As a utilisateur (Pentinou ou Alex),
I want to select a preset RGB effect and configure its parameters,
So that my keyboard has a dynamic lighting effect without needing to write QMK code.

## Acceptance Criteria

1. **Given** je suis dans l'onglet "RGB"
   **When** je regarde le sélecteur d'effets
   **Then** je vois au minimum : "Couleur statique uniforme", "Ripple au keystroke" (FR12)

2. **Given** je sélectionne "Couleur statique uniforme"
   **When** la sélection est confirmée
   **Then** un color picker s'affiche pour choisir la couleur uniforme
   **And** `rgb.effects[0]` dans le ProjectModel est mis à jour avec `type: "static"`

3. **Given** je sélectionne "Ripple au keystroke"
   **When** la sélection est confirmée
   **Then** trois paramètres configurables apparaissent (FR13) :
     - Couleur touche pressée (`color_primary`)
     - Couleur touches voisines (`color_secondary`)
     - Vitesse de fondu en ms (`fade_ms`)

4. **Given** je configure ripple avec couleur primaire #FF0000 et secondaire #FF8800
   **When** la configuration est validée
   **Then** `rgb.effects[0]` contient `{"type": "ripple", "color_primary": "#FF0000", "color_secondary": "#FF8800", "fade_ms": 500}`

5. **Given** je veux déclencher ripple sur une touche spécifique
   **When** j'active le mode "touche déclencheur" et je clique une touche dans le layout
   **Then** `trigger_key` dans l'effet est mis à jour avec l'ID de la touche (FR14)

## Tasks / Subtasks

- [x] Task 1: Créer modules/rgb_editor/effects.py — définitions d'effets (AC: 1)
  - [x] 1.1 Définir `EFFECT_TYPES: list[tuple[str, str]]` — (id, display_name) pour static et ripple
  - [x] 1.2 Aucun import Qt — pur Python

- [x] Task 2: Ajouter section effets dans RgbWidget (AC: 1, 2, 3, 4, 5)
  - [x] 2.1 Ajouter `QGroupBox("Effets RGB")` sous le scroll area des touches dans `_setup_ui()`
  - [x] 2.2 Ajouter `QComboBox` peuplé depuis `EFFECT_TYPES` avec `setObjectName("effect_combo")`
  - [x] 2.3 Ajouter panneau statique : bouton couleur `color_primary` (`setObjectName("btn_color_primary")`)
  - [x] 2.4 Ajouter panneau ripple : boutons `color_primary` + `color_secondary` + `QSpinBox` fade_ms + bouton trigger
  - [x] 2.5 QStackedWidget pour afficher/masquer les panneaux selon la sélection
  - [x] 2.6 `_on_effect_type_changed(index)` : crée/met à jour `model.rgb.effects[0]`
  - [x] 2.7 `_on_color_primary_clicked()`, `_on_color_secondary_clicked()` : QColorDialog → mise à jour modèle
  - [x] 2.8 `_on_fade_ms_changed(value)` : met à jour `model.rgb.effects[0].fade_ms`

- [x] Task 3: Implémenter le mode "touche déclencheur" (AC: 5)
  - [x] 3.1 Ajouter `self._trigger_mode = False` dans `__init__`
  - [x] 3.2 Bouton "Choisir touche déclencheur" → `self._trigger_mode = True`
  - [x] 3.3 Dans `_on_key_clicked()` : si `_trigger_mode` → setter `trigger_key` et quitter le mode

- [x] Task 4: Sync depuis le modèle (AC: 2, 3, 4, 5)
  - [x] 4.1 Étendre `_sync_from_model()` pour restaurer l'état du combo effet et les paramètres

- [x] Task 5: Écrire et valider les tests (AC: 1, 2, 3, 4, 5)
  - [x] 5.1 Créer `modules/rgb_editor/tests/test_effects.py` — tests EFFECT_TYPES
  - [x] 5.2 Ajouter `TestRgbWidgetEffects` dans `test_widget.py`
  - [x] 5.3 Vérifier `python3 -m pytest tests/ modules/ -v` — aucune régression

## Dev Notes

### effects.py

```python
# modules/rgb_editor/effects.py
EFFECT_TYPES: list[tuple[str, str]] = [
    ("static", "Couleur statique uniforme"),
    ("ripple", "Ripple au keystroke"),
]
```

### QStackedWidget pour panneaux dynamiques

```python
self._effect_stack = QStackedWidget()
self._effect_stack.addWidget(self._build_static_panel())   # index 0
self._effect_stack.addWidget(self._build_ripple_panel())   # index 1
```

### _on_effect_type_changed

```python
def _on_effect_type_changed(self, index: int) -> None:
    effect_id = EFFECT_TYPES[index][0]
    if not self._model.rgb.effects:
        self._model.rgb.effects = [RgbEffect(type=effect_id)]
    else:
        self._model.rgb.effects[0].type = effect_id
    self._effect_stack.setCurrentIndex(index)
```

### Mode trigger_key

```python
def _on_key_clicked(self, key_id: str) -> None:
    if self._trigger_mode:
        if self._model.rgb.effects:
            self._model.rgb.effects[0].trigger_key = key_id
        self._trigger_mode = False
        self._btn_trigger.setText("Choisir touche déclencheur")
        return
    # ... comportement normal (color picker) ...
```

### References

- PRD FR12 : sélection effet RGB prédéfini
- PRD FR13 : paramétrage effet ripple (couleurs, vitesse fondu)
- PRD FR14 : effets déclenchés par touches spécifiques
- RgbEffect dataclass : type, color_primary, color_secondary, fade_ms, trigger_key
- Epic 3 Story 3.2 : `_bmad-output/planning-artifacts/epics.md#Story-3.2`

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Story 3.2 implémentée avec succès — 149/149 tests passés, zéro régression (2026-02-22)
- `QStackedWidget` pour les panneaux statique/ripple (index = index du combo)
- Piège test : `setCurrentIndex(0)` sur combo déjà à 0 n'émet pas `currentIndexChanged` → fix : passer à index 1 d'abord
- `_ensure_effect()` : créé l'effet si `model.rgb.effects` est vide, sinon retourne effects[0]
- `blockSignals(True/False)` dans `_sync_from_model` pour combo et spinbox

### File List

- `modules/rgb_editor/effects.py` (nouveau — EFFECT_TYPES constant, pur Python)
- `modules/rgb_editor/widget.py` (modifié — section effets, QStackedWidget, trigger mode)
- `modules/rgb_editor/tests/test_effects.py` (nouveau — 7 tests)
- `modules/rgb_editor/tests/test_widget.py` (modifié — TestRgbWidgetEffects 17 tests)
