"""Flashlight command-line interface.

Usage:
  flashlight "task description"          route via supervisor and run
  flashlight --agent coder "task"        bypass routing, use one agent
  flashlight --chat [--agent KEY]        interactive session
  flashlight --list                      show the agent registry
  flashlight --check                     verify Ollama + all models are live
"""

from __future__ import annotations

import argparse
import sys

from .agents import run_agent
from .config import ConfigError, load_registry
from .ollama_client import OllamaClient, OllamaError
from .supervisor import RoutingError, route


def _err(msg: str) -> int:
    print(f"error: {msg}", file=sys.stderr)
    return 1


def _print_tool_call(name: str, args: dict) -> None:
    print(f"  [tool] {name}({args})", file=sys.stderr)


def cmd_list(registry) -> int:
    print(f"Supervisor: {registry.supervisor.model} "
          f"(base {registry.supervisor.base})")
    print("Agents:")
    for key, spec in registry.agents.items():
        tools = f"  tools: {', '.join(spec.tools)}" if spec.tools else ""
        print(f"  {key:<10} {spec.model:<22} base {spec.base}{tools}")
        print(f"             {spec.description}")
    return 0


def cmd_check(client: OllamaClient, registry) -> int:
    client.health()
    print(f"Ollama server reachable at {registry.ollama_host}")
    available = client.list_models()
    missing = [
        spec.model
        for spec in registry.all_specs()
        if spec.model not in available
    ]
    for spec in registry.all_specs():
        status = "MISSING" if spec.model in missing else "ok"
        print(f"  {spec.model:<24} {status}")
    if missing:
        print(
            "\nSome agent models are not built yet. Run: scripts/setup.sh",
            file=sys.stderr,
        )
        return 1
    print("\nAll models present. The ecosystem is fully operational.")
    return 0


def _dispatch(client, registry, task: str) -> int:
    decision = route(client, registry, task)
    spec = registry.agents[decision.agent_key]
    print(
        f"[supervisor] -> {decision.agent_key} ({spec.model}): "
        f"{decision.reason}",
        file=sys.stderr,
    )
    messages = [{"role": "user", "content": task}]
    for chunk in run_agent(client, spec, messages, on_tool_call=_print_tool_call):
        print(chunk, end="", flush=True)
    print()
    return 0


def cmd_chat(client, registry, agent_key: str | None) -> int:
    history: list[dict] = []
    fixed_spec = registry.agents[agent_key] if agent_key else None
    label = agent_key or "supervisor-routed"
    print(f"Flashlight chat ({label}). Ctrl-D or 'exit' to quit.")
    while True:
        try:
            task = input("\nyou> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not task or task.lower() in {"exit", "quit"}:
            return 0

        if fixed_spec:
            spec = fixed_spec
        else:
            decision = route(client, registry, task)
            spec = registry.agents[decision.agent_key]
            print(f"[supervisor] -> {decision.agent_key}", file=sys.stderr)

        history.append({"role": "user", "content": task})
        print(f"{spec.key}> ", end="", flush=True)
        reply_parts = []
        for chunk in run_agent(
            client, spec, history, on_tool_call=_print_tool_call
        ):
            reply_parts.append(chunk)
            print(chunk, end="", flush=True)
        print()
        history.append({"role": "assistant", "content": "".join(reply_parts)})


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="flashlight",
        description="Local AI ecosystem: a supervisor model delegating to "
                    "specialized local agents via Ollama.",
    )
    parser.add_argument("task", nargs="?", help="task to route and execute")
    parser.add_argument("--agent", help="bypass the supervisor; run this agent")
    parser.add_argument("--chat", action="store_true", help="interactive mode")
    parser.add_argument("--list", action="store_true", help="show the registry")
    parser.add_argument("--check", action="store_true",
                        help="verify server and models are live")
    parser.add_argument("--config", help="path to agents.yaml")
    args = parser.parse_args(argv)

    try:
        registry = load_registry(args.config)
    except ConfigError as exc:
        return _err(str(exc))

    if args.list:
        return cmd_list(registry)

    client = OllamaClient(registry.ollama_host)

    if args.agent and args.agent not in registry.agents:
        return _err(
            f"unknown agent {args.agent!r}; valid: {', '.join(registry.agents)}"
        )

    try:
        if args.check:
            return cmd_check(client, registry)

        client.health()

        if args.chat:
            return cmd_chat(client, registry, args.agent)

        if not args.task:
            parser.print_help()
            return 2

        if args.agent:
            spec = registry.agents[args.agent]
            for chunk in run_agent(
                client, spec,
                [{"role": "user", "content": args.task}],
                on_tool_call=_print_tool_call,
            ):
                print(chunk, end="", flush=True)
            print()
            return 0

        return _dispatch(client, registry, args.task)
    except (OllamaError, RoutingError) as exc:
        return _err(str(exc))


if __name__ == "__main__":
    sys.exit(main())
