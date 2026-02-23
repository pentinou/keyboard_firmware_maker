# Story 2.1: Import et conversion d'image en bitmap OLED

Status: done

## Story

As a utilisateur (Pentinou ou Alex),
I want to import an image file and see it automatically converted to a 1-bit 64×128px preview,
So that I can verify exactly what will appear on my keyboard's OLED screen before generating firmware.

## Acceptance Criteria

1. **Given** je suis dans l'onglet "OLED"
   **When** je clique "Importer une image" et je sélectionne un fichier PNG, BMP ou GIF
   **Then** l'application accepte le fichier (FR6)
   **And** convertit automatiquement en bitmap 1-bit 64×128px avec dithering Floyd-Steinberg (FR7)

2. **Given** la conversion est terminée
   **When** je regarde la zone de prévisualisation
   **Then** j'y vois le rendu exact en noir et blanc 64×128px, sans niveaux de gris (FR8)
   **And** la prévisualisation est mise à jour en moins de 500ms après import (NFR3)

3. **Given** j'importe une image dont les dimensions ne sont pas 64×128px
   **When** la conversion s'effectue
   **Then** l'image est redimensionnée et recadrée pour tenir dans 64×128px
   **And** aucun message d'erreur n'est affiché si le redimensionnement réussit

4. **Given** j'importe un fichier non supporté ou corrompu
   **When** la lecture échoue
   **Then** un message d'erreur lisible est affiché (ex : "Format de fichier non supporté")
   **And** l'onglet reste dans un état stable et utilisable

5. **Given** la conversion réussit
   **When** l'image est traitée
   **Then** `oled.image_path` est mis à jour avec le chemin absolu
   **And** `oled.frames` contient la liste de frames bytes (1 frame pour image statique)

## Tasks / Subtasks

- [x] Task 1: Installer NumPy et créer modules/oled_editor/processor.py (AC: 1, 2, 3, 5)
  - [x] 1.1 Installer NumPy : `python3 -m pip install --break-system-packages numpy`
  - [x] 1.2 Implémenter `convert_image(path: Path) -> list[bytes]` — Pillow load + resize/crop 64×128 + dithering Floyd-Steinberg + retour liste frames
  - [x] 1.3 Pour GIF multi-frames : extraire chaque frame, convertir chacune en 1-bit
  - [x] 1.4 Pour images statiques (PNG, BMP, GIF 1 frame) : retourner liste à 1 élément
  - [x] 1.5 Aucun import Qt dans processor.py — testable sans QApplication

- [x] Task 2: Créer modules/oled_editor/widget.py — OledWidget (AC: 1, 2, 4)
  - [x] 2.1 Créer `OledWidget(QWidget)` avec bouton "Importer une image…" et zone de prévisualisation (QLabel)
  - [x] 2.2 Bouton déclenche `QFileDialog.getOpenFileName()` avec filtre "Images (*.png *.bmp *.gif)"
  - [x] 2.3 Appeler `convert_image()` dans `QThread` (opération potentiellement > 50ms)
  - [x] 2.4 En succès : afficher la première frame comme QPixmap dans le QLabel de prévisualisation
  - [x] 2.5 Mettre à jour `model.oled.image_path` et `model.oled.frames`
  - [x] 2.6 En erreur (OSError, UnidentifiedImageError) : `QMessageBox.critical()` message lisible

- [x] Task 3: Intégrer OledWidget dans MainWindow (AC: 1, 2)
  - [x] 3.1 Remplacer `self._tab_oled = QWidget()` par `self._tab_oled = OledWidget(self._model)` dans `_setup_ui()`
  - [x] 3.2 Ajouter import `from modules.oled_editor.widget import OledWidget` dans main_window.py

- [x] Task 4: Écrire et valider les tests (AC: 1, 2, 3, 4, 5)
  - [x] 4.1 Créer `modules/oled_editor/tests/__init__.py`
  - [x] 4.2 Créer `modules/oled_editor/tests/fixtures/` avec une image PNG 100×100 et un GIF 3 frames
  - [x] 4.3 Créer `modules/oled_editor/tests/test_processor.py` — tests convert_image
  - [x] 4.4 Créer `modules/oled_editor/tests/test_widget.py` — tests OledWidget (qtbot)
  - [x] 4.5 Vérifier que tous les tests passent avec `python3 -m pytest tests/ modules/ -v` (aucune régression)

