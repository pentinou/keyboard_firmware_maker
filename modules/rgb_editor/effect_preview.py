"""EffectPreview — anime les effets RGB sur le layout visuel du clavier.

Supporte :
- Couleur statique uniforme : applique color_primary sur toutes les touches
- Ripple au keystroke : animation par distance Manhattan depuis un centre aléatoire

Fonctionne via QTimer — ne dépend pas d'un QWidget parent.
"""
from __future__ import annotations

import logging
import random

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QPushButton

from models.project_model import RgbEffect

logger = logging.getLogger(__name__)

RIPPLE_STEPS = 4
RIPPLE_INTERVAL_MS = 200


class EffectPreview:
    """Gère l'animation de prévisualisation des effets RGB sur les touches."""

    def __init__(self, key_buttons: dict[str, QPushButton]) -> None:
        self._key_buttons = key_buttons
        self._timer = QTimer()
        self._timer.timeout.connect(self._tick)
        self._effect: RgbEffect | None = None
        self._step = 0
        self._center: tuple[str, int, int] | None = None

    def start(self, effect: RgbEffect) -> None:
        """Démarre l'animation selon le type d'effet."""
        self._timer.stop()
        self._effect = effect
        self._step = 0
        if effect.type == "static":
            self._apply_static()
        elif effect.type == "ripple":
            self._pick_new_center()
            self._timer.setInterval(RIPPLE_INTERVAL_MS)
            self._timer.start()

    def stop(self) -> None:
        """Arrête le timer et réinitialise les couleurs des touches."""
        self._timer.stop()
        self._reset_keys()

    def update(self, effect: RgbEffect) -> None:
        """Met à jour l'animation sans redémarrer entièrement si possible."""
        self._effect = effect
        if effect.type == "static":
            self._timer.stop()
            self._apply_static()
        elif not self._timer.isActive():
            self.start(effect)

    def is_active(self) -> bool:
        """Indique si l'animation est en cours."""
        return self._timer.isActive()

    # ─────────────────────────────────────────────── Private helpers ──

    def _apply_static(self) -> None:
        if not self._effect:
            return
        for btn in self._key_buttons.values():
            btn.setStyleSheet(f"background-color: {self._effect.color_primary};")

    def _reset_keys(self) -> None:
        for btn in self._key_buttons.values():
            btn.setStyleSheet("")

    def _pick_new_center(self) -> None:
        if not self._key_buttons:
            self._center = None
            return
        key_id = random.choice(list(self._key_buttons.keys()))
        try:
            parts = key_id.split("_")
            side = parts[0]
            r = int(parts[1][1:])
            c = int(parts[2][1:])
            self._center = (side, r, c)
        except (IndexError, ValueError):
            logger.warning("key_id malformé ignoré dans _pick_new_center : %s", key_id)
            self._center = None

    def _distance(self, key_id: str) -> int:
        if self._center is None:
            return 999
        try:
            parts = key_id.split("_")
            side, r, c = parts[0], int(parts[1][1:]), int(parts[2][1:])
        except (IndexError, ValueError):
            return 999
        cs, cr, cc = self._center
        if side != cs:
            return 999  # demi-clavier différent
        return abs(r - cr) + abs(c - cc)  # distance Manhattan

    def _tick(self) -> None:
        if not self._effect or self._center is None:
            return
        self._reset_keys()
        step = self._step % RIPPLE_STEPS
        if step == 0:
            center_id = f"{self._center[0]}_r{self._center[1]}_c{self._center[2]}"
            if center_id in self._key_buttons:
                self._key_buttons[center_id].setStyleSheet(
                    f"background-color: {self._effect.color_primary};"
                )
        elif step == 1:
            for kid, btn in self._key_buttons.items():
                d = self._distance(kid)
                if d == 0:
                    btn.setStyleSheet(f"background-color: {self._effect.color_primary};")
                elif d == 1:
                    btn.setStyleSheet(f"background-color: {self._effect.color_secondary};")
        elif step == 2:
            for kid, btn in self._key_buttons.items():
                if self._distance(kid) == 1:
                    btn.setStyleSheet(f"background-color: {self._effect.color_secondary};")
        elif step == 3:
            self._pick_new_center()
            # L3: colorer immédiatement le nouveau centre (évite la frame vide de 200ms)
            if self._center:
                center_id = f"{self._center[0]}_r{self._center[1]}_c{self._center[2]}"
                if center_id in self._key_buttons:
                    self._key_buttons[center_id].setStyleSheet(
                        f"background-color: {self._effect.color_primary};"
                    )
            self._step = 0  # après += 1 ci-dessous → prochain step sera 1
        self._step += 1
