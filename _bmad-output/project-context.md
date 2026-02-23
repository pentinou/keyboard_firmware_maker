---
project_name: 'keyboard_firmware_maker'
user_name: 'Pentinou'
date: '2026-02-22'
sections_completed:
  ['technology_stack', 'language_rules', 'framework_rules', 'testing_rules', 'quality_rules', 'workflow_rules', 'anti_patterns']
status: 'complete'
rule_count: 32
optimized_for_llm: true
---

# Project Context for AI Agents

_Ce fichier contient les règles critiques et patterns que les agents IA doivent suivre lors de l'implémentation de code dans ce projet. Focus sur les détails non-évidents que les agents pourraient manquer._

---

## Technology Stack & Versions

- **Python** 3.11+ (no walrus operator in 3.9 compat paths — not needed here)
- **PySide6** 6.10.2 — UI framework (NOT PyQt5, NOT PyQt6, NOT PySide2)
- **Pillow** ≥ 10.0 — image processing (PIL import alias: `from PIL import Image`)
- **NumPy** ≥ 1.26 — image array operations
- **Jinja2** ≥ 3.1 — QMK C/H template generation
- **PyInstaller** ≥ 6.0 — packaging (.exe Windows, AppImage Linux)
- **pytest** ≥ 7.0 + **pytest-qt** ≥ 4.0 — tests
- **arm-none-eabi-gcc** — ARM cross-compiler, vendored in `toolchain/windows/` and `toolchain/linux/`
- **Vial-QMK** source — downloaded at first launch, cached in `~/.keyboard_firmware_maker/vial-qmk/`

---

## Critical Implementation Rules

### Language-Specific Rules

- **snake_case** for all Qt signals: `build_started`, `progress_updated`, `error_occurred` — NEVER camelCase for signals
- **PascalCase** for all classes: `OledEditor`, `BuildWorker`, `ProjectModel`
- **UPPER_SNAKE_CASE** for module-level constants: `MAX_LAYER_COUNT = 32`
- Type hints required on all public methods and `__init__` signatures
- No `print()` anywhere — stdlib `logging` only: `logger = logging.getLogger(__name__)`

### Framework-Specific Rules (PySide6 / Qt)

- **QThread for all operations > 50ms** — build, compile, file I/O, git clone, image processing
- Worker pattern: subclass `QThread`, emit signals (`progress`, `log_line`, `success`, `error`), never call UI methods from worker thread
- **Signals carry data, not exceptions** — catch all exceptions in workers, emit `error = Signal(str)` with message
- Connect signals with `signal.connect(slot)` — never use `lambda` with mutable loop variables (use `functools.partial` instead)
- `QApplication` must be created before any `QWidget` — enforce in `main.py` only
- Use `Qt.ConnectionType.QueuedConnection` when connecting signals across threads

### Architecture Patterns

- **ProjectModel** is a dataclass injected via constructor — never a singleton, never imported globally
  ```python
  class OledEditor(QWidget):
      def __init__(self, model: ProjectModel, parent=None): ...
  ```
- **widget.py / processor.py separation** within each module:
  - `widget.py` = Qt display + user interactions only, no business logic
  - `processor.py` = pure computation (no Qt widgets), testable without Qt
- **Inter-module communication via Qt signals only** — no direct method calls between sibling modules
- `MainWindow` owns the `ProjectModel` instance and passes it to all child widgets at construction

### PyInstaller Path Resolution (CRITICAL)

- Always use this pattern for bundled resource access:
  ```python
  BASE_DIR = Path(getattr(sys, '_MEIPASS', Path(__file__).parent.parent.parent))
  ```
- The `.spec` file must include `datas` entries for: `keyboards/`, `templates/`, `toolchain/`, `assets/`
- Never use `__file__` alone for resource paths — it breaks in frozen bundles

### File I/O Rules

- **Atomic writes** for all project `.json` saves:
  ```python
  tmp = path.with_suffix('.tmp')
  tmp.write_text(json.dumps(data, indent=2), encoding='utf-8')
  tmp.replace(path)
  ```
