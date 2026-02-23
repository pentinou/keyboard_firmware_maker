# Story 3.3: Aperçu animé des effets RGB

Status: done

## Story

As a utilisateur (Pentinou ou Alex),
I want to see an animated preview of my configured RGB effect in the application,
So that I can validate the visual result before compiling and flashing firmware.

## Acceptance Criteria

1. **Given** j'ai sélectionné et configuré un effet RGB
   **When** je regarde la zone de prévisualisation (onglet RGB)
   **Then** un aperçu animé de l'effet s'exécute sur le layout visuel du clavier (FR15)

2. **Given** l'effet "Ripple au keystroke" est configuré
   **When** l'aperçu s'affiche
   **Then** une animation montre une touche simulée pressée, avec propagation primary → secondary vers les voisines

3. **Given** l'effet "Couleur statique uniforme" est configuré
   **When** l'aperçu s'affiche
   **Then** toutes les touches s'affichent avec la couleur choisie (pas d'animation, pas de timer)

4. **Given** je modifie un paramètre d'effet (ex : changer la couleur secondaire)
   **When** la modification est appliquée
   **Then** l'aperçu se met à jour en moins de 200ms pour refléter le changement (NFR2)

5. **Given** l'aperçu utilise un QTimer pour l'animation ripple
   **When** je navigue vers un autre onglet
   **Then** l'animation se met en pause (le timer s'arrête) pour économiser les ressources

## Tasks / Subtasks

- [x] Task 1: Créer modules/rgb_editor/effect_preview.py (AC: 1, 2, 3, 4)
  - [x] 1.1 Créer `EffectPreview` avec référence à `key_buttons: dict[str, QPushButton]`
  - [x] 1.2 `start(effect: RgbEffect)` : démarre l'animation selon le type d'effet
  - [x] 1.3 `stop()` : arrête le timer et réinitialise les couleurs
  - [x] 1.4 `update(effect: RgbEffect)` : met à jour l'animation sans redémarrer
  - [x] 1.5 `_tick()` : avance d'un step ripple (distance Manhattan depuis centre)
  - [x] 1.6 `is_active() -> bool` : indique si l'animation est en cours

- [x] Task 2: Intégrer EffectPreview dans RgbWidget (AC: 1, 4, 5)
  - [x] 2.1 Créer `self._preview = EffectPreview(self._key_buttons)` après `_build_layout()`
  - [x] 2.2 Surcharger `showEvent` → `self._preview.start(effect)` si effet configuré
  - [x] 2.3 Surcharger `hideEvent` → `self._preview.stop()`
  - [x] 2.4 Appeler `_update_preview()` depuis `_on_effect_type_changed`, `_on_color_primary_clicked`, `_on_color_secondary_clicked`
  - [x] 2.5 `refresh_layout()` : recréer `EffectPreview` avec les nouveaux boutons

- [x] Task 3: Écrire et valider les tests (AC: 1, 2, 3, 4, 5)
  - [x] 3.1 Créer `modules/rgb_editor/tests/test_effect_preview.py`
  - [x] 3.2 Tester `start(static)` : couleurs appliquées, timer inactif
  - [x] 3.3 Tester `start(ripple)` : timer actif
  - [x] 3.4 Tester `stop()` : timer arrêté, couleurs effacées
  - [x] 3.5 Tester `update(static)` : couleurs mises à jour sans timer
  - [x] 3.6 Tester `hideEvent`/`showEvent` dans test_widget.py
  - [x] 3.7 Vérifier `python3 -m pytest tests/ modules/ -v` — aucune régression

## Dev Notes

### EffectPreview — structure

```python
RIPPLE_STEPS = 4
RIPPLE_INTERVAL_MS = 200

class EffectPreview:
    def __init__(self, key_buttons: dict[str, QPushButton]) -> None:
        self._key_buttons = key_buttons
        self._timer = QTimer()
        self._timer.timeout.connect(self._tick)
        self._effect: RgbEffect | None = None
        self._step = 0
        self._center: tuple[str, int, int] | None = None

    def start(self, effect: RgbEffect) -> None:
        self._timer.stop()
        self._effect = effect
        self._step = 0
        if effect.type == "static":
            self._apply_static()
        elif effect.type == "ripple":
            self._pick_new_center()
            self._timer.setInterval(RIPPLE_INTERVAL_MS)
            self._timer.start()

    def stop(self) -> None:
        self._timer.stop()
        self._reset_keys()

    def update(self, effect: RgbEffect) -> None:
        self._effect = effect
        if effect.type == "static":
            self._timer.stop()
            self._apply_static()
        elif not self._timer.isActive():
            self.start(effect)

    def is_active(self) -> bool:
        return self._timer.isActive()
```

### Ripple _tick — distance Manhattan

```python
def _distance(self, key_id: str) -> int:
    if self._center is None:
        return 999
    parts = key_id.split("_")
    side, r, c = parts[0], int(parts[1][1:]), int(parts[2][1:])
    cs, cr, cc = self._center
    if side != cs:
        return 999  # demi-clavier différent
    return abs(r - cr) + abs(c - cc)  # distance Manhattan

def _tick(self) -> None:
    self._reset_keys()
    step = self._step % RIPPLE_STEPS
    if step == 0:
        center_id = f"{self._center[0]}_r{self._center[1]}_c{self._center[2]}"
        if center_id in self._key_buttons:
            self._key_buttons[center_id].setStyleSheet(
                f"background-color: {self._effect.color_primary};"
            )
    elif step == 1:
        for kid, btn in self._key_buttons.items():
            d = self._distance(kid)
            if d == 0:
                btn.setStyleSheet(f"background-color: {self._effect.color_primary};")
            elif d == 1:
                btn.setStyleSheet(f"background-color: {self._effect.color_secondary};")
    elif step == 2:
        for kid, btn in self._key_buttons.items():
            if self._distance(kid) == 1:
                btn.setStyleSheet(f"background-color: {self._effect.color_secondary};")
    elif step == 3:
        self._pick_new_center()
    self._step += 1
```

### showEvent / hideEvent dans RgbWidget

```python
def showEvent(self, event: QShowEvent) -> None:
    super().showEvent(event)
    if self._preview and self._model.rgb.effects:
        self._preview.start(self._model.rgb.effects[0])

def hideEvent(self, event: QHideEvent) -> None:
    super().hideEvent(event)
    if self._preview:
        self._preview.stop()
```

### References

- PRD FR15 : aperçu animé effets RGB configurés
- NFR2 : interactions UI < 200ms
- Architecture §rgb_editor/effect_preview.py : aperçu animé (QTimer)
- Epic 3 Story 3.3 : `_bmad-output/planning-artifacts/epics.md#Story-3.3`

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Story 3.3 implémentée avec succès — 173/173 tests passés, zéro régression (2026-02-22)
- `EffectPreview` : timer QTimer + `_pick_new_center()` aléatoire, `_tick()` par distance Manhattan
- `showEvent`/`hideEvent` testés en appelant les méthodes directement (sans show/hide réel du widget)
- `_update_preview()` : appel depuis les 3 handlers d'effets (type, primaire, secondaire)
- `refresh_layout()` : recrée `EffectPreview` avec les nouveaux `_key_buttons`

### File List

- `modules/rgb_editor/effect_preview.py` (nouveau — EffectPreview, QTimer, distance Manhattan)
- `modules/rgb_editor/widget.py` (modifié — showEvent, hideEvent, _update_preview, refresh_layout)
- `modules/rgb_editor/tests/test_effect_preview.py` (nouveau — 17 tests)
