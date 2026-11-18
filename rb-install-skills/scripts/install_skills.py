#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
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
    return Path.home() / ".agents" / "skills"


def legacy_codex_skills_dest() -> Path:
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

    if os.environ.get("CODEX_HOME") or (Path.home() / ".codex").exists():
        return SkillsDestination(codex_skills_dest(), "codex")

    if looks_like_claude_code():
        return SkillsDestination(claude_skills_dest(), "claude")

    return SkillsDestination(codex_skills_dest(), "codex")


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
    return path.name == "skills" and path.parent.name in {".agents", ".codex", ".claude"}


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
        return [codex_skills_dest(), legacy_codex_skills_dest()]
    if agent == "claude":
        return [claude_skills_dest()]
    return [codex_skills_dest(), legacy_codex_skills_dest(), claude_skills_dest()]


def add_global_skill_link_candidates(candidates: list[Path], agent: str = "auto") -> None:
    for skills_dir in agent_skill_dirs(agent):
        if not skills_dir.exists():
            continue
        try:
            children = list(skills_dir.iterdir())
        except OSError:
            continue
        for child in children:
            if agent == "claude" and child.is_dir() and not child.is_symlink():
                try:
                    marker = json.loads((child / ".rb-claude-install.json").read_text(encoding="utf-8"))
                    source = marker.get("source") if isinstance(marker, dict) else None
                    if isinstance(source, str) and Path(source).is_absolute():
                        add_candidate(candidates, Path(source))
                except (OSError, ValueError):
                    pass
            if not child.is_symlink():
                continue
            try:
                target = child.resolve()
            except (OSError, RuntimeError):
                continue
            if (target / "SKILL.md").is_file():
                add_candidate(candidates, target.parent)


def find_pack_root(explicit: str | None, target: Path, agent: str = "auto") -> PackRoot:
    candidates: list[Path] = []
    if explicit:
        path = Path(explicit).expanduser().resolve()
        pack = detect_pack_root(path)
        if pack is None:
            raise SystemExit(f"No supported RB skills pack at --pack-root {path}")
        return pack

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


def install_flat_project_resources(target: Path, force: bool, claude: bool, cursor: bool) -> list[str]:
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

    if claude:
        claude_instructions = """@AGENTS.md

# Claude Code host guidance

- Use the generated Claude editions of the RB skills and `/rb-name` invocations.
- Use standard execution; the constrained runtime and Codex token reporter remain Codex-only.
- For subagents, use the Claude rb-delegate procedure. Ask the user which model to use unless an applicable user choice already exists; reuse it within that task. Do not apply Codex model defaults.
- Preserve required independent review and behavioural testing gates.
- Share the existing canonical RB diary; do not create a second history or change CODEX_HOME to a Claude directory.
"""
        results.append(write_project_file(target / "CLAUDE.md", claude_instructions, force))
    if cursor:
        cursor_rule = """---
description: RB agent workflow guidance
alwaysApply: true
---

Use the installed RB agent skills for matching workflows. Start normal onboarding with `$rb-start-project` in Codex or `/rb-start-project` in Claude Code, and read `CONTEXT.md` before domain-sensitive changes.
"""
        results.append(write_project_file(target / ".cursor" / "rules" / "rb-workflow.mdc", cursor_rule, force))

    return results


def established_codex_directory(pack_root: Path, default: Path) -> Path:
    legacy = legacy_codex_skills_dest()
    if not legacy.is_dir() or (default.is_dir() and default.samefile(legacy)):
        return default

    names = discover_flat_skills(pack_root)
    occupied = []
    linked = []
    for directory in (default, legacy):
        entries = [directory / name for name in names if os.path.lexists(directory / name)]
        if entries:
            occupied.append(directory)
        for entry in entries:
            try:
                if entry.is_symlink() and entry.samefile(pack_root / entry.name):
                    linked.append(directory)
                    break
            except OSError:
                continue  # Broken links still count as occupied entries.

    candidates = linked or occupied
    if len(candidates) > 1:
        raise SystemExit(f"Both {default} and {legacy} contain RB skills. Select one with --dest.")
    return candidates[0] if candidates else default


