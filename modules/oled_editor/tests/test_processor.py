"""Tests pytest pour modules/oled_editor/processor.py — convert_image."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pytest
from PIL import UnidentifiedImageError

from modules.oled_editor.processor import (
    OLED_BUFFER_SIZE,
    OLED_HEIGHT,
    OLED_WIDTH,
    composite_side_frame,
    composite_side_frames,
    composite_side_frames_per_layer,
    convert_image,
    convert_image_with_delays,
    frame_32x128_to_lvgl_128x32,
    frame_to_qmk_bytes,
    get_frame_delays,
)


@dataclass
class _FakeImageItem:
    """Stub minimal pour tests de composite_side_frame, évite l'import du modèle complet."""
    frames: list = field(default_factory=list)
    natural_w: int = 32
    natural_h: int = 128
    col: int = 0
    line: int = 0
    inverted: bool = False
    delays: list = field(default_factory=list)
    layer: int = -1

FIXTURES = Path(__file__).parent / "fixtures"


def test_convert_png_returns_one_frame():
    frames = convert_image(FIXTURES / "test_100x100.png")
    assert len(frames) == 1


def test_convert_output_dimensions():
    frames = convert_image(FIXTURES / "test_100x100.png")
    assert len(frames[0]) == OLED_WIDTH * OLED_HEIGHT  # 32 * 128 = 4096 bytes


def test_convert_output_is_binary():
    """La conversion doit produire uniquement des pixels 0 ou 255 (1-bit)."""
    frames = convert_image(FIXTURES / "test_100x100.png")
    arr = np.frombuffer(frames[0], dtype=np.uint8)
    unique_values = set(arr.tolist())
    assert unique_values <= {0, 255}


def test_convert_gif_multi_frame_returns_multiple():
    frames = convert_image(FIXTURES / "test_anim.gif")
    assert len(frames) >= 2


def test_convert_gif_each_frame_correct_size():
    frames = convert_image(FIXTURES / "test_anim.gif")
    for i, frame in enumerate(frames):
        assert len(frame) == OLED_WIDTH * OLED_HEIGHT, f"Frame {i} mauvaise taille"


def test_convert_gif_frames_are_binary():
    frames = convert_image(FIXTURES / "test_anim.gif")
    for frame in frames:
        arr = np.frombuffer(frame, dtype=np.uint8)
        assert set(arr.tolist()) <= {0, 255}


def test_convert_missing_file_raises_oserror():
    with pytest.raises(OSError):
        convert_image(Path("/nonexistent/image.png"))


def test_convert_invalid_format_raises(tmp_path):
    """L1 — doit lever OSError ou UnidentifiedImageError, pas une Exception générique."""
    bad = tmp_path / "bad.txt"
    bad.write_bytes(b"not an image")
    with pytest.raises((OSError, UnidentifiedImageError)):
        convert_image(bad)


def test_get_frame_delays_gif_returns_list():
    delays = get_frame_delays(FIXTURES / "test_anim.gif")
    assert isinstance(delays, list)
    assert len(delays) >= 2


def test_get_frame_delays_gif_all_positive():
    delays = get_frame_delays(FIXTURES / "test_anim.gif")
    assert all(d > 0 for d in delays)


def test_get_frame_delays_gif_minimum_50ms():
    delays = get_frame_delays(FIXTURES / "test_anim.gif")
    assert all(d >= 50 for d in delays)


def test_get_frame_delays_png_returns_default():
    """Pour une image statique, retourner [100] par défaut."""
    delays = get_frame_delays(FIXTURES / "test_100x100.png")
    assert delays == [100]


def test_get_frame_delays_single_frame_gif():
    delays = get_frame_delays(FIXTURES / "test_single_frame.gif")
    assert len(delays) == 1
    assert delays[0] >= 50


