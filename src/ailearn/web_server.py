from __future__ import annotations

import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote

from .api.app import AILearnOSApp, create_core_app
from .web_api import handle_api_request


def _json_bytes(data: dict[str, Any]) -> bytes:
    return json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")


class LearningOSRequestHandler(BaseHTTPRequestHandler):
    root: Path = Path.cwd()
    static_dir: Path | None = None
    api_core: AILearnOSApp | None = None

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("content-length", "0"))
        if length <= 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw) if raw.strip() else {}

    def _send_json(self, status: int, data: dict[str, Any]) -> None:
        body = _json_bytes(data)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def _send_static(self) -> None:
        if self.static_dir is None:
            self._send_json(404, {"error": "Frontend build not found. Run npm run build or use npm run dev."})
            return
        requested = self.path.split("?", 1)[0].lstrip("/") or "index.html"
        candidate = (self.static_dir / requested).resolve()
        if not str(candidate).startswith(str(self.static_dir.resolve())) or not candidate.is_file():
            candidate = self.static_dir / "index.html"
        if not candidate.is_file():
            self._send_json(404, {"error": "Frontend index.html not found."})
            return
        body = candidate.read_bytes()
        content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_local_file(self) -> None:
        decoded = unquote(self.path.split("?", 1)[0].removeprefix("/files/"))
        requested = Path(decoded)
        candidate = requested.resolve() if requested.is_absolute() else (self.root / requested).resolve()
        try:
            candidate.relative_to(self.root.resolve())
        except ValueError:
            self._send_json(403, {"error": "Local file access is limited to this project."})
            return
        if not candidate.is_file():
            self._send_json(404, {"error": f"File not found: {decoded}"})
            return
        body = candidate.read_bytes()
        content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        self._send_json(200, {"ok": True})

    def _handle(self, method: str) -> None:
        if self.path.startswith("/api/"):
            payload = self._read_json() if method in {"POST", "PUT", "PATCH"} else None
            if self.api_core is not None:
                status, data = self.api_core.handle(method, self.path, payload or {})
                if status != 404:
                    self._send_json(status, data if isinstance(data, dict) else {"items": data})
                    return
            response = handle_api_request(method, self.path, payload, self.root)
            self._send_json(response.status, response.data)
            return
        if method == "GET" and self.path.startswith("/files/"):
            self._send_local_file()
            return
        self._send_static()

    def do_GET(self) -> None:
        self._handle("GET")

    def do_POST(self) -> None:
        self._handle("POST")

    def do_PUT(self) -> None:
        self._handle("PUT")

    def do_PATCH(self) -> None:
        self._handle("PATCH")


def serve_ui(root: Path | str = ".", host: str = "127.0.0.1", port: int = 8765, static_dir: Path | None = None) -> None:
    base = Path(root).resolve()
    frontend_dist = static_dir or (base / "web" / "dist")
    core = create_core_app()

    class Handler(LearningOSRequestHandler):
        root = base
        static_dir = frontend_dist if frontend_dist.exists() else None
        api_core = core

    server = ThreadingHTTPServer((host, port), Handler)
    print(f"ai-learning-os UI: http://{host}:{port}")
    print(f"Project root: {base}")
    if Handler.static_dir is None:
        print("Frontend build not found; API is available, or run `npm run dev` from web/ for Vite.")
    server.serve_forever()
