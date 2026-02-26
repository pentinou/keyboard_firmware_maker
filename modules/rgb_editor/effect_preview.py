"""EffectPreview — anime les effets RGB sur le layout visuel du clavier.

Supporte tous les types de preview définis dans effects.py :
- solid, breathing, cycle_all, cycle_lr, cycle_ud, gradient_h, gradient_v,
  band_v, pinwheel, spiral, cycle_out_in, raindrops, heatmap, two_zone,
  reactive, ripple

Fonctionne via QTimer — ne dépend pas d'un QWidget parent.
"""
from __future__ import annotations

import logging
import math
import random

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QPushButton

from models.project_model import RgbEffect
from modules.rgb_editor.effects import EFFECT_TYPES

logger = logging.getLogger(__name__)

RIPPLE_STEPS = 4
RIPPLE_INTERVAL_MS = 200
SMOOTH_INTERVAL_MS = 50   # 20 fps
PHASE_STEP = 3             # degrés/tick → cycle complet ≈ 6s


def _hsv_to_hex(h: float, s: float, v: float) -> str:
    """Convertit HSV (h=0-360, s=0-1, v=0-1) en '#RRGGBB'."""
    h = h % 360
    hi = int(h / 60) % 6
    f = h / 60 - int(h / 60)
    p = v * (1 - s)
    q = v * (1 - f * s)
    t = v * (1 - (1 - f) * s)
    rgb_map = [(v, t, p), (q, v, p), (p, v, t), (p, q, v), (t, p, v), (v, p, q)]
    r, g, b = rgb_map[hi]
    return f"#{int(r*255):02X}{int(g*255):02X}{int(b*255):02X}"


def _hex_to_hsv(hex_color: str) -> tuple[float, float, float]:
    """Convertit '#RRGGBB' en HSV (h=0-360, s=0-1, v=0-1)."""
    h = hex_color.lstrip('#')
    r, g, bb = int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255
    mx = max(r, g, bb)
    mn = min(r, g, bb)
    d = mx - mn
    v = mx
    s = (d / mx) if mx != 0 else 0
    if d == 0:
        hue = 0.0
    elif mx == r:
        hue = 60 * ((g - bb) / d % 6)
    elif mx == g:
        hue = 60 * ((bb - r) / d + 2)
    else:
        hue = 60 * ((r - g) / d + 4)
    return hue % 360, s, v