def test_convert_rgba_transparent_regions_are_black(tmp_path):
    """L4/M1 — zones transparentes (alpha=0) rendues en noir sur l'OLED."""
    from PIL import Image as PILImage
    # Logo blanc opaque (centre) sur fond entièrement transparent
    rgba_img = PILImage.new("RGBA", (32, 32), (0, 0, 0, 0))       # tout transparent
    rgba_img.paste((255, 255, 255, 255), (8, 8, 24, 24))           # carré blanc opaque
    png_path = tmp_path / "transparent_logo.png"
    rgba_img.save(png_path)
    frames = convert_image(png_path)
    arr = np.frombuffer(frames[0], dtype=np.uint8)
    # Coin (0,0) du canvas = zone transparente → doit être noir
    assert arr[0] == 0, "Zone transparente doit être rendue noire (fond OLED)"
    # Le carré blanc opaque doit être présent quelque part
    assert 255 in arr, "Zone opaque blanche doit être présente"


def test_get_frame_delays_zero_duration_clamped_to_50ms(tmp_path):
    """L3 — frame GIF avec duration=0 → clampé à 50ms minimum."""
    from PIL import Image as PILImage
    gif_path = tmp_path / "zero_dur.gif"
    f1 = PILImage.new("L", (4, 4), 0)
    f2 = PILImage.new("L", (4, 4), 128)
    f1.save(gif_path, save_all=True, append_images=[f2], duration=0, loop=0)
    delays = get_frame_delays(gif_path)
    assert all(d >= 50 for d in delays)


def test_convert_image_with_delays_counts_match():
    """L4/M2 — convert_image_with_delays garantit len(frames) == len(delays)."""
    frames, delays = convert_image_with_delays(FIXTURES / "test_anim.gif")
    assert len(frames) == len(delays)
    assert len(frames) >= 2


def test_convert_image_with_delays_png_single():
    """L4 — PNG → 1 frame, 1 delay >= 50ms."""
    frames, delays = convert_image_with_delays(FIXTURES / "test_100x100.png")
    assert len(frames) == 1
    assert len(delays) == 1
    assert delays[0] >= 50
    assert len(frames[0]) == OLED_WIDTH * OLED_HEIGHT


class TestFrameToQmkBytes:
    def test_output_size_is_512(self):
        """frame_to_qmk_bytes retourne exactement 512 octets (32×16 pages)."""
        frame = bytes(4096)
        result = frame_to_qmk_bytes(frame)
        assert len(result) == OLED_BUFFER_SIZE == 512

    def test_all_black_frame_gives_zero_bytes(self):
        """Frame entièrement noire (0x00) → tous les bits à 0 → 512 × 0x00."""
        frame = bytes([0x00] * 4096)
        result = frame_to_qmk_bytes(frame)
        assert all(b == 0x00 for b in result)

    def test_all_white_frame_gives_ff_bytes(self):
        """Frame entièrement blanche (0xFF) → tous les bits à 1 → 512 × 0xFF."""
        frame = bytes([0xFF] * 4096)
        result = frame_to_qmk_bytes(frame)
        assert all(b == 0xFF for b in result)

    def test_single_pixel_bit_packing(self):
        """Un seul pixel blanc en (col=0, row=0) → bit 0 du premier octet = 1."""
        frame = bytearray([0x00] * 4096)
        frame[0 * OLED_WIDTH + 0] = 0xFF  # pixel (row=0, col=0) = blanc
        result = frame_to_qmk_bytes(bytes(frame))
        # Page 0, col 0 = octet 0 ; bit 0 (poids faible) doit être 1
        assert result[0] & 0x01 == 0x01

    def test_convert_and_pack_roundtrip(self):
        """Convertir une image réelle puis packer → 512 octets valides."""
        frames = convert_image(FIXTURES / "test_100x100.png")
        result = frame_to_qmk_bytes(frames[0])
        assert len(result) == 512
        # Tous les octets sont dans la plage uint8
        assert all(0 <= b <= 255 for b in result)


