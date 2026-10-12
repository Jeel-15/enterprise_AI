from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    llm_provider: str = "groq"
    llm_fallbacks: str = ""
    llm_max_tokens: int = 200
    llm_timeout: float = 60

    embed_model: str = "BAAI/bge-small-en-v1.5"
    cache_threshold: float = 0.92
    qdrant_path: str = "./qdrant_data"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
        
    groq_api_key: str = ""
    groq_model: str = "llama-3.1-8b-instant"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    openrouter_api_key: str = ""
    openrouter_model: str = "openai/gpt-oss-120b:free"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    ollama_model: str = "llama3.2:1b"
    vllm_model: str = "meta-llama/Llama-3.1-8B-Instruct"
    vllm_url: str = "http://localhost:8000/v1"
    


settings = Settings()