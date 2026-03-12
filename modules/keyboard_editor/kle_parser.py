"""kle_parser — Parse KLE (Keyboard Layout Editor) JSON into key data.

Parses the KLE JSON format used by keyboard-layout-editor.com and Vial.
The format is an array of rows, where each row contains alternating
property objects and key label strings.

Module pur Python sans dépendance Qt — testable sans QApplication.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class KleKey:
    """A single key parsed from KLE JSON."""

    x: float = 0.0
    y: float = 0.0
    w: float = 1.0
    h: float = 1.0
    r: float = 0.0
    rx: float = 0.0
    ry: float = 0.0
    row: int = -1   # matrix row (-1 = unassigned)
    col: int = -1   # matrix col (-1 = unassigned)
    label: str = ""
    encoder: bool = False


@dataclass
class KleParseResult:
    """Result of parsing KLE JSON."""

    keys: list[KleKey] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return len(self.keys) > 0 and not self.errors


def parse_kle_json(text: str) -> KleParseResult:
    """Parse KLE JSON text into a list of KleKey objects.

    Accepts either:
    - A full vial.json object with layouts.keymap array
    - Just the keymap array (array of arrays)
    - Raw text from keyboard-layout-editor.com (array of arrays)

    Returns a KleParseResult with keys and any errors.
    """
    result = KleParseResult()
    text = text.strip()

    if not text:
        result.errors.append("Le texte KLE est vide.")
        return result

    try:
        # strict=False: KLE raw data contains literal newlines inside string
        # values (multi-line key labels like "!\n1") which is invalid JSON
        # in strict mode but standard KLE format.
        data = json.loads(text, strict=False)
    except json.JSONDecodeError as e:
        # KLE raw data from the website isn't valid JSON — it's missing outer brackets
        # Try wrapping in brackets
        try:
            data = json.loads(f"[{text}]", strict=False)
        except json.JSONDecodeError:
            result.errors.append(f"JSON invalide : {e}")
            return result

    # Extract the keymap array from various formats
    rows = _extract_keymap(data)
    if rows is None:
        result.errors.append(
            "Format non reconnu. Attendu : tableau KLE (depuis keyboard-layout-editor.com) "
            "ou objet vial.json avec layouts.keymap."
        )
        return result

    # Parse the KLE rows
    result.keys = _parse_rows(rows)

    if not result.keys:
        result.errors.append("Aucune touche trouvée dans le JSON.")

    return result


def _extract_keymap(data: object) -> list | None:
    """Extract the keymap array from various input formats."""
    if isinstance(data, dict):
        # vial.json format: { "layouts": { "keymap": [...] } }
        layouts = data.get("layouts")
        if isinstance(layouts, dict):
            keymap = layouts.get("keymap")
            if isinstance(keymap, list):
                return keymap
        # Maybe top-level keymap
        keymap = data.get("keymap")
        if isinstance(keymap, list):
            return keymap
        return None

    if isinstance(data, list):
        # Check if it's an array of arrays (KLE format)
        if not data:
            return None
        # Skip metadata object if first element is a dict (KLE website format)
        if isinstance(data[0], dict) and not isinstance(data[0], list):
            # First element is metadata — skip it
            return data[1:] if len(data) > 1 else []
        # Check if first element is a list (array of rows)
        if isinstance(data[0], list):
            return data
        # It might be a single row — wrap it
        if any(isinstance(item, str) for item in data):
            return [data]
        return None

    return None


def _parse_rows(rows: list) -> list[KleKey]:
    """Parse KLE rows into KleKey objects.

    KLE format: each row is an array of alternating property dicts and key strings.
    Properties accumulate and apply to the next key string encountered.
    Some properties (x, y, w, h) reset after each key.
    Rotation properties (r, rx, ry) persist until changed.
    """
    keys: list[KleKey] = []

    # Current position tracking
    cur_x = 0.0
    cur_y = 0.0

    # Persistent rotation state
    cur_r = 0.0
    cur_rx = 0.0
    cur_ry = 0.0

    # Per-key overrides (reset after each key)
    next_w = 1.0
    next_h = 1.0
    next_x_offset = 0.0
    next_y_offset = 0.0

    for row in rows:
        if not isinstance(row, list):
            continue

        # Reset x to rotation origin at start of each row
        cur_x = cur_rx
        cur_y += 1  # advance one row

        for item in row:
            if isinstance(item, dict):
                # Property object — applies to next key(s)
                if "r" in item:
                    cur_r = float(item["r"])
                if "rx" in item:
                    cur_rx = float(item["rx"])
                    cur_x = cur_rx  # reset x to new rotation origin
                if "ry" in item:
                    cur_ry = float(item["ry"])
                    cur_y = cur_ry  # reset y to new rotation origin

                # Per-key offsets
                if "x" in item:
                    next_x_offset = float(item["x"])
                if "y" in item:
                    next_y_offset = float(item["y"])
                if "w" in item:
                    next_w = float(item["w"])
                if "h" in item:
                    next_h = float(item["h"])

            elif isinstance(item, str):
                # Key label — create a key at current position
                cur_x += next_x_offset
                cur_y += next_y_offset

                key = KleKey(
                    x=round(cur_x, 4),
                    y=round(cur_y, 4),
                    w=next_w,
                    h=next_h,
                    r=cur_r,
                    rx=cur_rx,
                    ry=cur_ry,
                    label=item,
                )

                # Try to parse matrix position from label ("row,col")
                _parse_matrix_label(key, item)

                keys.append(key)

                # Advance x by key width
                cur_x += next_w

                # Reset per-key properties
                next_w = 1.0
                next_h = 1.0
                next_x_offset = 0.0
                next_y_offset = 0.0

    # Normalize positions so minimum x,y = 0
    if keys:
        min_x = min(k.x for k in keys)
        min_y = min(k.y for k in keys)
        for k in keys:
            k.x = round(k.x - min_x, 4)
            k.y = round(k.y - min_y, 4)
            if k.rx != 0.0:
                k.rx = round(k.rx - min_x, 4)
            if k.ry != 0.0:
                k.ry = round(k.ry - min_y, 4)

    return keys


def _parse_matrix_label(key: KleKey, label: str) -> None:
    """Try to parse matrix row,col from a KLE label string.

    Vial format: "row,col" (e.g. "0,3" or "4,5")
    Encoder format: label contains "\\ne" on line 10 (Vial convention)
    Multi-line labels: split by \\n, matrix position is on various lines.
    """
    lines = label.split("\n")

    # Check for encoder marker (Vial uses line index 9+ for encoder)
    # Convention: if any line is just "e", it's an encoder
    if len(lines) > 9 and lines[9].strip().lower() == "e":
        key.encoder = True

    # Try first line for "row,col"
    first = lines[0].strip()
    if "," in first:
        parts = first.split(",", 1)
        try:
            key.row = int(parts[0])
            key.col = int(parts[1])
        except (ValueError, IndexError):
            pass
