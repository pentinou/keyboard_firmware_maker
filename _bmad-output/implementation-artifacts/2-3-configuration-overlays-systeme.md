# Story 2.3: Configuration des overlays d'informations système

Status: done

## Story

As a utilisateur (Pentinou),
I want to configure which system information is displayed on the OLED alongside my image,
So that I can see useful data like the active layer, Caps Lock state, or WPM on my keyboard.

## Acceptance Criteria

1. **Given** je suis dans l'onglet "OLED"
   **When** je regarde la section "Overlays"
   **Then** je vois des cases à cocher pour : "Layer actif", "Caps Lock", "WPM" (FR10)

2. **Given** je coche "Layer actif"
   **When** la configuration est mise à jour
   **Then** `oled.overlays` dans le ProjectModel inclut `"layer"`

3. **Given** je décoche "Caps Lock"
   **When** la configuration est mise à jour
   **Then** `oled.overlays` ne contient plus `"caps_lock"`

4. **Given** j'ai configuré des overlays et sauvegardé le projet
   **When** je recharge le projet
   **Then** les cases à cocher reflètent la configuration sauvegardée

5. **Given** j'ai activé plusieurs overlays
   **When** je consulte le ProjectModel
   **Then** `oled.overlays` contient exactement les identifiants cochés (snake_case)

## Tasks / Subtasks

- [x] Task 1: Ajouter les checkboxes overlay dans OledWidget (AC: 1, 2, 3, 5)
  - [x] 1.1 Ajouter un `QGroupBox("Overlays")` sous le bouton import dans `_setup_ui()`
  - [x] 1.2 Créer 3 `QCheckBox` : "Layer actif" (id: "layer"), "Caps Lock" (id: "caps_lock"), "WPM" (id: "wpm")
  - [x] 1.3 Attribuer `setObjectName` à chaque checkbox pour les trouver dans les tests
  - [x] 1.4 Connecter `stateChanged` de chaque checkbox → `_on_overlay_changed()`
  - [x] 1.5 `_on_overlay_changed()` reconstruit `model.oled.overlays` depuis l'état des checkboxes

- [x] Task 2: Synchroniser les checkboxes depuis le modèle (AC: 4)
  - [x] 2.1 Implémenter `_sync_overlays_from_model()` qui lit `model.oled.overlays` et coche les bonnes cases
  - [x] 2.2 Appeler `_sync_overlays_from_model()` dans `__init__` après `_setup_ui()`
  - [x] 2.3 Utiliser `blockSignals(True/False)` pendant la synchronisation pour éviter les mises à jour en cascade

- [x] Task 3: Écrire et valider les tests (AC: 1, 2, 3, 4, 5)
  - [x] 3.1 Ajouter `TestOledWidgetOverlays` dans `test_widget.py`
  - [x] 3.2 Tester présence des 3 checkboxes, état initial décoché
  - [x] 3.3 Tester que cocher "layer" met `"layer"` dans `model.oled.overlays`
  - [x] 3.4 Tester que décocher retire l'identifiant de `model.oled.overlays`
  - [x] 3.5 Tester `_sync_overlays_from_model()` avec un modèle pré-rempli
  - [x] 3.6 Vérifier `python3 -m pytest tests/ modules/ -v` — aucune régression

## Dev Notes

### Identifiants overlays (snake_case — règle project-context)

| QCheckBox label | id dans oled.overlays |
|---|---|
| "Layer actif" | `"layer"` |
| "Caps Lock"   | `"caps_lock"` |
| "WPM"         | `"wpm"` |

### Pattern _on_overlay_changed

```python
_OVERLAY_IDS = {
    "layer_check": "layer",
    "caps_lock_check": "caps_lock",
    "wpm_check": "wpm",
}

def _on_overlay_changed(self) -> None:
    overlays = []
    for obj_name, overlay_id in _OVERLAY_IDS.items():
        cb = self.findChild(QCheckBox, obj_name)
        if cb and cb.isChecked():
            overlays.append(overlay_id)
    self._model.oled.overlays = overlays
```

### _sync_overlays_from_model — éviter signaux en cascade

```python
def _sync_overlays_from_model(self) -> None:
    for obj_name, overlay_id in _OVERLAY_IDS.items():
        cb = self.findChild(QCheckBox, obj_name)
        if cb:
            cb.blockSignals(True)
            cb.setChecked(overlay_id in self._model.oled.overlays)
            cb.blockSignals(False)
```

### References

- PRD FR10 : configuration overlays infos système (layer, Caps Lock, WPM)
- Architecture §Format Patterns : clés snake_case obligatoires
- OledConfig.overlays : `list[str]` — identifiants des overlays actifs
- Epic 2 Story 2.3 : `_bmad-output/planning-artifacts/epics.md#Story-2.3`

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Story 2.3 implémentée avec succès — 106/106 tests passés, zéro régression (2026-02-22)
- `_OVERLAY_IDS` dict module-level : objectName → overlay_id (snake_case) — DRY pour setup + handler + sync
- `blockSignals(True/False)` dans `_sync_overlays_from_model` : empêche reconstruction de `overlays` pendant le chargement
- `QGroupBox("Overlays")` avec layout vertical propre pour les 3 checkboxes

### File List

- `modules/oled_editor/widget.py` (modifié — QGroupBox Overlays, 3 QCheckBox, _on_overlay_changed, _sync_overlays_from_model)
- `modules/oled_editor/tests/test_widget.py` (modifié — TestOledWidgetOverlays 12 tests)
