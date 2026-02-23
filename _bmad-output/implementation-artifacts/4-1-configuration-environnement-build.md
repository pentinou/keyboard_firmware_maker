# Story 4.1: Configuration de l'environnement de build

Status: done

## Story

As a utilisateur (Pentinou ou Alex),
I want the application to automatically set up the build toolchain and Vial-QMK source on first launch,
So that I can compile firmware without installing anything manually.

## Acceptance Criteria

1. **Given** je lance l'application pour la première fois
   **When** le cache Vial-QMK n'existe pas dans `~/.keyboard_firmware_maker/vial-qmk/`
   **Then** un dialogue de progression s'affiche et télécharge Vial-QMK automatiquement

2. **Given** le téléchargement de Vial-QMK est en cours
   **When** je regarde le dialogue
   **Then** je vois une barre de progression et un message d'état clair (ex : "Téléchargement de Vial-QMK…")

3. **Given** le cache Vial-QMK existe déjà
   **When** je lance l'application
   **Then** aucun téléchargement n'est déclenché — l'app démarre directement

4. **Given** je clique "Générer firmware"
   **When** la détection de la toolchain s'effectue
   **Then** l'application utilise `arm-none-eabi-gcc` vendoré dans `toolchain/{platform}/bin/`

5. **Given** les binaires vendorés sont absents
   **When** la détection de fallback s'effectue
   **Then** l'application détecte `arm-none-eabi-gcc` sur le PATH système
   **And** si absent, un message clair guide l'utilisateur vers l'installation manuelle (FR32)
   **And** la version de la toolchain est lue depuis `toolchain/version.txt` (NFR15)

## Tasks / Subtasks

- [x] Task 1: Créer toolchain/version.txt (AC: 5)
  - [x] 1.1 Créer `toolchain/version.txt` avec "13.3.rel1"

- [x] Task 2: Créer modules/build_manager/toolchain.py (AC: 4, 5)
  - [x] 2.1 Définir `ToolchainInfo` dataclass : `gcc_path`, `version`, `source`
  - [x] 2.2 `detect_toolchain() -> ToolchainInfo` : vendored first, then PATH
  - [x] 2.3 `_read_version() -> str` : lit `toolchain/version.txt`
  - [x] 2.4 `INSTALL_GUIDE_MSG: str` : message humanisé si toolchain absente (FR32)

- [x] Task 3: Créer modules/build_manager/vial_qmk_manager.py (AC: 1, 2, 3)
  - [x] 3.1 Constantes : `VIAL_QMK_SHA`, `VIAL_QMK_URL`, `CACHE_DIR`, `VIAL_QMK_DIR`
  - [x] 3.2 `VialQmkManager.is_ready() -> bool`
  - [x] 3.3 `VialQmkManager.download(progress_callback)` : urlretrieve + extract zip
  - [x] 3.4 `DownloadWorker(QThread)` : encapsule le download avec signal progress
  - [x] 3.5 `VialQmkSetupDialog(QDialog)` : label + QProgressBar + worker

- [x] Task 4: Intégrer dans MainWindow (AC: 1, 3)
  - [x] 4.1 Appeler `_check_vial_qmk()` dans `__init__`
  - [x] 4.2 Si non prêt → ouvrir `VialQmkSetupDialog`

- [x] Task 5: Écrire et valider les tests (AC: 1, 3, 4, 5)
  - [x] 5.1 Créer `modules/build_manager/tests/__init__.py`
  - [x] 5.2 Créer `modules/build_manager/tests/test_toolchain.py`
  - [x] 5.3 Tester `detect_toolchain()` source vendored
  - [x] 5.4 Tester `detect_toolchain()` fallback system PATH
  - [x] 5.5 Tester `detect_toolchain()` toolchain absente → source=missing
  - [x] 5.6 Tester `_read_version()` présent / absent
  - [x] 5.7 Tester `VialQmkManager.is_ready()` (prêt / non prêt)
  - [x] 5.8 Tester `VialQmkManager.download()` avec mocks
  - [x] 5.9 Tester `VialQmkSetupDialog` : widgets présents, signal progress → barre
  - [x] 5.10 Vérifier `python3 -m pytest tests/ modules/ -v` — aucune régression

## Dev Notes

### toolchain.py — structure

