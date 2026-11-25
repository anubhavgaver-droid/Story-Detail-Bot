"""webserver.py — Render free web service ke liye keep-alive server + self ping"""
import os
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

import config as C


# ───────────── Render keep-alive web server ─────────────
class Ping(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Story bot is running")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

    def log_message(self, *a):
        pass


def run_web():
    HTTPServer(("0.0.0.0", C.PORT), Ping).serve_forever()


def self_ping():
    url = os.getenv("RENDER_EXTERNAL_URL")
    while url:
        time.sleep(C.SELF_PING_SECONDS)
        try:
            urllib.request.urlopen(url, timeout=20)
        except Exception:
            pass


