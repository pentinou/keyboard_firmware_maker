"""template_generator.py — Génération du code source QMK depuis ProjectModel.

Utilise Jinja2 pour rendre les templates (.c.j2, .h.j2, .mk.j2, .json.j2)
paramétrés depuis ProjectModel. Aucun import Qt — pur Python (testable).

Structure de sortie dans output_dir/ :
  config.h
  rules.mk
  keymaps/default/keymap.c
  keymaps/default/rules.mk
  keymaps/default/vial.json
"""
from __future__ import annotations

import hashlib
import logging
import sys
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

from models.project_model import OledSideConfig, ProjectModel
from modules.oled_editor.processor import frame_to_qmk_bytes
from modules.hardware.keyboard_loader import KeyboardDefinition, McuPins, load_keyboard

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
    ("keymap_rules.mk.j2", "keymaps/default/rules.mk"),
    ("keymap_config.h.j2", "keymaps/default/config.h"),
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
        if model.oled.left.katawajojo_enabled or model.oled.right.katawajojo_enabled:
            template_files.append(("katawajojo.c.j2", "keymaps/default/katawajojo.c"))
        if model.oled.left.luna_enabled or model.oled.right.luna_enabled:
            template_files.append(("luna.c.j2", "keymaps/default/luna.c"))
        if model.oled.left.ocean_dream_enabled or model.oled.right.ocean_dream_enabled:
            template_files.append(("ocean_dream.c.j2", "keymaps/default/ocean_dream.c"))
        if model.oled.left.bongo_enabled or model.oled.right.bongo_enabled:
            template_files.append(("bongocat.c.j2", "keymaps/default/bongocat.c"))
            template_files.append(("bongocat.h.j2", "keymaps/default/bongocat.h"))
        if model.oled.left.crab_enabled or model.oled.right.crab_enabled:
            template_files.append(("crab.c.j2", "keymaps/default/crab.c"))
            template_files.append(("crab.h.j2", "keymaps/default/crab.h"))
            template_files.append(("animation-utils.c.j2", "keymaps/default/animation-utils.c"))
            template_files.append(("animation-utils.h.j2", "keymaps/default/animation-utils.h"))
        custom_effects = [e for e in model.rgb.effects if e.type in _CUSTOM_EFFECT_TYPES]
        if custom_effects:
            template_files.append(("rgb_matrix_user.inc.j2", "keymaps/default/rgb_matrix_user.inc"))

        # Check for static vial.json (official layout from keyboard vendor)
        static_vial = self._templates_dir.parent / "keyboards" / f"{model.keyboard.model}.vial.json"
        if static_vial.is_file():
            template_files = [(n, o) for n, o in template_files if n != "vial.json.j2"]

        for tmpl_name, out_rel in template_files:
            tmpl = env.get_template(tmpl_name)
            out_path = output_dir / out_rel
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(tmpl.render(**context), encoding="utf-8")
            result[tmpl_name] = out_path
            logger.debug("Template rendu : %s → %s", tmpl_name, out_path)

        # Copy static vial.json if available
        if static_vial.is_file():
            import shutil
            vial_out = output_dir / "keymaps" / "default" / "vial.json"
            vial_out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(static_vial, vial_out)
            result["vial.json"] = vial_out
            logger.debug("Copie vial.json statique : %s → %s", static_vial, vial_out)

        logger.info("Génération templates terminée dans %s", output_dir)
        return result

    def _build_context(self, model: ProjectModel) -> dict[str, Any]:
        """Construit le contexte Jinja2 depuis ProjectModel."""
        left = model.oled.left
        right = model.oled.right

        left_katawajojo = left.katawajojo_enabled
        right_katawajojo = right.katawajojo_enabled
        katawajojo_enabled = left_katawajojo or right_katawajojo

        left_luna = left.luna_enabled
        right_luna = right.luna_enabled
        luna_enabled = left_luna or right_luna

        left_ocean_dream = left.ocean_dream_enabled
        right_ocean_dream = right.ocean_dream_enabled
        ocean_dream_enabled = left_ocean_dream or right_ocean_dream

        left_bongo = left.bongo_enabled
        right_bongo = right.bongo_enabled

        left_crab = left.crab_enabled
        right_crab = right.crab_enabled

        wpm_needed = (
            left.wpm.enabled or right.wpm.enabled
            or left_katawajojo or right_katawajojo
            or left_luna or right_luna
            or left_ocean_dream or right_ocean_dream
            or left_bongo or right_bongo
            or left_crab or right_crab
        )

        def _side_has_content(side: OledSideConfig) -> bool:
            return bool(
                any(img.frames for img in side.images)
                or side.layer.enabled
                or side.caps_lock.enabled
                or side.wpm.enabled
                or side.rgb_mode.enabled
                or side.kfm.enabled
                or side.katawajojo_enabled
                or side.luna_enabled
                or side.ocean_dream_enabled
                or side.bongo_enabled
                or side.crab_enabled
            )

        oled_enabled = _side_has_content(left) or _side_has_content(right)

        mcu = model.keyboard.mcu or "rp2040"
        kb_def = _load_keyboard_def(model.keyboard.model, self._templates_dir.parent)
        matrix_rows = kb_def.matrix["rows"]
        matrix_cols = kb_def.matrix["cols"]
        vial_name = kb_def.vial_name or model.keyboard.model
        vial_vid = kb_def.vial_vid
        vial_pid = kb_def.vial_pid
        capabilities = kb_def.capabilities

        # Extract pins from the selected MCU
        pins = McuPins()
        bootloader = _BOOTLOADER_MAP.get(mcu, "rp2040")
        for mcu_opt in kb_def.mcu_options:
            if mcu_opt.id == mcu:
                pins = mcu_opt.pins
                if mcu_opt.bootloader:
                    bootloader = mcu_opt.bootloader
                break

        # Build raw layout dict for vial.json
        kb_layout: dict[str, list[dict]] = {}
        for side in ("left", "right"):
            kb_layout[side] = [
                {"row": k.row, "col": k.col, "x": k.x, "y": k.y,
                 "encoder": k.encoder}
                for k in kb_def.layout.get(side, [])
            ]

        # RGB enabled if the keyboard hardware supports it (capability from YAML)
        rgb_enabled = bool(capabilities.get("rgb", False))

        # Build flat key list for vial.json with physical positions
        vial_keys: list[dict] = []
        left_keys = kb_layout.get("left", [])
        right_keys = kb_layout.get("right", [])
        if left_keys and right_keys:
            max_left_x = max(k["x"] for k in left_keys)
            x_offset = max_left_x + 1.5
            for k in left_keys:
                if k.get("encoder"):
                    continue  # Skip encoder positions (not in LAYOUT_sofle)
                vial_keys.append({
                    "matrix_row": k["row"], "matrix_col": k["col"],
                    "x": round(k["x"], 3), "y": round(k["y"], 3),
                })
            for k in right_keys:
                if k.get("encoder"):
                    continue  # Skip encoder positions (not in LAYOUT_sofle)
                vial_keys.append({
                    "matrix_row": k["row"] + matrix_rows, "matrix_col": k["col"],
                    "x": round(k["x"] + x_offset, 3), "y": round(k["y"], 3),
                })
        else:
            # Fallback: simple grid
            for row in range(matrix_rows):
                for col in range(matrix_cols):
                    vial_keys.append({"matrix_row": row, "matrix_col": col,
                                      "x": col, "y": row})
            x_offset = matrix_cols + 1
            for row in range(matrix_rows):
                for col in range(matrix_cols):
                    vial_keys.append({"matrix_row": row + matrix_rows,
                                      "matrix_col": col, "x": col + x_offset, "y": row})

        def _build_images(side: OledSideConfig) -> list[dict]:
            result = []
            for i, img in enumerate(side.images):
                if not img.frames:
                    continue
                frames = _invert_frames(img.frames, img.natural_w, img.natural_h) if img.inverted else img.frames
                qmk_frames = [frame_to_qmk_bytes(f) for f in frames]
                delays = img.delays if img.delays else [200] * len(frames)
                result.append({
                    "idx": i,
                    "frames": _encode_oled_frames(qmk_frames),
                    "delays": delays,
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

        uid_seed = (model.keyboard.model or "keyboard").encode()
        uid_bytes = hashlib.md5(uid_seed).digest()[:8]
        vial_uid = ", ".join(f"0x{b:02X}" for b in uid_bytes)

        # Pins as a dict for templates
        pins_dict = {
            "matrix_rows": pins.matrix_rows,
            "matrix_cols": pins.matrix_cols,
            "encoder_a": pins.encoder_a,
            "encoder_b": pins.encoder_b,
            "encoder_a_right": pins.encoder_a_right,
            "encoder_b_right": pins.encoder_b_right,
            "ws2812": pins.ws2812,
            "serial_tx": pins.serial_tx,
            "serial_driver": pins.serial_driver,
            "ws2812_driver": pins.ws2812_driver,
            "encoder_default_pos": pins.encoder_default_pos,
        }

        return {
            "keyboard_model": model.keyboard.model or "keyboard_firmware_maker",
            "vial_name": vial_name,
            "vial_vid": vial_vid,
            "vial_pid": vial_pid,
            "mcu": mcu,
            "bootloader": bootloader,
            "vial_uid": vial_uid,
            "pins": pins_dict,
            "diode_direction": kb_def.diode_direction,
            "layout_macro": kb_def.layout_macro,
            "has_encoder": kb_def.has_encoder,
            "oled_driver": kb_def.oled_hw.driver,
            "oled_rotation": kb_def.oled_hw.rotation,
            "oled_display": kb_def.oled_hw.display,
            "rgb_max_brightness": kb_def.rgb_hw.max_brightness,
            "oled_enabled": oled_enabled,
            "wpm_needed": wpm_needed,
            "rgb_enabled": rgb_enabled,
            "katawajojo_enabled": katawajojo_enabled,
            "luna_enabled": luna_enabled,
            "ocean_dream_enabled": ocean_dream_enabled,
            # Left side
            "left_images": _build_images(left),
            "left_layer": {"enabled": left.layer.enabled, "col": left.layer.col, "line": left.layer.line},
            "left_caps_lock": {"enabled": left.caps_lock.enabled, "col": left.caps_lock.col, "line": left.caps_lock.line},
            "left_wpm": {"enabled": left.wpm.enabled, "col": left.wpm.col, "line": left.wpm.line},
            "left_rgb_mode": {"enabled": left.rgb_mode.enabled and rgb_enabled, "col": left.rgb_mode.col, "line": left.rgb_mode.line},
            "left_kfm": {"enabled": left.kfm.enabled, "col": left.kfm.col, "line": left.kfm.line},
            "left_katawajojo_enabled": left_katawajojo,
            "left_katawajojo_line": left.katawajojo_line,
            "left_luna_enabled": left_luna,
            "left_luna_line": left.luna_line,
            "left_ocean_dream_enabled": left_ocean_dream,
            "left_ocean_dream_line": left.ocean_dream_line,
            "left_bongo_enabled": left_bongo,
            "left_bongo_line": left.bongo_line,
            "left_crab_enabled": left_crab,
            "left_crab_line": left.crab_line,
            # Right side
            "right_images": _build_images(right),
            "right_layer": {"enabled": right.layer.enabled, "col": right.layer.col, "line": right.layer.line},
            "right_caps_lock": {"enabled": right.caps_lock.enabled, "col": right.caps_lock.col, "line": right.caps_lock.line},
            "right_wpm": {"enabled": right.wpm.enabled, "col": right.wpm.col, "line": right.wpm.line},
            "right_rgb_mode": {"enabled": right.rgb_mode.enabled and rgb_enabled, "col": right.rgb_mode.col, "line": right.rgb_mode.line},
            "right_kfm": {"enabled": right.kfm.enabled, "col": right.kfm.col, "line": right.kfm.line},
            "right_katawajojo_enabled": right_katawajojo,
            "right_katawajojo_line": right.katawajojo_line,
            "right_luna_enabled": right_luna,
            "right_luna_line": right.luna_line,
            "right_ocean_dream_enabled": right_ocean_dream,
            "right_ocean_dream_line": right.ocean_dream_line,
            "right_bongo_enabled": right_bongo,
            "right_bongo_line": right.bongo_line,
            "right_crab_enabled": right_crab,
            "right_crab_line": right.crab_line,
            # RGB
            "rgb_effects": [e.to_dict() for e in model.rgb.effects],
            "per_key_colors": model.rgb.per_key,
            "custom_effects": custom_effects_ctx,
            "has_custom_effects": bool(custom_effects_ctx),
            "has_reactive_effects": any(e["type"] == "ripple" for e in custom_effects_ctx),
            "matrix_rows": matrix_rows,
            "matrix_cols": matrix_cols,
            "vial_keys": vial_keys,
            "anti_burnin": model.oled.anti_burnin and oled_enabled,
            "oled_sleep": model.oled.sleep_enabled and oled_enabled,
            "oled_sleep_timeout_ms": model.oled.sleep_timeout_s * 1000,
            "rgb_sleep": model.oled.sleep_enabled and rgb_enabled,
        }


def _load_keyboard_def(model_name: str, project_root: Path) -> KeyboardDefinition:
    """Charge la définition complète du clavier depuis le YAML.

    Retourne un KeyboardDefinition par défaut en cas d'erreur.
    """
    kb_file = project_root / "keyboards" / f"{model_name}.yaml"
    try:
        return load_keyboard(kb_file)
    except Exception:
        logger.warning(
            "Impossible de lire la définition pour '%s' depuis %s — défaut",
            model_name, kb_file,
        )
        return KeyboardDefinition(
            model=model_name, display_name=model_name, description="",
        )


def _invert_frames(frames: list[bytes], nat_w: int, nat_h: int) -> list[bytes]:
    """Inverse uniquement les pixels de la zone de contenu (nat_w × nat_h).

    Le contenu est centré horizontalement et aligné en haut dans le frame 32×128.
    Le fond (padding noir) reste intact pour éviter de le rendre blanc.
    """
    from modules.oled_editor.processor import OLED_WIDTH
    crop_x = (OLED_WIDTH - nat_w) // 2
    result: list[bytes] = []
    for frame in frames:
        arr = bytearray(frame)
        for row in range(nat_h):
            for col in range(crop_x, crop_x + nat_w):
                arr[row * OLED_WIDTH + col] ^= 0xFF
        result.append(bytes(arr))
    return result


def _encode_oled_frames(frames: list[bytes]) -> list[str]:
    """Encode des frames binaires en tableaux C uint8_t pour les templates.

    Chaque frame bytes → "0x00, 0xFF, 0x01, ..." (une ligne par 16 octets).
    Les frames doivent être déjà au format QMK 512 octets (via frame_to_qmk_bytes).
    """
    result: list[str] = []
    for frame in frames:
        chunks: list[str] = []
        for i in range(0, len(frame), 16):
            row = frame[i : i + 16]
            chunks.append(", ".join(f"0x{b:02X}" for b in row))
        result.append(",\n    ".join(chunks))
    return result
