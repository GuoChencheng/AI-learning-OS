from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4


def now_utc() -> datetime:
    return datetime.now(UTC)


def new_id(prefix: str) -> str:
    safe_prefix = prefix.strip().lower().replace("-", "_").replace(" ", "_")
    timestamp = now_utc().strftime("%Y%m%d%H%M%S")
    suffix = uuid4().hex[:8]
    return f"{safe_prefix}_{timestamp}_{suffix}"
