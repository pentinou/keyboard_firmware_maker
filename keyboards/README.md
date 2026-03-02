# Adding a keyboard

Drop a `.yaml` file in this directory. The filename (without extension) becomes the keyboard's internal identifier and **must match the `model` key** inside the file.

The keyboard appears automatically in the application on next launch — no Python code changes required.

---

## Full annotated template

```yaml
# ── Identity ──────────────────────────────────────────────────────────────────
model: my-keyboard              # must equal the filename (my-keyboard.yaml)
display_name: "My Keyboard"    # shown in the UI selector
description: "..."             # shown as an info tooltip in the UI

# Optional — only if an official vial.json exists for this keyboard
vial_name: "MyKeyboard"        # name written into the generated vial.json
vial_vid: "0xFEED"             # USB Vendor ID (hex)
vial_pid: "0x0001"             # USB Product ID (hex)

# ── MCU options ───────────────────────────────────────────────────────────────
# List one entry per supported microcontroller.
mcu_options:
  - id: pro_micro                        # internal key, unique per list
    display_name: "Pro Micro (ATmega32U4)"
    description: "..."
    bootloader: "caterina"               # caterina | atmel-dfu | rp2040 | halfkay
    pins:
      matrix_rows: ["D4", "C6", "D7", "E6"]
      matrix_cols: ["F4", "F5", "F6", "F7", "B1", "B3"]
      serial_tx: "D2"                    # half-duplex split communication pin
      serial_driver: "bitbang"           # bitbang (AVR) | vendor (RP2040)

  - id: rp2040
    display_name: "RP2040"
    description: "..."
    bootloader: "rp2040"
    pins:
      matrix_rows: ["GP4", "GP5", "GP6", "GP7"]
      matrix_cols: ["GP29", "GP28", "GP27", "GP26", "GP22", "GP20"]
      serial_tx: "GP1"
      serial_driver: "vendor"
      # RGB (only if capabilities.rgb: true):
      ws2812: "GP0"
      ws2812_driver: "vendor"
      # Rotary encoder (only if has_encoder: true):
      encoder_a: ["GP29"]
      encoder_b: ["GP28"]
      encoder_a_right: ["GP28"]         # right side may differ
      encoder_b_right: ["GP29"]
      encoder_default_pos: "0x3"

# ── General config ────────────────────────────────────────────────────────────
diode_direction: "COL2ROW"             # COL2ROW or ROW2COL
layout_macro: "LAYOUT_split_3x6_3"    # QMK layout macro name
has_encoder: false

capabilities:
  oled: true                            # show OLED tab in the UI
  rgb: false                            # show RGB tab in the UI

matrix:
  rows: 4                               # rows per half (e.g. 4 → 8 total for split)
  cols: 6

# ── OLED (only if capabilities.oled: true) ────────────────────────────────────
oled:
  width: 64
  height: 128
  bits: 1
  driver: "ssd1306"
  rotation: 270                         # 0 | 90 | 180 | 270
  display: "128X32"                     # "128X32" or "128X64"

# ── RGB (only if capabilities.rgb: true) ──────────────────────────────────────
rgb:
  max_brightness: 200                   # 0-255

# ── Physical layout (used for Vial key mapping) ───────────────────────────────
# Positions in key units (1 = 1U ≈ 19 mm).
# row/col = matrix address ; x/y = physical position on the board.
# Right side x must be normalized: start at 0, not at the absolute board position.
layout:
  left:
    - {row: 0, col: 0, x: 0.0, y: 0.0}
    - {row: 0, col: 1, x: 1.0, y: 0.0}
    # ... one entry per key
    # Rotary encoders: add encoder: true (excluded from Vial key grid)
    - {row: 4, col: 5, x: 6.0, y: 2.75, encoder: true}
  right:
    - {row: 0, col: 5, x: 1.0, y: 0.0}
    # ...
```

---

## Field reference

| Field | Required | Notes |
|---|---|---|
| `model` | Yes | Must match filename |
| `display_name` | Yes | |
| `mcu_options` | Yes | At least one entry |
| `mcu_options[].id` | Yes | Unique string per entry |
| `mcu_options[].bootloader` | Yes | `caterina`, `atmel-dfu`, `rp2040`, `halfkay` |
| `mcu_options[].pins.matrix_rows` | Yes | One pin per physical row |
| `mcu_options[].pins.matrix_cols` | Yes | One pin per physical column |
| `mcu_options[].pins.serial_tx` | Yes | Half-duplex split pin |
| `mcu_options[].pins.serial_driver` | Yes | `bitbang` (AVR) or `vendor` (RP2040) |
| `diode_direction` | Yes | `COL2ROW` or `ROW2COL` |
| `layout_macro` | Yes | QMK `LAYOUT_*` macro name |
| `has_encoder` | Yes | `true` or `false` |
| `capabilities.oled` | Yes | |
| `capabilities.rgb` | Yes | |
| `matrix.rows` | Yes | Per-half row count |
| `matrix.cols` | Yes | |
| `layout.left` / `layout.right` | Yes | For Vial key mapping |
| `description` | No | UI tooltip |
| `vial_name` / `vial_vid` / `vial_pid` | No | Falls back to `model` if absent |
| `oled.*` | No | Required when `capabilities.oled: true` |
| `rgb.*` | No | Required when `capabilities.rgb: true` |
| Encoder pins (`encoder_a/b*`) | No | Required when `has_encoder: true` |
| `ws2812` / `ws2812_driver` | No | Required when `capabilities.rgb: true` |

