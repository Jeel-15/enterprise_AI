import json

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


def _headers(api_key: str) -> dict:
    return {"Authorization": f"Bearer {api_key}"} if api_key else {}


async def _call(name: str, prompt: str) -> str:
    p = PROVIDERS[name]
    r = await _client.post(
        f"{p.base_url}/chat/completions",
        headers=_headers(p.api_key),
        json={
            "model": p.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": settings.llm_max_tokens,
        },
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


async def generate(prompt: str, provider: str | None = None) -> tuple[str, str]:
    """Returns (reply, provider_used). Poro answer ek sathe."""
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


async def stream_generate(prompt: str, provider: str | None = None):
    """Async generator: yield (token_text, provider_used).
    Fallback fakt pehla token aavya PEHLA thay 6e."""
    errors: list[str] = []
    for name in _chain(provider):
        if name not in PROVIDERS:
            errors.append(f"{name}: unknown provider")
            continue
        if not is_ready(name):
            errors.append(f"{name}: API key missing")
            continue

        p = PROVIDERS[name]
        started = False
        try:
            async with _client.stream(
                "POST",
                f"{p.base_url}/chat/completions",
                headers=_headers(p.api_key),
                json={
                    "model": p.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": settings.llm_max_tokens,
                    "stream": True,
                },
            ) as r:
                r.raise_for_status()
                async for line in r.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    choices = chunk.get("choices") or []
                    if not choices:
                        continue
                    text = (choices[0].get("delta") or {}).get("content")
                    if text:
                        started = True
                        yield text, name
            if started:
                return
            errors.append(f"{name}: empty response")
        except httpx.HTTPStatusError as e:
            if started:
                raise LLMError(f"{name}: stream failed (HTTP {e.response.status_code})")
            errors.append(f"{name}: HTTP {e.response.status_code}")
        except httpx.HTTPError as e:
            if started:
                raise LLMError(f"{name}: stream interrupted ({type(e).__name__})")
            errors.append(f"{name}: {type(e).__name__}")
    raise LLMError("; ".join(errors))