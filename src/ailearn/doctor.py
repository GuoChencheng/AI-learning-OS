from __future__ import annotations

import importlib.util
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

from .config import AppConfig, config_file_path, load_config


@dataclass(frozen=True)
class DoctorCheck:
    name: str
    ok: bool
    detail: str


def run_doctor(root: Path | str = ".") -> list[DoctorCheck]:
    base = Path(root)
    checks: list[DoctorCheck] = []
    checks.append(
        DoctorCheck(
            "Python",
            sys.version_info >= (3, 11),
            f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        )
    )
    checks.append(DoctorCheck("Package import", importlib.util.find_spec("ailearn") is not None, "ailearn importable"))
    checks.append(DoctorCheck("Data directory", (base / "data").is_dir(), str(base / "data")))
    path = config_file_path(base)
    checks.append(DoctorCheck("Config file", True, str(path) if path.exists() else "config.yaml not found; defaults apply"))
    checks.append(DoctorCheck("Web build", (base / "web" / "dist" / "index.html").is_file(), "web/dist/index.html"))
    checks.append(DoctorCheck("Node", shutil.which("node") is not None, shutil.which("node") or "node not found"))
    checks.append(DoctorCheck("npm", shutil.which("npm") is not None, shutil.which("npm") or "npm not found"))
    try:
        config = load_config(base)
        checks.extend(_provider_checks(config))
    except Exception as exc:
        checks.append(DoctorCheck("Config parse", False, str(exc)))
    return checks


def _provider_checks(config: AppConfig) -> list[DoctorCheck]:
    checks: list[DoctorCheck] = []
    if not config.providers:
        checks.append(DoctorCheck("Providers", True, "No providers configured; prompt-only mode is available."))
        return checks
    import os

    for provider_id, provider in sorted(config.providers.items()):
        if provider.api_key_env:
            checks.append(
                DoctorCheck(
                    f"Provider {provider_id} key env",
                    bool(os.getenv(provider.api_key_env)),
                    f"{provider.api_key_env} {'is set' if os.getenv(provider.api_key_env) else 'is not set'}",
                )
            )
        else:
            checks.append(DoctorCheck(f"Provider {provider_id} key env", True, "No API key required by config."))
    return checks
