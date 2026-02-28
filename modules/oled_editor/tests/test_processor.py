"""Tests pytest pour modules/oled_editor/processor.py — convert_image."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from PIL import UnidentifiedImageError

from modules.oled_editor.processor import (
    OLED_BUFFER_SIZE, OLED_HEIGHT, OLED_WIDTH,
    convert_image, convert_image_with_delays, frame_to_qmk_bytes, get_frame_delays,
)

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


def test_no_qt_import_in_processor():
    """processor.py ne doit contenir aucun import PySide6/PyQt."""
    source = Path(__file__).parent.parent / "processor.py"
    content = source.read_text(encoding="utf-8")
    assert "PySide6" not in content
    assert "PyQt" not in content
