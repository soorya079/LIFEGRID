# AWS Free Tier and Cost Safety Plan

## Non-Negotiable Rule

“Free Tier” is not a promise that LIFEGRID will cost nothing. Eligibility, included usage, credits, limits, and overage pricing depend on the AWS account, region, service, and current AWS offer. Offers and service pricing change. **Before creating each AWS resource, verify the current account-specific terms and regional price in AWS Billing and the official service pricing page.** This document is a review checklist, not a price quote.

No LIFEGRID AWS resources have been created. Phase 6 is local-only. The preferred development path is local mock mode. The configured environment currently has no usable AWS credentials, and AWS SAM CLI is not installed; no cloud preflight or provisioning can be performed from this state. Do not deploy just to make the documentation or demo appear complete.

## Planned Service Review

The quantities below are intentionally modest MVP intent, not quotas, forecasts, or a guarantee of Free Tier eligibility. Confirm current allowance and paid overage for the intended account and region immediately before deployment.

| Service/resource | Intended MVP usage | Free allowance status | Main cost risk / control |
|---|---|---|---|
| S3 static assets | Small versioned frontend bundle | Check current S3 offer, request, storage, and transfer terms | Storage, requests, internet transfer, and optional CDN; delete old build objects and avoid large media |
| S3 private report media | Optional, small demo uploads | Check account/region eligibility and applicable storage/request terms | Object storage, requests, retrieval, and transfer; enforce upload size/type limits, lifecycle expiration, and private access |
| API Gateway | Low-volume demo API calls | Check API type, account offer, and request pricing | Requests, caching, data transfer, and logging; use quotas/throttling and avoid polling |
| AWS Lambda | Short, event-driven API and worker invocations | Check current request/compute offer and applicable duration/memory | Invocation volume, duration, memory, retries, and logs; cap payloads, execution time, and retry behavior |
| DynamoDB | Small on-demand demo tables | Check on-demand/provisioned mode, storage, request, backup, and account offer | Reads/writes, indexes, backups, streams, and retained data; design access patterns and set cleanup/retention policy |
| Cognito | Small test user pool | Check current user/MAU offer and feature-specific pricing | Active users and optional features; keep test users controlled and avoid paid add-ons without approval |
| EventBridge | Low-volume domain events | Check event bus/event type pricing and account offer | Event volume, archive/replay, cross-account or partner features; avoid unnecessary event duplication |
| SQS | Small asynchronous workload | Check request pricing and current account allowance | Requests, long polling, retries, and DLQ retention; batch appropriately and bound retries/retention |
| SNS | Opt-in demo email/SMS or event notifications | Check protocol-specific pricing and current offer | SMS destinations, delivery volume, retries, and subscriptions; do not enable SMS for demos by default and deduplicate alerts |
| CloudWatch | Limited logs, metrics, and alarms | Check ingestion, storage, metric, and alarm pricing/allowances | Log ingestion/retention and custom metrics can grow; redact, sample where appropriate, set retention, and monitor usage |
| IAM | Roles and policies | Review current service terms; IAM is not a reason to assume adjacent services are free | Mis-scoped access can cause security and cost incidents; use least privilege and no AdministratorAccess for application roles |
| OpenStreetMap tiles | Interactive map during low-volume tests | Not an AWS Free Tier item; follow the tile provider usage policy | External service availability/usage limits; do not bulk-download tiles or treat public tiles as guaranteed production capacity |
| CloudFront (optional) | Consider only if private static origin is needed | Check current offer and regional/feature terms | Requests, transfer, invalidations, and logs; omit unless architecture/security needs justify it |
| Route 53 / domain (optional) | Not required for local MVP | Check current hosted-zone, query, and registration pricing | Recurring hosted-zone/domain charges; avoid until custom DNS is required |
| NAT Gateway / RDS / EC2 / EKS / managed AI | Excluded from MVP by default | No free eligibility is assumed | Can create material recurring or usage-based charges; do not add without explicit architecture and cost approval |

## Pre-Provisioning Checklist

1. Confirm the AWS account, region, current Free Tier/credit terms, and service eligibility in the account's Billing console and official pricing pages.
2. Estimate normal and worst-case requests, storage, log ingestion, data transfer, retry volume, and retention using the AWS Pricing Calculator. Record assumptions and who approved the estimate.
3. Review the actual rendered infrastructure plan/template for every resource, including defaults, log groups, backups, endpoints, buckets, and optional features.
4. Enable appropriate billing notifications and budgets using the controls currently available to the account. Budgets/alerts are monitoring aids, not hard spending caps, and their own features may have charges.
5. Use a dedicated deployment role with least privilege and GitHub OIDC where CI deployment is introduced. Never store AWS access keys in frontend files or repository secrets when OIDC is viable.
6. Set request limits, payload limits, log retention, upload limits, retry/DLQ limits, and alert cooldown before opening a demo to users.
7. Confirm S3 Block Public Access for the report-media bucket, encryption, lifecycle policy, and scoped upload mechanism. Check that no personal or incident-sensitive data is placed in public demo fixtures.
8. Write down the expected teardown procedure and identify retained data or resources that will not be removed automatically.
9. Deploy only after explicit review. Recheck actual billing/usage after the demo and after any traffic or architecture change.

## Cleanup Checklist

- Stop demos and disable scheduled/event sources or public entry points that can continue generating requests.
- Inventory resources in every used region and account, including buckets/objects, tables/backups, user pools, queues/DLQs, topics/subscriptions, event rules, functions, APIs, logs, alarms, and optional CDN/DNS resources.
- Export only intentionally retained audit/demo data, subject to privacy policy; then delete temporary objects and data using the reviewed teardown procedure.
- Remove test subscriptions/users, unused versions, orphaned log groups, stale artifacts, and unused infrastructure stacks where appropriate.
- Verify dependent resources and retention settings before deletion. Do not blindly run a destructive command against a shared or production account.
- Revisit Billing and Cost Explorer after cleanup for delayed usage/charges; a deleted resource does not necessarily erase already incurred charges.

## Useful Review Locations

- AWS Free Tier information: https://aws.amazon.com/free/
- AWS Pricing Calculator: https://calculator.aws/
- AWS Billing and Cost Management: https://console.aws.amazon.com/billing/
- AWS service pricing pages should be checked for each service and chosen region at deployment time.

Do not publish fixed allowance numbers from this document. Record the verified terms and estimate alongside the deployment change, because the applicable offer may change between development and deployment.
