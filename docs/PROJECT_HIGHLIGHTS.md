---
noteId: "8f7c69d0c13c11f18cee674a2af03c45"
tags: []

---

# LIFEGRID Project Highlights

## Problem
During natural disasters and large-scale emergencies, citizen reports arrive chaotically and lack immediate actionable context. Decision-makers struggle to prioritize incoming data, assess localized risk, and calculate resource requirements (water, food, medical, shelter) fast enough to dispatch aid effectively.

## Solution
LIFEGRID is an event-driven emergency operations dashboard and backend that ingests citizen reports, automatically assesses geographical risk, and calculates resource requirements in near real-time. It provides a clean, responsive UI for operators to visualize data and make informed decisions.

## Architecture & AWS Services
- **API Gateway**: Provides a high-throughput, serverless HTTP endpoint for the frontend.
- **AWS Lambda**: Microservices wrap the FastAPI logic (via Mangum) for report ingestion and run asynchronous processors for Risk and Resource calculations.
- **Amazon EventBridge**: The central nervous system. Decouples ingestion from processing via domain events (`REPORT_CREATED`, `RISK_ASSESSED`).
- **Amazon DynamoDB**: Serverless, pay-per-request persistence for Reports, Resources, Events, and an Idempotency Ledger.
- **Frontend**: React + Vite + Tailwind CSS, built as a responsive Single Page Application (SPA).

## Event-Driven Design
The system relies on an asynchronous event choregraphy:
1. API receives a report and writes to DynamoDB.
2. API publishes `REPORT_CREATED` to EventBridge.
3. `RiskProcessor` Lambda listens, calculates risk, updates DynamoDB, and publishes `RISK_ASSESSED`.
4. `ResourceProcessor` Lambda listens, calculates needed resources, and updates the database.

## Security
- **Least Privilege IAM**: Every Lambda function has tailored permissions. The API can only `PutEvents` to the specific LIFEGRID EventBus, and can only CRUD specific DynamoDB tables.
- **No Hardcoded Credentials**: The app relies exclusively on IAM roles attached to the execution environment.
- **Strict Separation**: The project explicitly protects and isolated itself from any other pre-existing infrastructure (e.g. CloudVault / CloudSentinel).

## Cost Optimization
LIFEGRID is designed with a **100% Serverless, Scale-to-Zero Architecture**.
- No Load Balancers, NAT Gateways, or always-on EC2/ECS instances.
- Uses `PAY_PER_REQUEST` billing mode for DynamoDB.
- Idempotency prevents wasteful duplicate processing.
- Lambda execution times are optimized to < 10ms for standard requests, resulting in virtually zero standing costs.

## Key Technical Challenges
- **Python Type Serialization to DynamoDB**: Boto3 natively rejects `float` objects (often used for latitude/longitude). 
  - *Solution*: Built a recursive interceptor in the `DynamoDBStore` wrapper to seamlessly translate `float` to `Decimal` on write, and `Decimal` to `float` on read, ensuring the domain layer remained pristine.
- **In-Place Mutation Bugs**: The custom DB wrapper's diff-checker failed to trigger updates when Pydantic modified state dictionaries in place.
  - *Solution*: Implemented a `deepcopy` isolation boundary before applying updates, successfully persisting background state changes like `RISK_ASSESSMENT_PENDING`.
- **Idempotency in Distributed Systems**: EventBridge guarantees at-least-once delivery, risking duplicate resource assignments.
  - *Solution*: Implemented a generic `DynamoDBIdempotencyStore` with TTL that intercepts Lambda executions, dropping duplicate event hashes before they hit the domain layer.
