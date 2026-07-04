"""Thin HTTP client for a locally running Ollama server.

All inference in Flashlight goes through this client to a live Ollama
instance. If the server is unreachable the calls raise — there is no
offline fallback and no synthetic response path.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

import requests


class OllamaError(RuntimeError):
    pass


class OllamaUnavailable(OllamaError):
    pass


class OllamaClient:
    def __init__(self, host: str, timeout: float = 600.0):
        self.host = host.rstrip("/")
        self.timeout = timeout

    def health(self) -> None:
        """Raise OllamaUnavailable unless a live Ollama server responds."""
        try:
            resp = requests.get(f"{self.host}/api/version", timeout=5)
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise OllamaUnavailable(
                f"No Ollama server reachable at {self.host}. "
                "Start it with `ollama serve` (or `docker compose up -d`) "
                "and run `scripts/setup.sh` if you have not yet built the "
                "agent models."
            ) from exc

    def list_models(self) -> set[str]:
        resp = requests.get(f"{self.host}/api/tags", timeout=10)
        resp.raise_for_status()
        models = resp.json().get("models") or []
        names = set()
        for m in models:
            name = m.get("name", "")
            names.add(name)
            names.add(name.split(":", 1)[0])
        return names

    def chat(
        self,
        model: str,
        messages: list[dict[str, Any]],
        *,
        fmt: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Non-streaming chat. Returns the final message dict."""
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
        }
        if fmt:
            payload["format"] = fmt
        if tools:
            payload["tools"] = tools
        if options:
            payload["options"] = options

        resp = requests.post(
            f"{self.host}/api/chat", json=payload, timeout=self.timeout
        )
        if resp.status_code != 200:
            raise OllamaError(
                f"Ollama /api/chat returned {resp.status_code} for model "
                f"{model!r}: {resp.text[:500]}"
            )
        body = resp.json()
        message = body.get("message")
        if message is None:
            raise OllamaError(f"Malformed Ollama response: {body!r:.500}")
        return message

    def chat_stream(
        self,
        model: str,
        messages: list[dict[str, Any]],
        *,
        options: dict[str, Any] | None = None,
    ) -> Iterator[str]:
        """Streaming chat. Yields content chunks as the model generates."""
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": True,
        }
        if options:
            payload["options"] = options

        with requests.post(
            f"{self.host}/api/chat",
            json=payload,
            stream=True,
            timeout=self.timeout,
        ) as resp:
            if resp.status_code != 200:
                raise OllamaError(
                    f"Ollama /api/chat returned {resp.status_code} for model "
                    f"{model!r}: {resp.text[:500]}"
                )
            for line in resp.iter_lines():
                if not line:
                    continue
                chunk = json.loads(line)
                if "error" in chunk:
                    raise OllamaError(f"Ollama error: {chunk['error']}")
                content = (chunk.get("message") or {}).get("content", "")
                if content:
                    yield content
                if chunk.get("done"):
                    return
