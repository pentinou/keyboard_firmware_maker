# modules/oled_editor/processor.py
from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
from PIL import Image

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


def composite_side_frame(images: list) -> bytes:
    """Composite les images placées d'une moitié OLED en un buffer 32×128 grayscale.

    Chaque image est placée sur le canvas à `(col * 6, line * 8)` (grille QMK 6×8),
    croppée à sa taille naturelle (`natural_w × natural_h`). L'inversion par image
    est appliquée si présente. Les zones non couvertes restent noires.

    Args:
        images: liste d'`OledImageItem` (typing évité ici pour découpler de
            `models.project_model`). Chaque item doit exposer `frames`, `natural_w`,
            `natural_h`, `col`, `line`, `inverted`.

    Returns:
        4096 octets (`OLED_HEIGHT * OLED_WIDTH`) — un buffer grayscale 0x00/0xFF
        prêt pour conversion LVGL ou QMK ultérieure.
    """
    canvas = np.zeros((OLED_HEIGHT, OLED_WIDTH), dtype=np.uint8)
    for img in images:
        if not img.frames:
            continue
        nat_w = max(0, min(img.natural_w, OLED_WIDTH))
        nat_h = max(0, min(img.natural_h, OLED_HEIGHT))
        if nat_w == 0 or nat_h == 0:
            continue
        frame_arr = np.frombuffer(img.frames[0], dtype=np.uint8).reshape(OLED_HEIGHT, OLED_WIDTH)
        x_off = (OLED_WIDTH - nat_w) // 2  # contenu centré horizontalement par _convert_frame
        content = frame_arr[0:nat_h, x_off:x_off + nat_w]
        if img.inverted:
            content = content ^ 0xFF
        place_x = max(0, img.col * 6)
        place_y = max(0, img.line * 8)
        end_x = min(place_x + nat_w, OLED_WIDTH)
        end_y = min(place_y + nat_h, OLED_HEIGHT)
        h = end_y - place_y
        w = end_x - place_x
        if h > 0 and w > 0:
            canvas[place_y:end_y, place_x:end_x] = content[:h, :w]
    return canvas.tobytes()


def composite_side_frames(images: list) -> tuple[list[bytes], list[int]]:
    """Variante multi-frame de `composite_side_frame` pour les animations Phase 3.

    Toutes les images cyclent en lockstep au rythme de l'animation la plus longue.
    Les images statiques (1 frame) contribuent toujours leur seul frame.

    Args:
        images: liste d'`OledImageItem`. Doit exposer les mêmes attributs que
            pour `composite_side_frame`, plus `delays: list[int]` (ms par frame).

    Returns:
        Tuple `(composite_frames, delays_ms)` :
          - `composite_frames` : liste de bytes de longueur N (≥ 1), chaque entrée
            étant un buffer 32×128 grayscale identique au format de
            `composite_side_frame`.
          - `delays_ms` : liste de N délais en ms entre frames. Récupérés depuis
            la première image multi-frame qui matche la longueur de l'animation,
            sinon `[200] * N` par défaut.

    Si aucune image n'a de frames, retourne `([buffer_noir], [200])`.
    """
    valid = [img for img in images if img.frames]
    if not valid:
        return [bytes([0x00] * (OLED_WIDTH * OLED_HEIGHT))], [200]

    n_frames = max(len(img.frames) for img in valid)
    # Délais : première image multi-frame ayant ≥ n_frames de delays renseignés
    delays: list[int] = [200] * n_frames
    for img in valid:
        if len(img.frames) == n_frames and img.delays:
            src = list(img.delays)
            delays = [src[i] if i < len(src) else (src[-1] if src else 200) for i in range(n_frames)]
            break

    composite_frames: list[bytes] = []
    for step in range(n_frames):
        canvas = np.zeros((OLED_HEIGHT, OLED_WIDTH), dtype=np.uint8)
        for img in valid:
            nat_w = max(0, min(img.natural_w, OLED_WIDTH))
            nat_h = max(0, min(img.natural_h, OLED_HEIGHT))
            if nat_w == 0 or nat_h == 0:
                continue
            frame_idx = step % len(img.frames)
            frame_arr = np.frombuffer(img.frames[frame_idx], dtype=np.uint8).reshape(OLED_HEIGHT, OLED_WIDTH)
            x_off = (OLED_WIDTH - nat_w) // 2
            content = frame_arr[0:nat_h, x_off:x_off + nat_w]
            if img.inverted:
                content = content ^ 0xFF
            place_x = max(0, img.col * 6)
            place_y = max(0, img.line * 8)
            end_x = min(place_x + nat_w, OLED_WIDTH)
            end_y = min(place_y + nat_h, OLED_HEIGHT)
            h = end_y - place_y
            w = end_x - place_x
            if h > 0 and w > 0:
                canvas[place_y:end_y, place_x:end_x] = content[:h, :w]
        composite_frames.append(canvas.tobytes())
    return composite_frames, delays


