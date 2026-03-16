"""validator.py — Validation d'un KeyboardDefinition avant export YAML.

Module pur Python sans dépendance Qt — testable sans QApplication.
Appelé par CustomKeyboardEditorDialog avant export_keyboard().
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from modules.hardware.keyboard_loader import KeyboardDefinition


@dataclass
class ValidationResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def validate_keyboard(kd: "KeyboardDefinition") -> ValidationResult:
    """Valide un KeyboardDefinition et retourne les erreurs/avertissements.

    Les erreurs bloquent la sauvegarde.
    Les avertissements sont affichés mais permettent de continuer.
    """
    r = ValidationResult()

    for mcu in kd.mcu_options:
        prefix = f"MCU « {mcu.display_name} »"
        is_rp2040 = mcu.id == "rp2040"

        # Pins de lignes obligatoires
        if not mcu.pins.matrix_rows:
            r.errors.append(f"{prefix} : aucune broche de ligne (matrix_rows) définie.")
        # Pins de colonnes obligatoires
        if not mcu.pins.matrix_cols:
            r.errors.append(f"{prefix} : aucune broche de colonne (matrix_cols) définie.")

        # Split → serial_tx obligatoire
        if kd.split and not mcu.pins.serial_tx:
            r.errors.append(
                f"{prefix} : clavier split mais aucune broche série (serial_tx) définie."
            )

        # RGB → pin WS2812 obligatoire
        if kd.capabilities.get("rgb") and not mcu.pins.ws2812:
            r.errors.append(
                f"{prefix} : RGB activé mais aucune broche LED (WS2812) définie."
            )

        # RP2040 + RGB → driver vendor conseillé (avertissement si absent)
        if kd.capabilities.get("rgb") and mcu.pins.ws2812 and is_rp2040:
            if mcu.pins.ws2812_driver and mcu.pins.ws2812_driver != "vendor":
                r.warnings.append(
                    f"{prefix} : sur RP2040 le driver WS2812 doit être « vendor » "
                    f"(valeur actuelle : « {mcu.pins.ws2812_driver} »). "
                    "Il sera corrigé automatiquement à la compilation."
                )

        # RP2040 + split → driver série vendor conseillé
        if kd.split and is_rp2040:
            if mcu.pins.serial_driver and mcu.pins.serial_driver not in ("vendor",):
                r.warnings.append(
                    f"{prefix} : sur RP2040 le driver série doit être « vendor » "
                    f"(valeur actuelle : « {mcu.pins.serial_driver} »). "
                    "Il sera corrigé automatiquement à la compilation."
                )

        # Encodeur → pins encoder obligatoires
        if kd.has_encoder and not mcu.pins.encoder_a:
            r.warnings.append(
                f"{prefix} : encodeur activé mais broches encoder_a/encoder_b non définies. "
                "L'encodeur ne fonctionnera pas."
            )

        # Vérification cohérence rows : pour split, rangées côté gauche ≤ nb pins
        if kd.split and mcu.pins.matrix_rows:
            rows_per_side = len(mcu.pins.matrix_rows)
            left_keys = [k for k in kd.layout.get("left", []) if not k.encoder]
            right_keys = [k for k in kd.layout.get("right", []) if not k.encoder]

            if left_keys:
                left_rows = len(set(k.row for k in left_keys))
                if left_rows > rows_per_side:
                    r.warnings.append(
                        f"{prefix} : le côté gauche utilise {left_rows} rangées mais "
                        f"seulement {rows_per_side} broche(s) de ligne disponible(s). "
                        "Des touches pourraient partager la même position matrice."
                    )

            if right_keys:
                # Rangées côté droit normalisées (0-based)
                min_r = min(k.row for k in right_keys)
                right_rows = len(set(k.row - min_r for k in right_keys))
                if right_rows > rows_per_side:
                    r.warnings.append(
                        f"{prefix} : le côté droit utilise {right_rows} rangées mais "
                        f"seulement {rows_per_side} broche(s) de ligne disponible(s). "
                        "Des touches pourraient partager la même position matrice."
                    )

    # Positions matrice uniques par côté (pour split, chaque moitié est indépendante)
    all_keys = []
    for side_keys in kd.layout.values():
        all_keys.extend(side_keys)

    if kd.split:
        sides_to_check = [
            ("gauche", kd.layout.get("left", [])),
            ("droite", kd.layout.get("right", [])),
        ]
    else:
        sides_to_check = [("", all_keys)]

    for side_label, side_keys in sides_to_check:
        seen: set[tuple[int, int]] = set()
        duplicates: set[tuple[int, int]] = set()
        for k in side_keys:
            if k.encoder:
                continue
            pos = (k.row, k.col)
            if pos in seen:
                duplicates.add(pos)
            seen.add(pos)
        if duplicates:
            dup_str = ", ".join(f"({row},{col})" for row, col in sorted(duplicates))
            label = f" (côté {side_label})" if side_label else ""
            r.errors.append(
                f"Positions matrice dupliquées{label} : {dup_str}. "
                "Chaque touche doit occuper une position (rangée, colonne) unique."
            )

    # Au moins une touche
    non_enc = [k for k in all_keys if not k.encoder]
    if not non_enc:
        r.errors.append("Le clavier ne contient aucune touche.")

    return r
