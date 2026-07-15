#!/usr/bin/env python3
"""Validate deterministic contracts preserved during instruction-body cleanup."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def validate(manifest_path: Path, repo: Path) -> list[str]:
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"cannot load contract manifest: {exc}"]
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        return ["schema_version must be 1"]
    contracts = manifest.get("contracts")
    if not isinstance(contracts, list) or not contracts:
        return ["contracts must be a non-empty list"]

    errors: list[str] = []
    for index, contract in enumerate(contracts):
        label = f"contracts[{index}]"
        if not isinstance(contract, dict) or not isinstance(contract.get("path"), str):
            errors.append(f"{label}.path must be a string")
            continue
        relative = contract["path"]
        for field in ("required", "forbidden"):
            values = contract.get(field, [])
            if not isinstance(values, list) or not all(
                isinstance(value, str) for value in values
            ):
                errors.append(f"{label}.{field} must be a list of strings")
                values = []
            contract[field] = values
        occurrences = contract.get("max_occurrences", {})
        if not isinstance(occurrences, dict) or not all(
            isinstance(value, str)
            and isinstance(maximum, int)
            and not isinstance(maximum, bool)
            and maximum >= 0
            for value, maximum in occurrences.items()
        ):
            errors.append(
                f"{label}.max_occurrences must map strings to non-negative integers"
            )
            occurrences = {}
        maximum_lines = contract.get("max_lines")
        if not isinstance(maximum_lines, int) or isinstance(maximum_lines, bool) or maximum_lines < 1:
            errors.append(f"{label}.max_lines must be a positive integer")
            maximum_lines = None

        path = repo / relative
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            errors.append(f"{relative}: cannot read: {exc}")
            continue

        for required in contract.get("required", []):
            if required not in text:
                errors.append(f"{relative}: missing required text: {required!r}")
        for forbidden in contract.get("forbidden", []):
            if forbidden in text:
                errors.append(f"{relative}: contains forbidden text: {forbidden!r}")
        for value, maximum in occurrences.items():
            count = text.count(value)
            if count > maximum:
                errors.append(
                    f"{relative}: {value!r} occurs {count} times; maximum is {maximum}"
                )
        if isinstance(maximum_lines, int) and len(text.splitlines()) > maximum_lines:
            errors.append(f"{relative}: exceeds {maximum_lines} lines")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2])
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
