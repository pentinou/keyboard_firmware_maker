# Story 2.2: Prévisualisation animée d'un GIF

Status: done

## Story

As a utilisateur (Alex),
I want to see my imported GIF animate frame by frame in the OLED preview,
So that I can verify the animation will look correct on my keyboard before compiling.

## Acceptance Criteria

1. **Given** j'ai importé un fichier GIF multi-frames
   **When** la conversion est terminée
   **Then** la prévisualisation affiche les frames en séquence animée (FR9)
   **And** la vitesse d'animation reflète le délai inter-frames du GIF original

2. **Given** un GIF est en cours d'animation
   **When** j'observe chaque frame
   **Then** chaque frame est rendue en 1-bit 64×128px avec dithering (cohérent avec Story 2.1)

3. **Given** j'importe un GIF à frame unique (image statique déguisée en GIF)
   **When** la conversion s'effectue
   **Then** l'application affiche une prévisualisation statique sans erreur (pas d'animation)

4. **Given** j'importe une image PNG ou BMP statique
   **When** la conversion s'effectue
   **Then** aucune animation ne démarre (1 seule frame)

5. **Given** l'animation est en cours
   **When** j'importe une nouvelle image
   **Then** l'ancienne animation s'arrête et la nouvelle démarre si multi-frames

## Tasks / Subtasks

- [x] Task 1: Ajouter `get_frame_delays()` dans processor.py (AC: 1, 3, 4)
  - [x] 1.1 Implémenter `get_frame_delays(path: Path) -> list[int]` — lit les durées GIF en ms
  - [x] 1.2 Pour images non-GIF ou GIF 1 frame → retourner `[100]` (défaut)
  - [x] 1.3 Appliquer une durée minimale de 50ms par frame (éviter les GIF trop rapides)

- [x] Task 2: Modifier `_ConversionWorker` pour transmettre les délais (AC: 1)
  - [x] 2.1 Changer `finished = Signal(list)` → `finished = Signal(list, list)` (frames, delays)
  - [x] 2.2 Appeler `get_frame_delays()` dans `worker.run()` et émettre les deux listes

- [x] Task 3: Ajouter l'animation QTimer dans OledWidget (AC: 1, 2, 3, 4, 5)
  - [x] 3.1 Ajouter `self._timer = QTimer(self)` dans `__init__` avec `self._timer.timeout.connect(self._on_timer_tick)`
  - [x] 3.2 Ajouter `self._anim_idx = 0` et `self._frame_delays: list[int] = []` comme attributs
  - [x] 3.3 Mettre à jour `_on_conversion_done(frames, delays)` : stocker delays, arrêter timer existant, démarrer animation si len(frames) > 1
  - [x] 3.4 Implémenter `_on_timer_tick()` : avancer `_anim_idx`, afficher frame, régler l'intervalle du timer
  - [x] 3.5 Si 1 seule frame → afficher statique, ne pas démarrer le timer

- [x] Task 4: Écrire et valider les tests (AC: 1, 2, 3, 4, 5)
  - [x] 4.1 Créer fixture `test_single_frame.gif` (GIF 1 frame) dans tests/fixtures/
  - [x] 4.2 Ajouter tests `get_frame_delays` dans test_processor.py
  - [x] 4.3 Ajouter tests animation dans test_widget.py (timer actif/inactif)
  - [x] 4.4 Vérifier `python3 -m pytest tests/ modules/ -v` — aucune régression

## Dev Notes

### get_frame_delays — processor.py

```python
def get_frame_delays(path: Path) -> list[int]:
    """Retourne la liste des durées inter-frames en ms pour un GIF.

    Pour les images statiques ou GIF 1 frame : retourne [100].
    Applique un minimum de 50ms pour éviter les animations trop rapides.
    """
    img = Image.open(path)
    delays: list[int] = []
    try:
        while True:
            delay = img.info.get("duration", 100)
            delays.append(max(int(delay), 50))
            img.seek(img.tell() + 1)
    except EOFError:
        pass
    return delays if delays else [100]
```

### Animation QTimer — pattern variable interval

```python
def _on_conversion_done(self, frames: list, delays: list) -> None:
    self._model.oled.image_path = self._pending_path
    self._model.oled.frames = frames
    self._frame_delays = delays
    self._anim_idx = 0
    self._timer.stop()  # arrêter l'ancienne animation
    self._show_frame(0)
    if len(frames) > 1:
        self._timer.setInterval(delays[0])
        self._timer.start()

def _on_timer_tick(self) -> None:
    frames = self._model.oled.frames
    if not frames:
        return
    self._anim_idx = (self._anim_idx + 1) % len(frames)
    self._show_frame(self._anim_idx)
    # Intervalle variable selon le délai de la frame suivante
    next_delay = self._frame_delays[self._anim_idx] if self._frame_delays else 100
    self._timer.setInterval(next_delay)
```

### References

- PRD FR9 : prévisualisation animée GIF frame par frame
- Architecture : QThread obligatoire pour opérations > 50ms (conversion déjà en QThread)
- QTimer : intervalle variable selon durée GIF (frame-by-frame)
- Epic 2 Story 2.2 : `_bmad-output/planning-artifacts/epics.md#Story-2.2`

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Story 2.2 implémentée avec succès — 93/93 tests passés, zéro régression (2026-02-22)
- `Signal(list, list)` pour émettre (frames, delays) depuis le worker — les deux listes ensemble
- QTimer variable interval : `setInterval()` appelé à chaque tick selon le délai de la frame suivante
- `_on_timer_tick` stoppe le timer si frames vides (défense contre état incohérent)
- Mise à jour backward-compatible : tests existants de Story 2.1 mis à jour pour la nouvelle signature `_on_conversion_done(frames, delays)`

### File List

- `modules/oled_editor/processor.py` (modifié — ajout `get_frame_delays`)
- `modules/oled_editor/widget.py` (modifié — Signal(list,list), QTimer animation, _on_timer_tick, _show_frame)
- `modules/oled_editor/tests/fixtures/test_single_frame.gif` (nouveau — fixture GIF 1 frame)
- `modules/oled_editor/tests/test_processor.py` (modifié — 5 tests get_frame_delays ajoutés)
- `modules/oled_editor/tests/test_widget.py` (modifié — TestOledWidgetAnimation avec 7 tests)
