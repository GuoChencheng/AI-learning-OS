from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class Response:
    status_code: int
    _json: Any

    def json(self) -> Any:
        return self._json


class TestClient:
    __test__ = False

    def __init__(self, app: Any) -> None:
        self.app = app
        self._delegate: Any | None = None
        if not hasattr(app, "handle"):
            from fastapi.testclient import TestClient as FastAPITestClient

            self._delegate = FastAPITestClient(app)

    def get(self, path: str) -> Response:
        if self._delegate is not None:
            response = self._delegate.get(path)
            return Response(response.status_code, response.json())
        return self._request("GET", path, None)

    def post(self, path: str, json: dict[str, Any] | None = None, files: Any = None) -> Response:
        if self._delegate is not None:
            response = self._delegate.post(path, json=json, files=files)
            return Response(response.status_code, response.json())
        payload = dict(json or {})
        if files:
            payload["_files"] = files
        return self._request("POST", path, payload)

    def patch(self, path: str, json: dict[str, Any] | None = None) -> Response:
        if self._delegate is not None:
            response = self._delegate.patch(path, json=json)
            return Response(response.status_code, response.json())
        return self._request("PATCH", path, json or {})

    def _request(self, method: str, path: str, payload: dict[str, Any] | None) -> Response:
        status, data = self.app.handle(method, path, payload or {})
        return Response(status, data)
