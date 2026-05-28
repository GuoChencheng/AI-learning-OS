from __future__ import annotations

import json
from pathlib import Path

import yaml
from typer.testing import CliRunner

from ailearn.ai_runs import list_ai_runs, preview_payload, save_ai_run_artifact
from ailearn.cli import app
from ailearn.config import load_config
from ailearn.providers.base import ChatRequest, ChatResult
from ailearn.providers.openai_compatible import OpenAICompatibleProvider
from ailearn.providers.registry import build_provider, configured_provider_summaries
from ailearn.storage import init_project


def test_config_example_is_valid_and_prompt_only_default():
    config = load_config(config_path=Path("config.example.yaml"))

    assert config.prompt_only is True
    assert "openrouter" in config.providers
    assert config.providers["openrouter"].api_key_env == "OPENROUTER_API_KEY"


def test_config_loading_env_overrides(tmp_path: Path, monkeypatch):
    (tmp_path / "config.yaml").write_text(
        yaml.safe_dump({"timezone": "UTC", "default_provider": "local", "providers": {"local": {"type": "ollama", "base_url": "http://localhost:11434"}}}),
        encoding="utf-8",
    )
    monkeypatch.setenv("AI_LEARNING_OS_CONTEXT_BUDGET", "small")

    config = load_config(tmp_path)

    assert config.timezone == "UTC"
    assert config.context_budget == "small"
    assert config.default_provider == "local"


def test_provider_registry_and_missing_key(tmp_path: Path):
    (tmp_path / "config.yaml").write_text(
        yaml.safe_dump(
            {
                "providers": {
                    "mock": {
                        "type": "openai_compatible",
                        "base_url": "https://example.invalid/v1",
                        "api_key_env": "MISSING_TEST_KEY",
                        "default_model": "test-model",
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    config = load_config(tmp_path)

    provider = build_provider(config, "mock")
    ok, message = provider.test_connection()

    assert isinstance(provider, OpenAICompatibleProvider)
    assert ok is False
    assert "MISSING_TEST_KEY" in message
    assert configured_provider_summaries(config)[0]["api_key_present"] is False


def test_openai_compatible_provider_run_chat_with_mocked_http(monkeypatch):
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self):
            return json.dumps({"model": "test-model", "choices": [{"message": {"content": "mock answer"}}], "usage": {"total_tokens": 7}}).encode()

    captured = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["body"] = request.data.decode("utf-8")
        return FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    provider = OpenAICompatibleProvider(
        "mock",
        load_config(
            overrides={
                "providers": {"mock": {"type": "openai_compatible", "base_url": "https://example.test/v1", "default_model": "test-model"}}
            }
        ).providers["mock"],
    )

    result = provider.run_chat(ChatRequest(user_prompt="hello", context="selected context"))

    assert result.text == "mock answer"
    assert result.token_usage == {"total_tokens": 7}
    assert captured["url"].endswith("/chat/completions")
    assert "selected context" in captured["body"]


def test_ai_run_artifact_creation_does_not_store_api_key(tmp_path: Path):
    init_project(tmp_path)
    result = ChatResult(text="response", provider="mock", model="m", created_at="2026-05-27T00:00:00Z")

    metadata_path = save_ai_run_artifact(tmp_path, result=result, prompt_text="secret key is not here", prompt_type="prompt_file")
    text = metadata_path.read_text(encoding="utf-8") + (metadata_path.parent / "response.md").read_text(encoding="utf-8")

    assert metadata_path.exists()
    assert "api_key" not in text.lower()
    assert list_ai_runs(tmp_path)[0]["user_review_status"] == "unreviewed"


def test_context_preview_detects_records_and_raw_session_marker():
    preview = preview_payload("claim_example ref_source\n\n## AI used for\ntext")

    assert "claim_example" in preview.records_included
    assert "ref_source" in preview.references_included
    assert preview.raw_sessions_included is True


def test_gitignore_excludes_private_data_and_keeps_examples_public():
    text = Path(".gitignore").read_text(encoding="utf-8")

    assert ".env" in text
    assert "!.env.example" in text
    assert "config.yaml" in text
    assert "data/" in text
    assert "!examples/**/data/**" in text


def test_cli_provider_test_reports_missing_key(tmp_path: Path, monkeypatch):
    init_project(tmp_path)
    (tmp_path / "config.yaml").write_text(
        yaml.safe_dump(
            {
                "providers": {
                    "mock": {
                        "type": "openai_compatible",
                        "base_url": "https://example.invalid/v1",
                        "api_key_env": "MISSING_TEST_KEY",
                        "default_model": "test-model",
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(app, ["provider", "test", "mock"])

    assert result.exit_code == 1
    assert "MISSING_TEST_KEY" in result.output


def test_cli_ai_run_prompt_uses_explicit_prompt_file(tmp_path: Path, monkeypatch):
    init_project(tmp_path)
    (tmp_path / "config.yaml").write_text(
        yaml.safe_dump({"providers": {"mock": {"type": "ollama", "base_url": "http://localhost:11434", "default_model": "m"}}}),
        encoding="utf-8",
    )
    prompt_file = tmp_path / "prompt.md"
    prompt_file.write_text("claim_example: verify this", encoding="utf-8")

    class FakeProvider:
        def run_chat(self, request: ChatRequest):
            assert request.user_prompt == "claim_example: verify this"
            return ChatResult(text="mock response", provider="mock", model="m", created_at="2026-05-27T00:00:00Z")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("ailearn.cli.build_provider", lambda config, provider_id: FakeProvider())

    result = CliRunner().invoke(app, ["ai", "run-prompt", "--provider", "mock", "--prompt-file", str(prompt_file), "--yes"])

    assert result.exit_code == 0
    assert "Saved AI run artifact" in result.output
    assert list_ai_runs(tmp_path)[0]["provider"] == "mock"
