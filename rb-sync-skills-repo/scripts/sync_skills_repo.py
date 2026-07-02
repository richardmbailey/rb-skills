#!/usr/bin/env python3
"""Install or sync agent skill folders from a local repository."""

from __future__ import annotations

import argparse
import fnmatch
import os
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


EXCLUDED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".system",
    ".rb-agent-global-backups",
    "__pycache__",
    "codex-primary-runtime",
    "node_modules",
    "output",
    "outputs",
}

COPY_IGNORE_PATTERNS = (
    ".git",
    ".hg",
    ".svn",
    ".DS_Store",
    "__pycache__",
    "*.pyc",
    ".env",
    ".env.*",
)


@dataclass(frozen=True)
class SkillCandidate:
    name: str
    path: Path
    frontmatter_name: str | None


@dataclass(frozen=True)
class Destination:
    path: Path
    agent: str
    reason: str


def codex_dest() -> Path:
    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        return Path(codex_home).expanduser() / "skills"
    return Path.home() / ".codex" / "skills"


def claude_dest() -> Path:
    return Path.home() / ".claude" / "skills"


def looks_like_claude_code() -> bool:
    if os.environ.get("CLAUDE_PROJECT_DIR") or os.environ.get("CLAUDE_SESSION_ID"):
        return True
    if (Path.home() / ".claude").exists():
        return True
    return shutil.which("claude") is not None


def default_dest(agent: str) -> Destination:
    if agent == "codex":
        return Destination(codex_dest(), "codex", "forced with --agent codex")
    if agent == "claude":
        return Destination(claude_dest(), "claude", "forced with --agent claude")

    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        return Destination(codex_dest(), "codex", "CODEX_HOME is set")

    codex_path = Path.home() / ".codex"
    if codex_path.exists():
        return Destination(codex_path / "skills", "codex", "~/.codex exists")

    if looks_like_claude_code():
        return Destination(claude_dest(), "claude", "Claude Code was detected")

    return Destination(codex_path / "skills", "codex", "default fallback")


def parse_frontmatter_name(skill_md: Path) -> str | None:
    try:
        text = skill_md.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = skill_md.read_text(encoding="utf-8-sig")

    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None

    for line in lines[1:]:
        stripped = line.strip()
        if stripped == "---":
            return None
        if stripped.startswith("name:"):
            value = stripped.split(":", 1)[1].strip()
            return value.strip("\"'")
    return None


def discover_skills(source: Path, allow_name_mismatch: bool) -> list[SkillCandidate]:
    source = source.resolve()
    if not source.exists():
        raise SystemExit(f"Source does not exist: {source}")
    if not source.is_dir():
        raise SystemExit(f"Source is not a directory: {source}")

    candidates: list[SkillCandidate] = []
    if (source / "SKILL.md").is_file():
        candidates.append(candidate_from_dir(source, allow_name_mismatch))
    else:
        for child in sorted(source.iterdir(), key=lambda p: p.name):
            if not child.is_dir():
                continue
            if child.name.startswith(".") or child.name in EXCLUDED_DIRS:
                continue
            if (child / "SKILL.md").is_file():
                candidates.append(candidate_from_dir(child, allow_name_mismatch))

    if not candidates:
        raise SystemExit(f"No skill folders with SKILL.md found in {source}")
    return candidates


def candidate_from_dir(path: Path, allow_name_mismatch: bool) -> SkillCandidate:
    name = path.name
    frontmatter_name = parse_frontmatter_name(path / "SKILL.md")
    if frontmatter_name is None:
        raise SystemExit(f"{path}/SKILL.md is missing frontmatter name")
    if frontmatter_name != name and not allow_name_mismatch:
        raise SystemExit(
            f"{path}/SKILL.md name is {frontmatter_name!r}, but folder is {name!r}. "
            "Fix the skill or pass --allow-name-mismatch."
        )
    return SkillCandidate(name=name, path=path.resolve(), frontmatter_name=frontmatter_name)


def filter_candidates(candidates: list[SkillCandidate], names: list[str] | None) -> list[SkillCandidate]:
    if not names:
        return candidates
    by_name = {candidate.name: candidate for candidate in candidates}
    missing = [name for name in names if name not in by_name]
    if missing:
        available = ", ".join(sorted(by_name))
        raise SystemExit(f"Requested skills not found: {', '.join(missing)}. Available: {available}")
    return [by_name[name] for name in names]


