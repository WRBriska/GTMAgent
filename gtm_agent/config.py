"""Configuration: Claude client and model resolution.

The client reads ``ANTHROPIC_API_KEY`` from the environment (or a ``.env`` file
if ``python-dotenv`` is installed). The model defaults to ``claude-opus-4-8``
and can be overridden with the ``GTM_MODEL`` environment variable.
"""

from __future__ import annotations

import functools
import os

import anthropic

try:  # optional convenience — load a local .env if present
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover - dotenv is optional
    pass


# Default to the most capable Opus-tier model. Opus 4.8 supports structured
# outputs and rejects sampling params (temperature/top_p/top_k), so none are
# ever sent. Override with GTM_MODEL=claude-sonnet-4-6 for a cheaper/faster run.
DEFAULT_MODEL = "claude-opus-4-8"


def get_model() -> str:
    """Return the configured Claude model id."""
    return os.getenv("GTM_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL


@functools.lru_cache(maxsize=1)
def get_client() -> anthropic.Anthropic:
    """Return a process-wide singleton Claude client.

    Credentials are resolved from the environment at request time, so this never
    fails at construction even if the key is missing — it fails on first call
    with a clear ``anthropic.AuthenticationError``.
    """
    return anthropic.Anthropic()


def has_api_key() -> bool:
    """True if an Anthropic credential is present in the environment."""
    return bool(os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN"))