## Dev Notes

### processor.py — Implémentation attendue (pur Python, sans Qt)

```python
# modules/oled_editor/processor.py
from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
from PIL import Image, UnidentifiedImageError

logger = logging.getLogger(__name__)

OLED_WIDTH = 64
OLED_HEIGHT = 128


def _convert_frame(frame: Image.Image) -> bytes:
    """Convertit une frame PIL en bitmap 1-bit 64×128px (dithering Floyd-Steinberg).

    Redimensionne et recadre pour tenir dans OLED_WIDTH × OLED_HEIGHT.
    Retourne les pixels comme bytes : 0x00 = noir, 0xFF = blanc (1 byte par pixel).
    """
    # Redimensionner en conservant le ratio, puis centrer/recadrer
    img = frame.convert("L")  # niveaux de gris
    img.thumbnail((OLED_WIDTH, OLED_HEIGHT), Image.LANCZOS)
    # Créer canvas noir 64×128 et coller l'image centrée
    canvas = Image.new("L", (OLED_WIDTH, OLED_HEIGHT), 0)
    x = (OLED_WIDTH - img.width) // 2
    y = (OLED_HEIGHT - img.height) // 2
    canvas.paste(img, (x, y))
    # Conversion 1-bit avec dithering Floyd-Steinberg
    bw = canvas.convert("1", dither=Image.Dither.FLOYDSTEINBERG)
    # Convertir en bytes : 0 = noir, 255 = blanc
    arr = np.array(bw, dtype=np.uint8) * 255
    return arr.tobytes()


def convert_image(path: Path) -> list[bytes]:
    """Convertit une image (PNG, BMP, GIF) en liste de frames 1-bit 64×128px.

    - Image statique (PNG, BMP) ou GIF 1 frame → liste à 1 élément
    - GIF multi-frames → liste de N éléments (1 bytes par frame)

    Lève OSError si le fichier est inaccessible.
    Lève PIL.UnidentifiedImageError si le format n'est pas reconnu.
    """
    img = Image.open(path)
    frames: list[bytes] = []

    # Extraire toutes les frames (GIF) ou juste la frame courante
    try:
        while True:
            frames.append(_convert_frame(img.copy()))
            img.seek(img.tell() + 1)
    except EOFError:
        pass  # fin des frames GIF

    if not frames:
        frames.append(_convert_frame(img))

    logger.info("Image convertie : %s — %d frame(s)", path, len(frames))
    return frames
```

### QThread pattern pour la conversion (Task 2.3)

```python
from PySide6.QtCore import QThread, Signal as QtSignal

class ConversionWorker(QThread):
    finished = QtSignal(list)    # list[bytes]
    error = QtSignal(str)

    def __init__(self, path: Path):
        super().__init__()
        self._path = path

    def run(self) -> None:
        try:
            frames = convert_image(self._path)
            self.finished.emit(frames)
        except Exception as e:
            self.error.emit(str(e))
```

### Prévisualisation QLabel (Task 2.4)

La première frame (bytes, 64×128, 1 byte/pixel) est convertie en QImage puis QPixmap :

```python
from PySide6.QtGui import QImage, QPixmap

def _show_preview(self, frames: list[bytes]) -> None:
    if not frames:
        return
    data = frames[0]
    # QImage.Format_Grayscale8 : 1 byte par pixel (0=noir, 255=blanc)
    img = QImage(data, OLED_WIDTH, OLED_HEIGHT, OLED_WIDTH, QImage.Format.Format_Grayscale8)
    pixmap = QPixmap.fromImage(img)
    # Agrandir pour la prévisualisation (×3 : 192×384)
    self._preview_label.setPixmap(
        pixmap.scaled(OLED_WIDTH * 3, OLED_HEIGHT * 3, Qt.AspectRatioMode.KeepAspectRatio)
    )
```

### Structure des tests processor.py

