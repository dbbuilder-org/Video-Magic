"""
AI model configuration with automatic fallback resolution.

At startup, each model slot is validated against the Gemini API.
If the preferred model is unavailable, the next candidate in the
fallback chain is selected automatically. Import resolved names
from this module — never hardcode model strings in pipeline files.
"""
import logging
import os
from typing import Optional

import httpx

log = logging.getLogger(__name__)

# Env var overrides — set these on Render to pin a specific model without a deploy.
# e.g. GEMINI_FLASH_MODEL=gemini-2.5-flash
_ENV_OVERRIDES: dict[str, str] = {
    "FLASH": "GEMINI_FLASH_MODEL",
    "IMAGEN": "IMAGEN_MODEL",
    "VEO": "VEO_MODEL",
}

# Preference chains: first available wins.
_CHAINS: dict[str, list[str]] = {
    "FLASH": [
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
        "gemini-flash-latest",
    ],
    "IMAGEN": [
        "imagen-4.0-generate-001",
        "imagen-4.0-fast-generate-001",
        "imagen-4.0-ultra-generate-001",
    ],
    "VEO": [
        "veo-3.1-generate-preview",
        "veo-3.1-fast-generate-preview",
        "veo-3.0-generate-001",
        "veo-2.0-generate-001",
    ],
}

# Resolved at startup — module-level so pipeline files can import directly.
FLASH_MODEL: str = _CHAINS["FLASH"][0]
IMAGEN_MODEL: str = _CHAINS["IMAGEN"][0]
VEO_MODEL: str = _CHAINS["VEO"][0]

_resolved: dict[str, str] = {}


def _fetch_available(api_key: str) -> set[str]:
    """Return the set of short model names available to this API key."""
    try:
        resp = httpx.get(
            "https://generativelanguage.googleapis.com/v1beta/models",
            params={"key": api_key, "pageSize": 200},
            timeout=10,
        )
        resp.raise_for_status()
        return {m["name"].removeprefix("models/") for m in resp.json().get("models", [])}
    except Exception as exc:
        log.warning("model_config: could not fetch model list: %s", exc)
        return set()


def resolve_models() -> dict[str, str]:
    """
    Validate and resolve all model slots. Called once at startup.
    Returns a dict of slot → resolved model name.
    Falls back to the first candidate if the API is unreachable.
    """
    global FLASH_MODEL, IMAGEN_MODEL, VEO_MODEL, _resolved

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        log.warning("model_config: GEMINI_API_KEY not set — using defaults")
        _resolved = {k: v[0] for k, v in _CHAINS.items()}
        _apply()
        return _resolved

    available = _fetch_available(api_key)
    if not available:
        log.warning("model_config: model list unavailable — using defaults")
        _resolved = {k: v[0] for k, v in _CHAINS.items()}
        _apply()
        return _resolved

    for slot, chain in _CHAINS.items():
        # Env var override takes priority — skip validation, trust the operator.
        env_key = _ENV_OVERRIDES.get(slot, "")
        env_val = os.environ.get(env_key, "").strip()
        if env_val and env_val.upper() != "AUTO":
            log.info("model_config: %s → %s (from env %s)", slot, env_val, env_key)
            _resolved[slot] = env_val
            continue

        chosen: Optional[str] = None
        for candidate in chain:
            if candidate in available:
                chosen = candidate
                break
        if chosen is None:
            chosen = chain[0]
            log.error(
                "model_config: no available model found for slot %s (tried %s) — using %s anyway",
                slot, chain, chosen,
            )
        else:
            preferred = chain[0]
            if chosen != preferred:
                log.warning(
                    "model_config: %s preferred=%s UNAVAILABLE — auto-upgraded to %s",
                    slot, preferred, chosen,
                )
            else:
                log.info("model_config: %s → %s ✓", slot, chosen)
        _resolved[slot] = chosen

    _apply()
    return _resolved


def _apply() -> None:
    global FLASH_MODEL, IMAGEN_MODEL, VEO_MODEL
    FLASH_MODEL = _resolved.get("FLASH", _CHAINS["FLASH"][0])
    IMAGEN_MODEL = _resolved.get("IMAGEN", _CHAINS["IMAGEN"][0])
    VEO_MODEL = _resolved.get("VEO", _CHAINS["VEO"][0])
