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

from models.project_model import OledSideConfig, ProjectModel
from modules.hardware.keyboard_loader import load_keyboard

logger = logging.getLogger(__name__)

BASE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).parent.parent.parent))

_CUSTOM_EFFECT_TYPES: frozenset[str] = frozenset({"ripple"})

# Bootloader QMK par MCU (M1)
_BOOTLOADER_MAP: dict[str, str] = {
    "rp2040":    "rp2040",
    "pro_micro": "caterina",
    "elite_c":   "atmel-dfu",
}
TEMPLATES_DIR = BASE_DIR / "templates"

# (template_filename, output_path_relative_to_output_dir)
TEMPLATE_FILES: list[tuple[str, str]] = [
    ("keyboard.c.j2", "keyboard_firmware_maker.c"),
    ("keymap.c.j2",   "keymaps/default/keymap.c"),
    ("config.h.j2",   "config.h"),
    ("rules.mk.j2",   "rules.mk"),
    ("info.json.j2",  "keyboard.json"),
    ("vial.json.j2",  "keymaps/default/vial.json"),
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

        template_files = list(TEMPLATE_FILES)
        if model.oled.left.luna_enabled or model.oled.right.luna_enabled:
            template_files.append(("luna.c.j2", "keymaps/default/luna.c"))
        if model.oled.left.bongo_enabled or model.oled.right.bongo_enabled:
            template_files.append(("bongocat.c.j2", "keymaps/default/bongocat.c"))
            template_files.append(("bongocat.h.j2", "keymaps/default/bongocat.h"))
        custom_effects = [e for e in model.rgb.effects if e.type in _CUSTOM_EFFECT_TYPES]
        if custom_effects:
            template_files.append(("rgb_matrix_user.inc.j2", "keymaps/default/rgb_matrix_user.inc"))

        for tmpl_name, out_rel in template_files:
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
        left = model.oled.left
        right = model.oled.right

        left_luna = left.luna_enabled
        right_luna = right.luna_enabled
        luna_enabled = left_luna or right_luna

        left_bongo = left.bongo_enabled
        right_bongo = right.bongo_enabled

        wpm_needed = (
            left.wpm.enabled or right.wpm.enabled or left_luna or right_luna
            or left_bongo or right_bongo
        )

        def _side_has_content(side: OledSideConfig) -> bool:
            return bool(
                any(img.frames for img in side.images)
                or side.layer.enabled
                or side.caps_lock.enabled
                or side.wpm.enabled
                or side.luna_enabled
                or side.bongo_enabled
            )

        oled_enabled = _side_has_content(left) or _side_has_content(right)

        rgb_enabled = bool(model.rgb.effects or model.rgb.per_key)

        mcu = model.keyboard.mcu or "rp2040"
        matrix_rows, matrix_cols = _load_keyboard_matrix(
            model.keyboard.model, self._templates_dir.parent
        )

        def _build_images(side: OledSideConfig) -> list[dict]:
            result = []
            for i, img in enumerate(side.images):
                if not img.frames:
                    continue
                frames = _invert_frames(img.frames) if img.inverted else img.frames
                result.append({
                    "idx": i,
                    "frames": _encode_oled_frames(frames),
                    "col": img.col,
                    "line": img.line,
                })
            return result

        def _hex_to_rgb(h: str) -> tuple[int, int, int]:
            h = h.lstrip('#')
            return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)

        custom_effects_ctx = []
        for i, e in enumerate(model.rgb.effects):
            if e.type in _CUSTOM_EFFECT_TYPES:
                pr, pg, pb = _hex_to_rgb(e.color_primary)
                sr, sg, sb = _hex_to_rgb(e.color_secondary)
                custom_effects_ctx.append({
                    "idx": i, "type": e.type,
                    "name": f"{e.type.upper()}_{i}",
                    "primary_r": pr, "primary_g": pg, "primary_b": pb,
                    "secondary_r": sr, "secondary_g": sg, "secondary_b": sb,
                    "fade_ms": e.fade_ms,
                })

        return {
            "keyboard_model": model.keyboard.model or "keyboard_firmware_maker",
            "mcu": mcu,
            "bootloader": _BOOTLOADER_MAP.get(mcu, "rp2040"),
            "oled_enabled": oled_enabled,
            "wpm_needed": wpm_needed,
            "rgb_enabled": rgb_enabled,
            "luna_enabled": luna_enabled,
            # Left side
            "left_images": _build_images(left),
            "left_layer": {"enabled": left.layer.enabled, "col": left.layer.col, "line": left.layer.line},
            "left_caps_lock": {"enabled": left.caps_lock.enabled, "col": left.caps_lock.col, "line": left.caps_lock.line},
            "left_wpm": {"enabled": left.wpm.enabled, "col": left.wpm.col, "line": left.wpm.line},
            "left_luna_enabled": left_luna,
            "left_luna_line": left.luna_line,
            "left_bongo_enabled": left_bongo,
            "left_bongo_line": left.bongo_line,
            # Right side
            "right_images": _build_images(right),
            "right_layer": {"enabled": right.layer.enabled, "col": right.layer.col, "line": right.layer.line},
            "right_caps_lock": {"enabled": right.caps_lock.enabled, "col": right.caps_lock.col, "line": right.caps_lock.line},
            "right_wpm": {"enabled": right.wpm.enabled, "col": right.wpm.col, "line": right.wpm.line},
            "right_luna_enabled": right_luna,
            "right_luna_line": right.luna_line,
            "right_bongo_enabled": right_bongo,
            "right_bongo_line": right.bongo_line,
            # RGB
            "rgb_effects": [e.to_dict() for e in model.rgb.effects],
            "per_key_colors": model.rgb.per_key,
            "custom_effects": custom_effects_ctx,
            "has_custom_effects": bool(custom_effects_ctx),
            "has_reactive_effects": any(e["type"] == "ripple" for e in custom_effects_ctx),
            "matrix_rows": matrix_rows,
            "matrix_cols": matrix_cols,
        }


def _load_keyboard_matrix(model_name: str, project_root: Path) -> tuple[int, int]:
    """Charge les dimensions de matrice depuis le YAML du clavier.

    Returns:
        (rows_per_half, cols) — défaut (5, 6) si le fichier est introuvable.
    """
    kb_file = project_root / "keyboards" / f"{model_name}.yaml"
    try:
        kb = load_keyboard(kb_file)
        return kb.matrix["rows"], kb.matrix["cols"]
    except Exception:
        logger.warning(
            "Impossible de lire la matrice pour '%s' depuis %s — défaut 5×6",
            model_name, kb_file,
        )
        return 5, 6


def _invert_frames(frames: list[bytes]) -> list[bytes]:
    """Retourne les frames avec chaque octet inversé (XOR 0xFF)."""
    return [bytes(b ^ 0xFF for b in frame) for frame in frames]


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
