#!/usr/bin/env python3
"""Build blinded JSONL packets for independent semantic routing trials."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from routing_manifest import load_manifest


def extract_description(text: str, source: str) -> tuple[str, str]:
    """Read the strict one-line YAML subset used by skill frontmatter.

    Skill files in this repository keep ``name`` and ``description`` as
    top-level, one-line scalars. Rejecting anything else is safer here than
    pretending to implement the full YAML grammar without a YAML dependency.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError(f"missing frontmatter in {source}")
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise ValueError(f"unterminated frontmatter in {source}") from exc

    name = ""
    description = ""
    for line in lines[1:end]:
        if line[:1].isspace():
            continue
        if line.startswith("name:"):
            name = parse_scalar(line.split(":", 1)[1], source, "name")
        elif line.startswith("description:"):
            description = parse_scalar(
                line.split(":", 1)[1], source, "description"
            )
    if not name or not description:
        raise ValueError(f"name or description missing in {source}")
    return name, description


def parse_scalar(raw: str, source: str, field: str) -> str:
    value = raw.strip()
    if not value or value in {"|", ">", "|-", ">-", "|+", ">+"}:
        raise ValueError(f"{field} must be a one-line scalar in {source}")
    if value[0] in {'"', "'"}:
        if len(value) < 2 or value[-1] != value[0]:
            raise ValueError(f"unterminated quoted {field} in {source}")
        value = value[1:-1]
    return value


def read_at_condition(
    repo: Path,
    baseline_repo: Path,
    relative: Path,
    condition: str,
    baseline: str,
) -> str:
    if condition == "baseline":
        result = subprocess.run(
            [
                "git",
                "-C",
                str(baseline_repo),
                "show",
                f"{baseline}:{relative.as_posix()}",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout
    return (repo / relative).read_text(encoding="utf-8")


def discover_skill_paths(
    repo: Path, baseline_repo: Path, condition: str, baseline: str
) -> list[Path]:
    if condition == "revised":
        return sorted(path.relative_to(repo) for path in repo.glob("*/SKILL.md"))

    result = subprocess.run(
        ["git", "-C", str(baseline_repo), "ls-tree", "-r", "--name-only", baseline],
        check=True,
        capture_output=True,
        text=True,
    )
    return sorted(
        Path(line)
        for line in result.stdout.splitlines()
        if len(Path(line).parts) == 2
        and Path(line).parts[0].startswith("rb-")
        and Path(line).name == "SKILL.md"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--condition", choices=("baseline", "revised"), required=True)
    parser.add_argument("--trial", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument(
        "--baseline-repo",
        type=Path,
        help="Git repository containing baseline_commit (defaults to --repo)",
    )
    args = parser.parse_args()
    baseline_repo = args.baseline_repo or args.repo

    manifest = load_manifest(args.manifest)
    if args.trial < 1 or args.trial > manifest.get("default_trials", 0):
        raise SystemExit("trial must be within the manifest default_trials range")

    metadata = []
    for relative in discover_skill_paths(
        args.repo,
        baseline_repo,
        args.condition,
        manifest["baseline_commit"],
    ):
        text = read_at_condition(
            args.repo,
            baseline_repo,
            relative,
            args.condition,
            manifest["baseline_commit"],
        )
        name, description = extract_description(text, relative.as_posix())
        metadata.append({"name": name, "description": description})

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        for case in manifest["cases"]:
            packet = {
                "case_id": case["id"],
                "condition": args.condition,
                "trial": args.trial,
                "user_request": case["prompt"],
                "available_skills": metadata,
                "allowed_outcomes": ["select", "clarify", "no_skill"],
                "response_schema": {
                    "case_id": "string",
                    "condition": "baseline|revised",
                    "trial": "integer",
                    "outcome": "select|clarify|no_skill",
                    "skill": "skill name when outcome=select, otherwise null",
                    "confidence": "high|medium|low",
                    "explanation": "one sentence"
                }
            }
            handle.write(json.dumps(packet, sort_keys=True) + "\n")

    print(f"WROTE: {args.output} ({len(manifest['cases'])} packets)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
