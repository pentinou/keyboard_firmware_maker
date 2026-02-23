# Story 4.2: Génération du code QMK et compilation du firmware

Status: done

## Story

As a utilisateur (Pentinou ou Alex),
I want to click "Générer firmware" and watch my configuration compile into a .uf2 file,
So that I get a ready-to-flash firmware without writing any QMK code.

## Acceptance Criteria

1. **Given** j'ai configuré au minimum la sélection matériel
   **When** je clique "Générer firmware"
   **Then** les templates Jinja2 sont rendus depuis ProjectModel → code source QMK dans un répertoire temporaire (FR16)

2. **Given** la génération du code source est terminée
   **When** la compilation démarre
   **Then** BuildWorker(QThread) exécute make — le thread UI reste réactif (FR20)
   **And** une barre de progression s'incrémente de 0 à 100% (FR20)
   **And** les lignes de log apparaissent en temps réel dans une zone défilante (FR20)

3. **Given** la compilation se termine avec succès
   **When** le .uf2 est produit
   **Then** sa taille est affichée (ex : "847 KB / 2048 KB") (FR17)
   **And** le fichier est validé (format UF2 Microsoft) (NFR6)

4. **Given** la taille du firmware dépasse la capacité flash du MCU
   **When** la vérification de taille s'effectue
   **Then** un avertissement explicite est affiché (FR18)

## Tasks / Subtasks

- [x] Task 1: Créer les templates Jinja2 (AC: 1)
  - [x] 1.1 `templates/keymap.c.j2` : keymap QMK + OLED frames + RGB
  - [x] 1.2 `templates/config.h.j2` : config MCU, RGB brightness
  - [x] 1.3 `templates/rules.mk.j2` : MCU, OLED_ENABLE, RGB_MATRIX_ENABLE, VIAL_ENABLE
  - [x] 1.4 `templates/vial.json.j2` : layout Vial (matrix rows/cols)

- [x] Task 2: Créer modules/build_manager/template_generator.py (AC: 1)
  - [x] 2.1 `TemplateGenerator.generate(model, output_dir)` → dict[str, Path]
  - [x] 2.2 `_build_context(model)` : construit le dict Jinja2 depuis ProjectModel
  - [x] 2.3 `_encode_oled_frames(frames)` : bytes → tableaux C uint8_t
  - [x] 2.4 Aucun import Qt — pur Python

- [x] Task 3: Créer modules/build_manager/uf2_validator.py (AC: 3)
  - [x] 3.1 `Uf2ValidationResult` dataclass : valid, size_bytes, message
  - [x] 3.2 `validate_uf2(path: Path) -> Uf2ValidationResult`
  - [x] 3.3 Vérifier magic bytes (0x0A324655 + 0x9E5D5157), taille multiple de 512

- [x] Task 4: Créer modules/build_manager/builder.py (AC: 2, 3, 4)
  - [x] 4.1 `MCU_FLASH: dict[str, int]` : capacités flash par MCU
  - [x] 4.2 `BuildWorker(QThread)` : progress + log_line + success + error signals
  - [x] 4.3 `run()` : generate → make subprocess → parse progress → validate UF2
  - [x] 4.4 `_parse_progress(line)` : extrait % depuis output make "[  1%]"

- [x] Task 5: Créer modules/build_manager/widget.py (AC: 1, 2, 3, 4)
  - [x] 5.1 `BuildWidget` : label toolchain, bouton build, progress bar, log, label size
  - [x] 5.2 `_on_build_clicked()` : vérifie toolchain + vial-qmk, lance BuildWorker
  - [x] 5.3 `_on_build_success(uf2_path)` : affiche taille, avertit si dépassement flash
  - [x] 5.4 `_on_build_error(msg)` : QMessageBox.critical

- [x] Task 6: Intégrer BuildWidget dans MainWindow (AC: 1)
  - [x] 6.1 Remplacer `QWidget()` onglet Build par `BuildWidget(self._model)`

- [x] Task 7: Tests (AC: 1, 2, 3, 4)
  - [x] 7.1 Créer `modules/build_manager/tests/test_template_generator.py`
  - [x] 7.2 Tester generate() : fichiers créés, contenu MCU dans rules.mk
  - [x] 7.3 Tester _encode_oled_frames() : bytes → C array string
  - [x] 7.4 Créer `modules/build_manager/tests/test_builder.py`
  - [x] 7.5 Tester validate_uf2() : valid / magic invalide / taille invalide
  - [x] 7.6 Tester BuildWorker signaux avec subprocess mocké
  - [x] 7.7 Tester BuildWidget : widgets présents, click sans toolchain → warning
  - [x] 7.8 Vérifier `python3 -m pytest tests/ modules/ -v` — aucune régression

