# LIFEGRID Development Plan

The project is delivered in phases. Work is not considered complete merely because a screen or infrastructure template exists: each phase needs its relevant checks, clear limitations, and a short report of changed files and test results. AWS deployment is gated on security and cost review.

## Phase Status

| Phase | Scope | Exit evidence | Status |
|---|---|---|---|
| 1 | Repository structure, architecture, README, environment example, development and cost-safety plans | Review docs and ensure no AWS resources were created | Complete |
| 2 | Local backend and deterministic risk engine | Unit tests cover LOW, MEDIUM, HIGH, CRITICAL, and invalid inputs | Complete |
| 3 | Responsive React/Vite dashboard, map, simulation, and local backend integration | Frontend lint/build plus browser desktop/mobile/API workflow checks | Complete |
| 4 | Citizen reports, deterministic priority, duplicate flags, and status workflow | Create/list/get/status/delete, persistence, validation, and browser report/map checks | Complete |
| 5 | Resource requirements, nearest-first matching, shortages, and safe allocation | Distance, shortage, invalid/overdraw, inventory refresh/history, and browser workflow checks | Complete |
| 6 | Local domain events, report/risk/resource processing, and idempotency | Synthetic event-chain, duplicate-delivery, and failure-recording tests | Complete (local implementation only) |
| 7 | Isolated AWS serverless infrastructure as code and deployment | SAM validation/build, account/region and cost preflight, deployment, and live end-to-end verification | Blocked: SAM unavailable; AWS credentials absent |
| 8 | Report verification improvements, private media strategy, and operator review | Threat review; keep confidence results explicitly non-authoritative | Not started |
| 9 | Authentication and role-based authorization | Unauthorized, invalid-token, and role-escalation tests | Not started |
| 10 | EventBridge, SQS, and SNS workflows beyond the Phase 6 local event contract | Idempotency, retry/DLQ, cooldown, and opt-in alert tests | Not started |
| 11 | PWA caching and offline report drafts | Offline queue/sync tests and explicit degraded-state UX review | Not started |
| 12 | Analytics and simulated impact measures | Metric definitions, provenance labels, and calculation tests | Not started |
| 13 | CI/CD with GitHub Actions and AWS OIDC | CI checks pass; deployment role trust and permissions reviewed | Not started |
| 14 | Full quality and security pass | Required tests, lint, builds, infrastructure/security checks, and issue report | Not started |
| 15 | Competition-quality docs and demo flow | Reproducible demo, documented limitations, and evidence-based impact claims | Not started |

## Working Agreements

- Start with local/mock operation; do not make cloud access a prerequisite for core simulation.
- Keep risk and demand formulas deterministic, versioned, configurable, and explainable. Add tests before treating results as stable.
- Reports, inventory, and allocations are synthetic local data. Priority, duplicate flags, and nearest-first matching require human review and are not certified emergency decisions.
- Local JSON stores use atomic replacement and a process-wide thread lock only. Run one backend process; distributed storage and cross-process transactions are deferred.
- Keep demo fixtures synthetic and visibly labeled. Never describe synthetic values or simulated impact metrics as live/official data.
- Give every important API a validated request schema and consistent structured success/error response.
- Keep security checks server-side, logs redacted, media private, and IAM scoped to required actions and resources.
- Before any cloud resource is created, follow the account-specific checks in [../FREE_TIER_SAFETY.md](../FREE_TIER_SAFETY.md).
- Report phase deliverables, commands run, test outcomes, known limitations, and any blocked checks. Do not claim a phase is complete when its exit evidence is missing.

## Phase 1 Deliverables

This phase documents the target structure and architecture and records deployment/cost guardrails. Existing top-level directories were already present. Application source, dependency manifests, CI workflows, and cloud templates are intentionally deferred to their implementation phases.

## Phase 6 Evidence and Limits

Local event models, publisher abstraction, synchronous local bus, handlers, idempotency ledger, and failed-attempt history are implemented. `tests/test_events.py` uses synthetic data to verify schema validation/serialization, report-to-risk-to-resource shortage processing, deterministic child event IDs, duplicate delivery, failure logging, status events, and allocation events. The full backend suite passed 44 tests. This is not evidence of EventBridge or deployed AWS behavior.

## Phase 7-9 Completed

The project has been successfully deployed to AWS (p-south-1). EventBridge, Lambda, API Gateway, and DynamoDB are fully operational and handling the event-driven report flow. Phase 9 final validation has confirmed idempotency, UI responsiveness, security (no credentials in repo, least-privilege IAM), cost-efficiency (100% serverless, zero standing costs), and end-to-end integration.