def flat_destination(pack_root: Path, agent: str, dest: Path | None) -> SkillsDestination:
    default = default_skills_destination(agent)
    path = dest if dest is not None else default.path
    if dest is None and default.agent == "codex":
        path = established_codex_directory(pack_root, default.path)
    # Preserve the original path so the Claude installer can inspect its final component.
    path = path.expanduser().absolute()
    try:
        resolved = path.resolve()
    except (OSError, RuntimeError) as error:
        raise SystemExit(f"Cannot resolve skills destination {path}: {error}") from None
    if resolved.is_relative_to(pack_root) or pack_root.is_relative_to(resolved):
        raise SystemExit(f"Source and destination must not overlap: {pack_root}, {path}")
    return SkillsDestination(path, default.agent)


def readable_file_gap(path: Path) -> str | None:
    try:
        if path.is_file():
            with path.open("rb") as stream:
                stream.read(1)
            return None
    except OSError as error:
        return f"Cannot read {path}: {error}"
    return f"Missing or invalid file: {path}"


def audit_flat_visibility(pack_root: Path, destination: SkillsDestination) -> None:
    if destination.agent == "claude":
        run([sys.executable, "-B", str(pack_root / "platforms/claude/install.py"),
             str(pack_root), "--dest", str(destination.path), "--check"], pack_root)
        return
    skills = discover_flat_skills(pack_root)
    gaps = []
    for skill in skills:
        source_path = (pack_root / skill).resolve()
        path = destination.path / skill
        if not path.is_symlink():
            if path.exists():
                gaps.append(f"{path} exists but is not a symlink to {source_path}")
            else:
                gaps.append(f"Missing link: {path} -> {source_path}")
            continue
        try:
            actual = path.resolve(strict=True)
        except (OSError, RuntimeError) as error:
            gaps.append(f"Broken link {path}: {error}")
            continue
        if actual != source_path:
            gaps.append(f"{path} links to {actual} instead of {source_path}")
            continue
        gap = readable_file_gap(path / "SKILL.md")
        if gap:
            gaps.append(gap)
    if gaps:
        raise SystemExit("\n".join(gaps))
    print(f"Visibility check: {len(skills)} skills link to {pack_root} under {destination.path}")


def check_flat_setup(pack_root: Path, target: Path, args: argparse.Namespace) -> int:
    destination = flat_destination(pack_root, args.agent, args.dest)
    gaps = []
    try:
        audit_flat_visibility(pack_root, destination)
    except SystemExit as error:
        gaps.append(str(error))
    except subprocess.CalledProcessError:
        gaps.append(f"Claude visibility check failed under {destination.path}. Review the finding above.")
    resources = [target / "AGENTS.md", target / "CONTEXT.md"]
    if args.claude or destination.agent == "claude":
        resources.append(target / "CLAUDE.md")
    if args.cursor:
        resources.append(target / ".cursor/rules/rb-workflow.mdc")
    for path in resources:
        gap = readable_file_gap(path)
        if gap:
            gaps.append(gap)
        else:
            print(f"Readable project resource: {path}")
    local = target / ".rb-agent/skills"
    if os.path.lexists(local):
        gaps.append(f"Unexpected project-local skills: {local}")
    if gaps:
        print("\n".join(gaps), file=sys.stderr)
        return 1
    print(f"RB skills check passed for {target}")
    return 0


def run_legacy_install_skills(pack_root: Path, target: Path, args: argparse.Namespace) -> None:
    install_global = [sys.executable, "scripts/install_global_skills.py"]
    install_local = [sys.executable, "scripts/install_local_pack.py", "--target", str(target)]
    if args.force:
        install_local.append("--force")
    if args.claude:
        install_local.append("--claude")
    if args.cursor:
        install_local.append("--cursor")

    run(install_global, pack_root)
    run(install_local, pack_root)
    run([sys.executable, "scripts/audit_skill_visibility.py"], pack_root)


