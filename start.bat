@echo off
setlocal enabledelayedexpansion
title Keyboard Firmware Maker

echo === Keyboard Firmware Maker ===
echo.

set SCRIPT_DIR=%~dp0

:: ── Python 3.11+ ─────────────────────────────────────────────────────────────
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

:: ── git ──────────────────────────────────────────────────────────────────────
where git >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Git introuvable.
    echo   Installez Git depuis https://git-scm.com/download/win
    echo   Redemarrez ce script apres installation.
    pause & exit /b 1
)
for /f "tokens=3" %%v in ('git --version') do set GITVER=%%v
echo [OK] git !GITVER!

:: ── Environnement virtuel ────────────────────────────────────────────────────
set VENV_DIR=%SCRIPT_DIR%.venv
if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo Creation de l'environnement virtuel...
    python -m venv "%VENV_DIR%"
)
call "%VENV_DIR%\Scripts\activate.bat"

:: ── Dependances Python ───────────────────────────────────────────────────────
echo Verification des dependances Python...
pip install -q -r "%SCRIPT_DIR%requirements.txt"
if errorlevel 1 (
    echo [ERREUR] Echec de l'installation des dependances.
    pause & exit /b 1
)
echo [OK] Dependances Python

:: ── Outils de compilation (informatif) ───────────────────────────────────────
echo.
where make >nul 2>&1
if errorlevel 1 (
    echo [INFO] make non detecte — la compilation firmware sera configuree au premier build.
) else (
    echo [OK] make
)

where arm-none-eabi-gcc >nul 2>&1
if errorlevel 1 (
    echo [INFO] arm-none-eabi-gcc non detecte — sera telecharge automatiquement si besoin.
) else (
    for /f "tokens=*" %%v in ('arm-none-eabi-gcc --version 2^>^&1') do (
        echo [OK] %%v
        goto :gcc_done
    )
)
:gcc_done

:: ── west (Zephyr meta-tool, requis pour ZMK) ─────────────────────────────────
python -c "import west" >nul 2>&1
if errorlevel 1 (
    echo Installation de west ^(meta-tool Zephyr^)...
    pip install -q west
    if errorlevel 1 (
        echo [ERREUR] Echec de l'installation de west.
        pause ^& exit /b 1
    )
)
for /f "tokens=*" %%v in ('west --version 2^>^&1') do (
    echo [OK] %%v
    goto :west_done
)
:west_done
echo [INFO] Outils ZMK natifs (cmake, ninja, dtc, Zephyr SDK) : lances setup_zmk.bat avant le premier build ZMK.

:: ── Lancement ────────────────────────────────────────────────────────────────
echo.
python "%SCRIPT_DIR%main.py"
