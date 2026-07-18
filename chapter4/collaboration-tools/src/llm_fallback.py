"""Universal OpenRouter fallback for the collaboration tools' LLM clients.

Every LLM entry point in this experiment (sub-agent runs, intelligence tools,
browser-use) speaks the OpenAI-compatible API. This helper centralizes the
credential resolution so that:

  1. When OPENAI_API_KEY is present, behavior is unchanged (direct OpenAI, or a
     custom OPENAI_BASE_URL / OPENAI_MODEL if the user set them).
  2. When OPENAI_API_KEY is absent but OPENROUTER_API_KEY is present, requests
     transparently route through OpenRouter (base_url=https://openrouter.ai/api/v1)
     with the model id mapped to provider/model form.
  3. When neither is set, callers can detect "offline" and fall back to their
     deterministic mock paths (no fabricated model output).
"""

import os
from typing import Optional, Tuple


def map_model_for_openrouter(model: str) -> str:
    """Map a plain model id onto OpenRouter's `provider/model` form.

    Ids already containing "/" pass through unchanged; gpt-*/o1-*/o3-*/o4-*
    become openai/…; claude-* becomes anthropic/claude-opus-4.8.
    """
    if "/" in model:
        return model
    m = model.lower()
    if m.startswith(("gpt-", "o1-", "o3-", "o4-")):
        return f"openai/{model}"
    if m.startswith("claude-"):
        return "anthropic/claude-opus-4.8"
    return model


def has_llm() -> bool:
    """True when at least one usable LLM credential is configured."""
    return bool(os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY"))


def resolve_llm(default_model: str = "gpt-4o-mini") -> Tuple[str, Optional[str], str]:
    """Resolve (api_key, base_url, model), applying the OpenRouter fallback.

    Raises RuntimeError listing the accepted keys when neither credential is set.
    """
    model = os.getenv("OPENAI_MODEL", default_model)

    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        return api_key, os.getenv("OPENAI_BASE_URL"), model

    or_key = os.getenv("OPENROUTER_API_KEY")
    if or_key:
        return or_key, "https://openrouter.ai/api/v1", map_model_for_openrouter(model)

    raise RuntimeError(
        "No LLM key configured. Set OPENAI_API_KEY or OPENROUTER_API_KEY "
        "(universal fallback)."
    )
