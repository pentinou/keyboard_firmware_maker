# Story 4.4: Guide de flash, export du firmware et compatibilité Vial

Status: done

## Story

As a utilisateur (Pentinou ou Alex),
I want to export my compiled .uf2 file and follow an illustrated flashing guide,
So that I can flash my keyboard and immediately use it with vial.rocks.

## Acceptance Criteria

1. **Given** la compilation s'est terminée avec succès
   **When** je clique "Exporter le firmware"
   **Then** une fenêtre de dialogue s'ouvre pour choisir l'emplacement de sauvegarde (FR28)
   **And** le fichier .uf2 est copié à l'emplacement choisi

2. **Given** le firmware a été exporté
   **When** je clique "Guide de flash"
   **Then** un dialogue illustré s'ouvre avec 4 étapes (FR23, FR33) :
     1. Localiser le bouton BOOT sur le PCB
     2. Entrer en mode bootloader (maintenir BOOT + brancher USB)
     3. Lecteur "RPI-RP2" détecté dans l'explorateur
     4. Glisser-déposer le .uf2 dans le lecteur

3. **Given** le guide est affiché
   **When** je navigue avec "Suivant" / "Précédent"
   **Then** les étapes s'enchaînent correctement avec images et texte

4. **Given** l'application est offline
   **When** j'accède au guide de flash
   **Then** le guide s'affiche depuis les assets locaux — aucun appel réseau (FR29)

## Tasks / Subtasks

- [x] Task 1: Créer les assets du guide de flash (AC: 2, 4)
  - [x] 1.1 Générer `assets/flash_guide/step1_boot_button.png` (placeholder)
  - [x] 1.2 Générer `assets/flash_guide/step2_usb_connect.png` (placeholder)
  - [x] 1.3 Générer `assets/flash_guide/step3_rpi_rp2.png` (placeholder)
  - [x] 1.4 Générer `assets/flash_guide/step4_drag_drop.png` (placeholder)

- [x] Task 2: Créer ui/widgets/flash_guide_dialog.py (AC: 2, 3, 4)
  - [x] 2.1 `FLASH_GUIDE_STEPS: list[dict]` — 4 étapes avec title, text, image
  - [x] 2.2 `FlashGuideDialog(QDialog)` avec QStackedWidget + navigation
  - [x] 2.3 Boutons "Précédent" / "Suivant" / "Fermer" (Fermer visible seulement à étape 4)
  - [x] 2.4 Chargement images depuis ASSETS_DIR (local, pas de réseau)

- [x] Task 3: Ajouter export + guide dans BuildWidget (AC: 1, 2)
  - [x] 3.1 `self._last_uf2: str | None = None` — chemin du dernier .uf2 compilé
  - [x] 3.2 Bouton "Exporter le firmware" (`btn_export`) — désactivé jusqu'au succès du build
  - [x] 3.3 Bouton "Guide de flash" (`btn_guide`)
  - [x] 3.4 `_on_build_success()` : stocker le chemin, activer le bouton export
  - [x] 3.5 `_on_export_clicked()` : QFileDialog + shutil.copy2
  - [x] 3.6 `_on_guide_clicked()` : ouvrir FlashGuideDialog

- [x] Task 4: Tests (AC: 1, 2, 3, 4)
  - [x] 4.1 Créer `tests/test_flash_guide_dialog.py`
  - [x] 4.2 Tester FlashGuideDialog : 4 étapes, navigation Suivant/Précédent
  - [x] 4.3 Tester que les images sont chargées depuis assets locaux
  - [x] 4.4 Tester `btn_export` désactivé initialement, activé après succès
  - [x] 4.5 Tester `_on_export_clicked()` avec QFileDialog mocké → shutil.copy2 appelé
  - [x] 4.6 Vérifier `python3 -m pytest tests/ modules/ -v` — aucune régression

## Dev Notes

### FLASH_GUIDE_STEPS

```python
FLASH_GUIDE_STEPS = [
    {
        "title": "Étape 1 : Localiser le bouton BOOT",
        "text": (
            "Sur le PCB de votre Sofle, repérez le bouton marqué BOOT\n"
            "(souvent près du microcontrôleur RP2040)."
        ),
        "image": "step1_boot_button.png",
    },
    {
        "title": "Étape 2 : Entrer en mode bootloader",
        "text": (
            "1. Maintenez le bouton BOOT appuyé\n"
            "2. Branchez le câble USB à votre clavier\n"
            "3. Relâchez le bouton BOOT"
        ),
        "image": "step2_usb_connect.png",
    },
    {
        "title": "Étape 3 : Lecteur RPI-RP2 détecté",
        "text": (
            "Un lecteur nommé 'RPI-RP2' apparaît dans votre explorateur de fichiers.\n"
            "Si le lecteur n'apparaît pas, répétez l'étape 2."
        ),
        "image": "step3_rpi_rp2.png",
    },
    {
        "title": "Étape 4 : Installer le firmware",
        "text": (
            "Glissez-déposez le fichier .uf2 dans le lecteur RPI-RP2.\n"
            "Le clavier redémarre automatiquement.\n\n"
            "Votre clavier est prêt ! Configurez les layers sur vial.rocks"
        ),
        "image": "step4_drag_drop.png",
    },
]
```

### FlashGuideDialog navigation

```python
def _go_to_step(self, idx: int) -> None:
    self._stack.setCurrentIndex(idx)
    self._current = idx
    self._btn_prev.setEnabled(idx > 0)
    self._btn_next.setVisible(idx < len(FLASH_GUIDE_STEPS) - 1)
    self._btn_close.setVisible(idx == len(FLASH_GUIDE_STEPS) - 1)
```

### References

- FR23 : guide de flash illustré (procédure mode bootloader)
- FR28 : export .uf2 vers emplacement choisi
- FR29 : guide depuis assets locaux — aucun appel réseau
- FR33 : accès aux guides depuis l'application

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Story 4.4 implémentée avec succès — 280/280 tests passés, zéro régression (2026-02-23)
- 4 assets PNG placeholder générés avec Pillow (480×320, bandeau coloré par étape)
- `FlashGuideDialog` : QStackedWidget + `_go_to_step()` gère titre, progression, visibilité des boutons
- Piège headless : `isVisible()` retourne False si parent non affiché → tests utilisent `isHidden()`
- Piège segfault : mock de la classe entière `FlashGuideDialog` (pas juste `.exec`) dans le test `_on_guide_clicked`
- `btn_export` désactivé à l'init, activé uniquement dans `_on_build_success()` via `_last_uf2`
- Import lazy de `FlashGuideDialog` dans `_on_guide_clicked()` pour éviter dépendances circulaires

### File List

- `assets/flash_guide/step1_boot_button.png` (nouveau — placeholder Pillow)
- `assets/flash_guide/step2_usb_connect.png` (nouveau — placeholder Pillow)
- `assets/flash_guide/step3_rpi_rp2.png` (nouveau — placeholder Pillow)
- `assets/flash_guide/step4_drag_drop.png` (nouveau — placeholder Pillow)
- `ui/widgets/flash_guide_dialog.py` (nouveau — FLASH_GUIDE_STEPS, FlashGuideDialog, _make_step_page)
- `modules/build_manager/widget.py` (modifié — _last_uf2, btn_export, btn_guide, _on_export_clicked, _on_guide_clicked)
- `tests/test_flash_guide_dialog.py` (nouveau — 34 tests)
