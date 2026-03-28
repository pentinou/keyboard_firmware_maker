@echo off
setlocal enabledelayedexpansion
title Build — Keyboard Firmware Maker

echo === Build Windows — Keyboard Firmware Maker ===
echo.

set SCRIPT_DIR=%~dp0
set PROJECT_DIR=%SCRIPT_DIR%..

:: ── Python ───────────────────────────────────────────────────────────────────
where python >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Python introuvable. Installez Python 3.11+ et ajoutez-le au PATH.
    pause & exit /b 1
)
echo [OK] Python

:: ── Environnement virtuel ────────────────────────────────────────────────────
set VENV_DIR=%PROJECT_DIR%\.venv
if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo Creation de l'environnement virtuel...
    python -m venv "%VENV_DIR%"
)
call "%VENV_DIR%\Scripts\activate.bat"

:: ── Dependances ──────────────────────────────────────────────────────────────
echo Installation des dependances...
pip install -q -r "%PROJECT_DIR%\requirements.txt"
pip install -q pyinstaller>=6.0
echo [OK] Dependances

:: ── Build PyInstaller ────────────────────────────────────────────────────────
echo.
echo Lancement de PyInstaller...
pushd "%PROJECT_DIR%"
pyinstaller keyboard_firmware_maker.spec --noconfirm
popd

if errorlevel 1 (
    echo.
    echo [ERREUR] Le build PyInstaller a echoue.
    pause & exit /b 1
)

echo.
echo === Build termine avec succes ===
echo Dossier de sortie : %PROJECT_DIR%\dist\KeyboardFirmwareMaker\
echo Executable : %PROJECT_DIR%\dist\KeyboardFirmwareMaker\KeyboardFirmwareMaker.exe
echo.
pause
