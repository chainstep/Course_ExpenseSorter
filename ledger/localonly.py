"""Local-only guard. Refuses to start if a cloud LLM provider is configured."""
from __future__ import annotations

import os
import sys
from pathlib import Path

CLOUD_ENV_VARS = (
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "GOOGLE_API_KEY",
    "MOONSHOT_API_KEY",
)

CLOUD_PROVIDER_KEYS = (
    "anthropic",
    "openai",
    "google",
    "moonshot",
    "openrouter",
)


def _opencode_json_providers() -> list[str]:
    import json as _json

    candidates = [
        Path.cwd() / "opencode.json",
        Path.cwd() / "opencode.jsonc",
        Path.home() / ".config" / "opencode" / "opencode.json",
        Path.home() / ".config" / "opencode" / "opencode.jsonc",
    ]
    providers: list[str] = []
    for path in candidates:
        if not path.exists():
            continue
        try:
            data = _json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        prov = data.get("provider", {}) or {}
        if isinstance(prov, dict):
            providers.extend(str(k).lower() for k in prov.keys())
    return providers


def check(allow_skip: bool = False) -> list[str]:
    """Return a list of reasons the local-only guard would block startup.

    Empty list = OK. If `allow_skip` is True, the function returns an
    empty list regardless (used for explicit dev escape hatches).
    """
    if allow_skip:
        return []
    reasons: list[str] = []
    for var in CLOUD_ENV_VARS:
        if os.environ.get(var):
            reasons.append(f"env {var} is set")
    for prov in _opencode_json_providers():
        for key in CLOUD_PROVIDER_KEYS:
            if key in prov:
                reasons.append(f"opencode provider '{prov}' looks like a cloud provider")
                break
    return reasons


def assert_local_only(allow_skip: bool = False) -> None:
    reasons = check(allow_skip=allow_skip)
    if reasons:
        msg = "Refusing to start — local-only mode violated:\n  - " + "\n  - ".join(reasons)
        print(msg, file=sys.stderr)
        raise SystemExit(2)


__all__ = ["check", "assert_local_only", "CLOUD_ENV_VARS"]