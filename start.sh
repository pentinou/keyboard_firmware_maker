#!/usr/bin/env bash
# start.sh — Lance Keyboard Firmware Maker après vérification des prérequis.
#
# Usage :
#   ./start.sh           : check prérequis + lance KFM
#   ./start.sh --update  : met à jour KFM (git pull) + deps Python + ZMK workspace
#                          + vial-qmk, puis lance KFM
#   ./start.sh --help    : affiche cette aide
set -e

RED='\033[0;31m'; YELLOW='\033[1;33m'; GREEN='\033[0;32m'; BOLD='\033[1m'; NC='\033[0m'

# ── Parse args ────────────────────────────────────────────────────────────────
UPDATE_MODE=0
for arg in "$@"; do
    case "$arg" in
        --update|-u)
            UPDATE_MODE=1
            ;;
        --help|-h)
            awk '/^set -e/{exit} /^#/{sub(/^# ?/, ""); print}' "$0"
            exit 0
            ;;
        *)
            echo -e "${RED}[ERREUR] Argument inconnu : $arg${NC}"
            echo "Usage : $0 [--update | --help]"
            exit 1
            ;;
    esac
done

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

# ── Mode --update : git pull du repo KFM ──────────────────────────────────────
if [ "$UPDATE_MODE" -eq 1 ]; then
    echo ""
    echo -e "${BOLD}── Mode --update activé ──${NC}"
    echo ""
    if git -C "$SCRIPT_DIR" rev-parse --git-dir &>/dev/null; then
        echo "Mise à jour de KFM (git pull)..."
        # Avertit si modifs locales non commit pour éviter conflits silencieux
        if ! git -C "$SCRIPT_DIR" diff-index --quiet HEAD -- 2>/dev/null; then
            echo -e "${YELLOW}[ATTENTION]${NC} Modifications locales non committées détectées."
            echo "  Le pull peut échouer si un fichier modifié est aussi modifié sur origin."
            echo "  Pour annuler tes modifs : git stash"
        fi
        if git -C "$SCRIPT_DIR" pull --ff-only 2>&1; then
            echo -e "${GREEN}[OK]${NC} KFM à jour"
        else
            echo -e "${RED}[ERREUR]${NC} git pull a échoué (conflits ?). KFM non mis à jour."
            echo "  Continue avec la version locale actuelle."
        fi
    else
        echo -e "${YELLOW}[INFO]${NC} Pas de dépôt git détecté — skip update KFM."
    fi
fi

# ── Dépendances Python ────────────────────────────────────────────────────────
if [ "$UPDATE_MODE" -eq 1 ]; then
    echo "Mise à jour des dépendances Python (pip install --upgrade)..."
    pip install -q --upgrade -r "$SCRIPT_DIR/requirements.txt"
else
    echo "Vérification des dépendances Python..."
    pip install -q -r "$SCRIPT_DIR/requirements.txt"
fi
echo -e "${GREEN}[OK]${NC} Dépendances Python"

# ── libxcb-cursor0 (backend X11 de Qt) ────────────────────────────────────────
# Requis par Qt >= 6.5 pour charger le plugin xcb. Sans lui, Qt bascule sur
# Wayland ; sous WSLg les popups (listes déroulantes, menus) laissent alors des
# traces à l'écran après fermeture.
if ! ldconfig -p 2>/dev/null | grep -q "libxcb-cursor.so.0"; then
    echo -e "${YELLOW}[INFO]${NC} libxcb-cursor0 manquant (affichage Qt/X11) — installation..."
    _apt_update_once
    sudo apt-get install -y libxcb-cursor0
fi

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

# ── Mode --update : ZMK workspace + vial-qmk ──────────────────────────────────
if [ "$UPDATE_MODE" -eq 1 ]; then
    # ZMK workspace : west update (modules Zephyr + ZMK app)
    ZMK_WORKSPACE="$HOME/.keyboard_firmware_maker/zmk-workspace"
    if [ -d "$ZMK_WORKSPACE" ]; then
        echo "Mise à jour de la ZMK workspace (west update)..."
        if (cd "$ZMK_WORKSPACE" && west update 2>&1 | tail -20); then
            echo -e "${GREEN}[OK]${NC} ZMK workspace à jour"
        else
            echo -e "${YELLOW}[ATTENTION]${NC} west update a rencontré des problèmes."
            echo "  Vérifier $ZMK_WORKSPACE manuellement si besoin."
        fi
    else
        echo -e "${YELLOW}[INFO]${NC} ZMK workspace absente — skip (sera créée par setup_zmk.sh à la demande)."
    fi

    # vial-qmk repo (référence layouts compatibles QMK)
    VIAL_QMK_DIR="$HOME/.keyboard_firmware_maker/vial-qmk"
    if [ -d "$VIAL_QMK_DIR/.git" ]; then
        echo "Mise à jour de vial-qmk (git pull)..."
        if git -C "$VIAL_QMK_DIR" pull --ff-only 2>&1 | tail -3; then
            echo -e "${GREEN}[OK]${NC} vial-qmk à jour"
        else
            echo -e "${YELLOW}[ATTENTION]${NC} git pull vial-qmk a échoué."
        fi
    fi
    echo ""
fi

# ── Lancement ─────────────────────────────────────────────────────────────────
echo ""
python3 "$SCRIPT_DIR/main.py"
