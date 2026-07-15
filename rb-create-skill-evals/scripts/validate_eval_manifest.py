#!/usr/bin/env python3
"""Validate the portable manifest written by rb-create-skill-evals."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ALLOWED_CONDITIONS = {"with_skill", "without_skill"}
ALLOWED_KINDS = {"trigger", "outcome", "regression", "retirement"}
ALLOWED_EVALUATORS = {"deterministic", "semantic", "manual"}


def nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return [f"manifest does not exist: {path}"]
    except json.JSONDecodeError as exc:
        return [f"invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}"]

    if not isinstance(data, dict):
        return ["top-level JSON value must be an object"]

    if data.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if not nonempty_string(data.get("skill")):
        errors.append("skill must be a non-empty string")

    conditions = data.get("conditions")
    if not isinstance(conditions, list) or not conditions:
        errors.append("conditions must be a non-empty list")
    else:
        unknown = sorted(set(conditions) - ALLOWED_CONDITIONS)
        if unknown:
            errors.append(f"unknown conditions: {', '.join(unknown)}")
        if len(conditions) != len(set(conditions)):
            errors.append("conditions must not contain duplicates")

    default_trials = data.get("default_trials")
    if not isinstance(default_trials, int) or isinstance(default_trials, bool) or not 1 <= default_trials <= 20:
        errors.append("default_trials must be an integer from 1 to 20")

    cases = data.get("cases")
    if not isinstance(cases, list) or not cases:
        errors.append("cases must be a non-empty list")
        return errors

    seen_ids: set[str] = set()
    for index, case in enumerate(cases):
        label = f"cases[{index}]"
        if not isinstance(case, dict):
            errors.append(f"{label} must be an object")
            continue

        case_id = case.get("id")
        if not nonempty_string(case_id):
            errors.append(f"{label}.id must be a non-empty string")
        elif case_id in seen_ids:
            errors.append(f"{label}.id is duplicated: {case_id}")
        else:
            seen_ids.add(case_id)

        kind = case.get("kind")
        if kind not in ALLOWED_KINDS:
            errors.append(f"{label}.kind must be one of {sorted(ALLOWED_KINDS)}")
        if not nonempty_string(case.get("prompt")):
            errors.append(f"{label}.prompt must be a non-empty string")

        should_trigger = case.get("should_trigger")
        if "should_trigger" in case and should_trigger is not None and not isinstance(should_trigger, bool):
            errors.append(f"{label}.should_trigger must be true, false, or null")
        if kind == "trigger" and not isinstance(should_trigger, bool):
            errors.append(f"{label}.should_trigger must be true or false for trigger cases")

        fixture = case.get("fixture")
        if fixture is not None and not nonempty_string(fixture):
            errors.append(f"{label}.fixture must be a non-empty string when provided")

        success = case.get("success")
        if not isinstance(success, list) or not success:
            errors.append(f"{label}.success must be a non-empty list")
            continue

        for check_index, check in enumerate(success):
            check_label = f"{label}.success[{check_index}]"
            if not isinstance(check, dict):
                errors.append(f"{check_label} must be an object")
                continue
            if not nonempty_string(check.get("name")):
                errors.append(f"{check_label}.name must be a non-empty string")
            evaluator = check.get("evaluator")
            if evaluator not in ALLOWED_EVALUATORS:
                errors.append(
                    f"{check_label}.evaluator must be one of {sorted(ALLOWED_EVALUATORS)}"
                )
            elif evaluator == "deterministic" and not nonempty_string(check.get("command")):
                errors.append(f"{check_label}.command is required for deterministic checks")
            elif evaluator == "semantic" and not nonempty_string(check.get("rubric")):
                errors.append(f"{check_label}.rubric is required for semantic checks")
            elif evaluator == "manual" and not nonempty_string(check.get("instructions")):
                errors.append(f"{check_label}.instructions is required for manual checks")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="Path to eval-plan.json")
    args = parser.parse_args()

    errors = validate(args.manifest)
    if errors:
        print(f"FAIL: {args.manifest}")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"PASS: {args.manifest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
