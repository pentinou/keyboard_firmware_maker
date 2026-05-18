"""Génère un firmware ZMK COMPLET pour le Sofle v2.1 RGB sur SuperMini nRF52840 :
matrice + encodeur + OLED (deux côtés) + RGB underglow + per-key.

RGB initialisé à 50% de luminosité (économie batterie) en rouge solide.
Contrôles RGB sur le layer RAISE (Q/W/E/R/T).

Usage:
    python scripts/generate_test_firmware_full.py

Sortie: firmware_test_supermini_full/
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from models.project_model import KeyboardConfig, ProjectModel
from modules.build_manager.zmk_template_generator import ZmkTemplateGenerator


# Mêmes bindings RGB que generate_test_firmware_rgb.py
_RGB_KEYMAP_REPLACEMENTS = [
    ("&kp EXCL",  "&rgb_ug RGB_TOG"),  # Q = toggle on/off
    ("&kp AT",    "&rgb_ug RGB_EFF"),  # W = effet suivant
    ("&kp HASH",  "&rgb_ug RGB_BRI"),  # E = brightness +
    ("&kp DLLR",  "&rgb_ug RGB_BRD"),  # R = brightness -
    ("&kp PRCNT", "&rgb_ug RGB_HUI"),  # T = hue +
]


def _patch_keymap(keymap_path: Path) -> None:
    content = keymap_path.read_text(encoding="utf-8")
    for old, new in _RGB_KEYMAP_REPLACEMENTS:
        content = content.replace(old, new, 1)
    keymap_path.write_text(content, encoding="utf-8")


def _cap_brightness(conf_path: Path, brt_start: int = 50, brt_max: int = 50) -> None:
    """Limite BRT_START et BRT_MAX pour économiser la batterie.

    BRT_MAX = 50 empêche RGB_BRI de monter au-dessus de 50 % via touches.
    """
    content = conf_path.read_text(encoding="utf-8")
    content = content.replace(
        "CONFIG_ZMK_RGB_UNDERGLOW_BRT_MAX=100",
        f"CONFIG_ZMK_RGB_UNDERGLOW_BRT_MAX={brt_max}",
    )
    content = content.replace(
        "CONFIG_ZMK_RGB_UNDERGLOW_BRT_START=50",
        f"CONFIG_ZMK_RGB_UNDERGLOW_BRT_START={brt_start}",
    )
    conf_path.write_text(content, encoding="utf-8")


def main() -> int:
    model = ProjectModel(
        keyboard=KeyboardConfig(
            model="sofle-v2",
            mcu="supermini_nrf52840",
            oled_sides=["left", "right"],   # OLED activé des deux côtés
            rgb_enabled=True,                # RGB underglow activé
        )
    )

    output = ROOT / "firmware_test_supermini_full"
    if output.exists():
        shutil.rmtree(output)

    gen = ZmkTemplateGenerator()
    generated = gen.generate(model, output)

    _patch_keymap(generated["keymap"])
    _cap_brightness(generated["conf"], brt_start=50, brt_max=50)

    print(f"\nFirmware COMPLET généré dans : {output}")
    print("Périphériques :")
    print("  ✓ Matrice 5×6 split + encodeur")
    print("  ✓ OLED 128×32 (rotation 270°) sur les deux côtés (I2C D2/D3)")
    print("  ✓ RGB underglow + per-key, 36 LEDs/moitié, BRT 50% (cappé)")
    print("  ✓ BLE split + USB + ZMK Studio")
    print("\nContrôles RGB sur layer RAISE (LOWER+SPACE droit) :")
    print("  Q→TOG  W→EFF  E→BRI+  R→BRI-  T→HUE+")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