def run_flat_install_skills(pack_root: Path, target: Path, args: argparse.Namespace) -> None:
    sync_script = pack_root / "rb-sync-skills-repo" / "scripts" / "sync_skills_repo.py"
    destination = flat_destination(pack_root, args.agent, getattr(args, "dest", None))
    sync_cmd = [sys.executable, str(sync_script), str(pack_root), "--mode", "symlink",
                "--agent", destination.agent, "--dest", str(destination.path)]
    if args.replace_skills:
        sync_cmd.append("--replace")

    run(sync_cmd, pack_root)
    audit_flat_visibility(pack_root, destination)

    print("Project resources:")
    for result in install_flat_project_resources(
        target, args.force, args.claude or destination.agent == "claude", args.cursor
    ):
        print(f"- {result}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Install RB skills and project setup resources.")
    parser.add_argument("--target", default=".", help="Target repository path. Defaults to current directory.")
    parser.add_argument("--pack-root", help="Path to the rb-skills repo or legacy _rb-agent-skills pack.")
    parser.add_argument(
        "--agent",
        choices=("auto", "codex", "claude"),
        default="auto",
        help="Destination agent for global skill install. Auto tries Codex first, then Claude Code.",
    )
    parser.add_argument("--dest", type=Path, help="Skills directory for flat-pack installation or verification.")
    parser.add_argument("--check", action="store_true", help="Verify the flat-pack setup without writing files.")
    parser.add_argument("--force", action="store_true", help="Replace existing managed project resources without backups.")
    parser.add_argument(
        "--replace-skills",
        action="store_true",
        help="Back up and replace existing global skill folders during flat-pack sync.",
    )
    parser.add_argument("--claude", action="store_true", help="Install CLAUDE.md into the target repository.")
    parser.add_argument("--cursor", action="store_true", help="Install Cursor rule file into the target repository.")
    args = parser.parse_args()

    if args.check and (args.force or args.replace_skills):
        parser.error("--check cannot be combined with --force or --replace-skills")

    target = Path(args.target).expanduser().resolve()
    if not target.exists():
        raise SystemExit(f"Target path does not exist: {target}")
    if not target.is_dir():
        raise SystemExit(f"Target path is not a directory: {target}")

    pack_root = find_pack_root(args.pack_root, target, args.agent)
    print(f"Pack root: {pack_root.path}", flush=True)
    print(f"Pack layout: {pack_root.layout}", flush=True)

    if pack_root.layout == "legacy":
        if args.check:
            raise SystemExit("Read-only verification is unsupported for legacy packs. Inspect the legacy installation manually.")
        if args.dest is not None:
            raise SystemExit("Legacy pack helpers do not support --dest.")
        run_legacy_install_skills(pack_root.path, target, args)
    elif pack_root.layout == "flat":
        if args.check:
            try:
                return check_flat_setup(pack_root.path, target, args)
            except (OSError, RuntimeError) as error:
                raise SystemExit(f"Could not verify setup: {error}") from None
        run_flat_install_skills(pack_root.path, target, args)
    else:
        raise AssertionError(f"Unknown pack layout: {pack_root.layout}")

    local_skills = target / ".rb-agent" / "skills"
    if os.path.lexists(local_skills):
        raise SystemExit(f"Unexpected project-local skills folder exists: {local_skills}")

    print()
    print(f"RB skills setup complete for {target}")
    destination = default_skills_destination(args.agent)
    if destination.agent == "claude":
        print("Next: open Claude Code in that repository and send /rb-start-project, or continue onboarding now.")
    else:
        print("Next: open Codex in that repository and use $rb-start-project, or continue onboarding now.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
