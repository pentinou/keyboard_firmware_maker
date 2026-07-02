"""proc_stream.py — Lecture des lignes stdout d'un subprocess avec timeout réel.

Itérer directement sur `proc.stdout` bloque tant que le process n'émet rien :
un `west update` figé sur le réseau ou un `make` suspendu ne déclenche jamais
ni le timeout ni la vérification d'annulation. Ici, un thread lecteur pousse
les lignes dans une Queue ; l'appelant les consomme avec un timeout court, ce
qui lui permet de vérifier le deadline et l'annulation même en silence total.
Compatible Windows (pas de select() sur les pipes).

Utilisé par builder.py (QMK) et zmk_builder.py (ZMK).
"""
from __future__ import annotations

import queue
import subprocess
import threading
import time
from collections.abc import Callable, Iterator

_SENTINEL = object()

# Période de réveil de l'appelant quand aucune ligne n'arrive (vérification
# annulation + deadline). 0.5 s = réactivité perçue correcte pour un bouton stop.
_POLL_INTERVAL_S = 0.5


class ProcTimeoutError(Exception):
    """Le process n'a rien terminé avant le deadline — il a été tué."""


class ProcInterruptedError(Exception):
    """L'annulation a été demandée pendant la lecture — le process a été tué."""


def iter_lines_with_timeout(
    proc: subprocess.Popen,
    timeout_s: float,
    is_interrupted: Callable[[], bool],
) -> Iterator[str]:
    """Itère sur les lignes stdout de `proc` (lancé avec stdout=PIPE, text=True).

    Args:
        proc: process en cours dont on streame le stdout.
        timeout_s: durée max totale avant de tuer le process.
        is_interrupted: callback vérifié ~2×/s ; True → process tué.

    Raises:
        ProcTimeoutError: deadline dépassé (process tué avant de lever).
        ProcInterruptedError: annulation demandée (process tué avant de lever).
    """
    lines: queue.Queue = queue.Queue()

    def _reader() -> None:
        try:
            for line in proc.stdout:  # type: ignore[union-attr]
                lines.put(line)
        finally:
            lines.put(_SENTINEL)

    threading.Thread(target=_reader, daemon=True).start()
    deadline = time.monotonic() + timeout_s

    while True:
        if is_interrupted():
            _kill(proc)
            raise ProcInterruptedError
        if time.monotonic() > deadline:
            _kill(proc)
            raise ProcTimeoutError
        try:
            item = lines.get(timeout=_POLL_INTERVAL_S)
        except queue.Empty:
            continue
        if item is _SENTINEL:
            return
        yield item


def _kill(proc: subprocess.Popen) -> None:
    if proc.poll() is None:
        proc.kill()
