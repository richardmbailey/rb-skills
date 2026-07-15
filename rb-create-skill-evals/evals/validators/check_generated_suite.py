#!/usr/bin/env python3
"""Check that a generated skill-eval suite is substantial and discriminating."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()

    try:
        data = json.loads(args.manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"FAIL: cannot read a valid manifest: {exc}")
        return 1

    cases = data.get("cases", [])
    trigger_values = {case.get("should_trigger") for case in cases}
    evaluators = {
        check.get("evaluator")
        for case in cases
        for check in case.get("success", [])
        if isinstance(check, dict)
    }

    checks = {
        "at least ten cases": len(cases) >= 10,
        "matched ablation conditions": set(data.get("conditions", []))
        == {"with_skill", "without_skill"},
        "positive and negative trigger coverage": {True, False}.issubset(trigger_values),
        "deterministic evaluation": "deterministic" in evaluators,
        "semantic evaluation": "semantic" in evaluators,
    }
    failures = [name for name, passed in checks.items() if not passed]
    if failures:
        print("FAIL: generated suite is incomplete")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("PASS: generated suite has routing, outcome, and ablation coverage")
    return 0


if __name__ == "__main__":
    sys.exit(main())