class TestCompositeSideFrame:
    """Tests de composite_side_frame (compositing build-time pour ZMK custom OLED)."""

    def test_empty_list_gives_black_frame(self):
        result = composite_side_frame([])
        assert len(result) == OLED_WIDTH * OLED_HEIGHT
        assert all(b == 0x00 for b in result)

    def test_image_without_frames_is_skipped(self):
        item = _FakeImageItem(frames=[])
        result = composite_side_frame([item])
        assert all(b == 0x00 for b in result)

    def test_full_size_image_at_origin(self):
        """Image 32×128 placée à (0, 0) doit occuper tout le canvas."""
        white = bytes([0xFF] * (OLED_WIDTH * OLED_HEIGHT))
        item = _FakeImageItem(
            frames=[white], natural_w=OLED_WIDTH, natural_h=OLED_HEIGHT, col=0, line=0,
        )
        result = composite_side_frame([item])
        assert all(b == 0xFF for b in result)

    def test_image_inversion_applied(self):
        """Item avec inverted=True doit produire un canvas blanc à partir d'un frame noir."""
        black = bytes([0x00] * (OLED_WIDTH * OLED_HEIGHT))
        item = _FakeImageItem(
            frames=[black], natural_w=OLED_WIDTH, natural_h=OLED_HEIGHT,
            col=0, line=0, inverted=True,
        )
        result = composite_side_frame([item])
        assert all(b == 0xFF for b in result)

    def test_smaller_image_centered_then_placed_at_offset(self):
        """Image 16×16 dans un frame 32×128 (centrée à x=8) replacée à (col=2, line=10).

        Vérifie que le crop natural + placement (col*6, line*8) fonctionne.
        """
        # Construire un frame avec un carré 16×16 blanc centré à x=8 (32-16)/2
        frame = bytearray([0x00] * (OLED_WIDTH * OLED_HEIGHT))
        for y in range(16):
            for x in range(8, 24):
                frame[y * OLED_WIDTH + x] = 0xFF
        item = _FakeImageItem(
            frames=[bytes(frame)], natural_w=16, natural_h=16, col=2, line=10,
        )
        result = composite_side_frame([item])
        arr = np.frombuffer(result, dtype=np.uint8).reshape(OLED_HEIGHT, OLED_WIDTH)
        # Doit apparaître à place_x=12 (col*6), place_y=80 (line*8) sur 16×16 px
        assert arr[80, 12] == 0xFF
        assert arr[95, 27] == 0xFF
        # Hors zone : noir
        assert arr[0, 0] == 0x00
        assert arr[80, 11] == 0x00


class TestCompositeSideFramesAnimated:
    """Phase 3 — composite_side_frames : multi-frame compositing pour animations LVGL."""

    def test_empty_returns_one_black_frame(self):
        frames, delays = composite_side_frames([])
        assert len(frames) == 1
        assert len(delays) == 1
        assert all(b == 0x00 for b in frames[0])

    def test_single_static_image_returns_one_frame(self):
        white = bytes([0xFF] * (OLED_WIDTH * OLED_HEIGHT))
        item = _FakeImageItem(frames=[white], natural_w=OLED_WIDTH, natural_h=OLED_HEIGHT)
        frames, delays = composite_side_frames([item])
        assert len(frames) == 1
        assert len(delays) == 1
        assert all(b == 0xFF for b in frames[0])

    def test_multi_frame_image_returns_n_frames(self):
        """Image avec 3 frames distincts → 3 composites distincts."""
        f0 = bytes([0x00] * (OLED_WIDTH * OLED_HEIGHT))
        f1 = bytes([0xFF] * (OLED_WIDTH * OLED_HEIGHT))
        f2 = bytes([0x80] * (OLED_WIDTH * OLED_HEIGHT))
        item = _FakeImageItem(
            frames=[f0, f1, f2], natural_w=OLED_WIDTH, natural_h=OLED_HEIGHT,
            delays=[100, 150, 200],
        )
        frames, delays = composite_side_frames([item])
        assert len(frames) == 3
        assert delays == [100, 150, 200]
        assert all(b == 0x00 for b in frames[0])
        assert all(b == 0xFF for b in frames[1])
        assert all(b == 0x80 for b in frames[2])

    def test_multi_frame_default_delays(self):
        """Image multi-frame sans delays renseignés → 200 ms par défaut."""
        f0 = bytes([0xFF] * (OLED_WIDTH * OLED_HEIGHT))
        item = _FakeImageItem(
            frames=[f0, f0, f0], natural_w=OLED_WIDTH, natural_h=OLED_HEIGHT,
            delays=[],
        )
        _, delays = composite_side_frames([item])
        assert delays == [200, 200, 200]

    def test_lockstep_cycle_shorter_image(self):
        """Image A: 2 frames, image B: 3 frames → 3 composites (longueur de B).

        À chaque step, A cycle modulo 2 (donc 0, 1, 0) et B cycle 0, 1, 2.
        """
        a0 = bytes([0xAA] * (OLED_WIDTH * OLED_HEIGHT))
        a1 = bytes([0xBB] * (OLED_WIDTH * OLED_HEIGHT))
        # B sera placé en (0, 0) avec natural 16×16, donc A est dominant à pixel 0
        b0 = bytes([0x00] * (OLED_WIDTH * OLED_HEIGHT))
        b1 = bytes([0x11] * (OLED_WIDTH * OLED_HEIGHT))
        b2 = bytes([0x22] * (OLED_WIDTH * OLED_HEIGHT))
        # A est full-canvas (32×128), B est 32×128 mais placé après A → l'écrase
        # On teste seulement le cyclage en regardant le pixel (0, 0) de chaque step.
        item_a = _FakeImageItem(frames=[a0, a1], natural_w=OLED_WIDTH, natural_h=OLED_HEIGHT)
        item_b = _FakeImageItem(frames=[b0, b1, b2], natural_w=OLED_WIDTH, natural_h=OLED_HEIGHT)
        frames, _ = composite_side_frames([item_a, item_b])
        assert len(frames) == 3
        # Step 0 : B0 écrase A0 → 0x00
        assert frames[0][0] == 0x00
        # Step 1 : B1 écrase A1 → 0x11
        assert frames[1][0] == 0x11
        # Step 2 : B2 écrase A0 (A cycle 2 % 2 = 0) → 0x22
        assert frames[2][0] == 0x22


