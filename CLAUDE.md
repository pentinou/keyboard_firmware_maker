# Keyboard Firmware Maker — Developer Context

Desktop Qt application (PySide6) for creating, customizing, and compiling Vial-QMK firmware for mechanical keyboards — no coding required.

## Quick Reference

- **Entry point**: `main.py`
- **Python**: >= 3.11
- **GUI**: PySide6 (Qt 6)
- **Tests**: `pytest` with `pytest-qt` — run with `python3 -m pytest`
- **Language**: French-first UI, i18n via `i18n/translations.py` (FR, EN, IT)
- **Project files**: `.kfm.json` (JSON, atomic writes)

## Architecture

```
main.py → MainWindow (4 tabs)
├── HardwareWidget     → keyboard_loader, vialqmk_scanner
├── OledEditorWidget   → processor (image encoding)
├── RgbWidget          → effects, effect_preview (EffectPreview)
└── BuildWidget        → template_generator, builder, zmk_template_generator
```

### Key modules

| Module | Responsibility |
|--------|----------------|
| `modules/hardware/keyboard_loader.py` | Loads `keyboards/*.yaml` → `KeyboardDefinition` dataclass |
| `modules/hardware/vialqmk_scanner.py` | Indexes 620+ keyboards from vial-qmk repo, cached by git SHA |
| `modules/hardware/widget.py` | QStackedWidget: choice(0), compatible(1), custom/KLE(2) |
| `modules/keyboard_editor/dialog.py` | KLE import → matrix wiring → YAML export to `~/.keyboard_firmware_maker/custom_keyboards/` |
| `modules/oled_editor/widget.py` | Dual 128x32 canvas, GIF import, overlays (Luna, Bongo, etc.) |
| `modules/rgb_editor/widget.py` | `KeyColorItem` (QGraphicsRectItem), per-key colors, effect list with category separators |
| `modules/rgb_editor/effects.py` | `EFFECT_TYPES` tuple (49 EffectDef), `EFFECT_QMK_MODE` mapping |
| `modules/rgb_editor/effect_preview.py` | `EffectPreview` class — animates via QTimer on `KeyColorItem.set_color()` |
| `modules/build_manager/template_generator.py` | Jinja2 templates → QMK C source files |
| `modules/build_manager/zmk_template_generator.py` | ZMK shield/devicetree generation (nRF52840) |
| `modules/project_manager/file_io.py` | Atomic save/load of `.kfm.json` |
| `models/project_model.py` | `ProjectModel` dataclass tree (keyboard, oled, rgb, build configs) |

### Data flow

1. `keyboards/*.yaml` → `KeyboardDefinition` (dataclass with `McuOption`, `McuPins`, `KeyLayout`)
2. User config → `ProjectModel` (in-memory, serialized to `.kfm.json`)
3. `ProjectModel` + `KeyboardDefinition` → `TemplateGenerator` → Jinja2 context → C files
4. C files + vial-qmk repo → `make` → `.uf2` firmware

## Conventions

- **All pin mappings come from YAML** — templates use `{{ pins.xxx }}`, never hardcoded `{% if mcu == "rp2040" %}`
- **`KeyColorItem`** is a `QGraphicsRectItem` (not QWidget) — use `set_color(hex)` / `brush().color()`, not `setStyleSheet()`
- **Effect list** has category separators — use `widget._row_to_effect` dict to map QListWidget rows to `EFFECT_TYPES` indices
- **`keymap.c.j2`** uses `KC_TRNS` for ALL keyboards (no hardcoded QWERTY)
- **Static vial.json files** are copied with `shutil.copy` (not `copy2`)
- **`oled_sep` byte** is `0x04`
- **`_load_keyboard_def()`** returns full `KeyboardDefinition` (replaced old 7-tuple)

## Testing

```bash
python3 -m pytest              # all tests
python3 -m pytest --tb=short   # concise output
python3 -m pytest modules/rgb_editor/tests/  # single module
```

- Tests use `pytest-qt` with `qtbot` fixture for Qt widgets
- `EffectPreview` tests use `FakeKeyButton` stubs (not real Qt widgets)
- RGB widget tests use `_list_row_for(widget, effect_id)` to find QListWidget rows (due to category separators)
- Some QTimer-based tests require `qtbot` even without Qt widgets (to ensure QApplication exists)

## Supported keyboards

| Bundled YAML | Split | Encoders | RGB | OLED | MCUs |
|---|---|---|---|---|---|
| sofle-v2 | Yes | Yes | Yes | Yes | RP2040 |
| corne | Yes | No | No | Yes | Pro Micro, Elite-C, RP2040 |
| lily58 | Yes | No | No | Yes | Pro Micro, Elite-C, RP2040 |
| pancakexxl | No | No | No | No | RP2040 (2 layout variants) |

Plus 620+ auto-indexed from vial-qmk with native physical layouts.

## Adding a keyboard

Drop a `.yaml` in `keyboards/`. See `keyboards/README.md` for full schema and examples.
