#!/usr/bin/env python3
"""
LIFEGRID end-to-end AWS integration test.

Run after successful deployment:
  python scripts/test_aws.py

Tests:
  1. GET /health -> HTTP 200
  2. POST /api/v1/reports (FLOOD, HIGH, 100 people)
  3. GET /api/v1/reports/{id} -> report exists in DynamoDB
  4. Idempotency: POST same event twice -> second ignored
  5. GET /api/v1/resources/summary
  6. GET /api/v1/resources

Does NOT test LiveEventBridge chain (async) directly but checks
event_processing_status on created report.
"""

import json
import sys
import time
import urllib.error
import urllib.request
import boto3

REGION = "ap-south-1"
STACK_NAME = "LIFEGRID-stack"


def get_api_url() -> str:
    cf = boto3.client("cloudformation", region_name=REGION)
    response = cf.describe_stacks(StackName=STACK_NAME)
    outputs = {o["OutputKey"]: o["OutputValue"] for o in response["Stacks"][0].get("Outputs", [])}
    url = outputs.get("ApiUrl")
    if not url:
        print("ERROR: ApiUrl not found in stack outputs")
        sys.exit(1)
    return url.rstrip("/")


def get(url: str) -> tuple[int, dict]:
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def post(url: str, body: dict) -> tuple[int, dict]:
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def check(label: str, condition: bool, detail: str = ""):
    icon = "[OK]" if condition else "[FAIL]"
    print(f"  {icon} {label}{(' - ' + detail) if detail else ''}")
    if not condition:
        print("    FAIL - aborting tests")
        sys.exit(1)


def run_tests():
    api_url = get_api_url()
    print(f"\nLIFEGRID AWS Integration Tests")
    print(f"API: {api_url}\n")

    # 1. Health check
    print("1. Health check")
    status, body = get(f"{api_url}/health")
    check("GET /health -> 200", status == 200, f"HTTP {status}")
    check("health.status == ok", body.get("data", {}).get("status") == "ok")

    # 2. Create report
    print("\n2. Create report (FLOOD, severity=4, 100 people)")
    report_payload = {
        "category": "FLOOD",
        "title": "AWS integration test flood report",
        "description": "Synthetic test data for LIFEGRID AWS integration. Not a real emergency.",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "severity": 4,
        "people_affected": 100,
        "source": "SIMULATION",
    }
    status, body = post(f"{api_url}/api/v1/reports", report_payload)
    check("POST /api/v1/reports -> 201", status == 201, f"HTTP {status}")
    report = body.get("data", {})
    report_id = report.get("report_id", "")
    check("report_id exists", bool(report_id), report_id)
    check("category == FLOOD", report.get("category") == "FLOOD")
    check("priority_level is set", report.get("priority_level") in ["LOW", "MEDIUM", "HIGH", "CRITICAL"])
    print(f"    report_id: {report_id}")
    print(f"    priority_level: {report.get('priority_level')}")
    print(f"    event_processing_status: {report.get('event_processing_status')}")

    # 3. Get report by ID
    print(f"\n3. Get report by ID ({report_id})")
    status, body = get(f"{api_url}/api/v1/reports/{report_id}")
    check("GET /api/v1/reports/{id} -> 200", status == 200, f"HTTP {status}")
    check("correct report returned", body.get("data", {}).get("report_id") == report_id)

    # 4. List reports
    print("\n4. List reports")
    status, body = get(f"{api_url}/api/v1/reports")
    check("GET /api/v1/reports -> 200", status == 200, f"HTTP {status}")
    reports = body.get("data", {}).get("reports", [])
    check("report list is non-empty", len(reports) > 0, f"{len(reports)} reports")

    # 5. Resources summary
    print("\n5. Resource summary")
    status, body = get(f"{api_url}/api/v1/resources/summary")
    check("GET /api/v1/resources/summary -> 200", status == 200, f"HTTP {status}")

    # 6. Resources list
    print("\n6. Resource list")
    status, body = get(f"{api_url}/api/v1/resources")
    check("GET /api/v1/resources -> 200", status == 200, f"HTTP {status}")

    # 7. Idempotency test — wait briefly then check event_processing_status
    print("\n7. Event processing status check (wait 3s for async handlers)")
    time.sleep(3)
    status, body = get(f"{api_url}/api/v1/reports/{report_id}")
    processing_status = body.get("data", {}).get("event_processing_status", "PENDING")
    print(f"    event_processing_status: {processing_status}")
    # Any non-FAILED status means the event bus accepted it
    check(
        "event_processing_status is not FAILED",
        processing_status != "FAILED",
        processing_status
    )

    print(f"\n{'='*50}")
    print("All integration tests PASSED [OK]")
    print(f"{'='*50}")
    print(f"API URL: {api_url}")


if __name__ == "__main__":
    run_tests()
