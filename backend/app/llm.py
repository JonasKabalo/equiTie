"""LLM interface — kept behind a thin protocol so the model is a one-line swap.

Default narration model is Sonnet 4.6 (``ANTHROPIC_MODEL``). Drop to Haiku 4.5 for
lowest cost, or Opus 4.8 for the best answers, by setting that env var; nothing else
changes.

The engine owns every number, so the model's job is only to choose tools and write
the answer. We omit the ``thinking`` / ``effort`` parameters for broad compatibility
(Haiku 4.5 rejects them); on a 4.6+ model you can enable adaptive thinking here.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any, Protocol, cast

import anthropic

from .config import ANTHROPIC_MODEL


@dataclass
class ToolUse:
    id: str
    name: str
    input: dict


@dataclass
class AssistantTurn:
    text: str
    tool_uses: list[ToolUse]
    stop_reason: str
    raw_content: list = field(default_factory=list)  # blocks appended back to messages


class LLM(Protocol):
    def stream(
        self, *, system: str, messages: list[dict], tools: list[dict]
    ) -> Iterator[dict]:
        """Yield ``{'type': 'text_delta', 'text': str}`` events as the answer streams,
        then exactly one ``{'type': 'turn', 'turn': AssistantTurn}``."""
        ...


def _to_turn(message: object) -> AssistantTurn:
    text_parts: list[str] = []
    tool_uses: list[ToolUse] = []
    for block in message.content:  # type: ignore[attr-defined]
        if block.type == "text":
            text_parts.append(block.text)
        elif block.type == "tool_use":
            tool_uses.append(ToolUse(id=block.id, name=block.name, input=dict(block.input)))
    return AssistantTurn(
        text="".join(text_parts),
        tool_uses=tool_uses,
        stop_reason=getattr(message, "stop_reason", None) or "end_turn",
        raw_content=list(message.content),  # type: ignore[attr-defined]
    )


class AnthropicLLM:
    """Real LLM backed by the Anthropic SDK."""

    def __init__(self, api_key: str, model: str = ANTHROPIC_MODEL, max_tokens: int = 2048) -> None:
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens

    def stream(
        self, *, system: str, messages: list[dict], tools: list[dict]
    ) -> Iterator[dict]:
        with self._client.messages.stream(
            model=self._model,
            max_tokens=self._max_tokens,
            system=system,
            messages=cast(Any, messages),
            tools=cast(Any, tools),
        ) as stream:
            for text in stream.text_stream:
                yield {"type": "text_delta", "text": text}
            final = stream.get_final_message()
        yield {"type": "turn", "turn": _to_turn(final)}
