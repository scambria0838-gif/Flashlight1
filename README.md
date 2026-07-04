# Flashlight — Local AI Ecosystem

A fully local AI ecosystem: a central **supervisor model** reads each task,
decides which specialist should handle it, and delegates to one of **ten
specialized local agents**. Everything runs on your own machine through
[Ollama](https://ollama.com) — no cloud inference, no API keys for the
models, and **no mock data or simulations anywhere in the stack**.

```
                        ┌──────────────────────┐
        task ──────────▶│      SUPERVISOR      │  flashlight-supervisor
                        │  (routes via real    │  (qwen2.5:7b-instruct)
                        │   JSON inference)    │
                        └──────────┬───────────┘
                                   │ delegates to exactly one agent
   ┌───────────┬───────────┬───────┼────────┬───────────┬───────────┐
   ▼           ▼           ▼       ▼        ▼           ▼           ▼
 coder       unreal     sysadmin analytics webseo    finance     research
 media       home       general                      │
                                                     ▼
                                          live CoinGecko / Stooq /
                                          local Whisper tools
```

## The ten agents

| Key | Model | Base | Specialty |
|-----|-------|------|-----------|
| `coder` | flashlight-coder | qwen2.5-coder:7b | Software development |
| `unreal` | flashlight-unreal | qwen2.5-coder:7b | Unreal Engine game development |
| `sysadmin` | flashlight-sysadmin | llama3.1:8b | System administration & defensive security |
| `analytics` | flashlight-analytics | qwen2.5:7b-instruct | Data analytics |
| `webseo` | flashlight-webseo | llama3.1:8b | Web hosting & SEO |
| `finance` | flashlight-finance | qwen2.5:7b-instruct | Financial & crypto tracking (live price tools) |
| `research` | flashlight-research | llama3.1:8b | Knowledge research |
| `media` | flashlight-media | llama3.1:8b | Media management & transcription (real Whisper tool) |
| `home` | flashlight-home | llama3.2:3b | Residential maintenance |
| `general` | flashlight-general | llama3.2:3b | General assistant / fallback route |

Plus the router itself: `flashlight-supervisor` (qwen2.5:7b-instruct) — eleven
local models total, built from four shared base models (~18 GB).

## No mock data — how that is enforced

- **Routing is real inference.** The supervisor model produces the routing
  decision as strict JSON. There is no keyword matcher and no hard-coded
  default; if the model can't produce a valid decision, the run fails loudly
  (`src/flashlight/supervisor.py`).
- **No offline fallback.** Every request requires a live Ollama server; if it
  is unreachable the CLI errors out instead of returning canned text
  (`src/flashlight/ollama_client.py`).
- **Live data tools.** The finance agent fetches real prices from the
  CoinGecko and Stooq public APIs and is instructed never to quote prices
  from memory. The media agent transcribes audio with real local Whisper
  inference (faster-whisper) and is instructed never to invent transcript
  text. Tool failures are reported as errors, never papered over with
  fabricated numbers (`src/flashlight/tools.py`).
- **Verification is end-to-end.** `scripts/verify.sh` exercises the live
  server, real routing, real generation and a real external API call.

## Requirements

- Linux, macOS or Windows (WSL2)
- [Ollama](https://ollama.com/download) installed (or Docker, see below)
- Python 3.10+
- ~18 GB disk for the base models; 8 GB+ RAM (16 GB recommended;
  an NVIDIA/Apple-silicon GPU makes the 7B/8B models much faster)

## Setup

```bash
# 1. Start the Ollama server (skip if it is already running)
ollama serve            # or: docker compose up -d

# 2. Pull base models, build all 11 agent models, install the CLI
scripts/setup.sh

# 3. Verify the live system end to end
flashlight --check
scripts/verify.sh
```

## Usage

```bash
# Let the supervisor route the task
flashlight "my kitchen faucet is dripping, how do I fix it"
# [supervisor] -> home (flashlight-home): plumbing question

flashlight "profile and fix hitches in my UE5 Niagara effect"
# [supervisor] -> unreal ...

# Live market data via a real tool call
flashlight "what are bitcoin and ethereum trading at right now?"
# [supervisor] -> finance
#   [tool] get_crypto_price({'coin_ids': 'bitcoin,ethereum'})

# Real local transcription (pip install 'flashlight[media]' first)
flashlight --agent media "transcribe ~/recordings/meeting.mp3"

# Bypass routing
flashlight --agent coder "write a rate limiter in Go"

# Interactive session (routed per message, keeps history)
flashlight --chat

# Inspect / verify the registry
flashlight --list
flashlight --check
```

## Extending the ecosystem

1. Write a Modelfile in `modelfiles/` (base model + `SYSTEM` prompt).
2. Add an entry under `agents:` in `config/agents.yaml` — the supervisor's
   routing prompt is generated from this file, so the new agent is
   immediately routable.
3. Re-run `scripts/setup.sh` (existing models are reused; only the new one
   is built).

To give an agent a real tool, implement it in `src/flashlight/tools.py`,
add its JSON schema to `TOOL_SCHEMAS`, and list it under the agent's
`tools:` in the registry.

## Layout

```
config/agents.yaml        agent registry (single source of truth)
modelfiles/*.Modelfile    system prompt + parameters per model
src/flashlight/           orchestration: config, client, supervisor,
                          agent runner (tool loop), tools, CLI
scripts/setup.sh          pull bases, build agents, install CLI
scripts/verify.sh         live end-to-end verification
docker-compose.yml        optional containerized Ollama server
```
