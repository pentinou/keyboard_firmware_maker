"""Tests pytest-qt pour modules/rgb_editor/effect_preview.py — EffectPreview."""
from __future__ import annotations

import pytest
from models.project_model import RgbEffect
from modules.rgb_editor.effect_preview import EffectPreview


class FakeKeyButton:
    """Stub minimal imitant KeyColorItem pour les tests d'EffectPreview."""

    def __init__(self) -> None:
        self._color = ""

    def set_color(self, hex_color: str) -> None:
        self._color = hex_color

    def color_hex(self) -> str:
        return self._color


@pytest.fixture
def key_buttons(qtbot) -> dict[str, FakeKeyButton]:
    """Grille 3×3 pour les deux côtés (L/R), 18 boutons au total."""
    buttons: dict[str, FakeKeyButton] = {}
    for side in ("L", "R"):
        for r in range(3):
            for c in range(3):
                key_id = f"{side}_r{r}_c{c}"
                buttons[key_id] = FakeKeyButton()
    return buttons


@pytest.fixture
def preview(key_buttons) -> EffectPreview:
    return EffectPreview(key_buttons)


# ─────────────────────────────────────────── Tests statique ──

class TestEffectPreviewStatic:
    def test_start_static_applies_colors(self, preview, key_buttons):
        effect = RgbEffect(type="static", color_primary="#FF0000")
        preview.start(effect)
        for btn in key_buttons.values():
            assert btn.color_hex() == "#FF0000"

    def test_start_static_timer_inactive(self, preview):
        preview.start(RgbEffect(type="static"))
        assert not preview.is_active()

    def test_stop_clears_colors(self, preview, key_buttons):
        preview.start(RgbEffect(type="static", color_primary="#FF0000"))
        preview.stop()
        for btn in key_buttons.values():
            assert btn.color_hex() == "#000000"

    def test_stop_timer_inactive(self, preview):
        preview.start(RgbEffect(type="static"))
        preview.stop()
        assert not preview.is_active()

    def test_update_static_changes_color(self, preview, key_buttons):
        preview.start(RgbEffect(type="static", color_primary="#FF0000"))
        preview.update(RgbEffect(type="static", color_primary="#0000FF"))
        for btn in key_buttons.values():
            assert btn.color_hex() == "#0000FF"

    def test_update_static_timer_stays_inactive(self, preview):
        preview.start(RgbEffect(type="static"))
        preview.update(RgbEffect(type="static", color_primary="#00FF00"))
        assert not preview.is_active()


# ─────────────────────────────────────────── Tests reactive ──

class TestEffectPreviewReactive:
    def test_start_reactive_timer_active(self, preview):
        preview.start(RgbEffect(type="solid_reactive_simple"))
        assert preview.is_active()
        preview.stop()

    def test_stop_reactive_timer_inactive(self, preview):
        preview.start(RgbEffect(type="solid_reactive_simple"))
        preview.stop()
        assert not preview.is_active()

    def test_stop_reactive_clears_colors(self, preview, key_buttons):
        preview.start(RgbEffect(type="solid_reactive_simple"))
        preview.stop()
        for btn in key_buttons.values():
            assert btn.color_hex() == "#000000"

    def test_update_reactive_from_static_starts_timer(self, preview):
        preview.start(RgbEffect(type="static"))
        assert not preview.is_active()
        preview.update(RgbEffect(type="solid_reactive_simple"))
        assert preview.is_active()
        preview.stop()

    def test_update_reactive_keeps_timer_active(self, preview):
        preview.start(RgbEffect(type="solid_reactive_simple"))
        assert preview.is_active()
        # update ne redémarre pas si déjà actif
        preview.update(RgbEffect(type="solid_reactive_simple", color_primary="#00FF00"))
        assert preview.is_active()
        preview.stop()


# ─────────────────────────────────────────── Tests _tick ──

