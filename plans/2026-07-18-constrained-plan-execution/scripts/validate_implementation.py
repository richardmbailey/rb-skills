#!/usr/bin/env python3
"""Validate the implemented constrained-execution skills and retained evidence."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path


PLAN_ROOT = Path(__file__).resolve().parents[1]
REPO = PLAN_ROOT.parents[1]
LAUNCHER = REPO / "rb-safe-operation" / "scripts" / "run_runtime.py"


PHASES = [
    PLAN_ROOT / "phase-1-supported-walking-skeleton.md",
    PLAN_ROOT / "phase-2-planning-and-continuity.md",
    PLAN_ROOT / "phase-3-policy-and-assessment.md",
    PLAN_ROOT / "phase-4-execution-verification-and-resume.md",
    PLAN_ROOT / "phase-5-integration-and-release.md",
]
SKILLS = ["rb-create-low-level-plan", "rb-assess-plan-safety", "rb-safe-operation"]
CHECKBOX = re.compile(r"^- \[([ xv])\] ", re.MULTILINE)


def launcher_command(*arguments: str) -> list[str]:
    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser().resolve()
    manifest_path = codex_home / "rb-safe-operation" / "current.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    bootstrap = manifest.get("launcher_bootstrap_interpreter_path")
    if not isinstance(bootstrap, str) or not Path(bootstrap).is_absolute():
        raise RuntimeError(f"invalid launcher bootstrap in {manifest_path}")
    return [bootstrap, "-I", "-S", "-B", str(LAUNCHER), *arguments]


def validate(require_verified: bool) -> list[str]:
    failures: list[str] = []
    try:
        launcher_command("runtime-info")
    except Exception as exc:
        return [f"cannot resolve verified runtime launcher: {exc}"]
    for phase in PHASES:
        if not phase.is_file():
            failures.append(f"missing phase file: {phase.name}")
            continue
        states = CHECKBOX.findall(phase.read_text(encoding="utf-8"))
        if not states:
            failures.append(f"phase has no tasks: {phase.name}")
        if require_verified and any(state != "v" for state in states):
            failures.append(f"phase is not fully verified: {phase.name}")

    for skill in SKILLS:
        root = REPO / skill
        for relative in ("SKILL.md", "agents/openai.yaml", "evals/eval-plan.json"):
            if not (root / relative).is_file():
                failures.append(f"missing skill artifact: {skill}/{relative}")
        text = (root / "SKILL.md").read_text(encoding="utf-8")
        if "TODO" in text or "[TODO" in text:
            failures.append(f"scaffold placeholder remains: {skill}/SKILL.md")

    duplicate_python = [
        path for skill in SKILLS[:-1]
        for path in (REPO / skill).rglob("*.py")
    ]
    if duplicate_python:
        failures.append(f"consumer skills contain duplicated Python runtime code: {duplicate_python}")

    for skill in SKILLS:
        expected = REPO / skill / "references" / "generated"
        result = subprocess.run(
            launcher_command("check-schema-drift", "--expected", str(expected)),
            check=False, capture_output=True, text=True,
        )
        if result.returncode != 0:
            failures.append(f"generated schema drift for {skill}: {(result.stderr or result.stdout).strip()[:500]}")

    evidence = PLAN_ROOT / "evidence" / "phase-3"
    assessor = sorted(evidence.glob("semantic-assessor-trial-*.txt"))
    baseline = sorted(evidence.glob("semantic-baseline-trial-*.txt"))
    if len(assessor) != 3 or len(baseline) != 3:
        failures.append(f"semantic trial count mismatch: with_skill={len(assessor)}, without_skill={len(baseline)}")
    with tempfile.TemporaryDirectory(prefix="rb-safe-semantic-") as temporary:
        temporary_root = Path(temporary)
        for path in assessor:
            lines = path.read_text(encoding="utf-8").splitlines()
            try:
                proposal = json.loads(lines[0])
            except Exception as exc:
                failures.append(f"invalid typed semantic trial {path.name}: {exc}")
                continue
            candidate = temporary_root / f"{path.stem}.json"
            candidate.write_text(json.dumps(proposal, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
            validation = subprocess.run(
                launcher_command("validate", "--artifact-type", "semantic-assessment-proposal", "--input", str(candidate)),
                check=False, capture_output=True, text=True,
            )
            if validation.returncode != 0:
                failures.append(f"invalid typed semantic trial {path.name}: {validation.stderr.strip()[:500]}")
                continue
            if proposal.get("semantic_pass") or not proposal.get("findings") or lines[-1] != "FALSE":
                failures.append(f"unexpected semantic trial verdict: {path.name}")
    for path in baseline:
        if "FALSE" not in path.read_text(encoding="utf-8"):
            failures.append(f"baseline trial lacks preserved false verdict: {path.name}")

    top_plan = (PLAN_ROOT / "IMPLEMENTATION_PLAN.md").read_text(encoding="utf-8")
    if "four-folder install" in top_plan:
        failures.append("stale four-folder installation wording remains")
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    for skill in SKILLS:
        if f"`${skill}`" not in readme and f"`$${skill}`" not in readme and f"$${skill}" not in readme:
            if f"`${'$' + skill}`" not in readme:
                failures.append(f"README lacks {skill}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-verified", action="store_true")
    args = parser.parse_args()
    failures = validate(args.require_verified)
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("PASS: constrained execution skills, schemas, semantic evidence, and phase state are consistent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
