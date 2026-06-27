"""Chat orchestration — a streaming agentic loop.

The loop: stream the model's turn (tokens go straight to the client), and if it
asks for tools, run them against the deterministic engine (scoped to this
investor), feed the facts back, and continue. Citations from every tool result are
collected and emitted at the end.

It is a generator of plain event dicts so it can be unit-tested with a fake LLM
(no API key, no spend) and wrapped as SSE by the API layer.
"""

from __future__ import annotations

import json
from collections.abc import Iterator

from .data import DataStore
from .llm import LLM
from .prompt import build_system_prompt
from .tools import TOOLS, dispatch, extract_citations

MAX_TOOL_ROUNDS = 6


def run_chat(
    llm: LLM,
    store: DataStore,
    investor_id: str,
    question: str,
    history: list[dict] | None = None,
) -> Iterator[dict]:
    system = build_system_prompt(store, investor_id)
    messages: list[dict] = list(history or [])
    messages.append({"role": "user", "content": question})
    citations: list[dict] = []

    for _ in range(MAX_TOOL_ROUNDS):
        turn = None
        for event in llm.stream(system=system, messages=messages, tools=TOOLS):
            if event["type"] == "text_delta":
                yield {"event": "token", "data": {"text": event["text"]}}
            elif event["type"] == "turn":
                turn = event["turn"]

        if turn is None:
            break
        messages.append({"role": "assistant", "content": turn.raw_content})
        if turn.stop_reason != "tool_use":
            break

        results = []
        for tool_use in turn.tool_uses:
            yield {"event": "tool", "data": {"name": tool_use.name, "input": tool_use.input}}
            facts = dispatch(store, investor_id, tool_use.name, tool_use.input)
            citations.extend(extract_citations(facts))
            results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": json.dumps(facts, default=str),
                }
            )
        messages.append({"role": "user", "content": results})

    yield {"event": "done", "data": {"citations": _dedupe(citations)}}


def _dedupe(citations: list[dict]) -> list[dict]:
    seen: set[tuple] = set()
    out: list[dict] = []
    for c in citations:
        key = (c["source"], c["row_id"])
        if key not in seen:
            seen.add(key)
            out.append(c)
    return out


def sse_format(event: dict) -> str:
    """Format one orchestrator event as a Server-Sent Event frame."""
    return f"event: {event['event']}\ndata: {json.dumps(event['data'])}\n\n"
