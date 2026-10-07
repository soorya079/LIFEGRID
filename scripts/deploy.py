#!/usr/bin/env python3
"""
LIFEGRID deployment helper scripts.

Usage (from project root):
  python scripts/deploy.py validate   -- run SAM validate + lint
  python scripts/deploy.py build      -- run SAM build
  python scripts/deploy.py deploy     -- validate, build, then deploy
  python scripts/deploy.py status     -- show CloudFormation stack status
  python scripts/deploy.py outputs    -- show stack outputs (API URL etc.)
  python scripts/deploy.py test       -- run health + report creation test

All operations target LIFEGRID-stack in ap-south-1 ONLY.
Does NOT touch CloudVault or CloudSentinel resources.
"""

import json
import subprocess
import sys
from pathlib import Path

SAM = r"C:\Users\HP\AppData\Roaming\Python\Python313\Scripts\sam.exe"
REGION = "ap-south-1"
STACK_NAME = "LIFEGRID-stack"
TEMPLATE = "infrastructure/template.yaml"
ROOT = Path(__file__).parent.parent


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    print(f"\n$ {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(ROOT), capture_output=False, text=True)
    if check and result.returncode != 0:
        sys.exit(result.returncode)
    return result


def get_stack_outputs() -> dict:
    import boto3
    cf = boto3.client("cloudformation", region_name=REGION)
    try:
        response = cf.describe_stacks(StackName=STACK_NAME)
        outputs = response["Stacks"][0].get("Outputs", [])
        return {o["OutputKey"]: o["OutputValue"] for o in outputs}
    except Exception as e:
        print(f"Stack not found or error: {e}")
        return {}


def cmd_validate():
    run([SAM, "validate", "--template-file", TEMPLATE, "--region", REGION, "--lint"])


def cmd_build():
    run([SAM, "build", "--template-file", TEMPLATE, "--region", REGION])


def cmd_deploy():
    cmd_validate()
    cmd_build()
    run([
        SAM, "deploy",
        "--template-file", TEMPLATE,
        "--stack-name", STACK_NAME,
        "--region", REGION,
        "--capabilities", "CAPABILITY_IAM", "CAPABILITY_NAMED_IAM",
        "--resolve-s3",
        "--s3-prefix", "lifegrid",
        "--no-confirm-changeset",
        "--tags", "Project=LIFEGRID",
    ])
    outputs = get_stack_outputs()
    if outputs:
        print("\n=== LIFEGRID Stack Outputs ===")
        for key, value in outputs.items():
            print(f"  {key}: {value}")


def cmd_status():
    import boto3
    cf = boto3.client("cloudformation", region_name=REGION)
    try:
        response = cf.describe_stacks(StackName=STACK_NAME)
        stack = response["Stacks"][0]
        print(f"Stack: {stack['StackName']}")
        print(f"Status: {stack['StackStatus']}")
        print(f"Created: {stack.get('CreationTime', 'N/A')}")
        print(f"Updated: {stack.get('LastUpdatedTime', 'N/A')}")
    except Exception as e:
        print(f"Error: {e}")


def cmd_outputs():
    outputs = get_stack_outputs()
    if outputs:
        print("\n=== LIFEGRID Stack Outputs ===")
        for key, value in outputs.items():
            print(f"  {key}: {value}")
    else:
        print("No outputs found. Is the stack deployed?")


def cmd_test():
    import urllib.request
    import urllib.error

    outputs = get_stack_outputs()
    api_url = outputs.get("ApiUrl")
    if not api_url:
        print("ERROR: No ApiUrl in stack outputs. Is the stack deployed?")
        sys.exit(1)

    print(f"\nTesting API at: {api_url}")

    # Health check
    try:
        with urllib.request.urlopen(f"{api_url}/health", timeout=10) as resp:
            body = json.loads(resp.read())
            assert body.get("data", {}).get("status") == "ok", f"Unexpected health response: {body}"
            print(f"  GET /health -> HTTP {resp.status} OK ✓")
    except Exception as e:
        print(f"  GET /health FAILED: {e}")
        sys.exit(1)

    # Create report
    report_payload = json.dumps({
        "category": "FLOOD",
        "title": "Flood test report from deploy script",
        "description": "Synthetic test report for end-to-end verification. Not a real emergency.",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "severity": 4,
        "people_affected": 100,
        "source": "SIMULATION",
    }).encode()

    try:
        req = urllib.request.Request(
            f"{api_url}/api/v1/reports",
            data=report_payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read())
            report_id = body["data"]["report_id"]
            print(f"  POST /api/v1/reports -> HTTP {resp.status} ✓  report_id={report_id}")
            print(f"  priority_level: {body['data']['priority_level']}")
            print(f"  event_processing_status: {body['data']['event_processing_status']}")
    except Exception as e:
        print(f"  POST /api/v1/reports FAILED: {e}")
        sys.exit(1)

    print("\nEnd-to-end test PASSED ✓")


COMMANDS = {
    "validate": cmd_validate,
    "build": cmd_build,
    "deploy": cmd_deploy,
    "status": cmd_status,
    "outputs": cmd_outputs,
    "test": cmd_test,
}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(f"Usage: python scripts/deploy.py [{' | '.join(COMMANDS)}]")
        sys.exit(1)
    COMMANDS[sys.argv[1]]()
