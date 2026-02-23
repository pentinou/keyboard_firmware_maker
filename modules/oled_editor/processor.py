# modules/oled_editor/processor.py
from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
from PIL import Image, UnidentifiedImageError

logger = logging.getLogger(__name__)

OLED_WIDTH = 64
OLED_HEIGHT = 128


def _convert_frame(frame: Image.Image) -> bytes:
    """Convertit une frame PIL en bitmap 1-bit 64×128px (dithering Floyd-Steinberg).

    Redimensionne en conservant le ratio, centre sur un canvas noir 64×128,
    puis applique le dithering Floyd-Steinberg.
    Retourne 64*128 bytes : 0x00 = noir, 0xFF = blanc (1 byte par pixel).
    """
    # L3 : avertir si l'image est très petite (thumbnail ne fait pas d'upscale)
    if frame.width < 16 or frame.height < 16:
        logger.warning(
            "Image source très petite (%dx%d px) : thumbnail ne fera pas d'upscale — "
            "le rendu OLED sera minuscule",
            frame.width, frame.height,
        )
    # M1 : composite sur fond noir pour les images avec canal alpha
    # Les zones transparentes deviennent noires (fond OLED) plutôt que gris
    if frame.mode in ("RGBA", "LA") or (frame.mode == "P" and "transparency" in frame.info):
        frame_rgba = frame.convert("RGBA")
        black_bg = Image.new("RGBA", frame_rgba.size, (0, 0, 0, 255))
        black_bg.paste(frame_rgba, mask=frame_rgba.split()[3])
        img = black_bg.convert("L")
    else:
        img = frame.convert("L")
    img.thumbnail((OLED_WIDTH, OLED_HEIGHT), Image.Resampling.LANCZOS)
    canvas = Image.new("L", (OLED_WIDTH, OLED_HEIGHT), 0)
    x = (OLED_WIDTH - img.width) // 2
    y = (OLED_HEIGHT - img.height) // 2
    canvas.paste(img, (x, y))
    bw = canvas.convert("1", dither=Image.Dither.FLOYDSTEINBERG)
    arr = np.array(bw, dtype=np.uint8) * 255
    return arr.tobytes()


def convert_image(path: Path) -> list[bytes]:
    """Convertit une image (PNG, BMP, GIF) en liste de frames 1-bit 64×128px.

    - Image statique (PNG, BMP) ou GIF 1 frame → liste à 1 élément
    - GIF multi-frames → liste de N éléments (un bytes par frame)

    Lève OSError si le fichier est inaccessible.
    Lève PIL.UnidentifiedImageError si le format n'est pas reconnu.
    """
    img = Image.open(path)
    try:
        frames: list[bytes] = []
        try:
            while True:
                frames.append(_convert_frame(img))  # L1 : img.copy() inutile
                img.seek(img.tell() + 1)
        except EOFError:
            pass  # fin des frames GIF
        if not frames:
            frames.append(_convert_frame(img))
        logger.info("Image convertie : %s — %d frame(s)", path, len(frames))
        return frames
    finally:
        img.close()  # L2 : fermeture explicite du handle


def get_frame_delays(path: Path) -> list[int]:
    """Retourne la liste des durées inter-frames en ms pour un GIF.

    Pour les images statiques ou GIF 1 frame : retourne [100].
    Applique un minimum de 50ms par frame (éviter animations trop rapides).
    """
    img = Image.open(path)
    try:
        delays: list[int] = []
        try:
            while True:
                delay = img.info.get("duration", 100)
                delays.append(max(int(delay), 50))
                img.seek(img.tell() + 1)
        except EOFError:
            pass
        return delays if delays else [100]
    finally:
        img.close()  # L2 : fermeture explicite du handle


def convert_image_with_delays(path: Path) -> tuple[list[bytes], list[int]]:
    """Convertit une image et retourne (frames, delays_ms) en un seul passage.

    M1 : évite la double ouverture de fichier de convert_image() + get_frame_delays().
    Garantit que len(frames) == len(delays).
    """
    img = Image.open(path)
    try:
        frames: list[bytes] = []
        delays: list[int] = []
        try:
            while True:
                frames.append(_convert_frame(img))
                delay = img.info.get("duration", 100)
                delays.append(max(int(delay), 50))
                img.seek(img.tell() + 1)
        except EOFError:
            pass
        if not frames:
            frames.append(_convert_frame(img))
            delays.append(100)
        logger.info("Image convertie : %s — %d frame(s)", path, len(frames))
        return frames, delays
    finally:
        img.close()
