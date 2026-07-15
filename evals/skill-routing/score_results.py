#!/usr/bin/env python3
"""Score blinded skill-routing classifications against the hidden manifest."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from routing_manifest import load_manifest


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{number}: invalid JSON: {exc.msg}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{number}: each row must be an object")
        rows.append(value)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("results", type=Path, nargs="+")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    manifest = load_manifest(args.manifest)
    cases = {case["id"]: case for case in manifest["cases"]}
    rows = [row for path in args.results for row in load_jsonl(path)]
    seen: set[tuple[str, str, int]] = set()
    observed_runs: set[tuple[str, int]] = set()
    scored = []
    counts: Counter[str] = Counter()

    for row in rows:
        case_id = row.get("case_id")
        if case_id not in cases:
            raise SystemExit(f"unknown case_id in results: {case_id}")
        condition = row.get("condition")
        trial = row.get("trial")
        if condition not in manifest["conditions"]:
            raise SystemExit(f"invalid condition in results: {condition}")
        if not isinstance(trial, int) or not 1 <= trial <= manifest["default_trials"]:
            raise SystemExit(f"invalid trial in results: {trial}")
        key = (case_id, condition, trial)
        if key in seen:
            raise SystemExit(f"duplicate result: {key}")
        seen.add(key)
        observed_runs.add((condition, trial))

        outcome = row.get("outcome")
        if outcome not in {"select", "clarify", "no_skill"}:
            raise SystemExit(f"invalid outcome in result {key}: {outcome}")
        skill = row.get("skill")
        if outcome == "select" and not isinstance(skill, str):
            raise SystemExit(f"selected result must name a skill: {key}")
        if outcome != "select" and skill is not None:
            raise SystemExit(f"non-select result must use a null skill: {key}")
        if row.get("confidence") not in {"high", "medium", "low"}:
            raise SystemExit(f"invalid confidence in result {key}")
        if not isinstance(row.get("explanation"), str) or not row["explanation"].strip():
            raise SystemExit(f"missing explanation in result {key}")

        expected = cases[case_id]["expected"]
        outcome_ok = outcome == expected["outcome"]
        skill_ok = expected["outcome"] != "select" or skill == expected.get("skill")
        forbidden_hit = skill in cases[case_id]["forbidden_skills"]
        passed = outcome_ok and skill_ok and not forbidden_hit
        status = "pass" if passed else "fail"
        counts[status] += 1
        scored.append({
            **row,
            "expected": expected,
            "forbidden_hit": forbidden_hit,
            "passed": passed,
        })

    missing = sorted(
        (case_id, condition, trial)
        for condition, trial in observed_runs
        for case_id in cases
        if (case_id, condition, trial) not in seen
    )
    if missing:
        preview = ", ".join(str(item) for item in missing[:5])
        suffix = " ..." if len(missing) > 5 else ""
        raise SystemExit(f"missing {len(missing)} expected results: {preview}{suffix}")
    if not rows:
        raise SystemExit("no results supplied")

    summary = {
        "total": len(scored),
        "passed": counts["pass"],
        "failed": counts["fail"],
        "pass_rate": round(counts["pass"] / len(scored), 4) if scored else 0.0,
        "outcome_counts": dict(sorted(Counter(row["outcome"] for row in scored).items())),
        "selected_skill_counts": dict(
            sorted(
                Counter(
                    row["skill"]
                    for row in scored
                    if row["outcome"] == "select"
                ).items()
            )
        ),
        "failures": [row for row in scored if not row["passed"]],
        "runs": [
            {"condition": condition, "trial": trial}
            for condition, trial in sorted(observed_runs)
        ],
    }
    rendered = json.dumps(summary, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        print(f"WROTE: {args.output}")
    else:
        print(rendered, end="")
    return 1 if counts["fail"] else 0


if __name__ == "__main__":
    sys.exit(main())
