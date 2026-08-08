# AI-Powered Multi-Agent Code Review Platform

An AI-powered, multi-agent pull-request review system. It ingests git changes,
routes them through specialized AI agents (triage → core review ∥ security →
human-in-the-loop → summarizer), and surfaces findings, a live agent DAG, a
diff view, and metrics in a real-time React dashboard.

The whole pipeline runs **locally with zero credentials** in the default `demo`
mode, or against your enterprise LLM gateway when configured.

![Workflow](https://img.shields.io/badge/multi--agent-DAG-blue)
![Stack](https://img.shields.io/badge/FastAPI-React_Vite_TS-brightgreen)
![Demo mode](https://img.shields.io/badge/LLM_BACKEND-demo%20%7C%20http%20%7C%20gemini-orange)

---

## Table of Contents

- [How it works](#how-it-works)
- [Tech stack](#tech-stack)
- [Repository layout](#repository-layout)
- [Prerequisites](#prerequisites)
- [Quick start (demo, no credentials)](#quick-start-demo-no-credentials)
- [Running the full demo](#running-the-full-demo)
- [Using a real LLM backend](#using-a-real-llm-backend)
- [Reviewing your own repository](#reviewing-your-own-repository)
- [Dashboard pages](#dashboard-pages)
- [API reference](#api-reference)
- [Configuration reference](#configuration-reference)
- [Testing & quality](#testing--quality)
- [Project documentation](#project-documentation)
- [Known limitations](#known-limitations)

---

## How it works

```text
                        ┌──────────────┐
  git push / commit ──▶ │   INGESTION  │  local-git adapter / polling watcher /
   (webhook optional)   │  (X-Ingest-  │  on-demand "New Analysis"
                        │   Secret)    │
                        └──────┬───────┘
                               ▼
                        ┌──────────────┐
                        │   TRIAGE     │  routes changed files → core | security
                        └──────┬───────┘
                    ┌──────────┴──────────┐
                    ▼                     ▼
           ┌──────────────┐      ┌──────────────┐
           │ CORE REVIEW  │      │  SECURITY    │   RAG-retrieved guidelines
           │ style, bugs, │      │ OWASP, CWE   │   appended to prompts
           │ patches      │      │ confidence   │
           └──────────────┘      └──────┬───────┘
                                        ▼
                                 ┌──────────────┐
                                 │  HITL GATE   │  severe / low-confidence
                                 │  (pause &    │  security findings need an
                                 │   approve)   │  explicit human decision
                                 └──────┬───────┘
                                        ▼
                                 ┌──────────────┐
                                 │  SUMMARIZER  │  PR summary + changelog
                                 └──────┬───────┘
                                        ▼
                                 ┌──────────────┐
                                 │   PUBLISHER  │  dry-run (records comments)
                                 └──────────────┘

   Live progress → SSE events → React dashboard (DAG, diff, HITL, metrics)
```

1. **Ingestion** — a normalized `push` event is accepted via
   `POST /api/v1/ingest/git` (protected by `INGEST_SECRET`, idempotent by
   commit SHA) or on demand via `POST /api/v1/ingest/analyze`.
2. **Triage** — classifies the diff and routes files to the specialized agents.
3. **Core review ∥ Security** — run in parallel. RAG-retrieved project
   guidelines are appended to their prompts.
4. **HITL gate** — severe or low-confidence security findings pause the run at
   `waiting_hitl`; an authorized approve/reject/escalation decision resumes it.
5. **Summarizer** — synthesizes findings into a PR summary.
6. **Publication** — routes output through an adapter; the default is a
   **dry-run** that records what would be posted without touching a repository.

The frontend consumes REST resources for state and a **Server-Sent Events (SSE)**
stream for live DAG transitions, then updates the React Flow graph in real time.

## Tech stack

| Layer | Technology |
| --- | --- |
| Backend | Python 3.12, FastAPI, Uvicorn, Pydantic Settings, HTTPX |
| Frontend | React 19, TypeScript, Vite, Tailwind CSS v4, React Flow (`@xyflow/react`), React Router |
| Agents / models | Routed exclusively through the centralized GenAI Lab gateway (`https://genailab.tcs.in`) |
| Persistence | In-memory run store behind a repository interface (swappable for PostgreSQL) |
| Vector search | In-memory vector store with a deterministic offline embedder (swap for production embeddings) |
| Quality | pytest, ruff, mypy, oxlint, vitest |

## Repository layout

```text
hackathon/
├── backend/
│   ├── app/
│   │   ├── agents/          # triage, core review, security, summarizer
│   │   ├── api/routes/      # ingest, runs, hitl, rag, agents
│   │   ├── domain/          # normalized models + event schemas
│   │   ├── integrations/    # local-git adapter, publisher
│   │   ├── orchestration/   # review DAG / state machine
│   │   ├── persistence/     # run repository interface (+ in-memory impl)
│   │   ├── rag/             # chunking, embeddings, vector store, service
│   │   └── services/        # LLM gateway, demo/gemini backends, event bus
│   ├── scripts/             # seed_demo.py, watch_repo.py, post-receive hook
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── api/             # typed REST client
│   │   ├── hooks/           # SSE hook with reconnect
│   │   ├── components/      # DAGView, DiffViewer, HitlPanel, Metrics, …
│   │   ├── pages/           # Pipeline, ReviewDetail, ReviewSummary, Agents, Metrics
│   │   └── lib/             # diff parser, status helpers
│   └── (Vite + Tailwind config)
├── data/
│   ├── guidelines/          # *.md indexed into RAG at startup
│   └── repos/               # local clones used as review targets (gitignored)
├── docs/evaluation.md       # evaluation notes
├── .env.example             # safe configuration template
├── Makefile
├── CLAUDE.md / WORKFLOW.md / PLAN.md
└── README.md
```

## Prerequisites

- **Python 3.11+** (3.12 recommended) with `venv` available
- **Node.js 20+** and npm
- `git` (for reviewing local repositories)

## Quick start (demo, no credentials)

The default `LLM_BACKEND=demo` uses a deterministic offline gateway, so **no
API keys are required** to see the whole pipeline.

```bash
# 1. Clone & enter the repo
git clone <your-repo-url> && cd hackathon

# 2. One-time setup: virtualenv, backend deps, frontend deps, .env
make setup
#   (or manually):
#   python3 -m venv .venv && source .venv/bin/activate
#   pip install -r backend/requirements.txt
#   cp .env.example .env
#   cd frontend && npm install && cd ..

# 3. Start the backend (terminal 1)
source .venv/bin/activate
uvicorn backend.app.main:app --reload
#    → http://localhost:8000/docs

# 4. Start the dashboard (terminal 2)
cd frontend && npm run dev
#    → http://localhost:5173

# 5. Seed the demo reviews (terminal 3) — 3 synthetic pushes:
#    clean (0 findings) · style (2 findings) · security (HITL pause)
python backend/scripts/seed_demo.py
```

> The dashboard's **New Analysis** button analyzes the latest commit in the
> repository that `GIT_REPO_PATH` points to (or the last one reviewed). The
> seed script feeds synthetic pushes so the demo works without any repo.

## Running the full demo

1. After seeding, open `http://localhost:5173`.
2. **Pipeline** shows the runs with status, findings, and summary.
3. Open the *security* run to see:
   - the **agent DAG** — note the security node pausing at `waiting_hitl`;
   - the **diff view** with inline findings overlaid on the changed lines;
   - the **HITL panel** — approve (or reject) the checkpoint and watch the
     run resume through the summarizer to `succeeded` via SSE in real time;
   - the generated **PR summary** and per-run metrics.
4. Check the **Agents** page for gateway/model config and per-agent health, and
   the **Metrics** page for aggregate stats.

## Using a real LLM backend

All model calls go through the GenAI Lab gateway (`https://genailab.tcs.in`).
Select the backend with `LLM_BACKEND`:

| `LLM_BACKEND` | What it uses | Credentials required |
| --- | --- | --- |
| `demo` (default) | Deterministic offline gateway | none |
| `http` | GenAI Lab gateway via HTTPX | `GENAI_API_KEY`, `GENAI_GATEWAY_URL` |
| `gemini` | Google Gemini via `google-genai` SDK | `GEMINI_API_KEY`, `MODEL_GEMINI` |

```bash
# Edit .env, e.g. for the enterprise gateway:
#   LLM_BACKEND=http
#   GENAI_API_KEY=<your key>
#   GENAI_GATEWAY_URL=https://genailab.tcs.in
source .venv/bin/activate
uvicorn backend.app.main:app --reload
```

Model names default to the PLAN.md choices but are fully configurable:

| Role | `.env` var | Default model |
| --- | --- | --- |
| Triage & routing | `MODEL_TRIAGE` | `azure/genailab-maas-gpt-4o-mini` |
| Core code review | `MODEL_CORE_REVIEW` | `genailab-maas-gpt-5.3-codex` |
| Security analysis | `MODEL_SECURITY` | `azure_ai/genailab-maas-DeepSeek-R1` |
| PR summarizer | `MODEL_SUMMARIZER` | `gemini-2.5-pro` |
| Embeddings (RAG) | `MODEL_EMBEDDINGS` | `azure/genailab-maas-text-embedding-3-large` |

## Reviewing your own repository

Point the backend at any local git repo and either watch it or push to it.

```bash
# .env
GIT_REPO_PATH=/path/to/your/repo

# Option A — polling watcher (simplest): reviews HEAD on every new commit
python backend/scripts/watch_repo.py --repo /path/to/your/repo

# Option B — push-driven bare repo (no polling)
git init --bare /srv/review-hub.git
cp backend/scripts/post-receive /srv/review-hub.git/hooks/post-receive
chmod +x /srv/review-hub.git/hooks/post-receive
git remote add review /srv/review-hub.git && git push review main
```

Both paths POST the same normalized `push` event to
`POST /api/v1/ingest/git` with the `X-Ingest-Secret` header, so everything
downstream (triage → agents → HITL → summarizer → dashboard) is identical.

## Dashboard pages

| Route | Page | Purpose |
| --- | --- | --- |
| `/` | Pipeline | All review runs: status, findings, summary, hitl pending |
| `/runs/:runId` | Review detail | Agent DAG (React Flow), diff view with findings, HITL panel |
| `/runs/:runId/summary` | Review summary | Generated PR summary + per-run metrics |
| `/agents` | Agents | Gateway/model config and per-agent health |
| `/metrics` | Metrics | Aggregate review metrics |

## API reference

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/health` | Liveness probe |
| `POST` | `/api/v1/ingest/git` | Ingest a normalized push event (`X-Ingest-Secret`) |
| `POST` | `/api/v1/ingest/analyze` | Analyze the latest commit in `GIT_REPO_PATH` |
| `GET` | `/api/v1/runs` | List review runs |
| `GET` | `/api/v1/runs/{run_id}` | Run detail: status, nodes, findings, approvals, summary |
| `GET` | `/api/v1/runs/{run_id}/events` | SSE event stream (replays history for late joiners) |
| `POST` | `/api/v1/hitl/{approval_id}/decision` | `{decision: approve|reject, by}` for a HITL checkpoint |
| `GET` | `/api/v1/agents` | Agent inventory, gateway backend, models, health |
| `POST` | `/api/v1/rag/search` | RAG retrieval over indexed guidelines |
| `GET` | `/api/v1/metrics` | Aggregate metrics |

Interactive OpenAPI docs: `http://localhost:8000/docs`.

## Configuration reference

All configuration lives in `.env` (copied from `.env.example`). The full list:

| Variable | Default | Purpose |
| --- | --- | --- |
| `LLM_BACKEND` | `demo` | `demo` \| `http` \| `gemini` |
| `GENAI_GATEWAY_URL` / `GENAI_API_KEY` | `https://genailab.tcs.in` | Enterprise gateway (http backend) |
| `MODEL_*` | per PLAN.md | Model per agent role |
| `GEMINI_API_KEY` / `MODEL_GEMINI` | — | Google Gemini (gemini backend) |
| `INGEST_SECRET` | `dev-secret` | Shared secret for `POST /api/v1/ingest/git` |
| `INGESTION_SOURCE` | `local_git` | `local_git` \| `webhook` |
| `GIT_REPO_PATH` / `GIT_POLL_SECONDS` | — / `10` | Watched repo for local-git ingestion |
| `EMBEDDING_DIM` | `256` | Embedding dimension (demo embedder) |
| `RAG_GUIDELINES_DIR` | `data/guidelines` | `*.md` files indexed at startup |
| `PUBLISH_MODE` | `dry_run` | `dry_run` \| `none` |
| `CORS_ORIGINS` | `http://localhost:5173` | Comma-separated allowed origins |
| `LLM_TIMEOUT_SECONDS` / `LLM_MAX_RETRIES` | `60` / `2` | Gateway limits |

> **Frontend secrets:** if you change `INGEST_SECRET`, update
> `frontend/.env` with the same `VITE_INGEST_SECRET` (the dashboard sends it
> with "New Analysis"). It defaults to `dev-secret` to match `.env.example`.

## Testing & quality

```bash
# Backend: tests, lint, types
source .venv/bin/activate
pytest                                    # full suite (45 tests)
pytest backend/tests/test_orchestrator.py -q
ruff check backend && ruff format --check backend
mypy backend

# Frontend: tests, lint, build
cd frontend
npm run test          # vitest (single file: npm run test -- src/lib/diff.test.ts)
npm run lint          # oxlint
npm run build         # tsc -b && vite build
```

Or use the Makefile:

```bash
make test lint typecheck build
```

## Project documentation

- `PLAN.md` — the original product blueprint (requirements, model selection,
  data architecture, evaluation goals).
- `WORKFLOW.md` — the phased implementation sequence and delivery order.
- `CLAUDE.md` — guidance for AI-assisted development in this repository.
- `docs/evaluation.md` — evaluation notes and metrics.

## Known limitations

- **In-memory state** — review runs are stored in memory and reset on backend
  restart. Re-run `python backend/scripts/seed_demo.py` (or trigger a new
  analysis) to repopulate the dashboard. Persistence is isolated behind the
  `RunRepository` interface so a database-backed implementation can be swapped
  in without touching the pipeline.
- **Demo agent findings** — the `demo` gateway produces deterministic,
  pre-scripted findings so the flow is reproducible; it is not a real reviewer.
- **GitHub webhook** — the primary intake path is local-git ingestion. A
  GitHub webhook adapter (HMAC-SHA256) is a documented extension point and
  feeds the same pipeline.
- **Dry-run publishing** — comments are recorded, not posted to a real
  repository. Wire a `GitProvider` implementation to publish for real.