```python
# modules/oled_editor/tests/test_processor.py

FIXTURES = Path(__file__).parent / "fixtures"

def test_convert_png_returns_one_frame():
    frames = convert_image(FIXTURES / "test_100x100.png")
    assert len(frames) == 1

def test_convert_output_dimensions():
    frames = convert_image(FIXTURES / "test_100x100.png")
    assert len(frames[0]) == 64 * 128  # 1 byte par pixel

def test_convert_output_is_binary():
    frames = convert_image(FIXTURES / "test_100x100.png")
    arr = np.frombuffer(frames[0], dtype=np.uint8)
    unique_values = set(arr.tolist())
    assert unique_values <= {0, 255}  # uniquement noir/blanc

def test_convert_gif_multi_frame_returns_multiple():
    frames = convert_image(FIXTURES / "test_anim.gif")
    assert len(frames) >= 2

def test_convert_missing_file_raises_oserror():
    with pytest.raises(OSError):
        convert_image(Path("/nonexistent/file.png"))

def test_convert_invalid_format_raises():
    bad = FIXTURES / "bad.txt"
    bad.write_bytes(b"not an image")
    with pytest.raises(Exception):  # UnidentifiedImageError ou OSError
        convert_image(bad)

def test_no_qt_import_in_processor():
    source = Path(__file__).parent.parent / "processor.py"
    content = source.read_text(encoding="utf-8")
    assert "PySide6" not in content
    assert "PyQt" not in content
```

### Project Structure Notes

**Fichiers à créer :**
```
modules/oled_editor/
├── processor.py                        # NOUVEAU (pur Python — convert_image)
├── widget.py                           # NOUVEAU (OledWidget — bouton + preview)
└── tests/
    ├── __init__.py                     # NOUVEAU
    ├── fixtures/
    │   ├── test_100x100.png            # NOUVEAU (fixture image statique)
    │   └── test_anim.gif               # NOUVEAU (fixture GIF multi-frames)
    └── test_processor.py               # NOUVEAU
    └── test_widget.py                  # NOUVEAU
```

**Fichiers à modifier :**
```
ui/main_window.py                       # Remplacer QWidget() OLED par OledWidget
```

**Fichiers non touchés :**
```
modules/hardware/*, modules/project_manager/*, models/project_model.py
tests/test_main_window.py (les tests existants ne doivent pas régresser)
```

### References

- Architecture §Requirements Mapping : FR6-FR7 → `modules/oled_editor/processor.py`, FR8 → `modules/oled_editor/widget.py`
- Architecture §Module Structure : séparation widget.py / processor.py obligatoire
- Architecture §Communication Patterns : QThread obligatoire pour opérations > 50ms
- PRD FR6 (import GIF/PNG/BMP), FR7 (conversion 1-bit), FR8 (prévisualisation pixel-perfect)
- NFR3 : prévisualisation < 500ms après import
- Epic 2 Story 2.1 : `_bmad-output/planning-artifacts/epics.md#Story-2.1`

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Story 2.1 implémentée avec succès — 80/80 tests passés, zéro régression (2026-02-22)
- NumPy 2.4.2 installé via `python3 -m pip install --break-system-packages numpy`
- Pattern GIF : itération sur les frames avec `img.seek(img.tell() + 1)` jusqu'à EOFError
- `Image.Resampling.LANCZOS` (Pillow 10+) remplace l'ancien `Image.LANCZOS`
- QThread worker `_ConversionWorker` : signals `finished(list)` et `error(str)` — bouton désactivé pendant conversion

### File List

- `modules/oled_editor/processor.py` (nouveau — convert_image, _convert_frame, pur Python)
- `modules/oled_editor/widget.py` (nouveau — OledWidget, _ConversionWorker)
- `modules/oled_editor/tests/__init__.py` (nouveau)
- `modules/oled_editor/tests/fixtures/test_100x100.png` (nouveau — fixture PNG)
- `modules/oled_editor/tests/fixtures/test_anim.gif` (nouveau — fixture GIF 3 frames)
- `modules/oled_editor/tests/test_processor.py` (nouveau — 9 tests processor)
- `modules/oled_editor/tests/test_widget.py` (nouveau — 8 tests widget)
- `ui/main_window.py` (modifié — OledWidget remplace QWidget() pour l'onglet OLED)
