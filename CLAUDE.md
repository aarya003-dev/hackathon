# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

The repository currently contains the product blueprint in `PLAN.md`; application code is not scaffolded yet. The target is a Python FastAPI backend and a React/Vite frontend for an AI-powered, multi-agent pull-request review system.

Use `WORKFLOW.md` as the implementation sequence. Keep the phases vertical and contract-first so the backend and dashboard can be developed independently against stable review-run and event schemas.

## Target architecture

- `backend/`: FastAPI application, domain schemas, orchestration, integrations, persistence, RAG, and backend tests.
- `frontend/`: React + TypeScript + Vite dashboard. Tailwind CSS is the styling layer; React Flow renders the live agent DAG; an SSE client receives execution updates.
- `infra/`: local PostgreSQL/vector-store services and development fixtures.
- `docs/`: API/event contracts, evaluation notes, and architecture decisions.
- `tests/`: cross-service/e2e fixtures and synthetic review cases.

The backend is the system of record for review runs. Normalize provider-specific Git and model payloads at integration boundaries. The orchestration layer should persist agent transitions and expose normalized findings, summaries, HITL checkpoints, and metrics to the frontend. Model access must go through the configured GenAI Lab gateway, not directly from React.

RAG lives in `backend/app/rag/`: chunking, a deterministic offline embedder (`EMBEDDING_DIM`, swapped for the real embedding gateway in production), and an in-memory vector store scoped by repository/source-type. `data/guidelines/*.md` are indexed at startup; the orchestrator appends top-k retrieved guidance to the core and security agents' prompts. Exposed via `POST /api/v1/rag/index` and `/search`.

The intended flow is:

1. Ingestion is authenticated and normalized. The default path is local-git (a bare-repo `post-receive` hook or a polling watcher); the GitHub webhook adapter is an optional second path for when the app is deployed.
2. PR metadata, diff, history, and build results are ingested.
3. Triage routes files/functions to core-review and security agents, with RAG context.
4. Severe or uncertain security findings pause the run at a HITL checkpoint.
5. Findings are synthesized into a summary and published through an output
   adapter (`backend/app/integrations/publisher.py`); the demo uses
   `DryRunPublisher` (`PUBLISH_MODE=dry_run`), which records what would be
   posted without touching a repository.
6. The dashboard consumes REST resources and SSE events to show the run, diff findings, DAG state, and metrics.

The frontend (Vite + React + TS + Tailwind v4) uses `src/api/client.ts` as its
typed REST client, a reconnecting SSE hook (`src/hooks/useRunEvents.ts`), and a
poll fallback while a run is non-terminal. `npm run build` runs `tsc -b` then
`vite build`; `npm run lint` is `oxlint`; `npm run test` is vitest (single-file:
`npm run test -- src/lib/diff.test.ts`). `backend/scripts/seed_demo.py` seeds a
running backend with synthetic review fixtures for the demo.

## Python environment and configuration

Create the environment from the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate       # Windows: .venv\\Scripts\\activate
python -m pip install --upgrade pip
pip install -r backend/requirements.txt
```

Configuration belongs in a local `.env`, which must not be committed. Keep `.env.example` updated with variable names and safe placeholders. Load settings through a Pydantic settings module rather than reading environment variables throughout the application. Expected configuration includes the GenAI Lab gateway URL/model names, `LLM_BACKEND` (`demo` default | `http` | `gemini`, where `gemini` uses the `google-genai` SDK with `GEMINI_API_KEY`/`MODEL_GEMINI`), `INGESTION_SOURCE` (`local_git` | `webhook`) and `INGEST_SECRET`, `GIT_REPO_PATH`/`GIT_POLL_SECONDS`, Git webhook secrets, database URL, vector-store settings, CORS origins, and runtime limits.

## Common commands

Backend (from the repository root, with `.venv` active):

```bash
uvicorn backend.app.main:app --reload
pytest
pytest backend/tests/test_orchestrator.py -q
ruff check .
ruff format --check .
mypy backend
```

Local-git ingestion (no deployment / port forwarding needed):

```bash
# Option 1 - polling watcher (simplest): POSTs previous..HEAD on every commit
python -m scripts.watch_repo --repo /path/to/your/repo

# Option 2 - push-driven bare repo
git init --bare /srv/review-hub.git
cp backend/scripts/post-receive /srv/review-hub.git/hooks/post-receive
chmod +x /srv/review-hub.git/hooks/post-receive
# in your repo:
git remote add review /srv/review-hub.git && git push review main
```

Frontend:

```bash
cd frontend
npm install
npm run dev
npm run lint
npm run build
npm run test
npm run test -- src/path/to/file.test.tsx
```

The exact frontend test command may change with the selected runner; preserve a single-file test command in `frontend/package.json` and update this file if it changes.

## Implementation constraints

- Keep credentials and proprietary code out of source, logs, fixtures, and committed configuration.
- Verify ingestion authentication: `INGEST_SECRET` on the local-git route (`POST /api/v1/ingest/git`), HMAC-SHA256 on the webhook route. Make ingestion idempotent by commit SHA.
- Treat repository diffs as untrusted content; preserve prompt-injection boundaries when sending them to model adapters.
- Keep model/provider clients behind backend interfaces with deterministic fakes for tests.
- Enforce valid HITL state transitions and authorization on approval actions.
- Prefer synthetic/anonymized PR fixtures and dry-run publishing for local demos.
- Add or update tests alongside each vertical slice; run focused tests before the full suite.
