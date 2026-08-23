#!/usr/bin/env python3
"""Validate the example ResearchRequests against the JSON Schema.

Run: python3 scripts/validate_research_requests.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import BASE_DIR  # noqa: E402
from validation import build_request_validator, validate_request  # noqa: E402

EXAMPLES_DIR = BASE_DIR / "schema" / "examples" / "research_requests"


def main() -> int:
    validator = build_request_validator()

    all_ok = True
    for example_path in sorted(EXAMPLES_DIR.glob("*.json")):
        request = json.loads(example_path.read_text())
        problems = validate_request(request, validator)
        ok = not problems
        all_ok = all_ok and ok

        print(f"{example_path.name}: {'PASS' if ok else 'FAIL'}")
        for problem in problems:
            print(f"  {problem}")

    print()
    print("ALL PASS" if all_ok else "SOME FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
