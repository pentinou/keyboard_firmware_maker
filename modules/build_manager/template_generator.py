"""template_generator.py — Génération du code source QMK depuis ProjectModel.

Utilise Jinja2 pour rendre les templates (.c.j2, .h.j2, .mk.j2, .json.j2)
paramétrés depuis ProjectModel. Aucun import Qt — pur Python (testable).

Structure de sortie dans output_dir/ :
  config.h
  rules.mk
  keymaps/default/keymap.c
  keymaps/default/vial.json
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

from models.project_model import ProjectModel

logger = logging.getLogger(__name__)

BASE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).parent.parent.parent))

# Bootloader QMK par MCU (M1)
_BOOTLOADER_MAP: dict[str, str] = {
    "rp2040":    "rp2040",
    "pro_micro": "caterina",
    "elite_c":   "atmel-dfu",
}
TEMPLATES_DIR = BASE_DIR / "templates"

# (template_filename, output_path_relative_to_output_dir)
TEMPLATE_FILES: list[tuple[str, str]] = [
    ("keymap.c.j2",  "keymaps/default/keymap.c"),
    ("config.h.j2",  "config.h"),
    ("rules.mk.j2",  "rules.mk"),
    ("vial.json.j2", "keymaps/default/vial.json"),
]


class TemplateGenerator:
    """Génère les fichiers source QMK depuis ProjectModel + templates Jinja2."""

    def __init__(self, templates_dir: Path | None = None) -> None:
        self._templates_dir = templates_dir or TEMPLATES_DIR

    def generate(self, model: ProjectModel, output_dir: Path) -> dict[str, Path]:
        """Rend tous les templates et écrit les fichiers dans output_dir.

        Args:
            model: état du projet à sérialiser en code QMK.
            output_dir: répertoire de destination (créé si absent).

        Returns:
            Dict {nom_template: chemin_fichier_généré}.

        Raises:
            jinja2.TemplateNotFound: si un template est manquant.
            OSError: si l'écriture échoue.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        env = Environment(
            loader=FileSystemLoader(str(self._templates_dir)),
            autoescape=False,
            keep_trailing_newline=True,
        )
        context = self._build_context(model)
        result: dict[str, Path] = {}

        for tmpl_name, out_rel in TEMPLATE_FILES:
            tmpl = env.get_template(tmpl_name)
            out_path = output_dir / out_rel
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(tmpl.render(**context), encoding="utf-8")
            result[tmpl_name] = out_path
            logger.debug("Template rendu : %s → %s", tmpl_name, out_path)

        logger.info("Génération templates terminée dans %s", output_dir)
        return result

    def _build_context(self, model: ProjectModel) -> dict[str, Any]:
        """Construit le contexte Jinja2 depuis ProjectModel."""
        oled_enabled = bool(model.oled.image_path or model.oled.overlays)
        rgb_enabled = bool(model.rgb.effects or model.rgb.per_key)

        mcu = model.keyboard.mcu or "rp2040"
        return {
            "keyboard_model": model.keyboard.model or "keyboard_firmware_maker",
            "mcu": mcu,
            "bootloader": _BOOTLOADER_MAP.get(mcu, "rp2040"),  # M1
            "oled_enabled": oled_enabled,
            "rgb_enabled": rgb_enabled,
            "oled_frames": _encode_oled_frames(model.oled.frames) if oled_enabled else [],
            "oled_overlays": model.oled.overlays,
            "rgb_effects": [e.to_dict() for e in model.rgb.effects],
            "per_key_colors": model.rgb.per_key,
            "matrix_rows": 4,   # Sofle V2 : 4 lignes par half (3 regular + 1 thumb)
            "matrix_cols": 6,   # 6 colonnes par half
        }


def _encode_oled_frames(frames: list[bytes]) -> list[str]:
    """Encode des frames binaires en tableaux C uint8_t pour les templates.

    Chaque frame bytes → "0x00, 0xFF, 0x01, ..." (une ligne par 16 octets).
    """
    result: list[str] = []
    for frame in frames:
        chunks: list[str] = []
        for i in range(0, len(frame), 16):
            row = frame[i : i + 16]
            chunks.append(", ".join(f"0x{b:02X}" for b in row))
        result.append(",\n    ".join(chunks))
    return result
