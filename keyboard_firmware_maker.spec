# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — Keyboard Firmware Maker.

Produit un bundle one-directory (pas one-file) pour un demarrage rapide.
Usage :
    pyinstaller keyboard_firmware_maker.spec
"""

import sys
from pathlib import Path

block_cipher = None
ROOT = Path(SPECPATH)

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (str(ROOT / "keyboards"), "keyboards"),
        (str(ROOT / "templates"), "templates"),
        (str(ROOT / "assets"), "assets"),
        (str(ROOT / "toolchain"), "toolchain"),
        (str(ROOT / "i18n"), "i18n"),
        (str(ROOT / "_version.py"), "."),
    ],
    hiddenimports=[
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "unittest",
        "pytest",
        "black",
        "ruff",
        "pyinstaller",
    ],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="KeyboardFirmwareMaker",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=str(ROOT / "assets" / "icons" / "kfm.ico") if (ROOT / "assets" / "icons" / "kfm.ico").exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="KeyboardFirmwareMaker",
)
