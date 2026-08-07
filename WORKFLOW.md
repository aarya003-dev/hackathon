# Project Workflow

This document turns `PLAN.md` into an implementation sequence for the code-review platform. The repository will use a small monorepo:

```text
hackathon/
├── backend/                 # FastAPI service and Python tests
│   ├── app/
│   │   ├── api/             # REST, ingest, HITL, and SSE routes
│   │   ├── agents/          # triage, code-review, security, summarizer
│   │   ├── config.py        # Pydantic settings loaded from .env
│   │   ├── integrations/    # GenAI gateway, Git provider, local-git adapters
│   │   ├── orchestration/   # review DAG/state machine
│   │   ├── persistence/     # PostgreSQL models/repositories/migrations
│   │   └── rag/             # chunking, embeddings, vector retrieval
│   ├── scripts/             # bare-repo post-receive hook, watch_repo.py poller
│   └── tests/
├── frontend/                # React + TypeScript + Vite dashboard
│   └── src/
│       ├── api/             # typed REST and SSE clients
│       ├── features/        # reviews, agents, HITL, diff, metrics
│       └── components/
├── data/                    # synthetic/anonymized demo fixtures
├── docs/                    # contracts and architecture decisions
├── infra/                   # local PostgreSQL/vector-store setup
├── .env.example             # safe configuration template
├── .gitignore
└── PLAN.md
```

## Phase 0: Repository and local environment

