"""Génère un firmware ZMK minimaliste (matrix + split BLE + encodeur, sans OLED/RGB)
pour valider le pinout du SuperMini nRF52840 sur un PCB Sofle v2.1 identique au RP2040.

Le but est un premier flash de validation matrice. OLED/RGB sont désactivés pour
limiter les risques au boot. Une fois la matrice validée, régénérer avec les
flags appropriés via l'UI KFM (onglet Hardware).

Usage:
    python scripts/generate_test_firmware.py

Sortie: firmware_test_supermini/
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from models.project_model import KeyboardConfig, ProjectModel
from modules.build_manager.zmk_template_generator import ZmkTemplateGenerator


def main() -> int:
    model = ProjectModel(
        keyboard=KeyboardConfig(
            model="sofle-v2",
            mcu="supermini_nrf52840",
            oled_sides=[],         # OLED off (has_display=False)
            rgb_enabled=False,     # RGB off (rgb_underglow=False)
        )
    )

    output = ROOT / "firmware_test_supermini"
    if output.exists():
        shutil.rmtree(output)

    gen = ZmkTemplateGenerator()
    generated = gen.generate(model, output)

    print(f"\nFirmware minimaliste généré dans : {output}")
    print("Fichiers clés :")
    for key, path in sorted(generated.items()):
        rel = path.relative_to(output)
        print(f"  {key:20s} {rel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
