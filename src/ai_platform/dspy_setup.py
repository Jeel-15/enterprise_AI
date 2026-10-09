import dspy

from ai_platform.config import settings
from ai_platform.providers import PROVIDERS, is_ready


def get_lm(provider: str | None = None) -> dspy.LM:
    name = provider or settings.llm_provider
    if name not in PROVIDERS:
        raise ValueError(f"unknown provider: {name}")
    if not is_ready(name):
        raise ValueError(f"{name}: API key missing")
    p = PROVIDERS[name]
    # Custom api_base sathe "openai/" prefix lagavvo (OpenAI-compatible endpoints mate)
    return dspy.LM(
        f"openai/{p.model}",
        api_key=p.api_key or "none",
        api_base=p.base_url,
        max_tokens=600,
    )