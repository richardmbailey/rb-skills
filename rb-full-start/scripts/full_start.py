#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PackRoot:
    path: Path
    layout: str


@dataclass(frozen=True)
class SkillsDestination:
    path: Path
    agent: str


def codex_skills_dest() -> Path:
    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        return Path(codex_home).expanduser() / "skills"
    return Path.home() / ".codex" / "skills"


def claude_skills_dest() -> Path:
    return Path.home() / ".claude" / "skills"


def default_skills_destination(agent: str = "auto") -> SkillsDestination:
    if agent == "codex":
        return SkillsDestination(codex_skills_dest(), "codex")
    if agent == "claude":
        return SkillsDestination(claude_skills_dest(), "claude")

    codex_path = Path.home() / ".codex"
    if codex_path.exists():
        return SkillsDestination(codex_path / "skills", "codex")

    if looks_like_claude_code():
        return SkillsDestination(claude_skills_dest(), "claude")

    return SkillsDestination(codex_path / "skills", "codex")


def default_skills_dest(agent: str = "auto") -> Path:
    return default_skills_destination(agent).path


def looks_like_claude_code() -> bool:
    if os.environ.get("CLAUDE_PROJECT_DIR") or os.environ.get("CLAUDE_SESSION_ID"):
        return True
    if (Path.home() / ".claude").exists():
        return True
    return shutil.which("claude") is not None


def is_legacy_pack_root(path: Path) -> bool:
    return (
        (path / "scripts" / "install_global_skills.py").exists()
        and (path / "scripts" / "install_local_pack.py").exists()
        and (path / "skills").is_dir()
    )


def is_active_agent_skills_dir(path: Path) -> bool:
    for destination in (codex_skills_dest(), claude_skills_dest()):
        try:
            if path.resolve() == destination.resolve():
                return True
        except OSError:
            pass
    return path.name == "skills" and path.parent.name in {".codex", ".claude"}


def is_flat_skills_repo(path: Path) -> bool:
    if is_active_agent_skills_dir(path):
        return False
    sync_script = path / "rb-sync-skills-repo" / "scripts" / "sync_skills_repo.py"
    if not sync_script.is_file():
        return False
    return any(child.is_dir() and (child / "SKILL.md").is_file() for child in path.iterdir())


def detect_pack_root(path: Path) -> PackRoot | None:
    if is_legacy_pack_root(path):
        return PackRoot(path=path, layout="legacy")
    if is_flat_skills_repo(path):
        return PackRoot(path=path, layout="flat")
    return None


def add_candidate(candidates: list[Path], path: Path | None) -> None:
    if path is None:
        return
    try:
        resolved = path.expanduser().resolve()
    except OSError:
        return
    if resolved not in candidates:
        candidates.append(resolved)


def add_pack_searches(candidates: list[Path], base: Path) -> None:
    add_candidate(candidates, base)
    for parent in [base, *base.parents]:
        add_candidate(candidates, parent)
        add_candidate(candidates, parent / "_rb-agent-skills")
        add_candidate(candidates, parent / "rb-skills")


def agent_skill_dirs(agent: str = "auto") -> list[Path]:
    if agent == "codex":
        return [codex_skills_dest()]
    if agent == "claude":
        return [claude_skills_dest()]
    return [codex_skills_dest(), claude_skills_dest()]


def add_global_skill_link_candidates(candidates: list[Path], agent: str = "auto") -> None:
    for skills_dir in agent_skill_dirs(agent):
        if not skills_dir.exists():
            continue
        try:
            children = list(skills_dir.iterdir())
        except OSError:
            continue
        for child in children:
            if not child.is_symlink():
                continue
            try:
                target = child.resolve()
            except OSError:
                continue
            if (target / "SKILL.md").is_file():
                add_candidate(candidates, target.parent)


