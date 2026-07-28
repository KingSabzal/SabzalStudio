"""Adapter between the model router and this project's settings.

The router was written against a settings object with lowercase keys such as
``router9_url``. This project stores settings under environment-style names
such as ``ROUTER9_URL``, in config.json, with a .env fallback. Rather than
rewrite the router, which is the piece most worth keeping intact, this maps
between the two.
"""

from __future__ import annotations

import os
from typing import Any

# Router key -> the setting name this project uses.
KEY_MAP = {
    "llm_provider": "LLM_PROVIDER",
    "router9_url": "ROUTER9_URL",
    "router9_key": "ROUTER9_KEY",
    "openrouter_key": "OPENROUTER_API_KEY",
    "nvidia_nim_key": "NVIDIA_NIM_KEY",
    "nvidia_nim_url": "NVIDIA_NIM_URL",
    "cloudflare_account_id": "CLOUDFLARE_ACCOUNT_ID",
    "cloudflare_api_token": "CLOUDFLARE_API_TOKEN",
    "llm_model": "LLM_MODEL",
}


class RouterConfig:
    """Read-only settings view with the key names the router expects."""

    def get(self, key: str, default: Any = None) -> Any:
        name = KEY_MAP.get(key, key.upper())
        value = os.getenv(name)
        if value is None or value == "":
            return default
        return value

    def __getitem__(self, key: str) -> Any:
        return self.get(key)


_CONFIG = RouterConfig()


def get_config() -> RouterConfig:
    """The settings view the router uses."""
    return _CONFIG