def should_ignore(_dir: str, names: list[str]) -> set[str]:
    ignored: set[str] = set()
    for name in names:
        if any(fnmatch.fnmatch(name, pattern) for pattern in COPY_IGNORE_PATTERNS):
            ignored.add(name)
    return ignored


def backup_existing(dest_path: Path, backup_root: Path, dry_run: bool) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_path = backup_root / f"{dest_path.name}-{timestamp}"
    counter = 2
    while backup_path.exists():
        backup_path = backup_root / f"{dest_path.name}-{timestamp}-{counter}"
        counter += 1

    if not dry_run:
        backup_root.mkdir(parents=True, exist_ok=True)
        shutil.move(str(dest_path), str(backup_path))
    return backup_path


def install_candidate(
    candidate: SkillCandidate,
    dest_root: Path,
    mode: str,
    replace: bool,
    dry_run: bool,
) -> str:
    dest_path = dest_root / candidate.name

    if dest_path.is_symlink():
        current_target = dest_path.resolve()
        if current_target == candidate.path and mode == "symlink":
            return f"ok: {candidate.name} already links to {candidate.path}"

    if dest_path.exists() or dest_path.is_symlink():
        if not replace:
            return f"skip: {candidate.name} already exists at {dest_path} (use --replace to back it up)"
        backup_path = backup_existing(dest_path, dest_root / ".skill-backups", dry_run)
        action = f"backup {dest_path} -> {backup_path}; "
    else:
        action = ""

    if not dry_run:
        dest_root.mkdir(parents=True, exist_ok=True)
        if mode == "symlink":
            os.symlink(candidate.path, dest_path, target_is_directory=True)
        elif mode == "copy":
            shutil.copytree(candidate.path, dest_path, ignore=should_ignore)
        else:
            raise AssertionError(f"Unknown mode: {mode}")

    verb = "link" if mode == "symlink" else "copy"
    prefix = "dry-run: " if dry_run else ""
    return f"{prefix}{action}{verb} {candidate.path} -> {dest_path}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Install or sync Codex or Claude Code skill folders from a local repository.",
    )
    parser.add_argument("source", nargs="?", help="Repo root, skills subdirectory, or a single skill folder.")
    parser.add_argument(
        "--agent",
        choices=("auto", "codex", "claude"),
        default="auto",
        help="Destination agent for default install path. Auto tries Codex first, then Claude Code.",
    )
    parser.add_argument("--dest", type=Path, help="Destination skills directory. Overrides --agent.")
    parser.add_argument("--mode", choices=("symlink", "copy"), default="symlink", help="Install mode.")
    parser.add_argument("--skills", nargs="+", help="Specific skill folder names to install.")
    parser.add_argument("--dry-run", action="store_true", help="Print planned actions without writing.")
    parser.add_argument("--replace", action="store_true", help="Back up and replace existing destination skills.")
    parser.add_argument("--allow-name-mismatch", action="store_true", help="Allow SKILL.md name to differ from folder.")
    parser.add_argument("--list", action="store_true", help="List discovered skills without installing.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.source:
        raise SystemExit("source is required")

    source = Path(args.source).expanduser()
    if args.dest:
        destination = Destination(args.dest.expanduser(), "custom", "set with --dest")
    else:
        destination = default_dest(args.agent)
    dest = destination.path
    candidates = discover_skills(source, args.allow_name_mismatch)
    candidates = filter_candidates(candidates, args.skills)

    if args.list:
        for candidate in candidates:
            print(f"{candidate.name}\t{candidate.path}")
        return 0

    print(f"Source: {source.resolve()}")
    print(f"Destination: {dest.resolve()} ({destination.agent}; {destination.reason})")
    print(f"Mode: {args.mode}")
    print(f"Skills: {', '.join(candidate.name for candidate in candidates)}")

    for candidate in candidates:
        print(install_candidate(candidate, dest, args.mode, args.replace, args.dry_run))

    if not args.dry_run:
        if destination.agent == "claude":
            print("Done. Claude Code should pick up edits live when ~/.claude/skills is already watched; restart Claude Code if the skills directory was newly created.")
        elif destination.agent == "codex":
            print("Done. Restart Codex to pick up newly installed or updated skills.")
        else:
            print("Done. Restart or reload the target agent if newly installed skills are not visible.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
