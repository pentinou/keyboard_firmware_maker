"""Génère un firmware ZMK avec RGB underglow allumé en BLANC FIXE au boot,
luminosité 100%, pour valider directement le hardware RGB du Sofle v2.1 RGB.

Différence avec generate_test_firmware_rgb.py :
- SAT_START = 0  (saturation 0 → blanc pur, peu importe la hue)
- BRT_START = 100 (luminosité maximale)
- ON_START explicite (au cas où)

Usage:
    python scripts/generate_test_firmware_white.py

Sortie: firmware_test_supermini_white/
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from models.project_model import KeyboardConfig, ProjectModel
from modules.build_manager.zmk_template_generator import ZmkTemplateGenerator


def _force_white_solid(conf_path: Path) -> None:
    """Patch le .conf pour forcer blanc fixe à 100% au boot."""
    content = conf_path.read_text(encoding="utf-8")
    content = content.replace(
        "CONFIG_ZMK_RGB_UNDERGLOW_SAT_START=100",
        "CONFIG_ZMK_RGB_UNDERGLOW_SAT_START=0",  # 0 = blanc pur
    )
    content = content.replace(
        "CONFIG_ZMK_RGB_UNDERGLOW_BRT_START=50",
        "CONFIG_ZMK_RGB_UNDERGLOW_BRT_START=100",  # 100 % luminosité
    )
    # Force allumage au boot (par défaut y, mais explicite ne fait pas de mal)
    if "CONFIG_ZMK_RGB_UNDERGLOW_ON_START" not in content:
        content += "\nCONFIG_ZMK_RGB_UNDERGLOW_ON_START=y\n"
    conf_path.write_text(content, encoding="utf-8")


def main() -> int:
    model = ProjectModel(
        keyboard=KeyboardConfig(
            model="sofle-v2",
            mcu="supermini_nrf52840",
            oled_sides=[],
            rgb_enabled=True,
        )
    )

    output = ROOT / "firmware_test_supermini_white"
    if output.exists():
        shutil.rmtree(output)

    gen = ZmkTemplateGenerator()
    generated = gen.generate(model, output)

    # Force blanc fixe 100 % au boot
    _force_white_solid(generated["conf"])

    print(f"\nFirmware BLANC FIXE généré dans : {output}")
    print("Comportement : toutes les LEDs s'allument en BLANC à 100% au boot,")
    print("sans appui de touche. Si rien ne s'allume → hardware ou pin WS2812.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
