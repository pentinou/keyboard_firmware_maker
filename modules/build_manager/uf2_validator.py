"""uf2_validator.py — Validation du format UF2 Microsoft (NFR6).

Le format UF2 est défini sur https://github.com/microsoft/uf2 :
- Chaque bloc fait 512 octets
- Les 8 premiers octets de chaque bloc sont deux magic numbers 32-bit (little-endian)
- Magic 0 : 0x0A324655 ("UF2\n")
- Magic 1 : 0x9E5D5157

Aucun import Qt — pur Python.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path

UF2_MAGIC_START0: int = 0x0A324655  # "UF2\n"
UF2_MAGIC_START1: int = 0x9E5D5157
UF2_BLOCK_SIZE: int = 512


@dataclass
class Uf2ValidationResult:
    """Résultat de la validation d'un fichier UF2."""

    valid: bool
    size_bytes: int
    message: str


def validate_uf2(path: Path) -> Uf2ValidationResult:
    """Valide la conformité d'un fichier .uf2 au format UF2 Microsoft.

    Vérifie :
    - Le fichier existe et est lisible
    - La taille est un multiple de 512 octets
    - Les magic bytes du premier bloc sont corrects

    Args:
        path: chemin vers le fichier .uf2.

    Returns:
        Uf2ValidationResult avec valid=True si le fichier est valide.
    """
    if not path.is_file():
        return Uf2ValidationResult(
            valid=False,
            size_bytes=0,
            message=f"Fichier introuvable : {path}",
        )

    data = path.read_bytes()
    size = len(data)

    if size < UF2_BLOCK_SIZE:
        return Uf2ValidationResult(
            valid=False,
            size_bytes=size,
            message=f"Fichier trop petit ({size} octets) pour être un UF2 valide",
        )

    if size % UF2_BLOCK_SIZE != 0:
        return Uf2ValidationResult(
            valid=False,
            size_bytes=size,
            message=f"Taille incorrecte : {size} n'est pas un multiple de 512",
        )

    magic0, magic1 = struct.unpack_from("<II", data, 0)
    if magic0 != UF2_MAGIC_START0:
        return Uf2ValidationResult(
            valid=False,
            size_bytes=size,
            message=f"Magic UF2 invalide (bloc 0) : 0x{magic0:08X} ≠ 0x{UF2_MAGIC_START0:08X}",
        )
    if magic1 != UF2_MAGIC_START1:
        return Uf2ValidationResult(
            valid=False,
            size_bytes=size,
            message=f"Magic UF2 invalide (bloc 0) : 0x{magic1:08X} ≠ 0x{UF2_MAGIC_START1:08X}",
        )

    return Uf2ValidationResult(
        valid=True,
        size_bytes=size,
        message=f"Fichier UF2 valide ({size // 1024} KB, {size // UF2_BLOCK_SIZE} blocs)",
    )
