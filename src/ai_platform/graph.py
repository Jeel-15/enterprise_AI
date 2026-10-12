import asyncio
import operator
from typing import Annotated, TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from ai_platform.llm import generate
from ai_platform.vector_store import hybrid_search


class AgentState(TypedDict, total=False):
    question: str
    provider: str | None
    intent: str
    context: str
    approved: bool
    answer: str
    # Reducer: parallel nodes na trace list bhegi thay (replace nahi)
    trace: Annotated[list[str], operator.add]


# ---------- Nodes ----------
async def classify(state: AgentState):
    prompt = (
        "Classify the user message. Reply with exactly one word: "
        "'action' if it asks to perform a sensitive operation "
        "(send email, issue refund, approve payment, delete data), "
        "otherwise 'question'.\n\n"
        f"Message: {state['question']}"
    )
    reply, used = await generate(prompt, state.get("provider"))
    intent = "action" if "action" in reply.lower() else "question"
    return {"intent": intent, "trace": [f"classify -> {intent} ({used})"]}


async def retrieve(state: AgentState):
    hits = await asyncio.to_thread(hybrid_search, state["question"], 3)
    context = "\n".join(h.payload["text"] for h in hits)
    return {"context": context, "trace": [f"retrieve -> {len(hits)} docs"]}


def join(state: AgentState):
    return {"trace": ["join (classify + retrieve done)"]}


def route_after_join(state: AgentState) -> str:
    return "approval" if state.get("intent") == "action" else "generate"


async def generate_answer(state: AgentState):
    prompt = (
        "Answer using only the context below. "
        "If the context is not enough, say you don't know.\n\n"
        f"Context:\n{state.get('context', '')}\n\n"
        f"Question: {state['question']}"
    )
    reply, used = await generate(prompt, state.get("provider"))
    return {"answer": reply, "trace": [f"generate ({used})"]}


def approval(state: AgentState):
    # Aa line par graph PAUSE thay 6e. Resume thay tyare decision ma human no jawab male.
    # Dhyan: resume vakhte aa poru node fari chale 6e, etle interrupt pehla koi side-effect na karvo.
    decision = interrupt(
        {
            "message": "Sensitive action. Approve?",
            "question": state["question"],
        }
    )
    ok = bool(decision.get("approved"))
    return {"approved": ok, "trace": [f"approval -> {'approved' if ok else 'rejected'}"]}


def route_after_approval(state: AgentState) -> str:
    return "execute" if state.get("approved") else "reject"


def execute_action(state: AgentState):
    # Real project ma ahiya email/payment API call thase
    return {
        "answer": "Approved. (Demo: real action ahiya execute thase.)",
        "trace": ["execute_action"],
    }


def reject_action(state: AgentState):
    return {"answer": "Action rejected by human reviewer.", "trace": ["reject_action"]}


# ---------- Graph ----------
builder = StateGraph(AgentState)
builder.add_node("classify", classify)
builder.add_node("retrieve", retrieve)
builder.add_node("join", join)
builder.add_node("generate", generate_answer)
builder.add_node("approval", approval)
builder.add_node("execute", execute_action)
builder.add_node("reject", reject_action)

# Parallel fan-out
builder.add_edge(START, "classify")
builder.add_edge(START, "retrieve")
# Fan-in: banne puri thay pachhi j join chale
builder.add_edge(["classify", "retrieve"], "join")

builder.add_conditional_edges(
    "join", route_after_join, {"approval": "approval", "generate": "generate"}
)
builder.add_edge("generate", END)
builder.add_conditional_edges(
    "approval", route_after_approval, {"execute": "execute", "reject": "reject"}
)
builder.add_edge("execute", END)
builder.add_edge("reject", END)

graph = builder.compile(checkpointer=InMemorySaver())


# ---------- Helpers (API aa vapre 6e) ----------
def _format(result: dict, thread_id: str) -> dict:
    pending = result.get("__interrupt__")
    if pending:
        return {
            "status": "waiting_approval",
            "thread_id": thread_id,
            "interrupt": pending[0].value,
            "trace": result.get("trace", []),
        }
    return {
        "status": "done",
        "thread_id": thread_id,
        "answer": result.get("answer"),
        "trace": result.get("trace", []),
    }


async def run_agent(question: str, thread_id: str, provider: str | None = None) -> dict:
    config = {"configurable": {"thread_id": thread_id}}
    result = await graph.ainvoke(
        {"question": question, "provider": provider, "trace": []}, config
    )
    return _format(result, thread_id)


async def resume_agent(thread_id: str, approved: bool) -> dict:
    config = {"configurable": {"thread_id": thread_id}}
    result = await graph.ainvoke(Command(resume={"approved": approved}), config)
    return _format(result, thread_id)


async def is_waiting(thread_id: str) -> bool:
    config = {"configurable": {"thread_id": thread_id}}
    state = await graph.aget_state(config)
    return bool(state.next)