---

## Minimal example — Ferris Sweep (34 keys, RP2040, no OLED)

```yaml
model: ferris-sweep
display_name: "Ferris Sweep"
description: "34-key aggressive column-stagger split keyboard."
mcu_options:
  - id: rp2040
    display_name: "RP2040"
    bootloader: "rp2040"
    pins:
      matrix_rows: ["GP29", "GP28", "GP27", "GP26"]
      matrix_cols: ["GP4", "GP5", "GP6", "GP7", "GP8"]
      serial_tx: "GP1"
      serial_driver: "vendor"
diode_direction: "COL2ROW"
layout_macro: "LAYOUT_split_3x5_2"
has_encoder: false
capabilities:
  oled: false
  rgb: false
matrix:
  rows: 4
  cols: 5
layout:
  left:
    - {row: 0, col: 0, x: 0.0,  y: 0.93}
    - {row: 0, col: 1, x: 1.0,  y: 0.52}
    - {row: 0, col: 2, x: 2.0,  y: 0.19}
    - {row: 0, col: 3, x: 3.0,  y: 0.0}
    - {row: 0, col: 4, x: 4.0,  y: 0.28}
    - {row: 1, col: 0, x: 0.0,  y: 1.93}
    - {row: 1, col: 1, x: 1.0,  y: 1.52}
    - {row: 1, col: 2, x: 2.0,  y: 1.19}
    - {row: 1, col: 3, x: 3.0,  y: 1.0}
    - {row: 1, col: 4, x: 4.0,  y: 1.28}
    - {row: 2, col: 0, x: 0.0,  y: 2.93}
    - {row: 2, col: 1, x: 1.0,  y: 2.52}
    - {row: 2, col: 2, x: 2.0,  y: 2.19}
    - {row: 2, col: 3, x: 3.0,  y: 2.0}
    - {row: 2, col: 4, x: 4.0,  y: 2.28}
    - {row: 3, col: 3, x: 3.5,  y: 3.4}
    - {row: 3, col: 4, x: 4.5,  y: 3.7}
  right:
    - {row: 0, col: 4, x: 1.0,  y: 0.28}
    - {row: 0, col: 3, x: 2.0,  y: 0.0}
    - {row: 0, col: 2, x: 3.0,  y: 0.19}
    - {row: 0, col: 1, x: 4.0,  y: 0.52}
    - {row: 0, col: 0, x: 5.0,  y: 0.93}
    - {row: 1, col: 4, x: 1.0,  y: 1.28}
    - {row: 1, col: 3, x: 2.0,  y: 1.0}
    - {row: 1, col: 2, x: 3.0,  y: 1.19}
    - {row: 1, col: 1, x: 4.0,  y: 1.52}
    - {row: 1, col: 0, x: 5.0,  y: 1.93}
    - {row: 2, col: 4, x: 1.0,  y: 2.28}
    - {row: 2, col: 3, x: 2.0,  y: 2.0}
    - {row: 2, col: 2, x: 3.0,  y: 2.19}
    - {row: 2, col: 1, x: 4.0,  y: 2.52}
    - {row: 2, col: 0, x: 5.0,  y: 2.93}
    - {row: 3, col: 3, x: 1.5,  y: 3.7}
    - {row: 3, col: 4, x: 2.5,  y: 3.4}
```

---

## Tips

- **Pin names**: Use QMK notation — `GP0`–`GP29` for RP2040, `B0`–`F7` for AVR (Pro Micro / Elite-C).
- **layout_macro**: Must match exactly the macro defined in QMK/Vial for your keyboard (check `info.json` or `<keyboard>.h` in the QMK repo).
- **Right side layout**: x-coordinates should start near 0 (subtract the minimum x of the right side from all right x values). The application adds the offset automatically when building the Vial map.
- **Encoders**: Add `encoder: true` to the key entry so the position is excluded from the Vial key grid (encoders are not regular keys).
- **Multiple MCUs**: List them all under `mcu_options`. The user selects one at build time; unused pin sets are ignored.
