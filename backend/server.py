"""
Lightweight API for serving FormulaCast prediction JSON.

Run from the project root:
    python -m backend.server

Endpoints:
    GET /api/health
    GET /api/predictions/races.json
    GET /api/predictions/<year>/round_<n>.json
    GET /api/predictions/future/index.json
    GET /api/predictions/future/<year>_round_<n>.json
"""

import argparse
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from backend.main import BASE_DIR

PREDICTIONS_DIR = (Path(BASE_DIR) / "data" / "predictions").resolve()


class FormulaCastHandler(BaseHTTPRequestHandler):
    server_version = "FormulaCastAPI/1.0"

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(HTTPStatus.NO_CONTENT)
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path == "/api/health":
            self._send_json({"ok": True, "predictions_dir": str(PREDICTIONS_DIR)})
            return

        prefix = "/api/predictions/"
        if path.startswith(prefix):
            self._send_prediction_file(path[len(prefix):])
            return

        self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)

    def _send_prediction_file(self, relative_path):
        requested = (PREDICTIONS_DIR / unquote(relative_path)).resolve()
        if not requested.is_relative_to(PREDICTIONS_DIR) or requested.suffix != ".json":
            self._send_json({"error": "Invalid prediction path"}, status=HTTPStatus.BAD_REQUEST)
            return

        if not requested.exists() or not requested.is_file():
            self._send_json({"error": "Prediction file not found"}, status=HTTPStatus.NOT_FOUND)
            return

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        with open(requested, "rb") as f:
            self.wfile.write(f.read())

    def _send_json(self, payload, status=HTTPStatus.OK):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    parser = argparse.ArgumentParser(description="Serve FormulaCast prediction JSON")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8000, type=int)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), FormulaCastHandler)
    print(f"FormulaCast API serving {PREDICTIONS_DIR}")
    print(f"http://{args.host}:{args.port}/api/health")
    server.serve_forever()


if __name__ == "__main__":
    main()
