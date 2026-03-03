#!/usr/bin/env bash
# start.sh — Lance Keyboard Firmware Maker après vérification des prérequis.
# Usage : ./start.sh
set -e

RED='\033[0;31m'; YELLOW='\033[1;33m'; GREEN='\033[0;32m'; BOLD='\033[1m'; NC='\033[0m'

echo -e "${BOLD}=== Keyboard Firmware Maker ===${NC}"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

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
    echo -e "${RED}[ERREUR] git introuvable.${NC}"
    echo "  sudo apt install git"
    exit 1
fi
echo -e "${GREEN}[OK]${NC} git $(git --version | awk '{print $3}')"

# ── make ──────────────────────────────────────────────────────────────────────
if ! command -v make &>/dev/null; then
    echo -e "${RED}[ERREUR] make introuvable.${NC}"
    echo "  sudo apt install make"
    exit 1
fi
echo -e "${GREEN}[OK]${NC} make"

# ── arm-none-eabi-gcc (optionnel — avertissement seulement) ───────────────────
if ! command -v arm-none-eabi-gcc &>/dev/null; then
    echo -e "${YELLOW}[AVERT]${NC} arm-none-eabi-gcc introuvable."
    echo "        La compilation firmware sera désactivée jusqu'à son installation :"
    echo "          sudo apt install gcc-arm-none-eabi   # Ubuntu/Debian"
    echo "          sudo dnf install arm-none-eabi-gcc   # Fedora/RHEL"
else
    GCC_VER=$(arm-none-eabi-gcc --version | head -1 | grep -oP '\d+\.\d+(\.\d+)?' | head -1)
    echo -e "${GREEN}[OK]${NC} arm-none-eabi-gcc $GCC_VER"
fi

# ── Lancement ─────────────────────────────────────────────────────────────────
echo ""
python3 "$SCRIPT_DIR/main.py"