def find_pack_root(explicit: str | None, target: Path, agent: str = "auto") -> PackRoot:
    candidates: list[Path] = []
    if explicit:
        add_candidate(candidates, Path(explicit))

    env = os.environ.get("RB_AGENT_SKILLS_PACK")
    if env:
        add_candidate(candidates, Path(env))

    script_path = Path(__file__).resolve()
    for parent in script_path.parents:
        add_candidate(candidates, parent)

    add_pack_searches(candidates, Path.cwd())
    add_pack_searches(candidates, target)
    add_global_skill_link_candidates(candidates, agent)

    for candidate in candidates:
        pack_root = detect_pack_root(candidate)
        if pack_root is not None:
            return pack_root

    searched = "\n".join(f"- {candidate}" for candidate in candidates[:20])
    extra = "" if len(candidates) <= 20 else f"\n- ...and {len(candidates) - 20} more"
    raise SystemExit(
        "Could not find the RB skills pack. Run this command from the pack, "
        "pass --pack-root /path/to/rb-skills, or set RB_AGENT_SKILLS_PACK.\n"
        f"Searched:\n{searched}{extra}"
    )


def run(cmd: list[str], cwd: Path) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=str(cwd), check=True)


def discover_flat_skills(pack_root: Path) -> list[str]:
    return sorted(
        child.name
        for child in pack_root.iterdir()
        if child.is_dir() and (child / "SKILL.md").is_file()
    )


def write_project_file(path: Path, content: str, force: bool) -> str:
    existed = path.exists()
    if existed and not force:
        return f"skip existing {path}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    action = "replace" if existed and force else "write"
    return f"{action} {path}"


def install_flat_project_resources(target: Path, force: bool, codex: bool, claude: bool, cursor: bool) -> list[str]:
    agent_instructions = """# Agent Instructions

- Use installed RB agent skills when the task matches their descriptions.
- Start normal project onboarding with `$rb-start-project` in Codex or `/rb-start-project` in Claude Code.
- Read `CONTEXT.md` when present before making domain-sensitive changes.
- Keep implementation changes focused and verify them with the project's own checks.
- Preserve durable assumptions, decisions, and next actions with `$rb-working-diary` for long-running work.
"""

    project_context = """# Project Context

Use this file to capture project-specific context during start-project onboarding and later sessions.

## Project Goal

## Audience / Users

## Domain Language

## Constraints

## Run And Check Commands

## Important Assumptions
"""

    results = [
        write_project_file(target / "AGENTS.md", agent_instructions, force),
        write_project_file(target / "CONTEXT.md", project_context, force),
    ]

    if codex:
        results.append(write_project_file(target / "CODEX.md", agent_instructions, force))
    if claude:
        results.append(write_project_file(target / "CLAUDE.md", agent_instructions, force))
    if cursor:
        cursor_rule = """---
description: RB agent workflow guidance
alwaysApply: true
---

Use the installed RB agent skills for matching workflows. Start normal onboarding with `$rb-start-project` in Codex or `/rb-start-project` in Claude Code, and read `CONTEXT.md` before domain-sensitive changes.
"""
        results.append(write_project_file(target / ".cursor" / "rules" / "rb-workflow.mdc", cursor_rule, force))

    return results


def audit_flat_visibility(pack_root: Path, destination: SkillsDestination) -> None:
    skills = discover_flat_skills(pack_root)
    dest = destination.path
    missing: list[str] = []
    not_linked: list[str] = []

    for skill in skills:
        source_path = (pack_root / skill).resolve()
        dest_path = dest / skill
        if not (dest_path.exists() or dest_path.is_symlink()):
            missing.append(skill)
            continue
        if not dest_path.is_symlink():
            not_linked.append(f"{skill} exists but is not a symlink")
            continue
        if dest_path.resolve() != source_path:
            not_linked.append(f"{skill} links to {dest_path.resolve()} instead of {source_path}")

    if missing or not_linked:
        details = []
        if missing:
            details.append(f"missing: {', '.join(missing)}")
        if not_linked:
            details.append("not linked to this repo: " + "; ".join(not_linked))
        raise SystemExit(
            "Visibility check failed under "
            f"{dest}. {'; '.join(details)}. Existing folders are skipped by default; "
            "rerun with --replace-skills after confirming they should be backed up and replaced."
        )
    print(f"Visibility check: {len(skills)} skills link to {pack_root} under {dest}")


