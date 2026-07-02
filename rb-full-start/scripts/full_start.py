#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def is_pack_root(path: Path) -> bool:
    return (
        (path / "scripts" / "install_global_skills.py").exists()
        and (path / "scripts" / "install_local_pack.py").exists()
        and (path / "skills").is_dir()
    )


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


def find_pack_root(explicit: str | None, target: Path) -> Path:
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

    for candidate in candidates:
        if is_pack_root(candidate):
            return candidate

    searched = "\n".join(f"- {candidate}" for candidate in candidates[:20])
    extra = "" if len(candidates) <= 20 else f"\n- ...and {len(candidates) - 20} more"
    raise SystemExit(
        "Could not find the RB agent skills pack. Run this command from the pack, "
        "pass --pack-root /path/to/_rb-agent-skills, or set RB_AGENT_SKILLS_PACK.\n"
        f"Searched:\n{searched}{extra}"
    )


def run(cmd: list[str], cwd: Path) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, cwd=str(cwd), check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the full RB Codex project setup.")
    parser.add_argument("--target", default=".", help="Target repository path. Defaults to current directory.")
    parser.add_argument("--pack-root", help="Path to the _rb-agent-skills pack.")
    parser.add_argument("--force", action="store_true", help="Replace existing managed project resources without backups.")
    parser.add_argument("--codex", action="store_true", help="Install CODEX.md into the target repository.")
    parser.add_argument("--claude", action="store_true", help="Install CLAUDE.md into the target repository.")
    parser.add_argument("--cursor", action="store_true", help="Install Cursor rule file into the target repository.")
    args = parser.parse_args()

    target = Path(args.target).expanduser().resolve()
    if not target.exists():
        raise SystemExit(f"Target path does not exist: {target}")
    if not target.is_dir():
        raise SystemExit(f"Target path is not a directory: {target}")

    pack_root = find_pack_root(args.pack_root, target)

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

    local_skills = target / ".rb-agent" / "skills"
    if local_skills.exists():
        raise SystemExit(f"Unexpected project-local skills folder exists: {local_skills}")

    print()
    print(f"Full start complete for {target}")
    print("Next: open Codex in that repository and send /start, or continue with $rb-start-project now.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
