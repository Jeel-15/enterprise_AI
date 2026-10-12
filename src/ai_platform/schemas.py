from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    session_id: str | None = None
    provider: str | None = None   # optional override: "groq", "gemini", ...
    use_cache: bool = True


class ChatResponse(BaseModel):
    reply: str
    session_id: str | None = None
    source: str = "llm"           # "llm" ya "cache"
    provider: str | None = None   # kayo provider vapryo
    latency_ms: float = 0.0
    
class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    department: str | None = None
    provider: str | None = None
    
class AgentRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    thread_id: str | None = None
    provider: str | None = None


class ResumeRequest(BaseModel):
    approved: bool