class TestCompositeSideFramesPerLayer:
    """Phase 4 — composite_side_frames_per_layer : compositing par-couche keymap."""

    def test_empty_returns_default_only(self):
        result = composite_side_frames_per_layer([])
        assert list(result.keys()) == [-1]
        frames, delays = result[-1]
        assert len(frames) == 1
        assert all(b == 0x00 for b in frames[0])

    def test_only_global_images_returns_default_only(self):
        """Toutes les images sont layer=-1 → seule entrée -1 dans le résultat."""
        white = bytes([0xFF] * (OLED_WIDTH * OLED_HEIGHT))
        items = [
            _FakeImageItem(frames=[white], natural_w=OLED_WIDTH, natural_h=OLED_HEIGHT, layer=-1),
        ]
        result = composite_side_frames_per_layer(items)
        assert list(result.keys()) == [-1]

    def test_layer_assigned_creates_per_layer_entry(self):
        """Image layer=0 → résultat contient -1 (default) ET 0."""
        white = bytes([0xFF] * (OLED_WIDTH * OLED_HEIGHT))
        items = [
            _FakeImageItem(frames=[white], natural_w=OLED_WIDTH, natural_h=OLED_HEIGHT, layer=0),
        ]
        result = composite_side_frames_per_layer(items)
        assert sorted(result.keys()) == [-1, 0]

    def test_global_image_in_all_layer_composites(self):
        """Image layer=-1 doit apparaître dans la composition des deux couches.

        Image A globale (layer=-1) blanche full canvas, image B layer=0 noire full canvas.
        Layer 0 composite = A + B = B écrase A → noir.
        Layer -1 composite = A seule → blanc.
        """
        white = bytes([0xFF] * (OLED_WIDTH * OLED_HEIGHT))
        black = bytes([0x00] * (OLED_WIDTH * OLED_HEIGHT))
        items = [
            _FakeImageItem(frames=[white], natural_w=OLED_WIDTH, natural_h=OLED_HEIGHT, layer=-1),
            _FakeImageItem(frames=[black], natural_w=OLED_WIDTH, natural_h=OLED_HEIGHT, layer=0),
        ]
        result = composite_side_frames_per_layer(items)
        # Default (-1) : seulement l'image globale
        default_frames, _ = result[-1]
        assert all(b == 0xFF for b in default_frames[0])
        # Layer 0 : globale + spécifique → spécifique noire écrase
        layer0_frames, _ = result[0]
        assert all(b == 0x00 for b in layer0_frames[0])

    def test_multiple_layers_distinct_composites(self):
        """3 layers distincts donnent 3 composites distincts (+ default)."""
        f0 = bytes([0xAA] * (OLED_WIDTH * OLED_HEIGHT))
        f1 = bytes([0xBB] * (OLED_WIDTH * OLED_HEIGHT))
        f2 = bytes([0xCC] * (OLED_WIDTH * OLED_HEIGHT))
        items = [
            _FakeImageItem(frames=[f0], natural_w=OLED_WIDTH, natural_h=OLED_HEIGHT, layer=0),
            _FakeImageItem(frames=[f1], natural_w=OLED_WIDTH, natural_h=OLED_HEIGHT, layer=1),
            _FakeImageItem(frames=[f2], natural_w=OLED_WIDTH, natural_h=OLED_HEIGHT, layer=2),
        ]
        result = composite_side_frames_per_layer(items)
        assert sorted(result.keys()) == [-1, 0, 1, 2]
        assert result[0][0][0][0] == 0xAA
        assert result[1][0][0][0] == 0xBB
        assert result[2][0][0][0] == 0xCC


