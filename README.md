# Keyboard Firmware Maker

A desktop application to create, customize, and compile Vial-QMK firmware for split mechanical keyboards — no coding required.

![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue)
![License GPL-3.0](https://img.shields.io/badge/License-GPL--3.0-green)
![Platform](https://img.shields.io/badge/Platform-Linux%20%7C%20Windows%20%7C%20WSL2-lightgrey)

## Screenshots

| Hardware selection | OLED editor |
|---|---|
| ![Hardware](screenshots/hardware.png) | ![OLED](screenshots/oled.png) |

| RGB configurator | Build & flash |
|---|---|
| ![RGB](screenshots/rgb.png) | ![Build](screenshots/build.png) |

## Features

- **Hardware** — 4 bundled keyboards + 620+ Vial-QMK keyboards auto-indexed, category filters (split, macropad, 40%, 60%, 75%, TKL, fullsize), multiple MCU options per board, layout variants
- **Custom keyboards** — Import any layout from [keyboard-layout-editor.com](http://keyboard-layout-editor.com), assign matrix wiring visually, export as YAML definition
- **OLED editor** — Dual 128x32 canvas, drag-and-drop image positioning, animated GIF import, built-in sprites (Luna, Bongo Cat, Ocean Dream, KatawaJojo, Crab), anti-burn-in timeout, sleep mode
- **RGB lighting** — 60+ native effects with live preview, per-key color painting, custom timeline effects with reactive/static modes, trigger key assignment
- **Build system** — Jinja2-based QMK code generation, ZMK shield generation (nRF52840), one-click compilation, UF2 export, flash size display, illustrated step-by-step flash guide
- **Project files** — Save and load full configurations as `.kfm.json` with atomic writes
- **Internationalization** — French, English, Italian

## Supported Keyboards

### Bundled (YAML definitions)

| Keyboard | Keys | Split | MCU Options | Encoder | RGB | OLED |
|---|---|---|---|---|---|---|
| Sofle v2 | 58 + 2 enc. | Yes | RP2040 | Yes | Yes | Yes |
| Corne (crkbd) | 42 | Yes | Pro Micro, Elite-C, RP2040 | No | No | Yes |
| Lily58 | 58 | Yes | Pro Micro, Elite-C, RP2040 | No | No | Yes |
| PancakeXXL | 43 / 37 | No | RP2040 | No | No | No |

### Vial-QMK index

On first launch the app indexes the Vial-QMK repository and discovers **620+ keyboards** automatically. Keyboards are categorized by size and type, and the full physical layout from their `vial.json` is used.

### Custom keyboards (KLE import)

Any keyboard layout pasted from [keyboard-layout-editor.com](http://keyboard-layout-editor.com) can be turned into a full keyboard definition with visual matrix wiring.

## Requirements

- Python >= 3.11
- Linux, Windows 10/11, or WSL2
- `git` (required for Vial-QMK repository)
- `make` + `arm-none-eabi-gcc` (for firmware compilation — auto-installed on Windows)
- `libxcb-cursor0` on Linux/WSL2 (Qt X11 backend — auto-installed by `start.sh`).
  Without it Qt falls back to Wayland, where WSLg leaves popup menus painted on screen.

## Installation

### Linux / WSL2

```bash
git clone https://github.com/pentinou/keyboard_firmware_maker.git
cd keyboard_firmware_maker
./start.sh
```

`start.sh` checks all prerequisites and installs missing packages automatically.

### Windows

1. Install [Python 3.11+](https://www.python.org/downloads/) — check **"Add Python to PATH"**
2. Install [Git for Windows](https://git-scm.com/download/win)
3. Clone and launch:

```cmd
git clone https://github.com/pentinou/keyboard_firmware_maker.git
cd keyboard_firmware_maker
start.bat
```

On first firmware build, the app downloads the compilation tools automatically (MSYS2 + ARM toolchain).

> For contributors: `pip install -e ".[dev]"`

## Quick Start

```bash
python main.py
```

On first launch, the app prompts you to clone the Vial-QMK repository. Once that completes, select your keyboard, MCU, and start customizing.

See [`docs/USER_GUIDE.md`](docs/USER_GUIDE.md) for the complete user guide with all workflows.

## Adding a Custom Keyboard

Drop a `.yaml` file into the `keyboards/` directory. See [`keyboards/README.md`](keyboards/README.md) for the full annotated template, field reference, and a minimal example.

Quick example:

```yaml
model: my-keyboard
display_name: "My Keyboard"
mcu_options:
  - id: rp2040
    bootloader: "rp2040"
    pins:
      matrix_rows: ["GP4", "GP5", "GP6", "GP7"]
      matrix_cols: ["GP29", "GP28", "GP27", "GP26", "GP22", "GP20"]
      serial_tx: "GP1"
      serial_driver: "vendor"
diode_direction: "COL2ROW"
layout_macro: "LAYOUT_split_3x6_3"
has_encoder: false
capabilities:
  oled: true
  rgb: false
matrix:
  rows: 4
  cols: 6
layout:
  left: [...]
  right: [...]
```

## Project Structure

```
keyboard_firmware_maker/
├── main.py                  # Application entry point
├── models/                  # Data models (ProjectModel, configs)
├── ui/                      # MainWindow, dialogs
├── modules/
│   ├── hardware/            # Keyboard loader, Vial-QMK scanner, hardware widget
│   ├── keyboard_editor/     # KLE import, matrix wiring, YAML export
│   ├── oled_editor/         # OLED canvas, image processing, overlays
│   ├── rgb_editor/          # RGB effects, live preview, per-key editor
│   ├── build_manager/       # Template generator, builder, ZMK support
│   └── project_manager/     # Project save/load (.kfm.json)
├── keyboards/               # YAML keyboard definitions + vial.json
├── templates/               # Jinja2 templates for QMK code generation
├── i18n/                    # Translations (FR, EN, IT)
├── assets/                  # UI assets, icons, sprites
├── docs/                    # User guide and documentation
└── tests/                   # Integration tests
```

## Development

```bash
pip install -e ".[dev]"
pytest
```

Linting:

```bash
ruff check .
black --check .
```

## License

This project is licensed under the **GNU General Public License v3.0**. See [LICENSE](LICENSE) for the full text.
