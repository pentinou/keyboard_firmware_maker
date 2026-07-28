"""wiring_scene — Rendu statique du schéma de câblage PCB.

Dessine un diagramme de connectique montrant :
- Le MCU (composant DIP avec pins étiquetés)
- Les touches du clavier (rectangles colorés par row/col)
- Les lignes de câblage row → pin MCU (palette chaude)
- Les lignes de câblage col → pin MCU (palette froide)
- L'OLED (si activé) avec ses fils I2C
- L'encodeur (si activé) avec ses fils A/B
- Une légende couleur en bas

Module pur Qt sans logique métier — testable avec un QApplication minimal.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QPen
from PySide6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsLineItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
)

from modules.keyboard_editor.kle_parser import KleKey

# ── Constantes de rendu ────────────────────────────────────────────────────────

UNIT_PX = 30  # pixels par unité clavier (identique à _PREVIEW_PX)

MCU_BODY_W = 130  # largeur corps MCU en px
PIN_PITCH = 18  # espacement vertical entre pins
PIN_STUB_W = 20  # longueur du trait de pin
PIN_STUB_H = 10  # hauteur visuelle du stub
MCU_TOP_MARGIN = 10  # marge au-dessus du MCU
MCU_KEY_GAP = 60  # espace entre MCU et touches

CHANNEL_SPACING = 4  # écart entre fils parallèles dans le bus
WIRE_WIDTH = 1.5

# Couleurs du MCU
MCU_BODY_COLOR = QColor("#3C3C3C")
MCU_BODY_BORDER = QColor("#888888")
MCU_PIN_COLOR = QColor("#C0C0C0")
MCU_NOTCH_COLOR = QColor("#666666")

# Couleurs des touches
KEY_FILL = QColor("#3A3A4A")
KEY_BORDER = QColor("#1C3A5E")

# Palettes de couleurs pour les fils
ROW_COLORS = [
    QColor("#E74C3C"), QColor("#E67E22"), QColor("#F1C40F"),
    QColor("#E84393"), QColor("#D35400"), QColor("#FF6B6B"),
    QColor("#FFA07A"), QColor("#FF4757"),
]
COL_COLORS = [
    QColor("#2ECC71"), QColor("#3498DB"), QColor("#1ABC9C"),
    QColor("#9B59B6"), QColor("#00CED1"), QColor("#6C5CE7"),
    QColor("#48DBFB"), QColor("#0ABDE3"),
]

OLED_COLOR = QColor("#7B52C8")
ENCODER_COLOR = QColor("#2E8C6A")
SERIAL_COLOR = QColor("#95A5A6")
WS2812_COLOR = QColor("#F39C12")

BG_COLOR = QColor("#1E1E1E")


@dataclass
class WiringData:
    """Données nécessaires pour construire le schéma de câblage."""

    keys: list[KleKey] = field(default_factory=list)
    row_pins: list[str] = field(default_factory=list)
    col_pins: list[str] = field(default_factory=list)
    serial_tx: str = ""
    ws2812: str = ""
    has_oled: bool = False
    has_encoder: bool = False
    has_rgb: bool = False
    split: bool = False
    encoder_a: str = ""
    encoder_b: str = ""


def build_wiring_scene(data: WiringData) -> QGraphicsScene:
    """Construit et retourne une QGraphicsScene avec le schéma de câblage."""
    scene = QGraphicsScene()
    scene.setBackgroundBrush(QBrush(BG_COLOR))

    if not data.keys:
        _draw_empty_message(scene)
        return scene

    # ── Calculer les bounds des touches ────────────────────────────────
    keys_min_x = min(k.x for k in data.keys)
    keys_min_y = min(k.y for k in data.keys)
    keys_max_x = max(k.x + k.w for k in data.keys)
    keys_max_y = max(k.y + k.h for k in data.keys)
    keys_w_px = (keys_max_x - keys_min_x) * UNIT_PX
    keys_h_px = (keys_max_y - keys_min_y) * UNIT_PX

    # ── Positionner le MCU centré au-dessus des touches ────────────────
    n_left = max(len(data.row_pins), 1)
    n_right = max(len(data.col_pins), 1)
    n_extra_left = (1 if data.serial_tx else 0) + (1 if data.has_oled else 0) + (1 if data.has_oled else 0)
    n_extra_right = (1 if data.ws2812 else 0) + (1 if data.encoder_a else 0) + (1 if data.encoder_b else 0)
    mcu_pins_left = n_left + n_extra_left
    mcu_pins_right = n_right + n_extra_right
    mcu_h = max(mcu_pins_left, mcu_pins_right) * PIN_PITCH + 20

    keys_offset_x = 0.0
    keys_offset_y = MCU_TOP_MARGIN + mcu_h + MCU_KEY_GAP

    mcu_x = keys_offset_x + (keys_w_px - MCU_BODY_W) / 2
    mcu_y = MCU_TOP_MARGIN

    # ── Dessiner les composants ────────────────────────────────────────
    pin_points = _draw_mcu(scene, mcu_x, mcu_y, mcu_h, data)
    key_rects = _draw_keys(scene, data.keys, keys_offset_x, keys_offset_y, keys_min_x, keys_min_y)

    # ── Câblage rows (MCU gauche → touches) ────────────────────────────
    _draw_row_wires(scene, pin_points, key_rects, data)

    # ── Câblage cols (MCU droite → touches) ─────────────────────────────
    _draw_col_wires(scene, pin_points, key_rects, data, keys_offset_y + keys_h_px)

    # ── Périphériques ──────────────────────────────────────────────────
    if data.has_oled:
        oled_x = mcu_x - 100
        oled_y = mcu_y + 10
        _draw_oled(scene, oled_x, oled_y, pin_points)

    if data.has_encoder and (data.encoder_a or data.encoder_b):
        enc_x = mcu_x + MCU_BODY_W + PIN_STUB_W + 60
        enc_y = mcu_y + 10
        _draw_encoder(scene, enc_x, enc_y, pin_points, data)

    # ── Légende ────────────────────────────────────────────────────────
    legend_y = keys_offset_y + keys_h_px + 30
    _draw_legend(scene, keys_offset_x, legend_y, data)

    return scene


# ── Dessin du MCU ──────────────────────────────────────────────────────────────


def _draw_mcu(
    scene: QGraphicsScene,
    x: float, y: float, h: float,
    data: WiringData,
) -> dict[str, QPointF]:
    """Dessine le MCU en style DIP et retourne les points de connexion des pins."""
    pin_points: dict[str, QPointF] = {}

    # Corps du MCU
    body = QGraphicsRectItem(x, y, MCU_BODY_W, h)
    body.setBrush(QBrush(MCU_BODY_COLOR))
    body.setPen(QPen(MCU_BODY_BORDER, 2))
    body.setZValue(10)
    scene.addItem(body)

    # Encoche en haut (demi-cercle)
    notch_r = 8
    notch = QGraphicsEllipseItem(
        x + MCU_BODY_W / 2 - notch_r, y - notch_r,
        notch_r * 2, notch_r * 2,
    )
    notch.setBrush(QBrush(MCU_NOTCH_COLOR))
    notch.setPen(QPen(MCU_BODY_BORDER, 1))
    notch.setZValue(11)
    scene.addItem(notch)

    # Label MCU
    mcu_label = QGraphicsSimpleTextItem("MCU")
    mcu_label.setFont(_bold_font(10))
    mcu_label.setBrush(QBrush(QColor("#FFFFFF")))
    mcu_label.setPos(x + MCU_BODY_W / 2 - 15, y + 5)
    mcu_label.setZValue(12)
    scene.addItem(mcu_label)

    # ── Pins gauche : rows + spéciaux ─────────────────────────────────
    left_pins: list[tuple[str, QColor]] = []
    for i, rp in enumerate(data.row_pins):
        left_pins.append((rp, _row_color(i)))
    if data.has_oled:
        left_pins.append(("SDA", OLED_COLOR))
        left_pins.append(("SCL", OLED_COLOR))
    if data.serial_tx:
        left_pins.append((data.serial_tx + " (TX)", SERIAL_COLOR))

    pin_y_start = y + 25
    for i, (label, color) in enumerate(left_pins):
        py = pin_y_start + i * PIN_PITCH
        # Stub de pin (ligne)
        stub = QGraphicsLineItem(x - PIN_STUB_W, py, x, py)
        stub.setPen(QPen(MCU_PIN_COLOR, 2))
        stub.setZValue(10)
        scene.addItem(stub)
        # Point de connexion = extrémité gauche du stub
        pin_points[label] = QPointF(x - PIN_STUB_W, py)
        # Petit carré sur le bord du MCU
        dot = QGraphicsRectItem(x - 3, py - 3, 6, 6)
        dot.setBrush(QBrush(color))
        dot.setPen(QPen(Qt.PenStyle.NoPen))
        dot.setZValue(11)
        scene.addItem(dot)
        # Label du pin
        txt = QGraphicsSimpleTextItem(label)
        txt.setFont(_font(7))
        txt.setBrush(QBrush(color))
        txt.setPos(x - PIN_STUB_W - _text_width(label, 7) - 4, py - 7)
        txt.setZValue(12)
        scene.addItem(txt)

    # ── Pins droite : cols + spéciaux ─────────────────────────────────
    right_pins: list[tuple[str, QColor]] = []
    for i, cp in enumerate(data.col_pins):
        right_pins.append((cp, _col_color(i)))
    if data.encoder_a:
        right_pins.append((data.encoder_a + " (A)", ENCODER_COLOR))
    if data.encoder_b:
        right_pins.append((data.encoder_b + " (B)", ENCODER_COLOR))
    if data.ws2812:
        right_pins.append((data.ws2812 + " (WS)", WS2812_COLOR))

    for i, (label, color) in enumerate(right_pins):
        py = pin_y_start + i * PIN_PITCH
        rx = x + MCU_BODY_W
        stub = QGraphicsLineItem(rx, py, rx + PIN_STUB_W, py)
        stub.setPen(QPen(MCU_PIN_COLOR, 2))
        stub.setZValue(10)
        scene.addItem(stub)
        pin_points[label] = QPointF(rx + PIN_STUB_W, py)
        dot = QGraphicsRectItem(rx - 3, py - 3, 6, 6)
        dot.setBrush(QBrush(color))
        dot.setPen(QPen(Qt.PenStyle.NoPen))
        dot.setZValue(11)
        scene.addItem(dot)
        txt = QGraphicsSimpleTextItem(label)
        txt.setFont(_font(7))
        txt.setBrush(QBrush(color))
        txt.setPos(rx + PIN_STUB_W + 4, py - 7)
        txt.setZValue(12)
        scene.addItem(txt)

    return pin_points


# ── Dessin des touches ─────────────────────────────────────────────────────────


def _draw_keys(
    scene: QGraphicsScene,
    keys: list[KleKey],
    x_off: float, y_off: float,
    min_x: float, min_y: float,
) -> dict[tuple[int, int], QRectF]:
    """Dessine les touches et retourne un mapping (row,col) → rect en coords scène."""
    key_rects: dict[tuple[int, int], QRectF] = {}
    font = _font(7)

    for key in keys:
        px = (key.x - min_x) * UNIT_PX + x_off
        py = (key.y - min_y) * UNIT_PX + y_off
        pw = key.w * UNIT_PX - 2
        ph = key.h * UNIT_PX - 2

        # Couleur de fond : teinte basée sur la row
        if key.row >= 0:
            base_color = _row_color(key.row)
            fill = QColor(base_color)
            fill.setAlpha(40)
        else:
            fill = KEY_FILL

        rect = QGraphicsRectItem(px, py, pw, ph)
        rect.setBrush(QBrush(fill))
        rect.setPen(QPen(KEY_BORDER, 1))
        rect.setZValue(5)

        if key.r != 0.0:
            rect.setTransformOriginPoint(pw / 2, ph / 2)
            rect.setRotation(key.r)

        scene.addItem(rect)

        # Label R{row}C{col}
        label = f"R{key.row}C{key.col}" if key.row >= 0 else "?"
        txt = QGraphicsSimpleTextItem(label)
        txt.setFont(font)
        txt.setBrush(QBrush(QColor("#DDDDDD")))
        txt.setPos(px + 2, py + 1)
        txt.setZValue(6)
        scene.addItem(txt)

        if key.row >= 0 and key.col >= 0:
            scene_rect = QRectF(px, py, pw, ph)
            # Stocker toutes les touches de cette position
            if (key.row, key.col) not in key_rects:
                key_rects[(key.row, key.col)] = scene_rect

    return key_rects


# ── Câblage rows ───────────────────────────────────────────────────────────────


def _draw_row_wires(
    scene: QGraphicsScene,
    pin_points: dict[str, QPointF],
    key_rects: dict[tuple[int, int], QRectF],
    data: WiringData,
) -> None:
    """Dessine les fils reliant les pins row du MCU aux touches correspondantes."""
    if not data.row_pins:
        return

    # Trouver toutes les rows utilisées
    rows_used: dict[int, list[QRectF]] = {}
    for (r, c), rect in key_rects.items():
        rows_used.setdefault(r, []).append(rect)

    for row_idx, pin_name in enumerate(data.row_pins):
        if pin_name not in pin_points:
            continue
        rects = rows_used.get(row_idx, [])
        if not rects:
            continue

        color = _row_color(row_idx)
        pen = QPen(color, WIRE_WIDTH)
        pen.setCosmetic(True)
        pin_pt = pin_points[pin_name]

        # Bus vertical : descend du pin vers le haut des touches
        # Chaque row a un canal décalé pour éviter le chevauchement
        bus_x = pin_pt.x() - row_idx * CHANNEL_SPACING

        # Ligne horizontale : pin → bus_x
        _add_line(scene, pin_pt.x(), pin_pt.y(), bus_x, pin_pt.y(), pen)

        # Trouver le Y le plus haut des touches de cette row
        min_key_y = min(r.top() for r in rects)
        # Ligne verticale : descend dans le bus jusqu'au niveau des touches
        target_y = min_key_y + PIN_STUB_H / 2
        _add_line(scene, bus_x, pin_pt.y(), bus_x, target_y, pen)

        # Pour chaque touche de cette row, trait horizontal vers le bord gauche
        for kr in sorted(rects, key=lambda r: r.left()):
            key_left = kr.left()
            key_mid_y = kr.top() + kr.height() / 2
            # Ligne horizontale du bus vers la touche
            _add_line(scene, bus_x, key_mid_y, key_left, key_mid_y, pen)
            # Petit segment vertical si le bus n'est pas au même Y
            if abs(target_y - key_mid_y) > 1:
                _add_line(scene, bus_x, target_y, bus_x, key_mid_y, pen)
                target_y = key_mid_y


# ── Câblage cols ───────────────────────────────────────────────────────────────


def _draw_col_wires(
    scene: QGraphicsScene,
    pin_points: dict[str, QPointF],
    key_rects: dict[tuple[int, int], QRectF],
    data: WiringData,
    keys_bottom_y: float,
) -> None:
    """Dessine les fils reliant les pins col du MCU aux touches correspondantes."""
    if not data.col_pins:
        return

    # Trouver toutes les cols utilisées
    cols_used: dict[int, list[QRectF]] = {}
    for (r, c), rect in key_rects.items():
        cols_used.setdefault(c, []).append(rect)

    bus_y_base = keys_bottom_y + 10

    for col_idx, pin_name in enumerate(data.col_pins):
        if pin_name not in pin_points:
            continue
        rects = cols_used.get(col_idx, [])
        if not rects:
            continue

        color = _col_color(col_idx)
        pen = QPen(color, WIRE_WIDTH)
        pen.setCosmetic(True)
        pin_pt = pin_points[pin_name]

        # Bus horizontal en dessous des touches
        bus_y = bus_y_base + col_idx * CHANNEL_SPACING

        # Ligne du pin MCU droit → descente verticale
        bus_x = pin_pt.x() + col_idx * CHANNEL_SPACING
        _add_line(scene, pin_pt.x(), pin_pt.y(), bus_x, pin_pt.y(), pen)
        _add_line(scene, bus_x, pin_pt.y(), bus_x, bus_y, pen)

        # Pour chaque touche de cette col : trait vertical depuis le bus
        for kr in sorted(rects, key=lambda r: r.top()):
            key_center_x = kr.left() + kr.width() / 2
            key_bottom = kr.top() + kr.height()
            # Segment horizontal dans le bus
            _add_line(scene, bus_x, bus_y, key_center_x, bus_y, pen)
            # Segment vertical montant vers la touche
            _add_line(scene, key_center_x, bus_y, key_center_x, key_bottom, pen)


# ── Périphériques ──────────────────────────────────────────────────────────────


def _draw_oled(
    scene: QGraphicsScene,
    x: float, y: float,
    pin_points: dict[str, QPointF],
) -> None:
    """Dessine le composant OLED avec ses fils I2C."""
    w, h = 60, 40
    rect = QGraphicsRectItem(x, y, w, h)
    rect.setBrush(QBrush(QColor(OLED_COLOR.red(), OLED_COLOR.green(), OLED_COLOR.blue(), 60)))
    rect.setPen(QPen(OLED_COLOR, 2))
    rect.setZValue(8)
    scene.addItem(rect)

    # Label
    label = QGraphicsSimpleTextItem("OLED")
    label.setFont(_bold_font(8))
    label.setBrush(QBrush(OLED_COLOR))
    label.setPos(x + 12, y + 12)
    label.setZValue(9)
    scene.addItem(label)

    # Fils SDA / SCL vers les pins MCU
    pen = QPen(OLED_COLOR, WIRE_WIDTH)
    pen.setCosmetic(True)
    pen.setStyle(Qt.PenStyle.DashLine)

    if "SDA" in pin_points:
        oled_right = x + w
        sda_pt = pin_points["SDA"]
        mid_y = y + h * 0.33
        _add_line(scene, oled_right, mid_y, sda_pt.x(), mid_y, pen)
        _add_line(scene, sda_pt.x(), mid_y, sda_pt.x(), sda_pt.y(), pen)

    if "SCL" in pin_points:
        oled_right = x + w
        scl_pt = pin_points["SCL"]
        mid_y = y + h * 0.66
        _add_line(scene, oled_right, mid_y, scl_pt.x(), mid_y, pen)
        _add_line(scene, scl_pt.x(), mid_y, scl_pt.x(), scl_pt.y(), pen)

    # Labels SDA/SCL sur le composant
    for i, lbl in enumerate(["SDA", "SCL"]):
        t = QGraphicsSimpleTextItem(lbl)
        t.setFont(_font(6))
        t.setBrush(QBrush(OLED_COLOR.lighter(140)))
        t.setPos(x + w + 3, y + h * (0.33 * (i + 1)) - 6)
        t.setZValue(9)
        scene.addItem(t)


def _draw_encoder(
    scene: QGraphicsScene,
    x: float, y: float,
    pin_points: dict[str, QPointF],
    data: WiringData,
) -> None:
    """Dessine le composant encodeur rotatif."""
    r = 20
    circle = QGraphicsEllipseItem(x, y, r * 2, r * 2)
    circle.setBrush(QBrush(QColor(ENCODER_COLOR.red(), ENCODER_COLOR.green(), ENCODER_COLOR.blue(), 60)))
    circle.setPen(QPen(ENCODER_COLOR, 2))
    circle.setZValue(8)
    scene.addItem(circle)

    label = QGraphicsSimpleTextItem("ENC")
    label.setFont(_bold_font(8))
    label.setBrush(QBrush(ENCODER_COLOR))
    label.setPos(x + r - 12, y + r - 6)
    label.setZValue(9)
    scene.addItem(label)

    # Fils A/B vers les pins MCU
    pen = QPen(ENCODER_COLOR, WIRE_WIDTH)
    pen.setCosmetic(True)
    pen.setStyle(Qt.PenStyle.DashLine)

    pin_a_key = data.encoder_a + " (A)" if data.encoder_a else ""
    pin_b_key = data.encoder_b + " (B)" if data.encoder_b else ""

    if pin_a_key and pin_a_key in pin_points:
        pt = pin_points[pin_a_key]
        enc_left = x
        mid_y = y + r * 0.7
        _add_line(scene, enc_left, mid_y, pt.x(), mid_y, pen)
        _add_line(scene, pt.x(), mid_y, pt.x(), pt.y(), pen)

    if pin_b_key and pin_b_key in pin_points:
        pt = pin_points[pin_b_key]
        enc_left = x
        mid_y = y + r * 1.3
        _add_line(scene, enc_left, mid_y, pt.x(), mid_y, pen)
        _add_line(scene, pt.x(), mid_y, pt.x(), pt.y(), pen)

    # Labels A/B
    for i, lbl in enumerate(["A", "B"]):
        t = QGraphicsSimpleTextItem(lbl)
        t.setFont(_font(6))
        t.setBrush(QBrush(ENCODER_COLOR.lighter(140)))
        t.setPos(x - 12, y + r * (0.7 + i * 0.6) - 6)
        t.setZValue(9)
        scene.addItem(t)


# ── Légende ────────────────────────────────────────────────────────────────────


def _draw_legend(
    scene: QGraphicsScene,
    x: float, y: float,
    data: WiringData,
) -> None:
    """Dessine la légende des couleurs en bas du schéma."""
    cx = x
    row_h = 14

    # Titre Rows
    if data.row_pins:
        title = QGraphicsSimpleTextItem("ROWS")
        title.setFont(_bold_font(7))
        title.setBrush(QBrush(QColor("#AAAAAA")))
        title.setPos(cx, y)
        scene.addItem(title)
        cx += 40

        for i, pin in enumerate(data.row_pins):
            color = _row_color(i)
            dot = QGraphicsRectItem(cx, y + 2, 8, 8)
            dot.setBrush(QBrush(color))
            dot.setPen(QPen(Qt.PenStyle.NoPen))
            scene.addItem(dot)
            txt = QGraphicsSimpleTextItem(f"R{i}: {pin}")
            txt.setFont(_font(7))
            txt.setBrush(QBrush(color))
            txt.setPos(cx + 12, y)
            scene.addItem(txt)
            cx += _text_width(f"R{i}: {pin}", 7) + 24

    # Titre Cols (nouvelle ligne)
    if data.col_pins:
        cx = x
        y += row_h + 4
        title = QGraphicsSimpleTextItem("COLS")
        title.setFont(_bold_font(7))
        title.setBrush(QBrush(QColor("#AAAAAA")))
        title.setPos(cx, y)
        scene.addItem(title)
        cx += 40

        for i, pin in enumerate(data.col_pins):
            color = _col_color(i)
            dot = QGraphicsRectItem(cx, y + 2, 8, 8)
            dot.setBrush(QBrush(color))
            dot.setPen(QPen(Qt.PenStyle.NoPen))
            scene.addItem(dot)
            txt = QGraphicsSimpleTextItem(f"C{i}: {pin}")
            txt.setFont(_font(7))
            txt.setBrush(QBrush(color))
            txt.setPos(cx + 12, y)
            scene.addItem(txt)
            cx += _text_width(f"C{i}: {pin}", 7) + 24

    # Périphériques
    periph_entries: list[tuple[str, QColor]] = []
    if data.has_oled:
        periph_entries.append(("OLED (I2C)", OLED_COLOR))
    if data.has_encoder:
        periph_entries.append(("Encoder", ENCODER_COLOR))
    if data.has_rgb and data.ws2812:
        periph_entries.append(("WS2812", WS2812_COLOR))
    if data.serial_tx:
        periph_entries.append(("Serial TX", SERIAL_COLOR))

    if periph_entries:
        cx = x
        y += row_h + 4
        for label, color in periph_entries:
            dot = QGraphicsRectItem(cx, y + 2, 8, 8)
            dot.setBrush(QBrush(color))
            dot.setPen(QPen(Qt.PenStyle.NoPen))
            scene.addItem(dot)
            txt = QGraphicsSimpleTextItem(label)
            txt.setFont(_font(7))
            txt.setBrush(QBrush(color))
            txt.setPos(cx + 12, y)
            scene.addItem(txt)
            cx += _text_width(label, 7) + 30


# ── Helpers ────────────────────────────────────────────────────────────────────


def _draw_empty_message(scene: QGraphicsScene) -> None:
    """Affiche un message quand il n'y a pas de touches à dessiner."""
    txt = QGraphicsSimpleTextItem("Analysez un layout KLE pour voir le schéma de câblage")
    txt.setFont(_font(10))
    txt.setBrush(QBrush(QColor("#888888")))
    txt.setPos(20, 20)
    scene.addItem(txt)


def _add_line(
    scene: QGraphicsScene,
    x1: float, y1: float, x2: float, y2: float,
    pen: QPen,
) -> QGraphicsLineItem:
    """Ajoute une ligne à la scène avec le pen donné."""
    line = QGraphicsLineItem(x1, y1, x2, y2)
    line.setPen(pen)
    line.setZValue(3)
    scene.addItem(line)
    return line


def _row_color(index: int) -> QColor:
    """Retourne une couleur de la palette row (cyclique)."""
    return ROW_COLORS[index % len(ROW_COLORS)]


def _col_color(index: int) -> QColor:
    """Retourne une couleur de la palette col (cyclique)."""
    return COL_COLORS[index % len(COL_COLORS)]


def _font(size: int) -> QFont:
    """Retourne un QFont de la taille donnée."""
    f = QFont()
    f.setPointSize(size)
    return f


def _bold_font(size: int) -> QFont:
    """Retourne un QFont bold de la taille donnée."""
    f = QFont()
    f.setPointSize(size)
    f.setBold(True)
    return f


def _text_width(text: str, font_size: int) -> float:
    """Estime la largeur d'un texte en pixels (approximation)."""
    return len(text) * font_size * 0.65
