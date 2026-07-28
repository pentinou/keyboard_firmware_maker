"""Génère un firmware ZMK avec RGB underglow activé (chaîne WS2812 complète)
et touches de contrôle RGB sur le layer `raise` pour le SuperMini nRF52840.

ZMK ne supporte que l'underglow global (pas de per-key RGB indépendant comme
QMK) : toutes les LEDs de la chaîne reçoivent la même couleur/effet.

Usage:
    python scripts/generate_test_firmware_rgb.py

Sortie: firmware_test_supermini_rgb/
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from models.project_model import KeyboardConfig, ProjectModel
from modules.build_manager.zmk_template_generator import ZmkTemplateGenerator

# Bindings RGB à injecter sur le layer `raise`, aux emplacements des touches
# Q, W, E, R, T côté gauche (row 1 cols 1-5). Le keymap généré met `&kp EXCL`,
# `&kp AT`, etc. sur cette row ; on les remplace par les contrôles RGB.
_RGB_KEYMAP_REPLACEMENTS = [
    # (ancien binding, nouveau binding, commentaire pour documentation)
    ("&kp EXCL",  "&rgb_ug RGB_TOG"),  # Q = toggle on/off
    ("&kp AT",    "&rgb_ug RGB_EFF"),  # W = effet suivant
    ("&kp HASH",  "&rgb_ug RGB_BRI"),  # E = brightness +
    ("&kp DLLR",  "&rgb_ug RGB_BRD"),  # R = brightness -
    ("&kp PRCNT", "&rgb_ug RGB_HUI"),  # T = hue +
]


def _patch_keymap(keymap_path: Path) -> None:
    """Remplace les bindings du raise_layer pour exposer les contrôles RGB."""
    content = keymap_path.read_text(encoding="utf-8")
    for old, new in _RGB_KEYMAP_REPLACEMENTS:
        # Remplacement restreint au 1er match dans raise_layer (suffit ici
        # car ces bindings n'apparaissent qu'une fois dans le keymap généré)
        content = content.replace(old, new, 1)
    keymap_path.write_text(content, encoding="utf-8")


def main() -> int:
    model = ProjectModel(
        keyboard=KeyboardConfig(
            model="sofle-v2",
            mcu="supermini_nrf52840",
            oled_sides=[],         # OLED toujours off (on valide RGB en premier)
            rgb_enabled=True,      # RGB underglow activé
        )
    )

    output = ROOT / "firmware_test_supermini_rgb"
    if output.exists():
        shutil.rmtree(output)

    gen = ZmkTemplateGenerator()
    generated = gen.generate(model, output)

    # Post-patch : injection des bindings RGB sur le raise layer
    _patch_keymap(generated["keymap"])

    print(f"\nFirmware RGB généré dans : {output}")
    print("Contrôles RGB ajoutés sur le layer RAISE (= LOWER+SPACE droit) :")
    print("  Q → RGB toggle on/off")
    print("  W → Effet suivant")
    print("  E → Brightness +")
    print("  R → Brightness -")
    print("  T → Hue (teinte) +")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
