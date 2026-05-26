"""End-to-end local run against a fixture.

Usage:
    python -m scripts.run_local fixtures/tickets/sso_redirect_loop.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from src.triage.handler import lambda_handler  # noqa: E402


def main() -> None:
    if len(sys.argv) != 2:
        print("usage: python -m scripts.run_local <fixture.json>", file=sys.stderr)
        sys.exit(1)

    payload = json.loads(Path(sys.argv[1]).read_text())
    event = {"body": json.dumps(payload)}
    result = lambda_handler(event, None)
    print("\n--- handler result ---")
    print(json.dumps(json.loads(result["body"]), indent=2))


if __name__ == "__main__":
    main()
