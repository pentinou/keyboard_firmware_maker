#!/usr/bin/env bash
# setup_zmk.sh — Installe le Zephyr SDK (lourd, ~1 Go) pour la compilation ZMK locale.
# Lancé à la demande depuis KFM au premier build ZMK, ou manuellement.
# Idempotent : relancer n'annule rien si la version cible est déjà présente.
set -e

RED='\033[0;31m'; YELLOW='\033[1;33m'; GREEN='\033[0;32m'; BOLD='\033[1m'; NC='\033[0m'

echo -e "${BOLD}=== Installation Zephyr SDK pour ZMK ===${NC}"
echo ""

# ── Activation du venv KFM si présent ─────────────────────────────────────────
# Garantit que `pip install west` cible le même Python que celui utilisé par KFM.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KFM_VENV="$SCRIPT_DIR/../.venv"
if [ -f "$KFM_VENV/bin/activate" ]; then
    # shellcheck disable=SC1091
    source "$KFM_VENV/bin/activate"
    echo -e "${GREEN}[OK]${NC} venv KFM activé ($KFM_VENV)"
else
    echo -e "${YELLOW}[INFO]${NC} Pas de venv KFM détecté — lancez d'abord start.sh pour de meilleurs résultats."
fi

# Version du Zephyr SDK compatible avec Zephyr 3.5+ (utilisé par ZMK).
ZEPHYR_SDK_VERSION="0.17.0"
CACHE_DIR="$HOME/.keyboard_firmware_maker"
SDK_DIR="$CACHE_DIR/zephyr-sdk-$ZEPHYR_SDK_VERSION"

# Détection arch
ARCH="$(uname -m)"
case "$ARCH" in
    x86_64)  SDK_ARCH="x86_64" ;;
    aarch64) SDK_ARCH="aarch64" ;;
    *)
        echo -e "${RED}[ERREUR]${NC} Architecture non supportée : $ARCH"
        exit 1
        ;;
esac

ARCHIVE="zephyr-sdk-${ZEPHYR_SDK_VERSION}_linux-${SDK_ARCH}_minimal.tar.xz"
URL="https://github.com/zephyrproject-rtos/sdk-ng/releases/download/v${ZEPHYR_SDK_VERSION}/${ARCHIVE}"

mkdir -p "$CACHE_DIR"

# Le toolchain est ce qui valide une install complète : sans lui, ./setup.sh
# n'a jamais réussi (cmake manquant, interruption, etc.) et le SDK est à moitié extrait.
TOOLCHAIN_DIR="$SDK_DIR/arm-zephyr-eabi"

# ── Skip si déjà installé (SDK + toolchain) ───────────────────────────────────
if [ -d "$TOOLCHAIN_DIR" ] && [ -d "$SDK_DIR/cmake" ]; then
    echo -e "${GREEN}[OK]${NC} Zephyr SDK $ZEPHYR_SDK_VERSION déjà installé : $SDK_DIR"
    echo "    (Pour forcer une réinstallation : rm -rf \"$SDK_DIR\")"
else
    # ── Vérifs prérequis ──────────────────────────────────────────────────────
    for cmd in wget tar xz python3 cmake; do
        if ! command -v "$cmd" &>/dev/null; then
            echo -e "${RED}[ERREUR]${NC} $cmd introuvable. Installez-le puis relancez."
            exit 1
        fi
    done

    # ── Téléchargement + extraction (sauté si squelette déjà présent) ─────────
    if [ -f "$SDK_DIR/setup.sh" ]; then
        echo -e "${YELLOW}[INFO]${NC} Squelette SDK déjà extrait, install du toolchain seulement."
    else
        echo "Téléchargement de $ARCHIVE (~200 Mo)..."
        wget -q --show-progress -O "$CACHE_DIR/$ARCHIVE" "$URL"

        echo "Extraction..."
        tar -xJf "$CACHE_DIR/$ARCHIVE" -C "$CACHE_DIR"
        rm -f "$CACHE_DIR/$ARCHIVE"

        if [ ! -f "$SDK_DIR/setup.sh" ]; then
            echo -e "${RED}[ERREUR]${NC} Extraction échouée : $SDK_DIR/setup.sh introuvable."
            exit 1
        fi
        echo -e "${GREEN}[OK]${NC} Zephyr SDK extrait dans $SDK_DIR"
    fi

    # ── Installation toolchain ARM + host tools ───────────────────────────────
    echo "Installation du toolchain arm-zephyr-eabi + host tools (peut prendre plusieurs minutes)..."
    (cd "$SDK_DIR" && ./setup.sh -t arm-zephyr-eabi -c -h)

    if [ ! -d "$TOOLCHAIN_DIR" ]; then
        echo -e "${RED}[ERREUR]${NC} Toolchain arm-zephyr-eabi introuvable après setup.sh."
        exit 1
    fi
    echo -e "${GREEN}[OK]${NC} Toolchain arm-zephyr-eabi installé."
fi

# ── Vérification west ─────────────────────────────────────────────────────────
if ! command -v west &>/dev/null && ! python3 -c "import west" &>/dev/null; then
    echo -e "${YELLOW}[INFO]${NC} west manquant — installation..."
    pip install -q west
fi

# ── Python bindings protobuf (requis par protoc-gen-nanopb) ───────────────────
# nanopb_generator.py fait `import google.protobuf` pendant la compilation ZMK Studio.
if ! python3 -c "import google.protobuf" &>/dev/null; then
    echo -e "${YELLOW}[INFO]${NC} google.protobuf Python manquant — installation..."
    pip install -q protobuf grpcio-tools
fi

# ── protoc (Protocol Buffers) ─────────────────────────────────────────────────
# Requis par nanopb pour générer les stubs RPC de ZMK Studio pendant la compilation.
if ! command -v protoc &>/dev/null; then
    echo -e "${YELLOW}[INFO]${NC} protoc introuvable — tentative d'installation automatique..."
    if command -v apt-get &>/dev/null; then
        sudo apt-get install -y protobuf-compiler
    elif command -v dnf &>/dev/null; then
        sudo dnf install -y protobuf-compiler
    elif command -v pacman &>/dev/null; then
        sudo pacman -S --noconfirm --needed protobuf
    elif command -v brew &>/dev/null; then
        brew install protobuf
    else
        echo -e "${RED}[ERREUR]${NC} Aucun gestionnaire de paquets reconnu (apt/dnf/pacman/brew)."
        echo "  Installez manuellement protobuf-compiler puis relancez."
        exit 1
    fi
    if ! command -v protoc &>/dev/null; then
        echo -e "${RED}[ERREUR]${NC} Installation de protoc échouée."
        exit 1
    fi
    echo -e "${GREEN}[OK]${NC} protoc installé : $(protoc --version)"
else
    echo -e "${GREEN}[OK]${NC} protoc déjà présent : $(protoc --version)"
fi

echo ""
echo -e "${GREEN}${BOLD}=== Setup ZMK terminé ===${NC}"
echo ""
echo "Variables utiles (exportées automatiquement par KFM au build) :"
echo "  ZEPHYR_SDK_INSTALL_DIR=$SDK_DIR"
echo ""
echo "Pour compiler un zmk-config manuellement :"
echo "  cd <zmk-config>"
echo "  west init -l config"
echo "  west update"
echo "  west build -s zmk/app -b nice_nano_v2 -- -DSHIELD=<shield>_left -DZMK_CONFIG=\"\$PWD/config\""
