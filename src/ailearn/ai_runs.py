from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

from .ids import new_id, now_utc
from .providers.base import ChatResult


@dataclass(frozen=True)
class ContextPreview:
    source_path: str | None
    size_bytes: int
    records_included: list[str]
    references_included: list[str]
    raw_sessions_included: bool
    raw_references_included: bool


def preview_payload(text: str, source_path: Path | str | None = None) -> ContextPreview:
    record_ids = sorted(set(re.findall(r"\b(?:goal|claim|der|pos|test|dist|misc|ref|policy|visual|cluster|session)_[A-Za-z0-9_.-]+", text)))
    reference_ids = [record_id for record_id in record_ids if record_id.startswith("ref_")]
    raw_sessions = "Selected Session Excerpts" in text or "## AI used for" in text
    raw_references = bool(re.search(r"\b(full reference|paper text|pdf text)\b", text, flags=re.IGNORECASE))
    return ContextPreview(
        source_path=str(source_path) if source_path else None,
        size_bytes=len(text.encode("utf-8")),
        records_included=record_ids,
        references_included=reference_ids,
        raw_sessions_included=raw_sessions,
        raw_references_included=raw_references,
    )


def ai_runs_dir(root: Path | str = ".") -> Path:
    return Path(root) / "data" / "ai_runs"


def save_ai_run_artifact(
    root: Path | str,
    *,
    result: ChatResult,
    prompt_text: str,
    prompt_type: str,
    related_record_ids: list[str] | None = None,
    context_pack_path: Path | str | None = None,
    prompt_file_path: Path | str | None = None,
) -> Path:
    run_id = new_id("airun")
    run_dir = ai_runs_dir(root) / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    response_path = run_dir / "response.md"
    response_path.write_text(result.text, encoding="utf-8")
    metadata: dict[str, Any] = {
        "id": run_id,
        "provider": result.provider,
        "model": result.model,
        "prompt_type": prompt_type,
        "related_record_ids": related_record_ids or [],
        "context_pack_path": str(context_pack_path) if context_pack_path else None,
        "prompt_file_path": str(prompt_file_path) if prompt_file_path else None,
        "created_at": result.created_at or now_utc().isoformat(),
        "response_path": str(response_path),
        "user_review_status": "unreviewed",
        "prompt_sha256": hashlib.sha256(prompt_text.encode("utf-8")).hexdigest(),
        "prompt_size_bytes": len(prompt_text.encode("utf-8")),
        "token_usage": result.token_usage,
        "raw_metadata": result.raw_metadata,
    }
    (run_dir / "metadata.yaml").write_text(yaml.safe_dump(metadata, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return run_dir / "metadata.yaml"


def list_ai_runs(root: Path | str = ".") -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    directory = ai_runs_dir(root)
    if not directory.exists():
        return items
    for path in sorted(directory.glob("*/metadata.yaml"), reverse=True):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        data["metadata_path"] = str(path)
        items.append(data)
    return items


def load_ai_run(root: Path | str, run_id: str) -> tuple[dict[str, Any], str]:
    for metadata in list_ai_runs(root):
        if run_id in {metadata.get("id"), Path(str(metadata.get("metadata_path"))).parent.name}:
            response_path = Path(str(metadata["response_path"]))
            if not response_path.is_absolute():
                response_path = Path(root) / response_path
            response = response_path.read_text(encoding="utf-8") if response_path.exists() else ""
            return metadata, response
    raise FileNotFoundError(f"AI run not found: {run_id}")


def preview_as_dict(preview: ContextPreview) -> dict[str, Any]:
    return asdict(preview)
