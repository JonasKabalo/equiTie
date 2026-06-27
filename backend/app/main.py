"""FastAPI application.

Endpoints: health, the investor picker list, a portfolio endpoint (deterministic
engine), and the streaming chat endpoint (Claude tool-use over the same engine).
"""

from __future__ import annotations

import os
from dataclasses import asdict
from typing import Annotated, Literal

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from .chat import run_chat, sse_format
from .config import REPORT_DATE
from .data import get_store
from .llm import LLM, AnthropicLLM
from .metrics import build_portfolio

load_dotenv()  # read backend/.env if present (ANTHROPIC_API_KEY, ANTHROPIC_MODEL)

app = FastAPI(title="EquiTie Investor Assistant API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

store = get_store()


# -- request models -----------------------------------------------------------
class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    history: list[ChatMessage] = Field(default_factory=list, max_length=20)


# -- dependencies -------------------------------------------------------------
def get_llm() -> LLM:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="Chat is unavailable: set ANTHROPIC_API_KEY in backend/.env",
        )
    return AnthropicLLM(api_key=api_key)


# -- endpoints ----------------------------------------------------------------
@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "report_date": REPORT_DATE.isoformat(),
        "chat_enabled": bool(os.environ.get("ANTHROPIC_API_KEY")),
        "counts": {
            "investors": int(len(store.investors)),
            "companies": int(len(store.companies)),
            "deals": int(len(store.deals)),
            "allocations": int(len(store.allocations)),
        },
    }


@app.get("/api/investors")
def list_investors() -> list[dict]:
    """The investor picker: id, name and the profile fields used for personalisation."""
    deals_per_investor = (
        store.allocations.groupby("investor_id")["deal_id"].nunique().to_dict()
    )
    out: list[dict] = []
    for _, inv in store.investors.iterrows():
        investor_id = str(inv["investor_id"])
        tech = inv["tech_savviness"]  # str, or float NaN when absent
        out.append(
            {
                "investor_id": investor_id,
                "investor_name": str(inv["investor_name"]),
                "investor_type": str(inv["investor_type"]),
                "reporting_currency": str(inv["reporting_currency"]),
                "tech_savviness": None if isinstance(tech, float) else str(tech),
                "kyc_status": str(inv["kyc_status"]),
                "num_deals": int(deals_per_investor.get(investor_id, 0)),
            }
        )
    return out


@app.get("/api/portfolio/{investor_id}")
def portfolio(investor_id: str) -> dict:
    if not store.has_investor(investor_id):
        raise HTTPException(status_code=404, detail=f"Unknown investor {investor_id!r}")
    return asdict(build_portfolio(store, investor_id))


@app.post("/api/chat/{investor_id}")
def chat(
    investor_id: str,
    body: ChatRequest,
    llm: Annotated[LLM, Depends(get_llm)],
) -> StreamingResponse:
    if not store.has_investor(investor_id):
        raise HTTPException(status_code=404, detail=f"Unknown investor {investor_id!r}")
    history = [m.model_dump() for m in body.history]
    events = run_chat(llm, store, investor_id, body.question, history=history)
    return StreamingResponse(
        (sse_format(event) for event in events),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
