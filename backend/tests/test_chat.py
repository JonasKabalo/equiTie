"""Chat orchestration + endpoint — driven by a fake LLM (no API key, no spend)."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.chat import run_chat
from app.data import DataStore
from app.llm import AssistantTurn, ToolUse
from app.main import app, get_llm


class FakeLLM:
    """Replays scripted turns and records the messages it last saw."""

    def __init__(self, turns: list[tuple[list[str], AssistantTurn]]) -> None:
        self._turns = turns
        self._i = 0
        self.seen_messages: list[dict] | None = None

    def stream(self, *, system: str, messages: list[dict], tools: list[dict]) -> Iterator[dict]:
        self.seen_messages = [dict(m) for m in messages]
        deltas, turn = self._turns[self._i]
        self._i += 1
        for delta in deltas:
            yield {"type": "text_delta", "text": delta}
        yield {"type": "turn", "turn": turn}


def _portfolio_then_answer() -> FakeLLM:
    return FakeLLM(
        [
            (
                [],
                AssistantTurn(
                    text="",
                    tool_uses=[ToolUse(id="tu1", name="get_portfolio_overview", input={})],
                    stop_reason="tool_use",
                    raw_content=[
                        {
                            "type": "tool_use",
                            "id": "tu1",
                            "name": "get_portfolio_overview",
                            "input": {},
                        }
                    ],
                ),
            ),
            (
                ["Your portfolio ", "looks healthy."],
                AssistantTurn(
                    text="Your portfolio looks healthy.",
                    tool_uses=[],
                    stop_reason="end_turn",
                    raw_content=[{"type": "text", "text": "Your portfolio looks healthy."}],
                ),
            ),
        ]
    )


@pytest.fixture(autouse=True)
def _clear_overrides() -> Iterator[None]:
    yield
    app.dependency_overrides.clear()


def test_run_chat_executes_tool_then_answers(store: DataStore) -> None:
    fake = _portfolio_then_answer()
    events = list(run_chat(fake, store, "INV001", "How is my portfolio?"))
    kinds = [e["event"] for e in events]
    assert "tool" in kinds  # the model called a tool
    assert "token" in kinds  # narration streamed
    assert kinds[-1] == "done"

    # The tool actually ran against the engine and grounded facts were fed back.
    assert fake.seen_messages is not None
    tool_result_msg = fake.seen_messages[-1]
    assert tool_result_msg["role"] == "user"
    assert "has_holdings" in tool_result_msg["content"][0]["content"]


def test_chat_endpoint_streams_sse(store: DataStore) -> None:
    app.dependency_overrides[get_llm] = _portfolio_then_answer
    client = TestClient(app)
    r = client.post("/api/chat/INV001", json={"question": "How is my portfolio?"})
    assert r.status_code == 200
    assert "event: tool" in r.text
    assert "event: token" in r.text
    assert "event: done" in r.text


def test_chat_unknown_investor_404() -> None:
    app.dependency_overrides[get_llm] = _portfolio_then_answer
    client = TestClient(app)
    r = client.post("/api/chat/INV999", json={"question": "hi"})
    assert r.status_code == 404


def test_chat_empty_question_422() -> None:
    app.dependency_overrides[get_llm] = _portfolio_then_answer
    client = TestClient(app)
    r = client.post("/api/chat/INV001", json={"question": ""})
    assert r.status_code == 422


def test_chat_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    client = TestClient(app)
    r = client.post("/api/chat/INV001", json={"question": "hi"})
    assert r.status_code == 503