1. Initialize Git at the project root.
2. Add `.gitignore` entries for `.env`, `.venv`, Python caches, `node_modules`, frontend build output, IDE files, local databases, and logs.
3. Create the Python environment from the repository root:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate       # Windows: .venv\\Scripts\\activate
   python -m pip install --upgrade pip
   ```

4. Create `backend/requirements.txt` with FastAPI, Uvicorn, Pydantic Settings, HTTPX, PostgreSQL/SQLModel or SQLAlchemy tooling, vector-store tooling, and test/lint/type-check dependencies.
5. Create `.env.example`, copy it to `.env` locally, and keep `.env` untracked. Settings should include:
   - `GENAI_GATEWAY_URL` and gateway API credentials;
   - model names for triage, core review, security, summarization, and embeddings;
   - `INGESTION_SOURCE` (`local_git` default | `webhook`) and `INGEST_SECRET`;
   - `GIT_REPO_PATH` and `GIT_POLL_SECONDS` for the local-git intake path;
   - Git webhook secrets and provider credentials;
   - database/vector-store URLs;
   - CORS origins, timeouts, retry limits, and demo/dry-run flags.
6. Scaffold the frontend with Vite and React TypeScript:

   ```bash
   npm create vite@latest frontend -- --template react-ts
   cd frontend
   npm install
   ```

7. Add Tailwind CSS and the UI dependencies only when their feature phases begin: React Flow for the DAG, a diff viewer, query/cache state, routing, and metrics visualization.

**Gate:** a fresh checkout can create `.venv`, install backend dependencies, run the Vite dev server, and load the starter page without needing secrets.

## Phase 1: FastAPI foundation and contracts

1. Create the FastAPI app factory and `/health`/readiness endpoints.
2. Load all runtime configuration through a Pydantic settings class reading `.env`; do not call `os.getenv` throughout route or agent code.
3. Configure CORS for the Vite development origin and add structured, redacted logging.
4. Define normalized domain schemas for repositories, pull requests, diffs, review runs, agent nodes, findings, summaries, metrics, RAG documents, and HITL checkpoints.
5. Define event schemas for `review.created`, `run.started`, `agent.started`, `agent.completed`, `agent.failed`, `hitl.required`, `hitl.resolved`, and `review.completed`.
6. Add PostgreSQL persistence and migrations. Keep repositories behind interfaces so tests can use fakes and local development can use a disposable database.

**Gate:** the API starts with `.env`, exposes OpenAPI docs, and schema/unit tests pass without contacting external services.

## Phase 2: Local-git ingestion and secure intake

The default intake path is a **local git repository** — no deployment and no
port forwarding required. Git pushes are detected locally and converted into
the same normalized events a GitHub webhook would produce, so nothing
downstream changes.

1. Implement the local-git adapter (`integrations/local_git.py`): given
   `base_sha..head_sha`, run `git diff --no-color`, `git diff --name-only`,
   and `git log` to build a normalized `push` event (commit SHA, author,
   message, changed files, unified diff).
2. Expose `POST /api/v1/ingest/git`, protected by a shared `INGEST_SECRET`
   compared with `hmac.compare_digest` — the local analog of webhook
   signature validation.
3. Provide the two ways to trigger it:
   - **Bare-repo `post-receive` hook** (`scripts/post-receive`): `git init
     --bare /srv/review-hub.git`, add it as a remote, and the hook POSTs a
     normalized event for every pushed ref. Best for push-driven/multi-user.
   - **Polling watcher** (`scripts/watch_repo.py`): watches a local repo path
     and POSTs `previous..HEAD` whenever HEAD moves. Simplest for solo dev.
4. Add secret scrubbing for API keys, JWTs, and other credentials before code
   or diffs reach an LLM. Treat diffs as untrusted content.
5. Make ingestion idempotent by commit SHA: repeated deliveries of the same
   SHA must not create duplicate review runs.
6. Add a synthetic fixture path and dry-run publishing so the demo never
   requires a live repository.
7. Keep the GitHub webhook route (`/api/v1/webhook/github`, HMAC-SHA256) as an
   optional adapter for when the app is deployed and reachable; both paths
   feed the same orchestrator.

**Gate:** `POST /api/v1/ingest/git` accepts a real local push and creates one
review/run; a wrong or missing secret is rejected; re-pushing the same commit
does not create a duplicate run.

## Phase 3: Gateway adapters and multi-agent orchestration

1. Implement one asynchronous GenAI gateway client using HTTPX. It owns authentication, timeouts, retries, structured-response validation, and token/latency telemetry.
2. Configure the models from `PLAN.md` through `.env` rather than embedding model names in route handlers.
3. Implement common agent interfaces and deterministic fakes for tests.
4. Implement the review DAG:

   ```text
   queued → triage → core review + security → HITL gate if needed
          → summarizer → output delivery → completed
   ```

5. Have triage classify changed files/functions and route work to specialized agents.
6. Have the core agent report style, syntax, and functional findings with line ranges and suggestions.
7. Have the security agent report severity/confidence and request HITL when a severe vulnerability or uncertain high-risk result is found.
8. Pause and persist `waiting_for_human` state, then resume only after an authorized approval/rejection/escalation decision.
9. Synthesize findings into a PR summary and route publication through a Git provider adapter.

**Gate:** mocked gateway tests demonstrate deterministic routing, valid normalized findings, persisted state transitions, HITL pause/resume, and retry/failure behavior.

**Status (Phase 3):** implemented as a single-process slice. The default is the
deterministic `DemoGateway` (`LLM_BACKEND=demo`) so the pipeline runs with no
credentials. Two live backends are selectable without touching agents or the
orchestrator: `LLM_BACKEND=http` uses the GenAI Lab gateway via the HTTPX
client (`GENAI_GATEWAY_URL`/`GENAI_API_KEY`), and `LLM_BACKEND=gemini` uses
Google Gemini through the `google-genai` SDK (`GEMINI_API_KEY`,
`MODEL_GEMINI=gemini-3.6-flash`); the GenAI Lab path is preserved. Runs,
findings, and approvals live in the in-memory `RunRepository` (`GET
/api/v1/runs`, `POST /api/v1/hitl/{approval_id}/decision`, SSE at
`GET /api/v1/runs/{run_id}/events`). Swapping in PostgreSQL/Redis replaces the
in-memory repository and event bus behind the same interfaces.

## Phase 4: RAG pipeline

1. Add storage for historical review comments and repository coding guidelines.
2. Chunk source documents by language-aware function/class boundaries where possible, with a safe text fallback.
3. Generate embeddings through the configured gateway model and store vectors behind a vector-store interface.
4. Retrieve relevant guidelines/history for each core/security agent request.
5. Keep repository boundaries and privacy metadata attached to every chunk; use synthetic or anonymized fixtures in tests.

**Gate:** indexing and top-k retrieval work against the local vector store and the retrieved context is visible in agent test traces without leaking unrelated repositories.

**Status (Phase 4):** implemented against a self-contained slice. `app/rag/`
provides language-aware chunking (`chunk_source`), a deterministic offline
embedder (`FeatureHashEmbedder`, `EMBEDDING_DIM`), and an in-memory cosine
vector store scoped by `source_type`/`repo` metadata — all behind small
interfaces so pgvector + the real `MODEL_EMBEDDINGS` gateway can be swapped in
without touching agents or routes. `data/guidelines/*.md` is indexed at startup
(`RAG_GUIDELINES_DIR`); `POST /api/v1/rag/index` and `/search` expose the
pipeline, and the orchestrator appends top-k retrieved guidance to the core and
security agents' prompts (`Retrieved guidance:`). Repository boundaries are
enforced on every chunk, and the guidance content is treated as trusted (the
untrusted diff stays delimited separately).

## Phase 5: React/Vite dashboard

1. Add a typed API client mirroring backend response/event schemas and a reconnecting SSE hook.
2. Build the review dashboard with PR summary, run status, findings by severity/file, and key metrics.
3. Build the live DAG with React Flow. Map backend node statuses to consistent Idle/Running/Success/Failed/Paused visual states.
4. Build the HITL panel/modal. Clearly identify the paused security node, show evidence, and require an explicit decision.
5. Build the side-by-side diff view with inline findings, suggestions, line navigation, and publication state.
6. Build metrics for detection rate, manual-review time reduction, latency, cost, and evaluation quality.
7. Add loading, empty, failure, paused, and SSE reconnect states.
8. Add a demo mode that consumes synthetic review events when no backend integrations are configured.

**Gate:** the frontend can show a fixture review, update the DAG from SSE events, pause at a security checkpoint, submit a decision, and display final findings and summary.

**Status (Phase 5):** implemented. Vite + React + TypeScript + Tailwind v4
dashboard in `frontend/`. A typed REST client (`src/api/client.ts`) mirrors the
backend schemas; a reconnecting SSE hook (`src/hooks/useRunEvents.ts`) drives
live updates with a poll fallback while a run is active. The dashboard lists
runs with metrics; the run detail page renders the live agent DAG (React Flow,
Idle/Running/Success/Failed/Paused), findings grouped by severity with inline
diff markers (`src/components/DiffViewer.tsx`), the HITL approval panel, and a
severity breakdown. `backend/scripts/seed_demo.py` populates a running backend
with synthetic fixtures (clean / style / security) and auto-approves the
security checkpoint so the demo is fully reproducible. Verified: `npm run
build`, `npm run lint`, `npm run test`, plus a live smoke where the dev server
proxies `/api` and SSE event replay to a seeded backend.

## Phase 6: Testing, evaluation, and demo readiness

### Backend checks

```bash
source .venv/bin/activate
pytest
pytest backend/tests/test_orchestrator.py -q
ruff check .
ruff format --check .
mypy backend
```

Cover settings validation, webhook signatures/idempotency, normalization, diff parsing, gateway response validation, agent routing, state transitions, HITL authorization, RAG isolation, and output adapters.

### Frontend checks

```bash
cd frontend
npm run lint
npm run build
npm run test
npm run test -- src/path/to/file.test.tsx
```

Cover dashboard loading/error states, SSE reconnect/update behavior, DAG status rendering, finding navigation, diff suggestions, and HITL actions.

### End-to-end demo

1. Start PostgreSQL/vector services if enabled.
2. Start FastAPI with Uvicorn and the Vite app.
3. Ingest a fixture change by pushing to the local bare repo (or running the
   polling watcher) against a repo containing a known bug and a known
   security issue.
4. Confirm triage, parallel agent progress, SSE updates, and a persisted security pause.
5. Approve the checkpoint in the dashboard.
6. Confirm summary generation, metrics, inline finding display, and dry-run repository publication.
7. Run the same flow with gateway and Git provider fakes in CI; no external API should be required for tests.

**Status (Phase 6):** gates verified end-to-end. Backend: 36 tests passing
(`pytest`, plus `pytest backend/tests/test_orchestrator.py -q`), `ruff check`
and `ruff format --check` clean, `mypy` clean. Frontend: `npm run lint`
(oxlint), `npm run test` (9 tests), single-file `npm run test -- src/lib/diff.test.ts`,
and `npm run build` (tsc + vite) all pass. Output publication is now wired via
`backend/app/integrations/publisher.py`: `DryRunPublisher` records what would
be posted (no external calls; `PUBLISH_MODE=none` disables it), and completed
runs expose a `publication` metadata field shown in the dashboard. Settings
validation rejects invalid `LLM_BACKEND` and `EMBEDDING_DIM`; malformed gateway
JSON fails a run gracefully. `docs/evaluation.md` defines the metrics model
(detection rate, manual-review time reduction, cost, latency, evaluation
quality) and how the seeded demo exercises it. Live E2E confirmed: seed → DAG
progress + SSE events through the Vite proxy → security pause → approve →
`succeeded` with summary and dry-run publication.

Implement one vertical slice at a time: health/config → local-git ingestion/persistence → gateway/agents → orchestration/HITL/SSE → RAG → dashboard → full evaluation. Keep the frontend dependent only on documented backend contracts, and keep all third-party integrations behind adapters so the demo and test suite remain deterministic.
