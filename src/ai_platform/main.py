import dspy

from ai_platform.dspy_setup import get_lm
from ai_platform.rag import RAG
from ai_platform.schemas import AskRequest

import asyncio
import time
from collections.abc import AsyncIterator

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse

from ai_platform.cache import SemanticCache
from ai_platform.config import settings
from ai_platform.llm import LLMError, generate
from ai_platform.providers import PROVIDERS, is_ready
from ai_platform.schemas import ChatRequest, ChatResponse

app = FastAPI(title="Enterprise AI Gateway")
cache = SemanticCache()
rag = RAG()


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/providers")
async def providers():
    return {
        "active": settings.llm_provider,
        "fallbacks": settings.llm_fallbacks,
        "available": {
            name: {"model": p.model, "ready": is_ready(name)}
            for name, p in PROVIDERS.items()
        },
    }


# --- Phase 2 concurrency demo ---
@app.get("/async-wait")
async def async_wait():
    await asyncio.sleep(1)
    return {"mode": "async-nonblocking"}


@app.get("/blocking-bad")
async def blocking_bad():
    time.sleep(1)  # BAD: event loop block kare 6e
    return {"mode": "async-but-blocking"}


@app.get("/sync-def")
def sync_def():
    time.sleep(1)
    return {"mode": "sync-threadpool"}


# --- Chat: cache -> LLM (dynamic provider) ---
@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    t0 = time.perf_counter()
    provider_used: str | None = None

    hit = await asyncio.to_thread(cache.get, req.message) if req.use_cache else None
    if hit:
        reply, source = hit[0], "cache"
    else:
        try:
            reply, provider_used = await generate(req.message, req.provider)
        except LLMError as e:
            raise HTTPException(status_code=502, detail=str(e))
        source = "llm"
        if req.use_cache:
            await asyncio.to_thread(cache.put, req.message, reply)

    return ChatResponse(
        reply=reply,
        session_id=req.session_id,
        source=source,
        provider=provider_used,
        latency_ms=round((time.perf_counter() - t0) * 1000, 1),
    )


# --- SSE streaming demo ---
async def token_stream(message: str) -> AsyncIterator[str]:
    for word in f"Streaming reply for: {message}".split():
        yield f"data: {word}\n\n"
        await asyncio.sleep(0.15)
    yield "data: [DONE]\n\n"


@app.post("/ask")
async def ask(req: AskRequest):
    def run():
        # per-request provider switch
        with dspy.context(lm=get_lm(req.provider)):
            return rag(question=req.question, department=req.department)

    try:
        pred = await asyncio.to_thread(run)  # DSPy sync che + embedding CPU kaam
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "answer": pred.answer,
        "reasoning": getattr(pred, "reasoning", None) or getattr(pred, "rationale", None),
    }

@app.get("/chat/stream")
async def chat_stream(message: str):
    return StreamingResponse(token_stream(message), media_type="text/event-stream")