def run_legacy_full_start(pack_root: Path, target: Path, args: argparse.Namespace) -> None:
    install_global = [sys.executable, "scripts/install_global_skills.py"]
    install_local = [sys.executable, "scripts/install_local_pack.py", "--target", str(target)]
    if args.force:
        install_local.append("--force")
    if args.codex:
        install_local.append("--codex")
    if args.claude:
        install_local.append("--claude")
    if args.cursor:
        install_local.append("--cursor")

    run(install_global, pack_root)
    run(install_local, pack_root)
    run([sys.executable, "scripts/audit_skill_visibility.py"], pack_root)


def run_flat_full_start(pack_root: Path, target: Path, args: argparse.Namespace) -> None:
    sync_script = pack_root / "rb-sync-skills-repo" / "scripts" / "sync_skills_repo.py"
    destination = default_skills_destination(args.agent)
    sync_cmd = [sys.executable, str(sync_script), str(pack_root), "--mode", "symlink", "--agent", args.agent]
    if args.replace_skills:
        sync_cmd.append("--replace")

    run(sync_cmd, pack_root)
    audit_flat_visibility(pack_root, destination)

    print("Project resources:")
    for result in install_flat_project_resources(target, args.force, args.codex, args.claude, args.cursor):
        print(f"- {result}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the full RB agent project setup.")
    parser.add_argument("--target", default=".", help="Target repository path. Defaults to current directory.")
    parser.add_argument("--pack-root", help="Path to the rb-skills repo or legacy _rb-agent-skills pack.")
    parser.add_argument(
        "--agent",
        choices=("auto", "codex", "claude"),
        default="auto",
        help="Destination agent for global skill install. Auto tries Codex first, then Claude Code.",
    )
    parser.add_argument("--force", action="store_true", help="Replace existing managed project resources without backups.")
    parser.add_argument(
        "--replace-skills",
        action="store_true",
        help="Back up and replace existing global skill folders during flat-pack sync.",
    )
    parser.add_argument("--codex", action="store_true", help="Install CODEX.md into the target repository.")
    parser.add_argument("--claude", action="store_true", help="Install CLAUDE.md into the target repository.")
    parser.add_argument("--cursor", action="store_true", help="Install Cursor rule file into the target repository.")
    args = parser.parse_args()

    target = Path(args.target).expanduser().resolve()
    if not target.exists():
        raise SystemExit(f"Target path does not exist: {target}")
    if not target.is_dir():
        raise SystemExit(f"Target path is not a directory: {target}")

    pack_root = find_pack_root(args.pack_root, target, args.agent)
    print(f"Pack root: {pack_root.path}", flush=True)
    print(f"Pack layout: {pack_root.layout}", flush=True)

    if pack_root.layout == "legacy":
        run_legacy_full_start(pack_root.path, target, args)
    elif pack_root.layout == "flat":
        run_flat_full_start(pack_root.path, target, args)
    else:
        raise AssertionError(f"Unknown pack layout: {pack_root.layout}")

    local_skills = target / ".rb-agent" / "skills"
    if local_skills.exists():
        raise SystemExit(f"Unexpected project-local skills folder exists: {local_skills}")

    print()
    print(f"Full start complete for {target}")
    destination = default_skills_destination(args.agent)
    if destination.agent == "claude":
        print("Next: open Claude Code in that repository and send /rb-start-project, or continue onboarding now.")
    else:
        print("Next: open Codex in that repository and use $rb-start-project, or continue onboarding now.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
