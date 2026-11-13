#!/usr/bin/env python3
"""Réveil du serveur de calcul (Wake-on-LAN) : POST / envoie le « paquet magique » à
l'adresse MAC configurée. Écoute en local seulement ; nginx le place derrière le SSO."""
import os
import socket
from http.server import BaseHTTPRequestHandler, HTTPServer

MAC = os.environ["WAKE_MAC"]
PORT = int(os.environ["WAKE_PORT"])
# diffusion générale + celle du réseau du serveur de calcul (x.y.z.255), calculée à l'installation
CIBLES = ["255.255.255.255"] + [c for c in os.environ.get("WAKE_BROADCAST", "").split(",") if c]


def paquet_magique(mac):
    octets = bytes.fromhex(mac.replace(":", "").replace("-", ""))
    return b"\xff" * 6 + octets * 16


class Reveil(BaseHTTPRequestHandler):
    def do_POST(self):
        p = paquet_magique(MAC)
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            for cible in CIBLES:
                for port in (9, 7):
                    s.sendto(p, (cible, port))
        corps = b'{"ok": true}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(corps)))
        self.end_headers()
        self.wfile.write(corps)

    def log_message(self, fmt, *args):
        print(f"réveil demandé ({MAC})", flush=True)


HTTPServer(("127.0.0.1", PORT), Reveil).serve_forever()
