from __future__ import annotations

import base64
from io import BytesIO


def extract_reference_text(filename: str, text: str = "", content_base64: str | None = None) -> str:
    if text:
        return text
    if not content_base64:
        return ""
    raw = base64.b64decode(content_base64)
    if filename.lower().endswith(".pdf"):
        try:
            from pypdf import PdfReader
        except ModuleNotFoundError as exc:
            raise RuntimeError("PDF upload requires the optional pypdf dependency.") from exc
        reader = PdfReader(BytesIO(raw))
        return "\n\n".join(page.extract_text() or "" for page in reader.pages)
    return raw.decode("utf-8")
