import httpx

from ai_platform.config import settings
from ai_platform.providers import PROVIDERS, is_ready

_client = httpx.AsyncClient(timeout=settings.llm_timeout)


class LLMError(Exception):
    pass


def _chain(provider: str | None) -> list[str]:
    if provider:  # explicit provider => fallback nahi
        return [provider]
    fallbacks = [p.strip() for p in settings.llm_fallbacks.split(",") if p.strip()]
    return [settings.llm_provider, *fallbacks]


async def _call(name: str, prompt: str) -> str:
    p = PROVIDERS[name]
    headers = {"Authorization": f"Bearer {p.api_key}"} if p.api_key else {}
    r = await _client.post(
        f"{p.base_url}/chat/completions",
        headers=headers,
        json={
            "model": p.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": settings.llm_max_tokens,
        },
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


async def generate(prompt: str, provider: str | None = None) -> tuple[str, str]:
    """Returns (reply, provider_used)."""
    errors: list[str] = []
    for name in _chain(provider):
        if name not in PROVIDERS:
            errors.append(f"{name}: unknown provider")
            continue
        if not is_ready(name):
            errors.append(f"{name}: API key missing")
            continue
        try:
            return await _call(name, prompt), name
        except httpx.HTTPStatusError as e:
            errors.append(f"{name}: HTTP {e.response.status_code}")
        except httpx.HTTPError as e:
            errors.append(f"{name}: {type(e).__name__}")
    raise LLMError("; ".join(errors))