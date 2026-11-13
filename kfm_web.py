#!/usr/bin/env python3
"""Keyboard Firmware Maker — interface web.  python kfm_web.py [--port 8767] [--no-browser]"""
import argparse

from web import server

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Interface web de Keyboard Firmware Maker")
    ap.add_argument("--port", type=int, default=8767, help="port de l'interface (défaut 8767)")
    ap.add_argument("--no-browser", action="store_true", help="ne pas ouvrir le navigateur")
    ap.add_argument("--host", default="127.0.0.1",
                    help="adresse d'écoute (défaut 127.0.0.1 ; 0.0.0.0 = réseau local, sans authentification)")
    ap.add_argument("--allow", default="",
                    help="adresses autorisées en plus de cette machine, séparées par des virgules (ex. celle du portail YunoHost)")
    a = ap.parse_args()
    server.serve(a.port, not a.no_browser, a.host, [x.strip() for x in a.allow.split(",") if x.strip()])
