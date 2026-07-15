#!/usr/bin/env python3
"""Validate the repository-level RB skill-routing evaluation manifest."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from routing_manifest import load_manifest


ALLOWED_CONDITIONS = {"baseline", "revised"}
ALLOWED_OUTCOMES = {"select", "clarify", "no_skill"}


def nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def discover_skills(repo: Path) -> set[str]:
    return {
        path.parent.name
        for path in repo.glob("*/SKILL.md")
        if path.parent.is_dir()
    }


def validate(path: Path, repo: Path) -> list[str]:
    errors: list[str] = []
    try:
        data = load_manifest(path)
    except FileNotFoundError:
        return [f"manifest does not exist: {path}"]
    except (ValueError, OSError) as exc:
        if hasattr(exc, "lineno"):
            return [f"invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}"]
        return [str(exc)]

    if not isinstance(data, dict):
        return ["top-level JSON value must be an object"]

    if data.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if not nonempty(data.get("suite")):
        errors.append("suite must be a non-empty string")
    if not nonempty(data.get("baseline_commit")):
        errors.append("baseline_commit must be a non-empty string")

    conditions = data.get("conditions")
    if not isinstance(conditions, list) or set(conditions) != ALLOWED_CONDITIONS:
        errors.append("conditions must contain baseline and revised exactly once")
    elif len(conditions) != len(set(conditions)):
        errors.append("conditions must not contain duplicates")

    trials = data.get("default_trials")
    if not isinstance(trials, int) or isinstance(trials, bool) or not 1 <= trials <= 20:
        errors.append("default_trials must be an integer from 1 to 20")

    known_skills = discover_skills(repo)
    if not known_skills:
        errors.append(f"no skills discovered under repository: {repo}")

    cases = data.get("cases")
    if not isinstance(cases, list) or not cases:
        errors.append("cases must be a non-empty list")
        return errors

    seen: set[str] = set()
    for index, case in enumerate(cases):
        label = f"cases[{index}]"
        if not isinstance(case, dict):
            errors.append(f"{label} must be an object")
            continue

        case_id = case.get("id")
        if not nonempty(case_id):
            errors.append(f"{label}.id must be a non-empty string")
        elif case_id in seen:
            errors.append(f"{label}.id is duplicated: {case_id}")
        else:
            seen.add(case_id)

        for field in ("family", "prompt", "rationale"):
            if not nonempty(case.get(field)):
                errors.append(f"{label}.{field} must be a non-empty string")
        if not isinstance(case.get("critical"), bool):
            errors.append(f"{label}.critical must be true or false")

        expected = case.get("expected")
        if not isinstance(expected, dict):
            errors.append(f"{label}.expected must be an object")
            continue
        outcome = expected.get("outcome")
        if outcome not in ALLOWED_OUTCOMES:
            errors.append(f"{label}.expected.outcome must be one of {sorted(ALLOWED_OUTCOMES)}")
        skill = expected.get("skill")
        if outcome == "select":
            if skill not in known_skills:
                errors.append(f"{label}.expected.skill is not a discovered skill: {skill}")
        elif skill is not None:
            errors.append(f"{label}.expected.skill must be omitted for {outcome} outcomes")

        forbidden = case.get("forbidden_skills")
        if not isinstance(forbidden, list):
            errors.append(f"{label}.forbidden_skills must be a list")
            continue
        if len(forbidden) != len(set(forbidden)):
            errors.append(f"{label}.forbidden_skills must not contain duplicates")
        unknown = sorted(set(forbidden) - known_skills - {"github:github"})
        if unknown:
            errors.append(f"{label}.forbidden_skills contains unknown skills: {', '.join(unknown)}")
        if skill in forbidden:
            errors.append(f"{label}.expected.skill must not also be forbidden")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument(
        "--repo",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="Repository root used to discover skill folders",
    )
    args = parser.parse_args()

    errors = validate(args.manifest, args.repo)
    if errors:
        print(f"FAIL: {args.manifest}")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"PASS: {args.manifest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
