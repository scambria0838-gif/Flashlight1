"""Run a specialist agent, including its real tool-call loop."""

from __future__ import annotations

from collections.abc import Callable, Iterator

from .config import AgentSpec
from .ollama_client import OllamaClient
from .tools import TOOL_SCHEMAS, execute_tool

MAX_TOOL_ROUNDS = 5


def run_agent(
    client: OllamaClient,
    spec: AgentSpec,
    messages: list[dict],
    on_tool_call: Callable[[str, dict], None] | None = None,
) -> Iterator[str]:
    """Execute the agent on the given conversation, yielding output text.

    Agents without tools stream token-by-token. Agents with tools run a
    non-streaming tool loop first (Ollama tool calling is non-streaming),
    executing each real tool and feeding results back until the model
    answers, then yield the final answer.
    """
    if not spec.tools:
        yield from client.chat_stream(spec.model, messages)
        return

    tools = [TOOL_SCHEMAS[name] for name in spec.tools if name in TOOL_SCHEMAS]
    convo = list(messages)

    for _ in range(MAX_TOOL_ROUNDS):
        message = client.chat(spec.model, convo, tools=tools)
        tool_calls = message.get("tool_calls") or []
        if not tool_calls:
            yield message.get("content", "")
            return

        convo.append(message)
        for call in tool_calls:
            fn = call.get("function", {})
            name = fn.get("name", "")
            args = fn.get("arguments") or {}
            if on_tool_call:
                on_tool_call(name, args)
            result = execute_tool(name, args)
            convo.append({"role": "tool", "content": result})

    # Tool budget exhausted: force a final answer from what was gathered.
    convo.append(
        {
            "role": "user",
            "content": "Tool budget exhausted. Answer now using only the "
                       "tool results above; state plainly anything you "
                       "could not obtain.",
        }
    )
    message = client.chat(spec.model, convo)
    yield message.get("content", "")
