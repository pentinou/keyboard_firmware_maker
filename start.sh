#!/usr/bin/env bash
# start.sh — Lance Keyboard Firmware Maker après vérification des prérequis.
# Usage : ./start.sh
set -e

RED='\033[0;31m'; YELLOW='\033[1;33m'; GREEN='\033[0;32m'; BOLD='\033[1m'; NC='\033[0m'

echo -e "${BOLD}=== Keyboard Firmware Maker ===${NC}"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APT_UPDATED=0

# Lance "sudo apt-get update" une seule fois si nécessaire
_apt_update_once() {
    if [ "$APT_UPDATED" -eq 0 ]; then
        echo "Mise à jour des listes de paquets (sudo apt-get update)..."
        sudo apt-get update -qq
        APT_UPDATED=1
    fi
}

# ── Python 3.11+ ──────────────────────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
    echo -e "${RED}[ERREUR] Python 3 introuvable.${NC}"
    echo "  sudo apt install python3"
    exit 1
fi

PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_MAJ=$(echo "$PY_VER" | cut -d. -f1)
PY_MIN=$(echo "$PY_VER" | cut -d. -f2)

if [ "$PY_MAJ" -lt 3 ] || { [ "$PY_MAJ" -eq 3 ] && [ "$PY_MIN" -lt 11 ]; }; then
    echo -e "${RED}[ERREUR] Python 3.11+ requis (trouvé : $PY_VER).${NC}"
    exit 1
fi
echo -e "${GREEN}[OK]${NC} Python $PY_VER"

# ── python3-venv ──────────────────────────────────────────────────────────────
if ! python3 -c "import ensurepip" &>/dev/null; then
    echo -e "${YELLOW}[INFO]${NC} python3-venv manquant — installation..."
    _apt_update_once
    sudo apt-get install -y "python${PY_VER}-venv" 2>/dev/null \
        || sudo apt-get install -y python3-venv
fi

# ── Environnement virtuel ─────────────────────────────────────────────────────
VENV_DIR="$SCRIPT_DIR/.venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "Création de l'environnement virtuel..."
    python3 -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

# ── Dépendances Python ────────────────────────────────────────────────────────
echo "Vérification des dépendances Python..."
pip install -q -r "$SCRIPT_DIR/requirements.txt"
echo -e "${GREEN}[OK]${NC} Dépendances Python"

# ── git ───────────────────────────────────────────────────────────────────────
if ! command -v git &>/dev/null; then
    echo -e "${YELLOW}[INFO]${NC} git manquant — installation..."
    _apt_update_once
    sudo apt-get install -y git
fi
echo -e "${GREEN}[OK]${NC} git $(git --version | awk '{print $3}')"

# ── make ──────────────────────────────────────────────────────────────────────
if ! command -v make &>/dev/null; then
    echo -e "${YELLOW}[INFO]${NC} make manquant — installation..."
    _apt_update_once
    sudo apt-get install -y make
fi
echo -e "${GREEN}[OK]${NC} make"

# ── arm-none-eabi-gcc ─────────────────────────────────────────────────────────
if ! command -v arm-none-eabi-gcc &>/dev/null; then
    echo -e "${YELLOW}[INFO]${NC} arm-none-eabi-gcc manquant — installation..."
    _apt_update_once
    sudo apt-get install -y gcc-arm-none-eabi
fi
GCC_VER=$(arm-none-eabi-gcc --version | head -1 | grep -oP '\d+\.\d+(\.\d+)?' | head -1)
echo -e "${GREEN}[OK]${NC} arm-none-eabi-gcc $GCC_VER"

# ── Outils ZMK légers (cmake, ninja, dtc, gperf, ccache, dfu-util, xz-utils) ──
# Le Zephyr SDK (lourd) est installé à la demande via scripts/setup_zmk.sh.
ZMK_PKGS=()
command -v cmake    &>/dev/null || ZMK_PKGS+=(cmake)
command -v ninja    &>/dev/null || ZMK_PKGS+=(ninja-build)
command -v dtc      &>/dev/null || ZMK_PKGS+=(device-tree-compiler)
command -v gperf    &>/dev/null || ZMK_PKGS+=(gperf)
command -v ccache   &>/dev/null || ZMK_PKGS+=(ccache)
command -v dfu-util &>/dev/null || ZMK_PKGS+=(dfu-util)
command -v xz       &>/dev/null || ZMK_PKGS+=(xz-utils)
command -v wget     &>/dev/null || ZMK_PKGS+=(wget)

if [ ${#ZMK_PKGS[@]} -gt 0 ]; then
    echo -e "${YELLOW}[INFO]${NC} Outils ZMK manquants (${ZMK_PKGS[*]}) — installation..."
    _apt_update_once
    sudo apt-get install -y "${ZMK_PKGS[@]}"
fi
echo -e "${GREEN}[OK]${NC} Outils ZMK (cmake, ninja, dtc, gperf, ccache, dfu-util)"

# ── west (Zephyr meta-tool) ───────────────────────────────────────────────────
if ! python3 -c "import west" &>/dev/null; then
    echo "Installation de west (meta-tool Zephyr)..."
    pip install -q west
fi
WEST_VER=$(west --version 2>/dev/null | awk '{print $NF}')
echo -e "${GREEN}[OK]${NC} west $WEST_VER"

# ── Lancement ─────────────────────────────────────────────────────────────────
echo ""
python3 "$SCRIPT_DIR/main.py"
