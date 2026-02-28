# modules/oled_editor/processor.py
from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
from PIL import Image, UnidentifiedImageError

logger = logging.getLogger(__name__)

OLED_WIDTH = 32
OLED_HEIGHT = 128
OLED_BUFFER_SIZE = OLED_WIDTH * (OLED_HEIGHT // 8)  # 512 octets pour oled_write_raw_P()


def frame_to_qmk_bytes(frame_bytes: bytes) -> bytes:
    """Convertit un frame grayscale 32×128 (4096 octets) en format QMK OLED.

    QMK / SSD1306 page-addressing : 16 pages × 32 colonnes = 512 octets.
    Chaque octet encode 8 pixels verticaux d'une colonne :
      bit 0 = pixel le plus haut de la page, bit 7 = le plus bas.

    Ce format est celui attendu par oled_write_raw_P().
    """
    arr = np.frombuffer(frame_bytes, dtype=np.uint8).reshape(OLED_HEIGHT, OLED_WIDTH)
    pages = OLED_HEIGHT // 8  # 16
    # Reshape en (16 pages, 8 bits par page, 32 colonnes)
    bits = (arr.reshape(pages, 8, OLED_WIDTH) > 127).astype(np.uint32)
    weights = np.array([1, 2, 4, 8, 16, 32, 64, 128], dtype=np.uint32)
    packed = (bits * weights[np.newaxis, :, np.newaxis]).sum(axis=1).astype(np.uint8)
    return packed.tobytes()  # 512 octets en ordre row-major (page, col)


def _convert_frame(frame: Image.Image) -> bytes:
    """Convertit une frame PIL en bitmap 1-bit 32×128px (dithering Floyd-Steinberg).

    Redimensionne en conservant le ratio, centre sur un canvas noir 32×128,
    puis applique le dithering Floyd-Steinberg.
    Retourne 32*128 bytes : 0x00 = noir, 0xFF = blanc (1 byte par pixel).
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
    y = 0  # top-aligned
    canvas.paste(img, (x, y))
    bw = canvas.convert("1", dither=Image.Dither.FLOYDSTEINBERG)
    arr = np.array(bw, dtype=np.uint8) * 255
    return arr.tobytes()


def convert_image(path: Path) -> list[bytes]:
    """Convertit une image (PNG, BMP, GIF) en liste de frames 1-bit 32×128px.

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


def rotate_frame_90cw(frame_bytes: bytes) -> bytes:
    """Applique une rotation 90° horaire sur un frame OLED 32×128.

    Le résultat est redimensionné pour tenir dans 32×128 (déformation possible).
    """
    arr = np.frombuffer(frame_bytes, dtype=np.uint8).reshape(OLED_HEIGHT, OLED_WIDTH)
    img = Image.fromarray(arr, mode="L")
    # rotate(-90) = CW 90°, expand=True → résultat: 128×32
    rotated = img.rotate(-90, expand=True)
    # Redimensionner pour revenir à 32×128
    final = rotated.resize((OLED_WIDTH, OLED_HEIGHT), Image.Resampling.LANCZOS)
    return np.array(final, dtype=np.uint8).tobytes()


def convert_image_natural(path: Path) -> tuple[list[bytes], list[int], int, int]:
    """Convertit une image et retourne (frames, delays_ms, natural_w, natural_h).

    natural_w / natural_h : dimensions du thumbnail OLED (en pixels OLED, avant mise à l'échelle widget).
    Le thumbnail est centré dans le frame 32×128 ; ces valeurs permettent
    de connaître la zone de contenu réelle pour l'affichage et le hit-test.
    """
    img = Image.open(path)
    try:
        frames: list[bytes] = []
        delays: list[int] = []
        natural_w, natural_h = OLED_WIDTH, OLED_HEIGHT
        first = True
        try:
            while True:
                # Compute natural size from the thumbnail step (before centering)
                tmp = img.copy()
                tmp.thumbnail((OLED_WIDTH, OLED_HEIGHT), Image.Resampling.LANCZOS)
                if first:
                    natural_w, natural_h = tmp.width, tmp.height
                    first = False
                frames.append(_convert_frame(img))
                delay = img.info.get("duration", 100)
                delays.append(max(int(delay), 50))
                img.seek(img.tell() + 1)
        except EOFError:
            pass
        if not frames:
            tmp = img.copy()
            tmp.thumbnail((OLED_WIDTH, OLED_HEIGHT), Image.Resampling.LANCZOS)
            natural_w, natural_h = tmp.width, tmp.height
            frames.append(_convert_frame(img))
            delays.append(100)
        logger.info("Image convertie (natural) : %s — %d frame(s) %dx%d", path, len(frames), natural_w, natural_h)
        return frames, delays, natural_w, natural_h
    finally:
        img.close()


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