def composite_side_frames_per_layer(images: list) -> dict[int, tuple[list[bytes], list[int]]]:
    """Variante par-couche de `composite_side_frames` pour Phase 4 (layer-aware).

    Pour chaque couche L où au moins une image est assignée (`img.layer == L`),
    construit un composite incluant toutes les images de la couche L plus toutes
    les images "globales" (`img.layer == -1`). La couche `-1` (default fallback)
    est toujours présente dans le résultat tant qu'au moins une image globale
    est définie ; sinon retourne un seul composite noir.

    Args:
        images: liste d'`OledImageItem`. Chaque item doit exposer `layer: int`,
            en plus des attributs classiques (frames, natural_w/h, col, line, inverted, delays).

    Returns:
        dict `{layer_id: (frames, delays)}` où chaque entrée est le résultat de
        `composite_side_frames()` pour les images sélectionnées de cette couche.
        Toujours au moins une entrée (la couche -1 — fallback). Si aucune image
        n'a `layer != -1`, le dict ne contient que la clé `-1`.
    """
    valid = [img for img in images if img.frames]
    layer_ids: set[int] = {-1}
    for img in valid:
        if img.layer != -1:
            layer_ids.add(img.layer)
    result: dict[int, tuple[list[bytes], list[int]]] = {}
    for layer_id in sorted(layer_ids):
        relevant = [img for img in valid if img.layer == -1 or img.layer == layer_id]
        result[layer_id] = composite_side_frames(relevant)
    return result


def frame_32x128_to_lvgl_128x32(frame_bytes: bytes) -> bytes:
    """Convertit un frame 32×128 grayscale vers LVGL `LV_IMG_CF_INDEXED_1BIT` 128×32.

    Utilisé pour l'OLED ZMK : la dtsi déclare `width=128, height=32` (orientation
    native SSD1306) tandis que l'éditeur KFM travaille en 32×128 (orientation
    perçue par l'utilisateur quand le clavier est monté à la verticale type Sofle).
    On rotate 90° CW au build-time pour matcher le framebuffer LVGL.

    Format de sortie LVGL `LV_IMG_CF_INDEXED_1BIT` :
      - 8 octets de palette : 2 entrées BGRA (`00 00 00 FF` noir + `FF FF FF FF` blanc)
      - 512 octets de données : 1 bit par pixel, MSB-first par octet, row-major
        (128 colonnes / 8 = 16 octets par ligne × 32 lignes = 512 octets)
    Total : 520 octets.

    Args:
        frame_bytes: 4096 octets, 32×128 grayscale, 0x00 = noir / 0xFF = blanc.

    Returns:
        520 octets prêts à être embarqués dans un tableau C `static const uint8_t[]`.
    """
    arr = np.frombuffer(frame_bytes, dtype=np.uint8).reshape(OLED_HEIGHT, OLED_WIDTH)
    # 90° CW : (H, W) → (W, H) avec axes inversés. np.rot90(k=-1) = 90° CW.
    rotated = np.rot90(arr, k=-1)  # shape (32, 128) = (rows, cols) en LVGL
    bits = (rotated > 127).astype(np.uint8)
    packed = np.packbits(bits, axis=-1)  # MSB-first par défaut
    palette = bytes([0x00, 0x00, 0x00, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF])
    return palette + packed.tobytes()


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
