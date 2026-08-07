# Evaluation

How we measure the review system and how the local demo exercises those
metrics. The dashboard surfaces the operational subset today; the research
metrics are the evaluation agenda for moving beyond the demo.

## Operational metrics (shown in the dashboard)

These come straight from `GET /api/v1/runs` / `GET /api/v1/runs/{id}` and need
no instrumentation beyond what the pipeline already records.

| Metric | Definition | Where it lives |
| --- | --- | --- |
| Reviews completed | Runs reaching `succeeded` vs `failed` | `Dashboard` tiles |
| Awaiting human | `waiting_hitl` runs + pending approvals | `Dashboard` tile, run badge |
| Findings | Count by severity (critical/error/warning/info) | `FindingMetrics` panel |
| Findings requiring HITL | `requires_hitl` findings | Finding card badge, panel |
| Latency | Wall-clock from `created_at` to `updated_at` per run | Run header |
| Publication | Dry-run comment count posted to the repo | Summary card |

`updated_at` is refreshed on every transition, so
`updated_at - created_at` is the end-to-end review latency for a run. The
current in-memory repository is single-process; with a real datastore these
metrics aggregate across reviewers and repos.

## Research metrics (evaluation agenda)

These require a labelled evaluation set and are not yet surfaced in the demo.

### Detection rate

How often the system finds a defect a human would too.

- **Precision** = true findings / all findings. A finding is *true* if it maps
  to a real, human-validated defect (see labels below).
- **Recall** = true findings / total labelled defects in the change. RAG
  guidelines and better routing should raise recall on known bug classes.
- **F1** = harmonic mean of precision and recall.

Labelling workflow: every demo fixture ships with a ground-truth manifest
(`data/` fixtures), so precision/recall can be scored by comparing emitted
findings against the manifest keyed on `(file_path, line, category)`.

### Manual-review time reduction

Time saved vs an unaided human review of the same PR.

- Measure unaided review time and review time *with* the system (findings +
  summary + diff markers) over a small panel; report the median reduction.
- Proxy without a panel: findings per review and per 1k changed lines are a
  proxy for how much of the review the agents front-load.

### Cost

- **Per review**: gateway tokens in/out per agent (the gateway telemetry already
  returns `tokens_in`/`tokens_out`/`latency_ms` per call — aggregate by run).
- **Per finding**: cost of producing one accepted finding (cost / precision).
- **RAG**: extra context tokens added by retrieved guidelines vs precision gain,
  to decide the top-k budget.

### Latency

- **Critical path**: time from ingest to the first HITL pause (security) vs the
  full run — the pause is where human latency dominates.
- **Agent-level**: per-agent `agent.started` → `agent.completed` deltas from SSE
  events; parallel core+security should stay well under the sum of the two.

### Evaluation quality

Regression harness on the evaluation set: keep a golden corpus of PRs with
human-reviewed findings; re-run agents on every change and fail CI on
regressions in precision/recall. The demo fixtures (`data/`) and the
deterministic `DemoGateway` make this repeatable without external APIs.

## How the demo exercises this

1. `python backend/scripts/seed_demo.py` ingests three labelled fixtures:
   clean, style defects, and a security defect (known bug + known security
   issue).
2. The security fixture pauses at `waiting_hitl`; approving resumes the run.
3. The dashboard shows severity distribution, HITL state, latency, and the
   dry-run publication — the operational slice of the table above.
4. `pytest` + `npm run test` lock in the evaluation harness: findings from the
   `DemoGateway` are asserted against expected patterns, and the RAG
   retrieval tests assert the right guidelines surface.
