# SEO + AEO Multi-Agent System

A Google ADK multi-agent system that takes a **niche + target URL** and runs a full
SEO **and** AEO/GEO program: analyze → conclude → strategize → implement (gated) →
document → score (before/after). Built to be grounded (no hallucinated findings),
closed-loop (measures its own impact), and safe (human checkpoints between phases).

## How it works — 3 checkpointed phases
- **Phase 1 — DIAGNOSE & STRATEGIZE** (read-only): parallel collectors (competitor,
  technical, keyword, backlink, SERP/AEO) → grounded synthesis → prioritized roadmap →
  **baseline Health Score**.
- **Phase 2 — IMPLEMENT** (gated): draft → critic refine loop → apply approved changes
  to the CMS (blocked until you approve) → change log.
- **Phase 3 — VERIFY & SCORE**: re-crawl → recompute score → **before/after** report.

Anti-hallucination is structural: instruction contracts (ROLE/MUST/MUST NOT), typed
outputs, a runtime guardrail (read-only enforcement + quota + publish gate), a
deterministic (pure-code) scoring engine, and a separate RAG knowledge base for the
qualitative playbook. See `.agents-cli-spec.md` for the full blueprint.

## Project Structure

```
seo-agent/
├── app/
│   ├── agent.py              # Root coordinator (intake + 3-phase routing)
│   ├── phases.py             # The 3-phase state machine (Sequential/Parallel/Loop)
│   ├── config.py             # Deterministic rules: thresholds, quotas, model tiers
│   ├── guardrails.py         # Instruction contracts + runtime governance callbacks
│   ├── schemas/              # Pydantic typed outputs (Finding, Roadmap, ScoreCard…)
│   ├── sub_agents/           # collectors, strategy, aeo, execution agents
│   ├── tools/                # crawler+link auditor, gsc, ga4, pagespeed/crux,
│   │                         #   semrush MCP, scoring, knowledge retrieval, cms publish
│   ├── knowledge/            # RAG corpus (curated docs) + versions.yaml
│   ├── knowledge_base/       # RAG ingest pipeline + local vector store
│   └── .env                  # API keys / integration config
├── tests/                    # Unit, integration, eval
└── pyproject.toml
```

## Expose it to other agents (A2A)
The whole system is also an **A2A (Agent2Agent) service** — other agents can discover and
call it as a standard remote agent:
```bash
uv run uvicorn app.a2a_app:a2a_app --host 0.0.0.0 --port 8001
# Agent Card: http://localhost:8001/.well-known/agent-card.json
```
Consume it from another ADK agent:
```python
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent
seo = RemoteA2aAgent(name="seo_agent",
                     agent_card="http://localhost:8001/.well-known/agent-card.json")
```

## Setup & run
1. Put your Google AI Studio key in `app/.env` (`GOOGLE_API_KEY=...`). Optional
   integrations (Semrush MCP, PageSpeed, GSC, GA4, CMS) are documented in that file.
2. Install deps: `agents-cli install` (or `uv sync`).
3. Seed the RAG knowledge base: `uv run python -m app.knowledge_base.ingest`.
4. Launch: `agents-cli playground` — then give it a niche + target URL and let it run
   Phase 1. It stops for your approval before implementing.

> Note: "indexing" is verify-only (GSC URL Inspection; Google's Indexing API is
> JobPosting/Broadcast-only), and Google's reranker is measure-only (not controllable).
> The agent optimizes what is actually controllable and reports honestly on the rest.

> 💡 Use [Gemini CLI](https://github.com/google-gemini/gemini-cli) for AI-assisted development - project context is in `GEMINI.md`.

## Requirements

Before you begin, ensure you have:
- **uv**: Python package manager (used for all dependency management in this project) - [Install](https://docs.astral.sh/uv/getting-started/installation/) ([add packages](https://docs.astral.sh/uv/concepts/dependencies/) with `uv add <package>`)
- **agents-cli**: Agents CLI - Install with `uv tool install google-agents-cli`
- **Google Cloud SDK**: For GCP services - [Install](https://cloud.google.com/sdk/docs/install)


## Quick Start

Install `agents-cli` and its skills if not already installed:

```bash
uvx google-agents-cli setup
```

Install required packages:

```bash
agents-cli install
```

Test the agent with a local web server:

```bash
agents-cli playground
```

You can also use features from the [ADK](https://adk.dev/) CLI with `uv run adk`.

## Commands

| Command              | Description                                                                                 |
| -------------------- | ------------------------------------------------------------------------------------------- |
| `agents-cli install` | Install dependencies using uv                                                         |
| `agents-cli playground` | Launch local development environment                                                  |
| `agents-cli lint`    | Run code quality checks                                                               |
| `agents-cli eval`    | Evaluate agent behavior (generate, grade, analyze, and more — see `agents-cli eval --help`) |
| `uv run pytest tests/unit tests/integration` | Run unit and integration tests                                                        |

## 🛠️ Project Management

| Command | What It Does |
|---------|--------------|
| `agents-cli scaffold enhance` | Add CI/CD pipelines and Terraform infrastructure |
| `agents-cli infra cicd` | One-command setup of entire CI/CD pipeline + infrastructure |
| `agents-cli scaffold upgrade` | Auto-upgrade to latest version while preserving customizations |

---

## Development

Edit your agent logic in `app/agent.py` and test with `agents-cli playground` - it auto-reloads on save.

## Deployment

```bash
gcloud config set project <your-project-id>
agents-cli deploy
```

To add CI/CD and Terraform, run `agents-cli scaffold enhance`.
To set up your production infrastructure, run `agents-cli infra cicd`.

## Observability

Built-in telemetry exports to Cloud Trace, BigQuery, and Cloud Logging.
