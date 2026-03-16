"""Tests for KLE JSON parser."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from modules.keyboard_editor.kle_parser import KleKey, parse_kle_json


class TestParseKleJson:
    """Tests for parse_kle_json()."""

    def test_empty_input(self):
        result = parse_kle_json("")
        assert not result.ok
        assert result.errors

    def test_invalid_json(self):
        result = parse_kle_json("{invalid json")
        assert not result.ok

    def test_simple_grid(self):
        raw = '[["a","b","c"],["d","e","f"]]'
        result = parse_kle_json(raw)
        assert result.ok
        assert len(result.keys) == 6
        # First row at y=0, second row at y=1
        assert result.keys[0].x == 0.0
        assert result.keys[0].y == 0.0
        assert result.keys[2].x == 2.0
        assert result.keys[3].y == 1.0

    def test_matrix_labels_parsed(self):
        raw = '[["0,0","0,1"],["1,0","1,1"]]'
        result = parse_kle_json(raw)
        assert result.ok
        assert result.keys[0].row == 0
        assert result.keys[0].col == 0
        assert result.keys[3].row == 1
        assert result.keys[3].col == 1

    def test_no_matrix_labels(self):
        raw = '[["a","b"]]'
        result = parse_kle_json(raw)
        assert result.ok
        assert result.keys[0].row == -1
        assert result.keys[0].col == -1

    def test_key_width(self):
        raw = '[[{"w":2},"0,0","0,1"]]'
        result = parse_kle_json(raw)
        assert result.ok
        assert result.keys[0].w == 2.0
        assert result.keys[1].w == 1.0  # width resets after key

    def test_key_height(self):
        raw = '[[{"h":1.5},"0,0"]]'
        result = parse_kle_json(raw)
        assert result.ok
        assert result.keys[0].h == 1.5

    def test_x_offset(self):
        raw = '[[{"x":0.5},"0,0","0,1"]]'
        result = parse_kle_json(raw)
        assert result.ok
        # After normalization, first key at 0, second at 1.0
        assert result.keys[0].x == 0.0
        assert result.keys[1].x == 1.0  # gap of 1.0 (0.5 offset + 1.0 width - 0.5 norm)

    def test_y_offset(self):
        """Y offset on single key normalizes to 0."""
        raw = '[[{"y":0.5},"0,0"]]'
        result = parse_kle_json(raw)
        assert result.ok
        assert result.keys[0].y == 0.0  # normalized

    def test_rotation(self):
        raw = '[[{"r":15,"rx":4,"ry":5},"0,0"]]'
        result = parse_kle_json(raw)
        assert result.ok
        assert result.keys[0].r == 15.0

    def test_vial_json_format(self):
        """Parse a full vial.json object."""
        vial = {
            "name": "Test",
            "vendorId": "0x0000",
            "productId": "0x0001",
            "matrix": {"rows": 2, "cols": 2},
            "layouts": {
                "keymap": [
                    ["0,0", "0,1"],
                    ["1,0", "1,1"],
                ]
            },
        }
        result = parse_kle_json(json.dumps(vial))
        assert result.ok
        assert len(result.keys) == 4

    def test_kle_raw_data_format(self):
        """Parse KLE raw data (not wrapped in outer brackets)."""
        raw = '["0,0","0,1"],\n["1,0","1,1"]'
        result = parse_kle_json(raw)
        assert result.ok
        assert len(result.keys) == 4

    def test_corne_vial_json(self):
        """Parse the bundled corne.vial.json."""
        path = Path("keyboards/corne.vial.json")
        if not path.exists():
            pytest.skip("corne.vial.json not found")
        result = parse_kle_json(path.read_text())
        assert result.ok
        assert len(result.keys) == 42

    def test_sofle_vial_json(self):
        """Parse the bundled sofle-v2.vial.json."""
        path = Path("keyboards/sofle-v2.vial.json")
        if not path.exists():
            pytest.skip("sofle-v2.vial.json not found")
        result = parse_kle_json(path.read_text())
        assert result.ok
        assert len(result.keys) == 65
        encoders = [k for k in result.keys if k.encoder]
        assert len(encoders) == 4

    def test_positions_normalized(self):
        """Keys should be normalized so min x,y = 0."""
        raw = '[[{"x":5,"y":3},"0,0","0,1"]]'
        result = parse_kle_json(raw)
        assert result.ok
        assert result.keys[0].x == 0.0
        assert result.keys[0].y == 0.0
