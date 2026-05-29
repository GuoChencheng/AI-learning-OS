from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner
from fastapi.testclient import TestClient

from ailearn.cli import app
from ailearn.api.app import create_app
from ailearn.db.database import Database
from ailearn.model_gateway.factory import create_model_gateway_from_env
from ailearn.model_gateway.openai_compatible import OpenAICompatibleGateway
from ailearn.settings.local_provider import public_local_provider_settings, save_local_provider_settings


def test_local_provider_settings_save_key_without_publicly_exposing_it(tmp_path: Path, monkeypatch):
    local_file = tmp_path / ".env.local"
    monkeypatch.setenv("AI_LEARN_LOCAL_PROVIDER_FILE", str(local_file))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    public = save_local_provider_settings(
        api_key="sk-test-secret",
        base_url="https://api.deepseek.com",
        fast_model="deepseek-v4-flash",
        medium_model="deepseek-v4-flash",
        strong_model="deepseek-v4-pro",
    )

    text = local_file.read_text(encoding="utf-8")
    assert "sk-test-secret" in text
    assert public["api_key_present"] is True
    assert "api_key" not in public
    assert public["base_url"] == "https://api.deepseek.com"
    assert public["fast_model"] == "deepseek-v4-flash"
    assert public["strong_model"] == "deepseek-v4-pro"
    assert public_local_provider_settings()["api_key_present"] is True


def test_gateway_factory_uses_local_provider_file(tmp_path: Path, monkeypatch):
    local_file = tmp_path / ".env.local"
    monkeypatch.setenv("AI_LEARN_LOCAL_PROVIDER_FILE", str(local_file))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    save_local_provider_settings(
        api_key="sk-local-test",
        base_url="https://api.deepseek.com",
        fast_model="deepseek-v4-flash",
        medium_model="deepseek-v4-flash",
        strong_model="deepseek-v4-pro",
    )

    gateway = create_model_gateway_from_env()

    assert isinstance(gateway, OpenAICompatibleGateway)
    assert gateway.base_url == "https://api.deepseek.com"
    assert gateway.models


def test_ui_dev_starts_frontend_process_when_requested(monkeypatch, tmp_path: Path):
    calls: list[dict[str, object]] = []

    class FakeProcess:
        def __init__(self):
            self.returncode = None

        def poll(self):
            return self.returncode

        def terminate(self):
            self.returncode = 0

        def wait(self, timeout=None):
            self.returncode = 0

    def fake_popen(args, cwd=None, env=None):
        calls.append({"args": args, "cwd": cwd, "env": env})
        return FakeProcess()

    def fake_serve_ui(root, host, port):
        assert host == "127.0.0.1"
        assert port == 8899

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("ailearn.cli.subprocess.Popen", fake_popen)
    monkeypatch.setattr("ailearn.cli.serve_ui", fake_serve_ui)

    result = CliRunner().invoke(app, ["ui", "--dev", "--port", "8899"])

    assert result.exit_code == 0
    assert calls
    assert calls[0]["args"][:3] == ["npm", "run", "dev"]
    assert calls[0]["env"]["VITE_API_PROXY_TARGET"] == "http://127.0.0.1:8899"


def test_provider_settings_api_saves_local_provider_without_returning_key(tmp_path: Path, monkeypatch):
    local_file = tmp_path / ".env.local"
    monkeypatch.setenv("AI_LEARN_LOCAL_PROVIDER_FILE", str(local_file))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    database = Database(f"sqlite:///{tmp_path / 'alpha.sqlite3'}")
    client = TestClient(create_app(database=database))

    response = client.patch(
        "/api/settings/providers",
        json={
            "api_key": "sk-local-api-test",
            "base_url": "https://api.deepseek.com",
            "fast_model": "deepseek-v4-flash",
            "medium_model": "deepseek-v4-flash",
            "strong_model": "deepseek-v4-pro",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["providers"][0]["api_key_present"] is True
    assert data["providers"][0]["base_url"] == "https://api.deepseek.com"
    assert "api_key" not in data["providers"][0]
    assert "sk-local-api-test" not in response.text
    assert "sk-local-api-test" in local_file.read_text(encoding="utf-8")
