"""Génère un firmware ZMK DIAGNOSTIC pour le Sofle v2.1 RGB sur SuperMini nRF52840.

CHAQUE TOUCHE envoie `1` (kp N1), y compris les thumb clusters (row 4).
But : identifier toutes les touches mortes en tapant chaque switch un par un
dans un éditeur texte. Si une touche n'envoie pas de `1`, elle est défaillante
(soudure switch, diode, ou pin matrice).

Pas d'OLED, pas de RGB — focus matrice pure (boot rapide, isolation des variables).
Encodeur conservé (volume +/-).

Usage:
    python scripts/generate_test_firmware_diag.py

Sortie: firmware_test_supermini_diag/
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from models.project_model import KeyboardConfig, ProjectModel
from modules.build_manager.zmk_template_generator import ZmkTemplateGenerator


# Keymap où chaque touche = N1, structure Sofle v2 (5 rows split 6+6, row 4 = 10 thumbs)
_DIAG_KEYMAP = """\
/*
 * Diagnostic firmware - Sofle v2.1 RGB
 * Toutes les touches envoient `1`. Tape chaque switch dans un éditeur texte.
 * Si une touche n'envoie pas de `1` → switch ou diode défaillant.
 */

#include <behaviors.dtsi>
#include <dt-bindings/zmk/keys.h>
#include <dt-bindings/zmk/bt.h>
#include <dt-bindings/zmk/outputs.h>

/ {
    keymap {
        compatible = "zmk,keymap";

        default_layer {
            display-name = "Diag";
            bindings = <
                &kp N1  &kp N1  &kp N1  &kp N1  &kp N1  &kp N1    &kp N1  &kp N1  &kp N1  &kp N1  &kp N1  &kp N1
                &kp N1  &kp N1  &kp N1  &kp N1  &kp N1  &kp N1    &kp N1  &kp N1  &kp N1  &kp N1  &kp N1  &kp N1
                &kp N1  &kp N1  &kp N1  &kp N1  &kp N1  &kp N1    &kp N1  &kp N1  &kp N1  &kp N1  &kp N1  &kp N1
                &kp N1  &kp N1  &kp N1  &kp N1  &kp N1  &kp N1    &kp N1  &kp N1  &kp N1  &kp N1  &kp N1  &kp N1
                &kp N1  &kp N1  &kp N1  &kp N1  &kp N1            &kp N1  &kp N1  &kp N1  &kp N1  &kp N1
            >;
            sensor-bindings = <&inc_dec_kp C_VOL_UP C_VOL_DN>;
        };
    };
};
"""


def main() -> int:
    model = ProjectModel(
        keyboard=KeyboardConfig(
            model="sofle-v2",
            mcu="supermini_nrf52840",
            oled_sides=[],          # OLED off
            rgb_enabled=False,      # RGB off
        )
    )

    output = ROOT / "firmware_test_supermini_diag"
    if output.exists():
        shutil.rmtree(output)

    gen = ZmkTemplateGenerator()
    generated = gen.generate(model, output)

    # Overwrite le keymap avec le diagnostic
    generated["keymap"].write_text(_DIAG_KEYMAP, encoding="utf-8")

    print(f"\nFirmware DIAGNOSTIC généré dans : {output}")
    print("Comportement : chaque touche envoie `1`, encodeur = volume.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
