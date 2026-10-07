#!/usr/bin/env python3
"""
LIFEGRID Lambda pre-build script for Windows.

Assembles each Lambda deployment package by copying:
  - handler.py (from lambda/<name>/)
  - dynamo_store.py (from lambda/shared/)
  - backend/ package (entire backend source)
  - backend/data/ (synthetic fixtures including sample_zones.json)

Run from the project root BEFORE `sam build`:
  python scripts/prebuild.py

Output: .aws-sam/build/<FunctionName>/  directories ready for SAM packaging.
"""

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent

FUNCTIONS = {
    "LifegridApiFunction": ROOT / "lambda" / "api",
    "LifegridRiskProcessorFunction": ROOT / "lambda" / "risk_processor",
    "LifegridResourceProcessorFunction": ROOT / "lambda" / "resource_processor",
    "LifegridNotificationProcessorFunction": ROOT / "lambda" / "notification_processor",
}

BUILD_DIR = ROOT / ".aws-sam" / "build"
DYNAMO_STORE = ROOT / "lambda" / "shared" / "dynamo_store.py"
BACKEND_SRC = ROOT / "backend"


def prebuild():
    print("LIFEGRID Lambda pre-build")
    print(f"  Root: {ROOT}")
    print(f"  Build dir: {BUILD_DIR}\n")

    for fn_name, handler_dir in FUNCTIONS.items():
        target = BUILD_DIR / fn_name
        target.mkdir(parents=True, exist_ok=True)

        # Copy handler.py
        src_handler = handler_dir / "handler.py"
        if not src_handler.exists():
            print(f"  ERROR: {src_handler} not found")
            sys.exit(1)
        shutil.copy2(src_handler, target / "handler.py")

        # Copy dynamo_store.py
        shutil.copy2(DYNAMO_STORE, target / "dynamo_store.py")

        # Copy backend package
        backend_target = target / "backend"
        if backend_target.exists():
            shutil.rmtree(backend_target)
        shutil.copytree(BACKEND_SRC, backend_target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))

        print(f"  [OK] {fn_name} -> {target}")

    print("\nPre-build complete. Run: sam build --template-file infrastructure/template.yaml --skip-pull-image")


if __name__ == "__main__":
    prebuild()
