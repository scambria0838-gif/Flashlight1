# Flashlight — Local AI Ecosystem

A fully local AI ecosystem: a central **supervisor model** reads each task,
decides which specialist should handle it, and delegates to one of **ten
specialized local agents**. Everything runs on your own machine through
[Ollama](https://ollama.com) — no cloud inference, no API keys for the
models, and **no mock data or simulations anywhere in the stack**.

```
                        ┌──────────────────────┐
        task ──────────▶│      SUPERVISOR      │  local-supervisor
                        │  (routes via real    │  (qwen2.5:1.5b)
                        │   JSON inference)    │
                        └──────────┬───────────┘
                                   │ delegates to exactly one agent
   ┌───────────┬───────────┬───────┼────────┬───────────┬────────────┐
   ▼           ▼           ▼       ▼        ▼           ▼            ▼
 coder       unreal    sysadmin_ data_    web_seo   finance_      research
                       security  analytics          crypto
 media_      devops_   general_                     │
 transcription cloud   assistant                    ▼
                                          live CoinGecko / Stooq /
                                          local Whisper tools
```

## The ten agents

| Key | Model | Specialty |
|-----|-------|-----------|
| `coder` | local-coder | Full-stack software development |
| `unreal` | local-unreal | Unreal Engine 5 (Blueprints, C++, editor automation) |
| `sysadmin_security` | local-sysadmin-security | System administration & defensive security |
| `data_analytics` | local-data-analytics | Data analytics (pandas, stats, cleaning, charts) |
| `web_seo` | local-web-seo | Web hosting, SEO & conversion optimization |
| `finance_crypto` | local-finance-crypto | Financial & crypto tracking (live price tools) |
| `research` | local-research | Knowledge research & document review |
| `media_transcription` | local-media-transcription | Media management & transcription (real Whisper tool) |
| `devops_cloud` | local-devops-cloud | DevOps, CI/CD & cloud automation |
| `general_assistant` | local-general-assistant | General assistant / fallback route |

Plus the router itself: `local-supervisor` — eleven local models total, all
built from a single shared base (`qwen2.5:1.5b`, ~1 GB), so the whole
ecosystem runs comfortably on modest hardware. To trade speed for quality,
change `FROM` in a Modelfile (e.g. to `qwen2.5:7b-instruct`) and update the
`base:` field in `config/agents.yaml`, then re-run the build script.

## No mock data — how that is enforced

- **Routing is real inference.** The supervisor model produces the routing
  decision as strict JSON. There is no keyword matcher and no hard-coded
  default; if the model can't produce a valid decision, the run fails loudly
  (`src/flashlight/supervisor.py`).
- **No offline fallback.** Every request requires a live Ollama server; if it
  is unreachable the CLI errors out instead of returning canned text
  (`src/flashlight/ollama_client.py`).
- **Live data tools.** The finance_crypto agent fetches real prices from the
  CoinGecko and Stooq public APIs and is instructed never to fabricate
  market data. The media_transcription agent transcribes audio with real
  local Whisper inference (faster-whisper) and is instructed never to claim
  it heard media without a real tool result. Tool failures are reported as
  errors, never papered over with fabricated numbers
  (`src/flashlight/tools.py`).
- **Honest-execution prompts.** Every agent's system prompt forbids claiming
  a command, build, deployment or tool call happened unless it actually ran.
- **Verification is end-to-end.** `scripts/verify.sh` exercises the live
  server, real routing, real generation and a real external API call.

## Requirements

- Linux, macOS or Windows (WSL2)
- [Ollama](https://ollama.com/download) installed (or Docker, see below)
- Python 3.10+
- ~1 GB disk for the base model; 4 GB+ RAM (any modern CPU is fine at
  this model size; a GPU makes it faster)

## Setup

```bash
# 1. Start the Ollama server (skip if it is already running)
ollama serve            # or: docker compose up -d

# 2. Pull the base model, build all 11 agent models, install the CLI
scripts/setup.sh

# (or build just the models without the Python layer)
scripts/build_ollama_models.sh

# 3. Verify the live system end to end
flashlight --check
scripts/verify.sh
```

## Usage

```bash
# Let the supervisor route the task
flashlight "set up a github actions workflow that deploys on tag push"
# [supervisor] -> devops_cloud (local-devops-cloud): CI/CD deployment task

flashlight "profile and fix hitches in my UE5 Niagara effect"
# [supervisor] -> unreal ...

# Live market data via a real tool call
flashlight "what are bitcoin and ethereum trading at right now?"
# [supervisor] -> finance_crypto
#   [tool] get_crypto_price({'coin_ids': 'bitcoin,ethereum'})

# Real local transcription (pip install 'flashlight[media]' first)
flashlight --agent media_transcription "transcribe ~/recordings/meeting.mp3"

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
3. Add the matching `ollama create` line to `scripts/build_ollama_models.sh`
   and re-run it (existing models are reused; only the new one is built).

To give an agent a real tool, implement it in `src/flashlight/tools.py`,
add its JSON schema to `TOOL_SCHEMAS`, and list it under the agent's
`tools:` in the registry.

## Layout

```
config/agents.yaml              agent registry (single source of truth)
modelfiles/*.Modelfile          system prompt + parameters per model
src/flashlight/                 orchestration: config, client, supervisor,
                                agent runner (tool loop), tools, CLI
scripts/build_ollama_models.sh  build all agent models from Modelfiles
scripts/setup.sh                pull base, build agents, install CLI
scripts/verify.sh               live end-to-end verification
docker-compose.yml              optional containerized Ollama server
```