class TestEffectPreviewTick:
    def test_tick_step0_colors_center_key(self, preview, key_buttons):
        """Étape 0 : seule la touche centrale est colorée en primaire."""
        effect = RgbEffect(type="solid_reactive_simple", color_primary="#FF0000")
        preview._effect = effect
        preview._center = ("L", 1, 1)
        preview._step = 0
        preview._tick()
        assert key_buttons["L_r1_c1"].color_hex() == "#FF0000"

    def test_tick_step1_colors_center_and_neighbors(self, preview, key_buttons):
        """Étape 1 : centre en primaire, voisins à distance 1 en secondaire."""
        effect = RgbEffect(type="solid_reactive_simple", color_primary="#FF0000", color_secondary="#0000FF")
        preview._effect = effect
        preview._center = ("L", 1, 1)
        preview._step = 1
        preview._tick()
        assert key_buttons["L_r1_c1"].color_hex() == "#FF0000"
        assert key_buttons["L_r0_c1"].color_hex() == "#0000FF"
        assert key_buttons["L_r1_c0"].color_hex() == "#0000FF"
        assert key_buttons["L_r2_c1"].color_hex() == "#0000FF"
        assert key_buttons["L_r1_c2"].color_hex() == "#0000FF"

    def test_tick_step2_colors_only_neighbors(self, preview, key_buttons):
        """Étape 2 : seuls les voisins à distance 1 gardent la couleur secondaire."""
        effect = RgbEffect(type="solid_reactive_simple", color_secondary="#0000FF")
        preview._effect = effect
        preview._center = ("L", 1, 1)
        preview._step = 2
        preview._tick()
        assert key_buttons["L_r0_c1"].color_hex() == "#0000FF"
        # Le centre n'est pas recoloré (juste reset)
        assert key_buttons["L_r1_c1"].color_hex() != "#0000FF"

    def test_tick_increments_step(self, preview, key_buttons):
        """_tick() doit incrémenter _step."""
        effect = RgbEffect(type="solid_reactive_simple")
        preview._effect = effect
        preview._center = ("L", 1, 1)
        preview._step = 0
        preview._tick()
        assert preview._step == 1

    def test_distance_same_side(self, preview):
        preview._center = ("L", 1, 1)
        assert preview._distance("L_r0_c1") == 1
        assert preview._distance("L_r1_c1") == 0
        assert preview._distance("L_r2_c2") == 2

    def test_distance_other_side_returns_999(self, preview):
        preview._center = ("L", 1, 1)
        assert preview._distance("R_r1_c1") == 999

    def test_tick_step3_colors_new_center_immediately(self, preview, key_buttons):
        """L3 — step 3 colore le nouveau centre (plus de frame vide de 200ms)."""
        effect = RgbEffect(type="solid_reactive_simple", color_primary="#FF0000")
        preview._effect = effect
        preview._center = ("L", 1, 1)
        preview._step = 3
        # Force un centre prévisible
        preview._pick_new_center = lambda: setattr(preview, "_center", ("R", 0, 0))
        preview._tick()
        assert key_buttons["R_r0_c0"].color_hex() == "#FF0000"

    def test_tick_step3_next_step_is_one(self, preview, key_buttons):
        """L3 — après step 3, le prochain step est 1 (center + neighbors)."""
        effect = RgbEffect(type="solid_reactive_simple")
        preview._effect = effect
        preview._center = ("L", 1, 1)
        preview._step = 3
        preview._tick()
        assert preview._step == 1  # 0 (reset interne) + 1 (increment final)


# ─────────────────────────────────────────── Tests robustesse ──

class TestEffectPreviewRobustness:
    def test_pick_new_center_ignores_malformed_key(self):
        """L1 — _pick_new_center ne plante pas sur un key_id malformé."""
        preview = EffectPreview({"bad_key": FakeKeyButton()})
        preview._pick_new_center()  # ne doit pas lever d'exception
        assert preview._center is None

    def test_distance_returns_999_for_malformed_key(self):
        """L1 — _distance retourne 999 pour un key_id malformé."""
        preview = EffectPreview({"bad_key": FakeKeyButton()})
        preview._center = ("L", 1, 1)
        assert preview._distance("bad_key") == 999

    def test_update_reactive_active_new_color_used_in_next_tick(self, preview, key_buttons):
        """L4 — update() reactive actif : la nouvelle couleur est utilisée au prochain _tick()."""
        preview.start(RgbEffect(type="solid_reactive_simple", color_primary="#FF0000"))
        assert preview.is_active()
        preview.update(RgbEffect(type="solid_reactive_simple", color_primary="#00FF00"))
        # Forcer tick step 0 avec centre connu
        preview._step = 0
        preview._center = ("L", 1, 1)
        preview._tick()
        assert key_buttons["L_r1_c1"].color_hex() == "#00FF00"
        preview.stop()
