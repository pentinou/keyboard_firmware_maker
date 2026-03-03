@echo off
setlocal enabledelayedexpansion
title Keyboard Firmware Maker

echo === Keyboard Firmware Maker ===
echo.

set SCRIPT_DIR=%~dp0

:: ── Python 3.11+ ──────────────────────────────────────────────────────────────
where python >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Python introuvable.
    echo   Installez Python 3.11+ depuis https://www.python.org/downloads/
    echo   Cochez bien "Add Python to PATH" durant l'installation.
    pause & exit /b 1
)

for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYVER=%%v
for /f "tokens=1,2 delims=." %%a in ("!PYVER!") do (
    set PYMAJ=%%a
    set PYMIN=%%b
)
if !PYMAJ! LSS 3 goto :python_too_old
if !PYMAJ! EQU 3 if !PYMIN! LSS 11 goto :python_too_old
goto :python_ok

:python_too_old
echo [ERREUR] Python 3.11+ requis (trouve : !PYVER!).
pause & exit /b 1

:python_ok
echo [OK] Python !PYVER!

:: ── Environnement virtuel ─────────────────────────────────────────────────────
set VENV_DIR=%SCRIPT_DIR%.venv
if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo Creation de l'environnement virtuel...
    python -m venv "%VENV_DIR%"
)
call "%VENV_DIR%\Scripts\activate.bat"

:: ── Dépendances Python ────────────────────────────────────────────────────────
echo Verification des dependances Python...
pip install -q -r "%SCRIPT_DIR%requirements.txt"
if errorlevel 1 (
    echo [ERREUR] Echec de l'installation des dependances.
    pause & exit /b 1
)
echo [OK] Dependances Python

:: ── Note compilation ──────────────────────────────────────────────────────────
echo.
echo [INFO] Compilation firmware : necessite WSL2 avec arm-none-eabi-gcc installe
echo        DANS WSL2 — pas sur Windows.
echo        Dans WSL2 : sudo apt install gcc-arm-none-eabi
echo        L'interface graphique fonctionne sans WSL2.
echo.

:: ── Lancement ─────────────────────────────────────────────────────────────────
python "%SCRIPT_DIR%main.py"