```python
import sys, shutil
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(getattr(sys, '_MEIPASS', Path(__file__).parent.parent.parent))
TOOLCHAIN_DIR = BASE_DIR / 'toolchain'

INSTALL_GUIDE_MSG = (
    "La toolchain ARM est introuvable.\n"
    "Installez arm-none-eabi-gcc :\n"
    "  • Ubuntu/Debian : sudo apt install gcc-arm-none-eabi\n"
    "  • Windows : https://developer.arm.com/downloads/-/arm-gnu-toolchain-downloads"
)

@dataclass
class ToolchainInfo:
    gcc_path: Path | None
    version: str
    source: str  # "vendored" | "system" | "missing"

def detect_toolchain() -> ToolchainInfo:
    platform_name = "windows" if sys.platform == "win32" else "linux"
    binary = "arm-none-eabi-gcc.exe" if sys.platform == "win32" else "arm-none-eabi-gcc"
    vendored = TOOLCHAIN_DIR / platform_name / "bin" / binary
    version = _read_version()
    if vendored.is_file():
        return ToolchainInfo(gcc_path=vendored, version=version, source="vendored")
    system = shutil.which("arm-none-eabi-gcc")
    if system:
        return ToolchainInfo(gcc_path=Path(system), version=version, source="system")
    return ToolchainInfo(gcc_path=None, version=version, source="missing")

def _read_version() -> str:
    f = TOOLCHAIN_DIR / "version.txt"
    return f.read_text(encoding="utf-8").strip() if f.is_file() else "unknown"
```

### vial_qmk_manager.py — structure

```python
VIAL_QMK_SHA = "b0ec5a8e9f1c2d3a4b5c6d7e8f9a0b1c2d3e4f5a"
VIAL_QMK_URL = f"https://github.com/vial-kb/vial-qmk/archive/{VIAL_QMK_SHA}.zip"
CACHE_DIR = Path.home() / ".keyboard_firmware_maker"
VIAL_QMK_DIR = CACHE_DIR / "vial-qmk"

class VialQmkManager:
    def is_ready(self) -> bool:
        return VIAL_QMK_DIR.is_dir() and (VIAL_QMK_DIR / "Makefile").is_file()

    def download(self, progress_callback=None) -> None:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        zip_path = CACHE_DIR / "vial-qmk.zip"
        def reporthook(b, bs, total):
            if total > 0 and progress_callback:
                progress_callback(min(100, int(b * bs / total * 100)))
        urllib.request.urlretrieve(VIAL_QMK_URL, zip_path, reporthook)
        _extract_zip(zip_path, CACHE_DIR)
        zip_path.unlink(missing_ok=True)
```

### VialQmkSetupDialog

```python
class DownloadWorker(QThread):
    progress = Signal(int)
    finished = Signal()
    error = Signal(str)

    def run(self) -> None:
        try:
            VialQmkManager().download(progress_callback=self.progress.emit)
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))

class VialQmkSetupDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Initialisation de l'environnement")
        self.setModal(True)
        layout = QVBoxLayout(self)
        self._label = QLabel("Téléchargement de Vial-QMK…")
        self._label.setObjectName("setup_label")
        self._progress = QProgressBar()
        self._progress.setObjectName("setup_progress")
        self._progress.setRange(0, 100)
        layout.addWidget(self._label)
        layout.addWidget(self._progress)
        self._worker = DownloadWorker()
        self._worker.progress.connect(self._progress.setValue)
        self._worker.finished.connect(self.accept)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_error(self, msg: str) -> None:
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.critical(self, "Erreur de téléchargement", msg)
        self.reject()
```

### References

- Architecture Gap 1 (Résolu) : vial_qmk_manager.py — download unique, cache local
- Architecture toolchain : vendored + fallback système, version.txt
- NFR15 : toolchain versionnée explicitement
- FR32 : toolchain embarquée ou instructions d'installation claires

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Story 4.1 implémentée avec succès — 191/191 tests passés, zéro régression (2026-02-23)
- `toolchain.py` pur Python : detect_toolchain() → vendored > PATH > missing, is_available property
- `vial_qmk_manager.py` : VialQmkManager (pur Python) + DownloadWorker (QThread) + VialQmkSetupDialog (QDialog)
- `_extract_zip()` : renomme automatiquement `vial-qmk-{sha}/` → `vial-qmk/`
- MainWindow : `_check_vial_qmk()` appelé dans `__init__` — dialog lancé seulement si pas prêt
- Piège tests : mock `DownloadWorker.start` pour ne pas lancer le thread réseau dans les tests dialog

### File List

- `toolchain/version.txt` (nouveau — "13.3.rel1")
- `modules/build_manager/toolchain.py` (nouveau — ToolchainInfo, detect_toolchain, INSTALL_GUIDE_MSG)
- `modules/build_manager/vial_qmk_manager.py` (nouveau — VialQmkManager, DownloadWorker, VialQmkSetupDialog)
- `modules/build_manager/tests/__init__.py` (nouveau)
- `modules/build_manager/tests/test_toolchain.py` (nouveau — 18 tests)
- `ui/main_window.py` (modifié — _check_vial_qmk, import VialQmkManager)
