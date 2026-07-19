#!/usr/bin/env python3
"""Deterministic structural checks for constrained-execution Phase 0 documents."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
PLAN = ROOT / "IMPLEMENTATION_PLAN.md"
PHASE = ROOT / "phase-0-plan-hardening-and-feasibility.md"
REFERENCES = sorted((ROOT / "references").glob("*.md"))
EVIDENCE_MD = sorted((ROOT / "evidence").glob("*.md"))
DOCS = [PLAN, PHASE, *REFERENCES, *EVIDENCE_MD]
MATRIX = ROOT / "references" / "validation-matrix.md"
REVISION = ROOT / "evidence" / "revision-note.md"
HOST_PROBE = ROOT / "evidence" / "host-capability-probe.md"
WORKTREE_BASELINE = ROOT / "evidence" / "preexisting-worktree.json"
REVIEW_FINDINGS = ROOT / "evidence" / "review-findings.json"
FINAL_REVIEW = ROOT / "evidence" / "final-review.md"

INVARIANT_DEFINITION = re.compile(r"^### `([A-Z]-\d{3})` ", re.MULTILINE)
MATRIX_ROW = re.compile(r"^\| `([A-Z]-\d{3})` \|", re.MULTILINE)
LOCAL_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
FINDING = re.compile(r"F-(?:0[1-9]|1[0-4])")
CHECKBOX = re.compile(r"^- \[([ xv])\] ", re.MULTILINE)
ALLOWED_LEVELS = {
    "host_enforced",
    "host_observed",
    "coordinator_observed",
    "agent_reported",
    "instruction_only",
    "unknown",
}
EXPECTED_ROLES = {
    "Route coordinator",
    "Phase planner",
    "Deterministic validator",
    "Semantic assessor",
    "Execution coordinator",
    "Executor",
    "Verifier",
    "Repair executor",
    "Shared runtime",
    "Human reviewer",
}
EXPECTED_STATE_OWNERS = {
    "Route coordinator": "Route coordinator",
    "Phase planner": "Coordinator",
    "Deterministic validator": "Coordinator",
    "Semantic assessor": "Coordinator",
    "Execution coordinator": "Execution coordinator",
    "Executor": "Current leased executor",
    "Verifier": "Coordinator",
    "Repair executor": "Current leased repair executor",
    "Shared runtime": "Explicit runtime setup command holding setup lock",
    "Human reviewer": "Coordinator",
}
EXPECTED_REVIEW_IDS = {f"RV-{number:02d}" for number in range(1, 19)}
EXPECTED_REFERENCE_NAMES = {
    "assurance-and-threat-model.md",
    "execution-audit-state-model.md",
    "operation-and-policy-contract.md",
    "validation-matrix.md",
}
EXPECTED_EVIDENCE_MD_NAMES = {
    "final-review.md",
    "host-capability-probe.md",
    "phase-0-baseline.md",
    "revision-note.md",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--require-verified",
        action="store_true",
        help="Require every Phase 0 task checkbox to be [v].",
    )
    parser.add_argument(
        "--allow-implementation",
        action="store_true",
        help="Skip the Phase 0 worktree-scope freeze after later implementation phases have begun.",
    )
    return parser.parse_args()


def markdown_cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def fail(message: str, failures: list[str]) -> None:
    failures.append(message)


def validate_documents(texts: dict[Path, str], failures: list[str]) -> None:
    for path, content in texts.items():
        for number, line in enumerate(content.splitlines(), start=1):
            if line != line.rstrip():
                fail(f"trailing whitespace: {path.relative_to(ROOT)}:{number}", failures)
        for target in LOCAL_LINK.findall(content):
            if target.startswith(("http://", "https://", "#")):
                continue
            target_path = (path.parent / target.split("#", 1)[0]).resolve()
            try:
                target_path.relative_to(ROOT.resolve())
            except ValueError:
                fail(f"local link escapes plan root: {path.relative_to(ROOT)} -> {target}", failures)
                continue
            if not target_path.exists():
                fail(f"broken local link: {path.relative_to(ROOT)} -> {target}", failures)


def validate_invariants(texts: dict[Path, str], failures: list[str]) -> None:
    definitions: list[str] = []
    for path in REFERENCES:
        definitions.extend(INVARIANT_DEFINITION.findall(texts[path]))
    definition_counts = Counter(definitions)
    duplicates = sorted(key for key, count in definition_counts.items() if count != 1)
    if duplicates:
        fail(f"invariant definitions are not unique: {', '.join(duplicates)}", failures)
    if len(definitions) != 50:
        fail(f"expected 50 invariant definitions, found {len(definitions)}", failures)

    rows = MATRIX_ROW.findall(texts[MATRIX])
    row_counts = Counter(rows)
    duplicate_rows = sorted(key for key, count in row_counts.items() if count != 1)
    if duplicate_rows:
        fail(f"validation matrix rows are not unique: {', '.join(duplicate_rows)}", failures)
    if set(rows) != set(definitions):
        missing = sorted(set(definitions) - set(rows))
        extra = sorted(set(rows) - set(definitions))
        fail(f"matrix/definition mismatch; missing={missing}, extra={extra}", failures)


def validate_findings(texts: dict[Path, str], failures: list[str]) -> None:
    expected = {f"F-{number:02d}" for number in range(1, 15)}
    for path in (PHASE, MATRIX, REVISION):
        observed = set(FINDING.findall(texts[path]))
        absent = sorted(expected - observed)
        if absent:
            fail(f"{path.relative_to(ROOT)} missing findings: {', '.join(absent)}", failures)

    data = json.loads(REVIEW_FINDINGS.read_text(encoding="utf-8"))
    findings = data.get("findings")
    if not isinstance(findings, list) or not findings:
        fail("review-findings.json has no findings", failures)
        return
    ids: set[str] = set()
    for item in findings:
        identifier = item.get("id")
        if not isinstance(identifier, str) or identifier in ids:
            fail(f"invalid or duplicate review finding id: {identifier!r}", failures)
        ids.add(identifier)
        if item.get("severity") not in {"P0", "P1", "P2", "P3"}:
            fail(f"invalid review severity for {identifier}", failures)
        if item.get("status") not in {"fixed", "accepted"}:
            fail(f"unresolved review finding {identifier}: {item.get('status')}", failures)
        if item.get("severity") in {"P0", "P1"} and (
            item.get("status") != "fixed" or item.get("blocking") is not True
        ):
            fail(f"P0/P1 finding must be blocking and fixed: {identifier}", failures)
        if item.get("blocking") and item.get("status") != "fixed":
            fail(f"blocking review finding not fixed: {identifier}", failures)
        if not item.get("resolution"):
            fail(f"review finding lacks resolution: {identifier}", failures)
    if ids != EXPECTED_REVIEW_IDS:
        fail(
            f"review finding set mismatch; missing={sorted(EXPECTED_REVIEW_IDS - ids)}, "
            f"extra={sorted(ids - EXPECTED_REVIEW_IDS)}",
            failures,
        )


def validate_architecture(texts: dict[Path, str], failures: list[str]) -> None:
    lines = texts[PLAN].splitlines()
    expected_header = [
        "Role/component",
        "Responsibility",
        "Input",
        "Output",
        "State owner",
        "Permission level",
        "Context/handoff",
        "Observation source",
        "Failure mode",
    ]
    try:
        start = next(index for index, line in enumerate(lines) if markdown_cells(line) == expected_header)
    except StopIteration:
        fail("architecture table lacks required boundary columns", failures)
        return

    roles: set[str] = set()
    for line in lines[start + 2 :]:
        if not line.startswith("|"):
            break
        cells = markdown_cells(line)
        if len(cells) != len(expected_header) or any(not cell for cell in cells):
            fail(f"invalid or empty architecture row: {line}", failures)
            continue
        roles.add(cells[0])
        expected_owner = EXPECTED_STATE_OWNERS.get(cells[0])
        if expected_owner is not None and cells[4] != expected_owner:
            fail(
                f"architecture state owner mismatch for {cells[0]}: "
                f"expected {expected_owner!r}, observed {cells[4]!r}",
                failures,
            )
    if roles != EXPECTED_ROLES:
        fail(f"architecture role mismatch; missing={sorted(EXPECTED_ROLES - roles)}, extra={sorted(roles - EXPECTED_ROLES)}", failures)


def validate_enforcement_levels(texts: dict[Path, str], failures: list[str]) -> None:
    in_capability_table = False
    for line in texts[HOST_PROBE].splitlines():
        if line.startswith("| Capability |"):
            in_capability_table = True
            continue
        if in_capability_table and not line.startswith("|"):
            in_capability_table = False
            continue
        if not in_capability_table or line.startswith("| ---"):
            continue
        cells = markdown_cells(line)
        if len(cells) != 6:
            fail(f"invalid host capability row: {line}", failures)
            continue
        level_match = re.fullmatch(r"`([a-z_]+)`", cells[2])
        if not level_match or level_match.group(1) not in ALLOWED_LEVELS:
            fail(f"host capability has non-canonical or compound level: {cells[0]} -> {cells[2]}", failures)

    normative_text = "\n".join(texts[path] for path in [PLAN, *REFERENCES, HOST_PROBE])
    banned = (
        "It has no mutation or execution tools",
        "record every actual tool call",
        "with `FALSE` and no target writes",
        "monotonically numbered immutable event",
        "read-only validator adapter",
        "false/review",
        "denied or detected",
    )
    for phrase in banned:
        if phrase in normative_text:
            fail(f"stale or ambiguous assurance claim remains: {phrase}", failures)


def validate_plan_and_checklist(texts: dict[Path, str], require_verified: bool, failures: list[str]) -> None:
    plan_text = texts[PLAN]
    if len(plan_text.splitlines()) >= 498:
        fail("revised top-level plan is not shorter than the 498-line baseline", failures)
    if "## Open Questions" in plan_text:
        fail("top-level plan still has an unresolved Open Questions section", failures)
    if "no product-plane mutation" not in plan_text:
        fail("Phase 1 lacks corrected unsafe-path product-plane criterion", failures)

    statuses = CHECKBOX.findall(texts[PHASE])
    if len(statuses) != 110:
        fail(f"expected 110 Phase 0 checklist tasks, found {len(statuses)}", failures)
    if require_verified and any(status != "v" for status in statuses):
        fail(
            "Phase 0 checklist is not fully verified: "
            + ", ".join(f"{key}={statuses.count(key)}" for key in (" ", "x", "v")),
            failures,
        )


def validate_worktree_scope(failures: list[str]) -> None:
    baseline_data = json.loads(WORKTREE_BASELINE.read_text(encoding="utf-8"))
    expected = sorted((item["status"], item["path"]) for item in baseline_data["entries"])
    result = subprocess.run(
        ["git", "status", "--porcelain=v1", "--untracked-files=normal", "-z"],
        cwd=REPO,
        check=True,
        capture_output=True,
        text=True,
    )
    observed: list[tuple[str, str]] = []
    for entry in result.stdout.split("\0"):
        if not entry:
            continue
        status, path = entry[:2], entry[3:]
        if path == str(ROOT.relative_to(REPO)) or path.startswith(str(ROOT.relative_to(REPO)) + "/"):
            continue
        observed.append((status, path))
    observed.sort()
    if observed != expected:
        fail(f"repository paths outside Phase 0 scope changed; expected={expected}, observed={observed}", failures)


def main() -> int:
    args = parse_args()
    failures: list[str] = []
    required_files = [*DOCS, WORKTREE_BASELINE, REVIEW_FINDINGS, FINAL_REVIEW]
    missing = [str(path.relative_to(ROOT)) for path in required_files if not path.is_file()]
    if missing:
        fail(f"missing documents: {', '.join(missing)}", failures)
    if failures:
        for message in failures:
            print(f"FAIL: {message}")
        return 1

    if {path.name for path in REFERENCES} != EXPECTED_REFERENCE_NAMES:
        fail("reference document inventory differs from the four authoritative files", failures)
    if {path.name for path in EVIDENCE_MD} != EXPECTED_EVIDENCE_MD_NAMES:
        fail("Markdown evidence inventory differs from the required Phase 0 files", failures)
    if failures:
        for message in failures:
            print(f"FAIL: {message}")
        return 1

    texts = {path: path.read_text(encoding="utf-8") for path in DOCS}
    validate_documents(texts, failures)
    validate_invariants(texts, failures)
    validate_findings(texts, failures)
    validate_architecture(texts, failures)
    validate_enforcement_levels(texts, failures)
    validate_plan_and_checklist(texts, args.require_verified, failures)
    if not args.allow_implementation:
        validate_worktree_scope(failures)

    if failures:
        for message in failures:
            print(f"FAIL: {message}")
        return 1

    statuses = Counter(CHECKBOX.findall(texts[PHASE]))
    print(
        "PASS: Phase 0 documents have resolving local links, no trailing whitespace, "
        "50 one-to-one invariant/matrix rows, complete F-01..F-14 and review closure, "
        f"10 complete architecture roles, canonical host levels, "
        f"{'post-Phase-0 implementation permitted' if args.allow_implementation else 'scoped repository paths'}, "
        f"a {len(texts[PLAN].splitlines())}-line top-level plan, and checklist states "
        f"blank={statuses[' ']}, x={statuses['x']}, v={statuses['v']}."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
