#!/bin/sh
# Démarre l'interface web de Keyboard Firmware Maker avec la machine (service systemd).
#
#   sudo sh linux/installer-service-web.sh                        # portail sur cette machine
#   sudo sh linux/installer-service-web.sh --allow 192.168.1.10   # portail sur une autre machine
#   sh linux/installer-service-web.sh --print …                   # montrer le service sans l'installer
#
# Options : --allow IP[,IP…] (adresses du portail ; cette machine toujours acceptée)
#           --port 8767      --user NOM
# Enlever : sudo systemctl disable --now kfm-web && sudo rm /etc/systemd/system/kfm-web.service
set -e
ICI=$(cd "$(dirname "$0")/.." && pwd)
ALLOW=""; PORT=8767; U=${SUDO_USER:-$(id -un)}; PRINT=0
while [ $# -gt 0 ]; do
    case "$1" in
        --allow) ALLOW="$2"; shift 2 ;;
        --port) PORT="$2"; shift 2 ;;
        --user) U="$2"; shift 2 ;;
        --print) PRINT=1; shift ;;
        *) echo "option inconnue : $1"; exit 1 ;;
    esac
done
# l'environnement virtuel créé par start.sh (PySide6, Jinja2, Pillow…)
PY="$ICI/.venv/bin/python"
[ -x "$PY" ] || { echo "$PY introuvable : lancez d'abord ./start.sh une fois"; exit 1; }
# Sans --allow, écoute locale seulement ; avec, sur le réseau mais filtrée par adresse.
if [ -n "$ALLOW" ]; then HOTE="0.0.0.0"; else HOTE="127.0.0.1"; fi

UNIT="[Unit]
Description=Keyboard Firmware Maker — interface web (port $PORT)
After=network-online.target
Wants=network-online.target

[Service]
User=$U
WorkingDirectory=$ICI
Environment=QT_QPA_PLATFORM=offscreen
ExecStart=$PY \"$ICI/kfm_web.py\" --port $PORT --host $HOTE --no-browser${ALLOW:+ --allow $ALLOW}
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target"

if [ "$PRINT" = 1 ]; then echo "$UNIT"; exit 0; fi
[ "$(id -u)" = 0 ] || { echo "à lancer avec sudo (ou --print pour voir le service)"; exit 1; }
command -v systemctl >/dev/null && [ -d /run/systemd/system ] || {
    echo "systemd n'est pas actif ici (sous WSL : [boot] systemd=true dans /etc/wsl.conf, puis wsl --shutdown)."; exit 1; }
id "$U" >/dev/null
echo "$UNIT" > /etc/systemd/system/kfm-web.service
systemctl daemon-reload
systemctl enable --now kfm-web
sleep 2
systemctl --no-pager --lines=3 status kfm-web || true
echo "OK : http://127.0.0.1:$PORT${ALLOW:+ (adresses acceptées : 127.0.0.1, $ALLOW)}"