class EffectPreview:
    """Gère l'animation de prévisualisation des effets RGB sur les touches."""

    def __init__(self, key_buttons: dict[str, QPushButton]) -> None:
        self._key_buttons = key_buttons
        self._timer = QTimer()
        self._timer.timeout.connect(self._tick)
        self._effect: RgbEffect | None = None
        self._step = 0
        self._phase = 0.0          # pour animations smooth
        self._center: tuple[str, int, int] | None = None

        # Caches géométriques
        self._key_meta: dict[str, tuple[int, int, int]] = {}  # key_id → (row, col, side_idx)
        self._max_row = 1
        self._max_col = 1

        # États internes pour raindrops / heatmap
        self._drops: dict[str, tuple[float, float]] = {}   # key_id → (hue, v 0-1)
        self._heat: dict[str, float] = {}                  # key_id → 0-1

    # ─────────────────────────────────────────────── Public API ──

    def start(self, effect: RgbEffect) -> None:
        """Démarre l'animation selon le type d'effet."""
        self._timer.stop()
        self._effect = effect
        self._step = 0
        self._phase = 0.0
        self._build_key_cache()

        preview = self._get_preview_type()

        if preview in ("solid", "gradient_h", "gradient_v", "two_zone"):
            self._render_frame()
        elif preview in ("breathing", "cycle_all", "cycle_lr", "cycle_ud",
                         "band_v", "pinwheel", "spiral", "cycle_out_in",
                         "raindrops", "heatmap"):
            self._init_stateful(preview)
            self._render_frame()
            self._timer.setInterval(SMOOTH_INTERVAL_MS)
            self._timer.start()
        elif preview == "reactive":
            self._pick_new_center()
            self._timer.setInterval(RIPPLE_INTERVAL_MS)
            self._timer.start()
        elif preview == "ripple":
            self._pick_new_center()
            self._timer.setInterval(RIPPLE_INTERVAL_MS)
            self._timer.start()

    def stop(self) -> None:
        """Arrête le timer et réinitialise les couleurs des touches."""
        self._timer.stop()
        self._reset_keys()

    def update(self, effect: RgbEffect) -> None:
        """Met à jour l'animation sans redémarrer entièrement si possible."""
        prev_type = self._effect.type if self._effect else None
        self._effect = effect
        if effect.type != prev_type:
            self.start(effect)
        elif effect.type == "static":
            self._timer.stop()
            self._apply_static()
        elif not self._timer.isActive():
            self.start(effect)

    def is_active(self) -> bool:
        """Indique si l'animation est en cours."""
        return self._timer.isActive()

    # ─────────────────────────────────────────────── Private helpers ──

    def _get_preview_type(self) -> str:
        if not self._effect:
            return "solid"
        for e in EFFECT_TYPES:
            if e.id == self._effect.type:
                return e.preview
        return "solid"

    def _build_key_cache(self) -> None:
        """Construit le cache géométrique key_id → (row, col, side_idx)."""
        self._key_meta.clear()
        side_map = {"L": 0, "R": 1}
        max_row = 0
        max_col = 0
        for key_id in self._key_buttons:
            try:
                parts = key_id.split("_")
                side_idx = side_map.get(parts[0], 0)
                r = int(parts[1][1:])
                c = int(parts[2][1:])
                self._key_meta[key_id] = (r, c, side_idx)
                max_row = max(max_row, r)
                max_col = max(max_col, c)
            except (IndexError, ValueError):
                pass
        self._max_row = max(max_row, 1)
        self._max_col = max(max_col, 1)

    def _init_stateful(self, preview: str) -> None:
        """Initialise les états pour raindrops / heatmap."""
        if preview == "raindrops":
            self._drops = {k: (random.uniform(0, 360), random.uniform(0.1, 1.0))
                           for k in self._key_buttons}
        elif preview == "heatmap":
            self._heat = {k: random.uniform(0.0, 0.3) for k in self._key_buttons}

    def _tick(self) -> None:
        if not self._effect:
            return
        preview = self._get_preview_type()

        if preview in ("breathing", "cycle_all", "cycle_lr", "cycle_ud",
                       "band_v", "pinwheel", "spiral", "cycle_out_in",
                       "raindrops", "heatmap"):
            self._phase = (self._phase + PHASE_STEP) % 360
            self._render_frame()
        elif preview == "reactive":
            self._tick_reactive()
        elif preview == "ripple":
            self._tick_ripple()

    def _render_frame(self) -> None:
        """Applique la couleur courante à chaque touche selon le type de preview."""
        if not self._effect:
            return
        preview = self._get_preview_type()
        phase = self._phase
        primary_h, primary_s, primary_v = _hex_to_hsv(self._effect.color_primary)
        cr = self._max_row / 2
        cc = self._max_col / 2

        if preview == "solid":
            for btn in self._key_buttons.values():
                btn.setStyleSheet(f"background-color: {self._effect.color_primary};")

        elif preview == "breathing":
            v = (1 - math.cos(phase * math.pi / 180)) / 2
            color = _hsv_to_hex(primary_h, primary_s, v)
            for btn in self._key_buttons.values():
                btn.setStyleSheet(f"background-color: {color};")

        elif preview == "cycle_all":
            color = _hsv_to_hex(phase, 1.0, 1.0)
            for btn in self._key_buttons.values():
                btn.setStyleSheet(f"background-color: {color};")

        elif preview == "cycle_lr":
            total_cols = self._max_col + 1
            for key_id, btn in self._key_buttons.items():
                meta = self._key_meta.get(key_id)
                if meta is None:
                    continue
                r, c, side_idx = meta
                col_total = c + side_idx * total_cols
                hue = (phase + col_total * 360 / (total_cols * 2)) % 360
                btn.setStyleSheet(f"background-color: {_hsv_to_hex(hue, 1.0, 1.0)};")

        elif preview == "cycle_ud":
            for key_id, btn in self._key_buttons.items():
                meta = self._key_meta.get(key_id)
                if meta is None:
                    continue
                r, c, side_idx = meta
                hue = (phase + r * 360 / (self._max_row + 1)) % 360
                btn.setStyleSheet(f"background-color: {_hsv_to_hex(hue, 1.0, 1.0)};")

        elif preview == "gradient_h":
            total_cols = (self._max_col + 1) * 2
            for key_id, btn in self._key_buttons.items():
                meta = self._key_meta.get(key_id)
                if meta is None:
                    continue
                r, c, side_idx = meta
                col_total = c + side_idx * (self._max_col + 1)
                hue = col_total * 240 / total_cols
                btn.setStyleSheet(f"background-color: {_hsv_to_hex(hue, 1.0, 1.0)};")

        elif preview == "gradient_v":
            for key_id, btn in self._key_buttons.items():
                meta = self._key_meta.get(key_id)
                if meta is None:
                    continue
                r, c, side_idx = meta
                hue = r * 240 / (self._max_row + 1)
                btn.setStyleSheet(f"background-color: {_hsv_to_hex(hue, 1.0, 1.0)};")

        elif preview == "band_v":
            band_row = phase * (self._max_row + 1) / 360
            for key_id, btn in self._key_buttons.items():
                meta = self._key_meta.get(key_id)
                if meta is None:
                    continue
                r, c, side_idx = meta
                dist = abs(r - band_row)
                v = max(0.0, 1.0 - dist * 0.5)
                color = _hsv_to_hex(primary_h, primary_s, v)
                btn.setStyleSheet(f"background-color: {color};")

        elif preview == "pinwheel":
            for key_id, btn in self._key_buttons.items():
                meta = self._key_meta.get(key_id)
                if meta is None:
                    continue
                r, c, side_idx = meta
                angle = math.degrees(math.atan2(r - cr, c - cc))
                hue = (angle + phase) % 360
                btn.setStyleSheet(f"background-color: {_hsv_to_hex(hue, 1.0, 1.0)};")

        elif preview == "spiral":
            for key_id, btn in self._key_buttons.items():
                meta = self._key_meta.get(key_id)
                if meta is None:
                    continue
                r, c, side_idx = meta
                angle = math.degrees(math.atan2(r - cr, c - cc))
                dist = math.sqrt((r - cr) ** 2 + (c - cc) ** 2)
                hue = (angle + dist * 20 + phase) % 360
                btn.setStyleSheet(f"background-color: {_hsv_to_hex(hue, 1.0, 1.0)};")

        elif preview == "cycle_out_in":
            max_dist = math.sqrt(cr ** 2 + cc ** 2) + 1
            for key_id, btn in self._key_buttons.items():
                meta = self._key_meta.get(key_id)
                if meta is None:
                    continue
                r, c, side_idx = meta
                dist_edge = min(r, self._max_row - r, c, self._max_col - c)
                hue = (phase + dist_edge * 40) % 360
                btn.setStyleSheet(f"background-color: {_hsv_to_hex(hue, 1.0, 1.0)};")

        elif preview == "raindrops":
            new_drops: dict[str, tuple[float, float]] = {}
            keys = list(self._key_buttons.keys())
            # Fade all drops
            for key_id, (hue, v) in self._drops.items():
                new_v = max(0.0, v - 0.12)
                new_drops[key_id] = (hue, new_v)
            # Add 1-2 new drops
            for _ in range(random.randint(1, 2)):
                kid = random.choice(keys)
                new_drops[kid] = (random.uniform(0, 360), 1.0)
            self._drops = new_drops
            for key_id, btn in self._key_buttons.items():
                hue, v = self._drops.get(key_id, (0.0, 0.0))
                if v < 0.05:
                    btn.setStyleSheet("background-color: #000000;")
                else:
                    btn.setStyleSheet(f"background-color: {_hsv_to_hex(hue, 1.0, v)};")

        elif preview == "heatmap":
            keys = list(self._key_buttons.keys())
            # Cool down
            for key_id in keys:
                self._heat[key_id] = max(0.0, self._heat.get(key_id, 0.0) - 0.03)
            # Heat up random keys
            for _ in range(random.randint(1, 3)):
                kid = random.choice(keys)
                self._heat[kid] = min(1.0, self._heat.get(kid, 0.0) + random.uniform(0.3, 0.7))
            for key_id, btn in self._key_buttons.items():
                heat = self._heat.get(key_id, 0.0)
                hue = 240 - heat * 240
                v = 0.2 + heat * 0.8
                btn.setStyleSheet(f"background-color: {_hsv_to_hex(hue, 1.0, v)};")

        elif preview == "two_zone":
            secondary_color = self._effect.color_secondary
            for key_id, btn in self._key_buttons.items():
                meta = self._key_meta.get(key_id)
                if meta is None:
                    continue
                r, c, side_idx = meta
                if c == 0 or c == self._max_col:
                    btn.setStyleSheet(f"background-color: {secondary_color};")
                else:
                    btn.setStyleSheet(f"background-color: {self._effect.color_primary};")

    # ─────────────────────────────────────────────── Static / Reset ──

    def _apply_static(self) -> None:
        if not self._effect:
            return
        for btn in self._key_buttons.values():
            btn.setStyleSheet(f"background-color: {self._effect.color_primary};")

    def _reset_keys(self) -> None:
        for btn in self._key_buttons.values():
            btn.setStyleSheet("")

    # ─────────────────────────────────────────────── Ripple / Reactive ──

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
            return 999
        return abs(r - cr) + abs(c - cc)

    def _tick_ripple(self) -> None:
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
            if self._center:
                center_id = f"{self._center[0]}_r{self._center[1]}_c{self._center[2]}"
                if center_id in self._key_buttons:
                    self._key_buttons[center_id].setStyleSheet(
                        f"background-color: {self._effect.color_primary};"
                    )
            self._step = 0
        self._step += 1

    def _tick_reactive(self) -> None:
        """Réutilise la logique ripple pour les effets réactifs natifs."""
        self._tick_ripple()
