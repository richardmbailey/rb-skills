#!/usr/bin/env python3
"""Validate cross-file routing, metadata, capability, documentation, and eval consistency."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot load JSON {path}: {exc}") from exc


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"cannot read {path}: {exc}") from exc


def frontmatter_name(text: str) -> str | None:
    match = re.match(r"^---\n(.*?)\n---\n", text, flags=re.DOTALL)
    if match is None:
        return None
    for line in match.group(1).splitlines():
        key, separator, value = line.partition(":")
        if separator and key.strip() == "name":
            return value.strip().strip('"\'')
    return None


def _case_ids(cases: list[object], relative: str, errors: list[str]) -> list[str]:
    ids: list[str] = []
    for index, case in enumerate(cases):
        if not isinstance(case, dict):
            errors.append(f"{relative}: cases[{index}] must be an object")
            continue
        case_id = case.get("id")
        if not isinstance(case_id, str) or not case_id.strip():
            errors.append(f"{relative}: cases[{index}].id must be a non-empty string")
            continue
        ids.append(case_id)
    if len(ids) != len(set(ids)):
        errors.append(f"{relative}: eval case IDs must be unique")
    return ids


def _directory_files(path: Path) -> dict[str, bytes]:
    if not path.is_dir():
        raise ValueError(f"directory does not exist: {path}")
    return {
        item.relative_to(path).as_posix(): item.read_bytes()
        for item in sorted(path.rglob("*"))
        if item.is_file()
    }


def validate(manifest_path: Path, repo: Path) -> list[str]:
    try:
        manifest = load_json(manifest_path)
    except ValueError as exc:
        return [str(exc)]
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        return ["consistency manifest schema_version must be 1"]

    errors: list[str] = []

    for index, contract in enumerate(manifest.get("file_contracts", [])):
        label = f"file_contracts[{index}]"
        if not isinstance(contract, dict) or not isinstance(contract.get("path"), str):
            errors.append(f"{label}.path must be a string")
            continue
        relative = contract["path"]
        try:
            text = read_text(repo / relative)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        for required in contract.get("required", []):
            if required not in text:
                errors.append(f"{relative}: missing required text: {required!r}")
        for forbidden in contract.get("forbidden", []):
            if forbidden in text:
                errors.append(f"{relative}: contains forbidden text: {forbidden!r}")

    for index, contract in enumerate(manifest.get("skill_metadata_contracts", [])):
        label = f"skill_metadata_contracts[{index}]"
        skill = contract.get("skill") if isinstance(contract, dict) else None
        if not isinstance(skill, str):
            errors.append(f"{label}.skill must be a string")
            continue
        skill_path = repo / skill / "SKILL.md"
        agent_path = repo / skill / "agents" / "openai.yaml"
        try:
            skill_text = read_text(skill_path)
            agent_text = read_text(agent_path)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        observed_name = frontmatter_name(skill_text)
        if observed_name != skill:
            errors.append(f"{skill}: frontmatter name {observed_name!r} does not match directory")
        if f"${skill}" not in agent_text:
            errors.append(f"{agent_path.relative_to(repo)}: default prompt does not invoke ${skill}")
        lower = agent_text.lower()
        for required in contract.get("required", []):
            if str(required).lower() not in lower:
                errors.append(
                    f"{agent_path.relative_to(repo)}: metadata missing concept {required!r}"
                )

    for index, contract in enumerate(manifest.get("json_case_contracts", [])):
        label = f"json_case_contracts[{index}]"
        relative = contract.get("path") if isinstance(contract, dict) else None
        if not isinstance(relative, str):
            errors.append(f"{label}.path must be a string")
            continue
        try:
            payload = load_json(repo / relative)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if not isinstance(payload, list):
            errors.append(f"{relative}: expected a JSON list")
            continue
        ids = set(_case_ids(payload, relative, errors))
        for required_id in contract.get("required_ids", []):
            if required_id not in ids:
                errors.append(f"{relative}: missing required case ID {required_id!r}")
        serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        for required in contract.get("required_substrings", []):
            if required not in serialized:
                errors.append(f"{relative}: missing required case concept {required!r}")
        for forbidden in contract.get("forbidden_substrings", []):
            if forbidden in serialized:
                errors.append(f"{relative}: contains forbidden case concept {forbidden!r}")

    for index, contract in enumerate(manifest.get("behavioural_eval_contracts", [])):
        label = f"behavioural_eval_contracts[{index}]"
        if not isinstance(contract, dict):
            errors.append(f"{label} must be an object")
            continue
        relative = contract.get("path")
        skill = contract.get("skill")
        minimum_cases = contract.get("minimum_cases")
        if not isinstance(relative, str) or not isinstance(skill, str):
            errors.append(f"{label} requires string path and skill")
            continue
        if not isinstance(minimum_cases, int) or isinstance(minimum_cases, bool) or minimum_cases < 1:
            errors.append(f"{label}.minimum_cases must be a positive integer")
            continue
        try:
            payload = load_json(repo / relative)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if not isinstance(payload, dict) or payload.get("schema_version") != 1:
            errors.append(f"{relative}: eval plan schema_version must be 1")
            continue
        if payload.get("skill") != skill:
            errors.append(f"{relative}: expected skill {skill!r}, found {payload.get('skill')!r}")
        cases = payload.get("cases")
        if not isinstance(cases, list):
            errors.append(f"{relative}: cases must be a list")
            continue
        if len(cases) < minimum_cases:
            errors.append(f"{relative}: requires at least {minimum_cases} cases; found {len(cases)}")
        _case_ids(cases, relative, errors)

    for index, contract in enumerate(manifest.get("directory_mirror_contracts", [])):
        label = f"directory_mirror_contracts[{index}]"
        if not isinstance(contract, dict) or not isinstance(contract.get("canonical"), str):
            errors.append(f"{label}.canonical must be a string")
            continue
        mirrors = contract.get("mirrors")
        if not isinstance(mirrors, list) or not mirrors or not all(isinstance(item, str) for item in mirrors):
            errors.append(f"{label}.mirrors must be a non-empty list of strings")
            continue
        canonical_relative = contract["canonical"]
        try:
            canonical_files = _directory_files(repo / canonical_relative)
        except (OSError, ValueError) as exc:
            errors.append(str(exc))
            continue
        for mirror_relative in mirrors:
            try:
                mirror_files = _directory_files(repo / mirror_relative)
            except (OSError, ValueError) as exc:
                errors.append(str(exc))
                continue
            canonical_names = set(canonical_files)
            mirror_names = set(mirror_files)
            missing = sorted(canonical_names - mirror_names)
            extra = sorted(mirror_names - canonical_names)
            if missing:
                errors.append(f"{mirror_relative}: missing canonical files: {missing}")
            if extra:
                errors.append(f"{mirror_relative}: contains extra files: {extra}")
            for name in sorted(canonical_names & mirror_names):
                if canonical_files[name] != mirror_files[name]:
                    errors.append(
                        f"{mirror_relative}/{name}: differs from {canonical_relative}/{name}"
                    )

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
