"""The supervisor: routes each task to a specialist via real inference.

Routing is always performed by the supervisor model itself. There is no
keyword matcher and no default shortcut — if the model cannot produce a
valid routing decision within the configured retries, the run fails
loudly rather than silently degrading.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from .config import Registry
from .ollama_client import OllamaClient, OllamaError

FALLBACK_KEY = "general_assistant"


class RoutingError(RuntimeError):
    pass


@dataclass
class RoutingDecision:
    agent_key: str
    reason: str


def _registry_prompt(registry: Registry, task: str) -> str:
    lines = ["Agent registry:"]
    for key, spec in registry.agents.items():
        marker = " (fallback)" if key == FALLBACK_KEY else ""
        lines.append(f"- {key}{marker}: {spec.description}")
    lines.append("")
    lines.append("Task to route:")
    lines.append(task)
    lines.append("")
    lines.append(
        'Respond with JSON only: {"agent": "<agent_key>", "reason": "<why>"}'
    )
    return "\n".join(lines)


def route(client: OllamaClient, registry: Registry, task: str) -> RoutingDecision:
    prompt = _registry_prompt(registry, task)
    messages = [{"role": "user", "content": prompt}]
    attempts = max(1, registry.routing_retries + 1)
    last_error = "no attempts made"

    for attempt in range(attempts):
        try:
            message = client.chat(
                registry.supervisor.model,
                messages,
                fmt="json",
                options={"temperature": 0.1},
            )
        except OllamaError as exc:
            raise RoutingError(f"Supervisor inference failed: {exc}") from exc

        content = (message.get("content") or "").strip()
        try:
            decision = json.loads(content)
            agent_key = str(decision["agent"]).strip().lower()
            reason = str(decision.get("reason", "")).strip()
        except (json.JSONDecodeError, KeyError, TypeError):
            last_error = f"invalid routing JSON: {content[:200]!r}"
        else:
            if agent_key in registry.agents:
                return RoutingDecision(agent_key=agent_key, reason=reason)
            last_error = f"unknown agent key: {agent_key!r}"

        # Feed the error back so the model can correct itself on retry.
        if attempt < attempts - 1:
            messages.append({"role": "assistant", "content": content})
            messages.append(
                {
                    "role": "user",
                    "content": (
                        f"That response was rejected ({last_error}). Respond "
                        "again with JSON only, and 'agent' must be one of: "
                        + ", ".join(registry.agents)
                    ),
                }
            )

    raise RoutingError(
        f"Supervisor failed to produce a valid routing decision after "
        f"{attempts} attempts. Last problem: {last_error}"
    )