- Project files use **snake_case JSON keys**: `{"layer_count": 4, "oled_frames": [...], "rgb_effect": "breathing"}`
- Colors stored as **hex strings**: `"#FF0000"` — never RGB tuples in JSON
- Paths in JSON stored as **absolute strings** — resolve to `Path` on load

### OLED Image Pipeline (FR6–10)

- Output format: **1-bit monochrome** (no greyscale, no alpha)
- Dithering: **Floyd-Steinberg** algorithm via `Image.convert("1", dither=Image.Dither.FLOYDSTEINBERG)`
- GIF animation: extract each frame, convert individually, store as `List[bytes]` in `ProjectModel`
- Display is **64×128 pixels**, column-major (vertical bytes) for QMK
- C array format in templates: `const uint8_t PROGMEM oled_frame_0[] = {0x00, 0xFF, ...};`
- `oled_editor/processor.py` produces `List[bytes]` → stored in model → `build_manager/template_generator.py` encodes to C

### Toolchain & Build

- Toolchain detection order: vendored `toolchain/{platform}/bin/arm-none-eabi-gcc` → system PATH fallback
- Platform detection: `sys.platform == 'win32'` (Windows), `sys.platform.startswith('linux')` (Linux)
- Vial-QMK manager (`modules/build_manager/vial_qmk_manager.py`) handles: check cache → git clone if missing → shallow clone (`--depth 1`)
- Cache location: `Path.home() / '.keyboard_firmware_maker' / 'vial-qmk'`
- Build runs in `QThread`, emitting `log_line` per stdout line and `progress` (0–100) at milestones

### Testing Rules

- Tests co-located per module: `modules/<name>/tests/test_<module>.py`
- Integration tests in `tests/integration/`
- `processor.py` classes must be testable **without instantiating Qt** (pure Python)
- `widget.py` tests use `pytest-qt` fixtures (`qtbot`)
- Mock `QThread` in unit tests — never spawn real threads in test suite
- Test GIF→OLED pipeline with a known 64×128 reference image and assert exact byte output

### Code Quality & Style Rules

- Max line length: **120 characters** (configured in `pyproject.toml`)
- `ruff` for linting, `black` for formatting (both configured in `pyproject.toml`)
- No bare `except:` — always catch specific exceptions
- No mutable default arguments in function signatures
- Keyboard YAML definitions in `keyboards/` are read-only at runtime — never write to them

### Development Workflow Rules

- `pyproject.toml` is the single source of truth for dependencies and tool configuration
- GitHub Actions matrix: `windows-latest` + `ubuntu-latest` runners for release builds
- Release artifact naming: `keyboard_firmware_maker-{version}-windows.exe`, `keyboard_firmware_maker-{version}-linux.AppImage`
- All new keyboards added as YAML in `keyboards/` — never hardcoded in Python
- Jinja2 templates in `templates/` with `.c.j2` / `.h.j2` extensions

### Critical Don't-Miss Rules (Anti-Patterns)

- **NEVER block the Qt main thread** — any subprocess, file read, or network call goes to `QThread`
- **NEVER use `QApplication.processEvents()`** as a workaround for blocking code — fix the threading
- **NEVER raise exceptions to the UI layer** — workers catch and emit `error` signal
- **NEVER import `ProjectModel` as a global** — always pass via constructor injection
- **NEVER use `camelCase` for signal names** — Qt convention is overridden by project convention (snake_case)
- **NEVER write to `keyboards/` YAML files at runtime** — they are static definitions
- **NEVER use `os.path`** — use `pathlib.Path` exclusively
- **NEVER call `Path.resolve()`** on bundled resources — it may fail; use `BASE_DIR / relative_path`

---

## Usage Guidelines

**For AI Agents:**

- Read this file before implementing any code
- Follow ALL rules exactly as documented
- When in doubt, prefer the more restrictive option
- The PyInstaller path resolution pattern is non-negotiable — missing it breaks the packaged app
- The QThread >50ms rule is non-negotiable — blocking main thread causes UI freeze

**For Humans:**

- Keep this file lean and focused on agent needs
- Update when technology stack or patterns change
- Review after each epic completion for new patterns
- Remove rules that become obvious over time

Last Updated: 2026-02-22
