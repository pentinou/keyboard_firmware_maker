"""Compile une série de firmwares WHITE-RGB pour identifier le pin WS2812 réel
du PCB Sofle v2.1 RGB par essai successif.

Pour chaque pin candidat, le script :
1. Modifie temporairement keyboards/sofle-v2.yaml pour pointer ws2812 vers ce pin
2. Lance le générateur ZMK + west build (côté gauche uniquement)
3. Renomme le .uf2 avec le suffixe du pin testé
4. Restaure le YAML à son état initial

Usage:
    python scripts/scan_ws2812_pins.py

Sortie: firmware_test_supermini_pinscan/uf2/sofle_v2_left_pinD{N}.uf2
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from models.project_model import KeyboardConfig, ProjectModel
from modules.build_manager.zmk_template_generator import ZmkTemplateGenerator

# Pads candidats (= positions Pro Micro libres après matrice + encodeur)
PINS_TO_TEST = [0, 1, 2, 4]

YAML_PATH = ROOT / "keyboards" / "sofle-v2.yaml"
WORKSPACE = Path.home() / ".keyboard_firmware_maker" / "zmk-workspace"
SDK_DIR = Path.home() / ".keyboard_firmware_maker" / "zephyr-sdk-0.17.0"
WEST = ROOT / ".venv" / "bin" / "west"
OUTPUT = ROOT / "firmware_test_supermini_pinscan"


def _force_white(conf_path: Path) -> None:
    content = conf_path.read_text(encoding="utf-8")
    content = content.replace(
        "CONFIG_ZMK_RGB_UNDERGLOW_SAT_START=100",
        "CONFIG_ZMK_RGB_UNDERGLOW_SAT_START=0",
    )
    content = content.replace(
        "CONFIG_ZMK_RGB_UNDERGLOW_BRT_START=50",
        "CONFIG_ZMK_RGB_UNDERGLOW_BRT_START=100",
    )
    if "CONFIG_ZMK_RGB_UNDERGLOW_ON_START" not in content:
        content += "\nCONFIG_ZMK_RGB_UNDERGLOW_ON_START=y\n"
    conf_path.write_text(content, encoding="utf-8")


def _swap_yaml_ws2812(pin_n: int) -> None:
    """Réécrit toutes les lignes ws2812 du YAML vers `&pro_micro {pin_n}`."""
    text = YAML_PATH.read_text(encoding="utf-8")
    new_lines = []
    for line in text.splitlines(keepends=True):
        stripped = line.lstrip()
        if stripped.startswith("ws2812:") and "&pro_micro" in stripped:
            indent = line[: len(line) - len(stripped)]
            new_lines.append(f'{indent}ws2812: "&pro_micro {pin_n}"\n')
        else:
            new_lines.append(line)
    YAML_PATH.write_text("".join(new_lines), encoding="utf-8")


def _build_left() -> Path:
    build_dir = WORKSPACE / "build" / "sofle_pinscan_left"
    config_dir = OUTPUT / "config"
    env = {
        **os.environ,
        "PATH": f"{ROOT/'.venv/bin'}:{os.environ.get('PATH', '')}",
        "ZEPHYR_SDK_INSTALL_DIR": str(SDK_DIR),
        "ZEPHYR_BASE": str(WORKSPACE / "zephyr"),
        "ZEPHYR_TOOLCHAIN_VARIANT": "zephyr",
    }
    cmd = [
        str(WEST), "build",
        "-s", "zmk/app",
        "-d", str(build_dir),
        "-b", "nice_nano//zmk",
        "--pristine", "auto",
        "--",
        "-DSHIELD=sofle_v2_left",
        f"-DZMK_CONFIG={config_dir}",
        "-DSNIPPET=studio-rpc-usb-uart",
    ]
    subprocess.run(cmd, cwd=str(WORKSPACE), env=env, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    return build_dir / "zephyr" / "zmk.uf2"


def main() -> int:
    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    (OUTPUT / "uf2").mkdir(parents=True)

    backup = YAML_PATH.read_text(encoding="utf-8")
    gen = ZmkTemplateGenerator()

    try:
        for pin in PINS_TO_TEST:
            print(f"\n=== Compilation pour ws2812 = &pro_micro {pin} ===")
            _swap_yaml_ws2812(pin)

            model = ProjectModel(
                keyboard=KeyboardConfig(
                    model="sofle-v2",
                    mcu="supermini_nrf52840",
                    oled_sides=[],
                    rgb_enabled=True,
                )
            )
            generated = gen.generate(model, OUTPUT)
            _force_white(generated["conf"])

            uf2 = _build_left()
            dest = OUTPUT / "uf2" / f"sofle_v2_left_pinD{pin}.uf2"
            shutil.copy(uf2, dest)
            print(f"  → {dest.name}")

    finally:
        YAML_PATH.write_text(backup, encoding="utf-8")
        print("\nYAML restauré à son état initial.")

    print(f"\n{len(PINS_TO_TEST)} firmwares disponibles dans {OUTPUT/'uf2'}/")
    print("Flashe-les un par un côté gauche jusqu'à voir les LEDs s'allumer.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
