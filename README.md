# Majority AI

A local, multi-model **council**. Several Ollama models each draft an answer,
critique each other, and a **Safeguard Overseer** synthesizes the final verdict.

The design principle: **oversight is a role, not a switch.** There is no
"disable the supervisor" mode. Anything the council proposes that would run
commands, modify files, or touch the host system is flagged **REQUIRES
APPROVAL** and never executes on its own — a human with the overseer role signs
off first.

## Requirements

- [Node.js](https://nodejs.org) 20+
- [Ollama](https://ollama.ai) running locally

## Setup

```bash
# 1. Pull a few general models (start lean)
ollama pull mistral:7b
ollama pull openhermes:7b
ollama pull llama3.1:8b

# 2. Install and run
npm install
npm start
```

Open http://localhost:8080. Toggle models on/off in the sidebar, type a prompt,
and watch the council draft → critique → verdict.

## Configuration

| Env var          | Default                  | Purpose                        |
| ---------------- | ------------------------ | ------------------------------ |
| `PORT`           | `8080`                   | Dashboard port                 |
| `OLLAMA_HOST`    | `http://127.0.0.1:11434` | Ollama endpoint                |
| `OVERSEER_MODEL` | `llama3.1:8b`            | Model that synthesizes verdict |

Edit `config/models.js` to change the roster and `config/roles.js` for the
role/permission model (Viewer, Operator, Safeguard Overseer).

## Roles

| Role                  | Can do                                         |
| --------------------- | ---------------------------------------------- |
| Viewer                | Watch council debates                          |
| Operator              | Dispatch prompts, toggle models                |
| **Safeguard Overseer**| Everything, **and** approve host-system actions |

## What this is not

This project deliberately does **not** run safety-stripped models autonomously
with root access and removable oversight. If you want to add real tool
execution later, wire it through the `/api/actions/propose` →
`/api/actions/:id/decide` approval flow so a human always signs off.
