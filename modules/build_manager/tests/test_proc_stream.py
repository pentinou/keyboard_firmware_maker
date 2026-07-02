"""Tests pour proc_stream.py — lecture stdout avec timeout et annulation réels.

Utilise de vrais sous-processus Python (pas de Qt) : le point critique testé
est justement le comportement quand le process ne produit AUCUNE sortie,
cas où l'ancienne boucle `for line in proc.stdout` bloquait indéfiniment.
"""
from __future__ import annotations

import subprocess
import sys
import time

import pytest

from modules.build_manager.proc_stream import (
    ProcInterruptedError,
    ProcTimeoutError,
    iter_lines_with_timeout,
)


def _spawn(code: str) -> subprocess.Popen:
    return subprocess.Popen(
        [sys.executable, "-u", "-c", code],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


class TestIterLinesWithTimeout:
    def test_yields_all_lines_then_terminates(self):
        proc = _spawn("print('a'); print('b')")
        lines = [
            line.strip()
            for line in iter_lines_with_timeout(proc, timeout_s=30, is_interrupted=lambda: False)
        ]
        assert lines == ["a", "b"]
        assert proc.wait() == 0

    def test_timeout_fires_on_silent_hang(self):
        proc = _spawn("import time; time.sleep(60)")
        start = time.monotonic()
        with pytest.raises(ProcTimeoutError):
            list(iter_lines_with_timeout(proc, timeout_s=1, is_interrupted=lambda: False))
        # L'ancien code bloquait 60 s ici — le timeout doit tuer bien avant.
        assert time.monotonic() - start < 10
        proc.wait()
        assert proc.poll() is not None

    def test_interruption_fires_on_silent_hang(self):
        proc = _spawn("import time; time.sleep(60)")
        with pytest.raises(ProcInterruptedError):
            list(iter_lines_with_timeout(proc, timeout_s=60, is_interrupted=lambda: True))
        proc.wait()
        assert proc.poll() is not None

    def test_lines_before_timeout_are_delivered(self):
        proc = _spawn("print('early'); import time; time.sleep(60)")
        received: list[str] = []
        with pytest.raises(ProcTimeoutError):
            for line in iter_lines_with_timeout(proc, timeout_s=2, is_interrupted=lambda: False):
                received.append(line.strip())
        assert received == ["early"]
        proc.wait()
