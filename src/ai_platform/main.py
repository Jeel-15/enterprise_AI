import asyncio
import json
import time
import uuid

import dspy
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from ai_platform.cache import SemanticCache
from ai_platform.config import settings
from ai_platform.dspy_setup import get_lm
from ai_platform.graph import is_waiting, resume_agent, run_agent
from ai_platform.llm import LLMError, generate, stream_generate
from ai_platform.providers import PROVIDERS, is_ready
from ai_platform.rag import RAG
from ai_platform.schemas import (
    AgentRequest,
    AskRequest,
    ChatRequest,
    ChatResponse,
    ResumeRequest,
)

app = FastAPI(title="Enterprise AI Gateway")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)

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


# --- Chat (poro answer ek sathe) ---
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


# --- Chat (real token streaming, SSE) ---
def sse(obj: dict) -> str:
    return f"data: {json.dumps(obj)}\n\n"


async def chat_events(req: ChatRequest):
    t0 = time.perf_counter()

    def ms() -> float:
        return round((time.perf_counter() - t0) * 1000, 1)

    try:
        hit = await asyncio.to_thread(cache.get, req.message) if req.use_cache else None
        if hit:
            yield sse({"type": "meta", "source": "cache"})
            yield sse({"type": "token", "text": hit[0]})
            yield sse({"type": "done", "source": "cache", "provider": None,
                       "latency_ms": ms(), "ttft_ms": ms()})
            return

        yield sse({"type": "meta", "source": "llm"})
        parts: list[str] = []
        provider_used: str | None = None
        ttft: float | None = None

        async for token, provider_used in stream_generate(req.message, req.provider):
            if ttft is None:
                ttft = ms()
            parts.append(token)
            yield sse({"type": "token", "text": token})

        answer = "".join(parts)
        if req.use_cache and answer:
            await asyncio.to_thread(cache.put, req.message, answer)

        yield sse({"type": "done", "source": "llm", "provider": provider_used,
                   "latency_ms": ms(), "ttft_ms": ttft})
    except LLMError as e:
        yield sse({"type": "error", "message": str(e)})


@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    return StreamingResponse(
        chat_events(req),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# --- DSPy RAG ---
@app.post("/ask")
async def ask(req: AskRequest):
    def run():
        with dspy.context(lm=get_lm(req.provider)):
            return rag(question=req.question, department=req.department)

    try:
        pred = await asyncio.to_thread(run)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "answer": pred.answer,
        "reasoning": getattr(pred, "reasoning", None) or getattr(pred, "rationale", None),
    }


# --- LangGraph agent (human-in-the-loop) ---
@app.post("/agent")
async def agent(req: AgentRequest):
    thread_id = req.thread_id or str(uuid.uuid4())
    try:
        return await run_agent(req.question, thread_id, req.provider)
    except LLMError as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.post("/agent/{thread_id}/resume")
async def agent_resume(thread_id: str, req: ResumeRequest):
    if not await is_waiting(thread_id):
        raise HTTPException(status_code=404, detail="No paused run for this thread")
    return await resume_agent(thread_id, req.approved)