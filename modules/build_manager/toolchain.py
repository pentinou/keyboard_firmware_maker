"""toolchain.py — Détection de la toolchain ARM (arm-none-eabi-gcc).

Stratégie (FR32, NFR15) :
1. Cherche les binaires vendorés dans toolchain/{platform}/bin/
2. Fallback : détecte arm-none-eabi-gcc sur le PATH système
3. Si absent : retourne ToolchainInfo(source="missing") + message guide installation

Aucun import Qt — pur Python.
"""
from __future__ import annotations

import logging
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from config import DOWNLOADED_TOOLCHAIN_DIR, TOOLCHAIN_DIR

logger = logging.getLogger(__name__)

INSTALL_GUIDE_MSG = (
    "La toolchain ARM est introuvable.\n"
    "Installez arm-none-eabi-gcc :\n"
    "  • Ubuntu/Debian : sudo apt install gcc-arm-none-eabi\n"
    "  • Fedora/RHEL   : sudo dnf install arm-none-eabi-gcc\n"
    "  • Windows       : https://developer.arm.com/downloads/-/arm-gnu-toolchain-downloads\n"
    "Puis relancez l'application."
)


@dataclass
class ToolchainInfo:
    """Résultat de la détection de la toolchain ARM."""

    gcc_path: Path | None
    version: str
    source: str  # "vendored" | "system" | "missing"

    @property
    def is_available(self) -> bool:
        return self.gcc_path is not None


def detect_toolchain() -> ToolchainInfo:
    """Détecte arm-none-eabi-gcc : vendored → downloaded → PATH système.

    Returns:
        ToolchainInfo avec source="vendored" | "downloaded" | "system" | "missing"
    """
    platform_name = "windows" if sys.platform == "win32" else "linux"
    binary = "arm-none-eabi-gcc.exe" if sys.platform == "win32" else "arm-none-eabi-gcc"
    version = _read_version()

    # 1. Binaire vendoré (dans l'application)
    vendored_path = TOOLCHAIN_DIR / platform_name / "bin" / binary
    if vendored_path.is_file():
        logger.info("Toolchain vendorée détectée : %s", vendored_path)
        return ToolchainInfo(gcc_path=vendored_path, version=version, source="vendored")

    # 2. Binaire téléchargé (dans le cache utilisateur, Windows uniquement)
    if sys.platform == "win32" and DOWNLOADED_TOOLCHAIN_DIR.is_dir():
        candidates = list(DOWNLOADED_TOOLCHAIN_DIR.rglob(binary))
        if candidates:
            dl_path = candidates[0]
            logger.info("Toolchain téléchargée détectée : %s", dl_path)
            dl_version = _get_system_gcc_version(str(dl_path))
            return ToolchainInfo(gcc_path=dl_path, version=dl_version, source="downloaded")

    # 3. Fallback PATH système
    system_path = shutil.which("arm-none-eabi-gcc")
    if system_path:
        logger.info("Toolchain système détectée : %s", system_path)
        sys_version = _get_system_gcc_version(system_path)
        return ToolchainInfo(gcc_path=Path(system_path), version=sys_version, source="system")

    # 4. Absente
    logger.warning("arm-none-eabi-gcc introuvable (vendored + downloaded + PATH)")
    return ToolchainInfo(gcc_path=None, version=version, source="missing")


def _read_version() -> str:
    """Lit la version vendored depuis toolchain/version.txt (NFR15)."""
    version_file = TOOLCHAIN_DIR / "version.txt"
    if version_file.is_file():
        return version_file.read_text(encoding="utf-8").strip()
    return "unknown"


def _get_system_gcc_version(gcc_path: str) -> str:
    """Retourne la version réelle du GCC système via --version.

    Falls back to 'unknown' si le sous-processus échoue.
    """
    try:
        out = subprocess.check_output(
            [gcc_path, "--version"], stderr=subprocess.STDOUT, timeout=5
        )
        first_line = out.decode("utf-8", errors="replace").splitlines()[0]
        # e.g. "arm-none-eabi-gcc (GNU Arm Embedded Toolchain 13.3.Rel1) 13.3.1 20240614"
        # Match X.Y.Z (all-digit segments) first, then fall back to X.Y
        m = re.search(r"\b(\d+\.\d+\.\d+)\b", first_line) or re.search(
            r"\b(\d+\.\d+)\b", first_line
        )
        return m.group(1) if m else first_line.strip()
    except Exception:
        return "unknown"
