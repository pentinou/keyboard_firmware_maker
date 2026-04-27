@echo off
setlocal enabledelayedexpansion
title Setup Zephyr SDK (ZMK)

echo === Installation Zephyr SDK pour ZMK ===
echo.

:: ── Activation du venv KFM si present ───────────────────────────────────────
:: Garantit que `pip install west` cible le meme Python que celui utilise par KFM.
set SCRIPT_DIR=%~dp0
set KFM_VENV=%SCRIPT_DIR%..\.venv
if exist "%KFM_VENV%\Scripts\activate.bat" (
    call "%KFM_VENV%\Scripts\activate.bat"
    echo [OK] venv KFM active ^(%KFM_VENV%^)
) else (
    echo [INFO] Pas de venv KFM detecte — lancez d'abord start.bat pour de meilleurs resultats.
)

:: Version du Zephyr SDK compatible Zephyr 3.5+ (utilise par ZMK)
set ZEPHYR_SDK_VERSION=0.17.0
set CACHE_DIR=%USERPROFILE%\.keyboard_firmware_maker
set SDK_DIR=%CACHE_DIR%\zephyr-sdk-%ZEPHYR_SDK_VERSION%
set ARCHIVE=zephyr-sdk-%ZEPHYR_SDK_VERSION%_windows-x86_64_minimal.7z
set URL=https://github.com/zephyrproject-rtos/sdk-ng/releases/download/v%ZEPHYR_SDK_VERSION%/%ARCHIVE%

if not exist "%CACHE_DIR%" mkdir "%CACHE_DIR%"

:: ── Prerequis : MSYS2 (fournit cmake, ninja, dtc, gperf, ccache) ─────────────
set MSYS2_DIR=%CACHE_DIR%\msys2
set MSYS2_BASH=%MSYS2_DIR%\usr\bin\bash.exe
if not exist "%MSYS2_BASH%" (
    echo [ERREUR] MSYS2 introuvable dans %MSYS2_DIR%
    echo   Lancez d'abord une compilation QMK depuis KFM pour installer MSYS2,
    echo   ou installez-le manuellement depuis https://www.msys2.org/
    pause ^& exit /b 1
)
echo [OK] MSYS2 detecte

echo Installation des paquets MSYS2 (cmake, ninja, dtc, gperf, ccache, protobuf)...
:: protobuf fournit protoc, requis par nanopb pour generer les stubs RPC de ZMK Studio.
"%MSYS2_BASH%" -lc "pacman -S --noconfirm --needed mingw-w64-x86_64-cmake mingw-w64-x86_64-ninja mingw-w64-x86_64-dtc gperf ccache mingw-w64-x86_64-protobuf"
if errorlevel 1 (
    echo [ERREUR] Echec de l'installation des paquets MSYS2.
    pause ^& exit /b 1
)
echo [OK] Paquets MSYS2 installes

:: ── Skip si SDK deja installe ────────────────────────────────────────────────
if exist "%SDK_DIR%\setup.cmd" (
    echo [OK] Zephyr SDK %ZEPHYR_SDK_VERSION% deja present : %SDK_DIR%
    goto :verify_west
)

:: ── Telechargement Zephyr SDK (PowerShell) ───────────────────────────────────
echo Telechargement de %ARCHIVE% (~200 Mo)...
powershell -NoProfile -Command "Invoke-WebRequest -Uri '%URL%' -OutFile '%CACHE_DIR%\%ARCHIVE%'"
if errorlevel 1 (
    echo [ERREUR] Echec du telechargement.
    pause ^& exit /b 1
)

:: ── Extraction via Python + py7zr ────────────────────────────────────────────
echo Installation de py7zr (extraction .7z)...
python -m pip install -q py7zr
if errorlevel 1 (
    echo [ERREUR] Impossible d'installer py7zr.
    pause ^& exit /b 1
)

echo Extraction...
python -c "import py7zr; py7zr.SevenZipFile(r'%CACHE_DIR%\%ARCHIVE%').extractall(path=r'%CACHE_DIR%')"
if errorlevel 1 (
    echo [ERREUR] Extraction echouee.
    pause ^& exit /b 1
)
del /q "%CACHE_DIR%\%ARCHIVE%"

if not exist "%SDK_DIR%\setup.cmd" (
    echo [ERREUR] %SDK_DIR%\setup.cmd introuvable apres extraction.
    pause ^& exit /b 1
)
echo [OK] Zephyr SDK extrait dans %SDK_DIR%

:: ── Installation toolchain ARM + host tools ──────────────────────────────────
echo Installation du toolchain arm-zephyr-eabi + host tools...
pushd "%SDK_DIR%"
call setup.cmd -t arm-zephyr-eabi -c -h
popd

:verify_west
:: ── west ─────────────────────────────────────────────────────────────────────
python -c "import west" >nul 2>&1
if errorlevel 1 (
    echo Installation de west...
    pip install -q west
)

:: ── Python bindings protobuf (requis par protoc-gen-nanopb) ──────────────────
:: nanopb_generator.py fait `import google.protobuf` pendant la compilation ZMK Studio.
python -c "import google.protobuf" >nul 2>&1
if errorlevel 1 (
    echo Installation de protobuf + grpcio-tools...
    pip install -q protobuf grpcio-tools
)

echo.
echo === Setup ZMK termine ===
echo.
echo Variable exportee automatiquement par KFM au build :
echo   ZEPHYR_SDK_INSTALL_DIR=%SDK_DIR%
echo.
pause
