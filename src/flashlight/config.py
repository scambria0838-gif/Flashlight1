"""Load and validate the agent registry from config/agents.yaml."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

DEFAULT_CONFIG = Path(__file__).resolve().parents[2] / "config" / "agents.yaml"


class ConfigError(RuntimeError):
    pass


@dataclass
class AgentSpec:
    key: str
    model: str
    base: str
    modelfile: str
    description: str
    tools: list[str] = field(default_factory=list)


@dataclass
class Registry:
    ollama_host: str
    routing_retries: int
    supervisor: AgentSpec
    agents: dict[str, AgentSpec]

    def all_specs(self) -> list[AgentSpec]:
        return [self.supervisor, *self.agents.values()]


def load_registry(path: str | os.PathLike | None = None) -> Registry:
    config_path = Path(path) if path else Path(
        os.environ.get("FLASHLIGHT_CONFIG", DEFAULT_CONFIG)
    )
    if not config_path.is_file():
        raise ConfigError(f"Config file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)

    for required in ("ollama_host", "supervisor", "agents"):
        if required not in raw:
            raise ConfigError(f"Missing required key in {config_path}: {required}")

    sup = raw["supervisor"]
    supervisor = AgentSpec(
        key="supervisor",
        model=sup["model"],
        base=sup["base"],
        modelfile=sup["modelfile"],
        description="Task router",
    )

    agents: dict[str, AgentSpec] = {}
    for key, spec in raw["agents"].items():
        agents[key] = AgentSpec(
            key=key,
            model=spec["model"],
            base=spec["base"],
            modelfile=spec["modelfile"],
            description=" ".join(str(spec["description"]).split()),
            tools=list(spec.get("tools") or []),
        )
    if not agents:
        raise ConfigError("Agent registry is empty")

    host = os.environ.get("OLLAMA_HOST_URL", raw["ollama_host"])
    return Registry(
        ollama_host=host.rstrip("/"),
        routing_retries=int(raw.get("routing_retries", 2)),
        supervisor=supervisor,
        agents=agents,
    )