## Dev Notes

### TEMPLATE_FILES constant

```python
TEMPLATE_FILES = [
    ("keymap.c.j2",   "keymaps/default/keymap.c"),
    ("config.h.j2",   "config.h"),
    ("rules.mk.j2",   "rules.mk"),
    ("vial.json.j2",  "keymaps/default/vial.json"),
]
```

### _build_context — champs clés

```python
{
    "keyboard_model": model.keyboard.model,
    "mcu": model.keyboard.mcu or "rp2040",
    "oled_enabled": bool(model.oled.image_path or model.oled.overlays),
    "rgb_enabled": bool(model.rgb.effects or model.rgb.per_key),
    "oled_frames": _encode_oled_frames(model.oled.frames),
    "oled_overlays": model.oled.overlays,
    "rgb_effects": [e.to_dict() for e in model.rgb.effects],
    "per_key_colors": model.rgb.per_key,
    "matrix_rows": 4,   # 4 lignes par half (3 regular + 1 thumb) — matrix_rows * 2 dans config.h/vial.json
    "matrix_cols": 6,   # 6 colonnes par half — NON 12 (les templates multiplient matrix_rows par 2 pour le total)
}
```

### MCU_FLASH (capacités flash)

```python
MCU_FLASH: dict[str, int] = {
    "rp2040":    2 * 1024 * 1024,   # 2 MB
    "pro_micro": 28 * 1024,          # 28 KB (32KB - 4KB bootloader)
    "elite_c":   28 * 1024,
}
```

### BuildWorker.run() structure

```python
def run(self) -> None:
    try:
        with tempfile.TemporaryDirectory() as tmp:
            src_dir = Path(tmp) / "keyboards" / "keyboard_firmware_maker"
            src_dir.mkdir(parents=True)
            gen = TemplateGenerator()
            gen.generate(self._model, src_dir)
            self.progress.emit(10)
            self.log_line.emit("Code source QMK généré.")
            self._run_make(src_dir)
    except Exception as exc:
        self.error.emit(str(exc))
```

### UF2 magic bytes

```python
UF2_MAGIC_START0 = 0x0A324655  # "UF2\n"
UF2_MAGIC_START1 = 0x9E5D5157
UF2_BLOCK_SIZE   = 512
```

### References

- Architecture §build_manager/ : builder.py, template_generator.py, uf2_validator.py
- FR16-FR20 : génération + compilation + progression
- NFR1 : < 2 min, NFR6 : UF2 valide, NFR8 : app stable après erreur

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Story 4.2 implémentée avec succès — 227/227 tests passés, zéro régression (2026-02-23)
- `_run_make()` retourne `None` après avoir émis son propre signal error — `_build()` fait `if uf2_path is None: return` pour éviter double erreur
- Templates Jinja2 : keymap.c.j2 (OLED frames + RGB conditionnel), config.h.j2, rules.mk.j2, vial.json.j2
- `_encode_oled_frames()` : bytes → "0xFF, 0x00, ..." par lignes de 16 octets pour inclusion C
- `validate_uf2()` : magic bytes struct.unpack_from + multiple de 512
- `_parse_progress()` : regex `\[\s*(\d+)%\]` sur les lignes make
- `BuildWidget._on_build_clicked()` : vérifie toolchain + vial-qmk avant de lancer le worker

### File List

- `templates/keymap.c.j2` (nouveau)
- `templates/config.h.j2` (nouveau)
- `templates/rules.mk.j2` (nouveau)
- `templates/vial.json.j2` (nouveau)
- `modules/build_manager/template_generator.py` (nouveau — TemplateGenerator, _encode_oled_frames)
- `modules/build_manager/uf2_validator.py` (nouveau — validate_uf2, Uf2ValidationResult)
- `modules/build_manager/builder.py` (nouveau — BuildWorker, MCU_FLASH, _parse_progress)
- `modules/build_manager/widget.py` (nouveau — BuildWidget)
- `modules/build_manager/tests/test_template_generator.py` (nouveau — 16 tests)
- `modules/build_manager/tests/test_builder.py` (nouveau — 20 tests)
- `ui/main_window.py` (modifié — BuildWidget remplace QWidget pour l'onglet Build)