class TestFrameToLvgl:
    """Tests de frame_32x128_to_lvgl_128x32 (conversion LVGL INDEXED_1BIT)."""

    def test_output_size_is_520_bytes(self):
        """8 octets palette + 512 octets data = 520 octets."""
        frame = bytes([0x00] * (OLED_WIDTH * OLED_HEIGHT))
        result = frame_32x128_to_lvgl_128x32(frame)
        assert len(result) == 8 + 512

    def test_palette_is_black_white_bgra(self):
        frame = bytes([0x00] * (OLED_WIDTH * OLED_HEIGHT))
        result = frame_32x128_to_lvgl_128x32(frame)
        # Palette : 2 entrées BGRA (4 octets chacune)
        assert result[0:4] == bytes([0x00, 0x00, 0x00, 0xFF])  # noir opaque
        assert result[4:8] == bytes([0xFF, 0xFF, 0xFF, 0xFF])  # blanc opaque

    def test_all_black_frame_data_is_zero(self):
        frame = bytes([0x00] * (OLED_WIDTH * OLED_HEIGHT))
        result = frame_32x128_to_lvgl_128x32(frame)
        assert all(b == 0x00 for b in result[8:])

    def test_all_white_frame_data_is_ff(self):
        frame = bytes([0xFF] * (OLED_WIDTH * OLED_HEIGHT))
        result = frame_32x128_to_lvgl_128x32(frame)
        assert all(b == 0xFF for b in result[8:])

    def test_rotation_90cw_maps_topleft_correctly(self):
        """Pixel blanc en (row=0, col=0) du frame 32×128 → après 90° CW → (row=0, col=127) en 128×32.

        Le pixel le plus à gauche en haut de l'éditeur devient le pixel le plus
        à droite en haut sur l'OLED LVGL native (rotation horaire).
        """
        frame = bytearray([0x00] * (OLED_WIDTH * OLED_HEIGHT))
        frame[0] = 0xFF  # pixel (y=0, x=0)
        result = frame_32x128_to_lvgl_128x32(bytes(frame))
        data = result[8:]
        # 128×32 : 16 octets par ligne (128 cols / 8). Ligne 0, col 127 = octet 15 du row 0,
        # bit 0 (LSB du dernier octet, MSB-first donc bit 0 = position col 127 % 8 = 7).
        # Attention : np.packbits MSB-first signifie bit 7 = col 0 du chunk.
        # Col 127 dans la ligne = chunk 15 (cols 120-127), position dans le chunk = 7,
        # donc bit 0 (MSB-first → bit (7-7)=0 du chunk).
        assert data[15] == 0x01  # row 0, col 127 → MSB-first byte 15 bit LSB

    """processor.py ne doit contenir aucun import PySide6/PyQt."""
    source = Path(__file__).parent.parent / "processor.py"
    content = source.read_text(encoding="utf-8")
    assert "PySide6" not in content
    assert "PyQt" not in content
