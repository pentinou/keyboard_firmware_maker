"""yaml_exporter — exporte un KeyboardDefinition vers un fichier YAML.

Module pur Python sans dépendance Qt — testable sans QApplication.
Utilisé par CustomKeyboardEditorDialog pour sauvegarder les claviers custom.
Les fichiers sont écrits dans ~/.keyboard_firmware_maker/custom_keyboards/,
jamais dans keyboards/ (dossier bundlé PyInstaller).
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

from modules.hardware.keyboard_loader import KeyboardDefinition, KeyLayout

_VALID_MODEL_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def _key_dict(k: KeyLayout) -> dict:
    """Convertit un KeyLayout en dict compact pour l'export YAML."""
    d: dict = {"row": k.row, "col": k.col, "x": float(k.x), "y": float(k.y)}
    if k.w != 1.0:
        d["w"] = float(k.w)
    if k.h != 1.0:
        d["h"] = float(k.h)
    if getattr(k, "r", 0.0) != 0.0:
        d["r"] = float(k.r)
    if k.encoder:
        d["encoder"] = True
    return d


class _FlowDict(dict):
    """Marqueur pour forcer le style flow sur un dict YAML."""


def _flow_representer(dumper: yaml.Dumper, data: "_FlowDict") -> yaml.Node:
    return dumper.represent_mapping("tag:yaml.org,2002:map", data, flow_style=True)


# Dumper dérivé — ne modifie pas yaml.Dumper global (F10)
_KFMDumper = type("_KFMDumper", (yaml.Dumper,), {})
_KFMDumper.add_representer(_FlowDict, _flow_representer)


def _build_layout_list(keys: list[KeyLayout]) -> list[_FlowDict]:
    return [_FlowDict(_key_dict(k)) for k in keys]


def _keyboard_to_dict(kd: KeyboardDefinition) -> dict:
    """Construit le dict YAML depuis un KeyboardDefinition."""
    all_keys: list[KeyLayout] = []
    for side_keys in kd.layout.values():
        all_keys.extend(side_keys)

    rows = max((k.row for k in all_keys), default=0) + 1
    cols = max((k.col for k in all_keys), default=0) + 1

    mcu_options = []
    for mcu in kd.mcu_options:
        p = mcu.pins
        pins: dict = {}
        if p.matrix_rows:
            pins["matrix_rows"] = list(p.matrix_rows)
        if p.matrix_cols:
            pins["matrix_cols"] = list(p.matrix_cols)
        if p.serial_tx:
            pins["serial_tx"] = p.serial_tx
        if p.serial_driver:
            pins["serial_driver"] = p.serial_driver
        if p.ws2812:
            pins["ws2812"] = p.ws2812
        if p.ws2812_driver:
            pins["ws2812_driver"] = p.ws2812_driver
        if p.encoder_a:
            pins["encoder_a"] = list(p.encoder_a)
        if p.encoder_b:
            pins["encoder_b"] = list(p.encoder_b)
        if p.encoder_a_right:
            pins["encoder_a_right"] = list(p.encoder_a_right)
        if p.encoder_b_right:
            pins["encoder_b_right"] = list(p.encoder_b_right)
        mcu_options.append({
            "id": mcu.id,
            "display_name": mcu.display_name,
            "description": mcu.description,
            "bootloader": mcu.bootloader,
            "pins": pins,
        })

    data: dict = {
        "model": kd.model,
        "display_name": kd.display_name,
        "description": kd.description,
        "split": kd.split,
        "mcu_options": mcu_options,
        "vial_vid": kd.vial_vid,
        "vial_pid": kd.vial_pid,
        "diode_direction": kd.diode_direction,
        "layout_macro": kd.layout_macro,
        "has_encoder": kd.has_encoder,
        "capabilities": dict(kd.capabilities),
        "matrix": {"rows": rows, "cols": cols},
    }

    if kd.capabilities.get("oled"):
        data["oled"] = {
            "driver": kd.oled_hw.driver,
            "rotation": kd.oled_hw.rotation,
            "display": kd.oled_hw.display,
        }

    if kd.capabilities.get("rgb"):
        data["rgb"] = {"max_brightness": kd.rgb_hw.max_brightness}

    layout: dict = {}
    if kd.split:
        if kd.layout.get("left"):
            layout["left"] = _build_layout_list(kd.layout["left"])
        if kd.layout.get("right"):
            layout["right"] = _build_layout_list(kd.layout["right"])
    else:
        keys_list = kd.layout.get("keys", [])
        if keys_list:
            layout["keys"] = _build_layout_list(keys_list)

    if layout:
        data["layout"] = layout

    return data


def export_keyboard(kd: KeyboardDefinition, path: Path) -> None:
    """Exporte un KeyboardDefinition vers un fichier YAML.

    Args:
        kd: Définition du clavier à exporter.
        path: Chemin de destination (créé si absent).

    Raises:
        ValueError: Si kd.model est vide ou invalide.
        OSError: Si l'écriture échoue.
    """
    if not kd.model or not _VALID_MODEL_RE.match(kd.model):
        raise ValueError(
            f"model invalide : {kd.model!r} — doit correspondre à [a-z0-9][a-z0-9-]*"
        )

    data = _keyboard_to_dict(kd)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.dump(data, Dumper=_KFMDumper, allow_unicode=True, sort_keys=False, default_flow_style=False),
        encoding="utf-8",
    )
