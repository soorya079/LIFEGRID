# LIFEGRID

**AI-Powered Early-Action & Emergency Resource Coordination Network**

LIFEGRID is planned as a cost-conscious, serverless coordination tool for urban flood response. It brings together synthetic weather conditions, citizen reports, risk estimates, resource availability, and auditable early-action recommendations. It is an MVP design and is not an official warning system or a substitute for emergency services.

## Project Status

**Phases 1–6: local-first MVP foundation, backend, responsive frontend, citizen reporting, resource matching/allocation, and a tested local domain-event pipeline.** FastAPI and the React/Vite client run locally against synthetic JSON fixtures. Phase 7 AWS infrastructure is not validated or deployed; the current environment has no AWS credentials and AWS SAM CLI is unavailable.

## MVP Scope

The first scenario is urban flooding. The planned local-first MVP will provide deterministic, explainable risk scoring and demand estimates, resource matching, citizen-report intake and MVP verification, response actions, and an operational interface. Numerical risk decisions will not depend on an LLM. Future hazards may be added behind shared hazard and incident interfaces after the flood workflow is validated.

## Architecture and AWS

See [ARCHITECTURE.md](ARCHITECTURE.md) for the component diagram and system boundaries. The proposed AWS path uses a static frontend, API Gateway, Lambda, and DynamoDB, with optional EventBridge, SQS, SNS, Cognito, and S3 integrations. The application must also run locally in mock mode before AWS integration.

AWS Free Tier eligibility, quotas, and pricing depend on the account, region, service, and current offer. There is no guarantee that usage will be free. Read [FREE_TIER_SAFETY.md](FREE_TIER_SAFETY.md) before creating cloud resources. **No AWS resources have been created for LIFEGRID.**

## Repository Layout

```text
.
|-- backend/                 # Local FastAPI API and deterministic domain logic
|-- data/                    # Shared/versioned synthetic demo fixtures
|-- docs/                    # Development and operational planning
|-- frontend/                # React/Vite operations UI
|-- infrastructure/          # AWS infrastructure as code (planned)
|-- lambda/                  # AWS Lambda entry points (planned)
|-- tests/                   # Risk, demand, report/resource, and API tests
|-- .github/workflows/       # CI/CD workflows (planned)
|-- .env.example             # Safe configuration placeholders
|-- ARCHITECTURE.md          # Architecture and trust boundaries
|-- FREE_TIER_SAFETY.md      # Cost and cleanup controls
`-- README.md
```

## Security Principles

- Never put AWS credentials, private keys, or tokens in source control or frontend configuration.
- Validate identity and authorization on the server; never trust a role supplied by a browser.
- Keep citizen-uploaded media in a private S3 bucket and issue narrowly scoped, short-lived upload authorization only after server-side checks.
- Use least-privilege IAM, input validation, structured errors, restricted CORS, and redacted logs.
- Keep synthetic, external, and verified data sources distinct and visible to operators.
- Treat LIFEGRID recommendations as decision support. A human coordinator remains responsible for operational actions.

## Development

### Windows PowerShell

Terminal 1, backend:

```powershell
cd C:\Users\HP\Desktop\LIFEGRID

.\.venv\Scripts\Activate.ps1

python -m pip install -r backend\requirements.txt

python -m uvicorn backend.main:app --reload
```

Terminal 2, frontend:

```powershell
cd C:\Users\HP\Desktop\LIFEGRID\frontend

npm install

npm run dev
```

Open the app at http://127.0.0.1:5173. Backend API and interactive docs:

- http://127.0.0.1:8000
- http://127.0.0.1:8000/docs

Testing:

```powershell
python -m pytest
```

Frontend checks:

```powershell
cd C:\Users\HP\Desktop\LIFEGRID\frontend
npm run lint
npm run build
```

The service uses synthetic local data and does not require AWS credentials or paid APIs. Reports, allocation events, and local domain-event records are written to JSON files in `backend/data/`. Writes use atomic replacement and an in-process thread lock; run one Uvicorn worker only. No LIFEGRID AWS resources have been created.

The current phase-by-phase scope and exit checks are in [docs/DEVELOPMENT_PLAN.md](docs/DEVELOPMENT_PLAN.md). The backend test suite was run with `python -m pytest -q --basetemp .pytest-tmp -p no:cacheprovider` (44 passed). Frontend checks, SAM validation/build, AWS preflight and deployment have not been run in this continuation.

## Limitations

- Initial scenarios and data are synthetic; they do not represent live government, weather, river-sensor, or population feeds.
- Risk and need calculations are transparent MVP estimates, not certified forecasts or official resource requirements.
- Citizen-report verification is a heuristic confidence model, not proof that a report is true.
- Authentication, private media upload, report verification beyond heuristic duplicate flags, notifications, distributed persistence, and multi-process locking are not implemented yet.
- Service quotas and Free Tier offers can change. The account owner must verify current terms and monitor billing.

## Roadmap

Work proceeds in the phase plan in [docs/DEVELOPMENT_PLAN.md](docs/DEVELOPMENT_PLAN.md). The next work is hardened verification/authentication and cloud-independent quality improvements; AWS deployment remains explicitly deferred.

## Phase 7 & 8 Completed
AWS Serverless Infrastructure is deployed via AWS SAM to p-south-1. The backend runs entirely on Lambda, API Gateway, DynamoDB, and EventBridge, completely replacing local JSON storage without altering the core business logic.
