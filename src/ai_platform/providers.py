from dataclasses import dataclass

from ai_platform.config import settings


@dataclass(frozen=True)
class Provider:
    base_url: str
    model: str
    api_key: str = ""
    needs_key: bool = True


s = settings

PROVIDERS: dict[str, Provider] = {
    "groq": Provider("https://api.groq.com/openai/v1", s.groq_model, s.groq_api_key),
    "gemini": Provider(
        "https://generativelanguage.googleapis.com/v1beta/openai",
        s.gemini_model,
        s.gemini_api_key,
    ),
    "openrouter": Provider(
        "https://openrouter.ai/api/v1", s.openrouter_model, s.openrouter_api_key
    ),
    "openai": Provider("https://api.openai.com/v1", s.openai_model, s.openai_api_key),
    # Local / self-hosted (key nathi joti)
    "ollama": Provider("http://localhost:11434/v1", s.ollama_model, needs_key=False),
    "vllm": Provider(s.vllm_url, s.vllm_model, needs_key=False),
}


def is_ready(name: str) -> bool:
    p = PROVIDERS.get(name)
    return bool(p) and (not p.needs_key or bool(p.api_key))