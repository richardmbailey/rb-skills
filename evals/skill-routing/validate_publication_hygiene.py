#!/usr/bin/env python3
"""Fail when local safe-operation control state can enter the public repository."""

from __future__ import annotations

import subprocess
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CONTROL_ROOT = ".rb-safe-operation"
IGNORE_PROBE = f"{CONTROL_ROOT}/pending/nested/publication-probe.json"


def run_git(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *arguments],
        cwd=REPOSITORY_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def main() -> int:
    failures: list[str] = []

    tracked = run_git("ls-files", "--", CONTROL_ROOT)
    if tracked.returncode != 0:
        failures.append(f"could not inspect tracked control state: {tracked.stderr.strip()}")
    elif tracked.stdout.strip():
        paths = ", ".join(tracked.stdout.splitlines())
        failures.append(f"local control state is tracked: {paths}")

    ignored = run_git("check-ignore", "--quiet", "--no-index", IGNORE_PROBE)
    if ignored.returncode != 0:
        failures.append(
            f"{CONTROL_ROOT}/ is not ignored recursively; probe remained visible: {IGNORE_PROBE}"
        )

    visible = run_git("ls-files", "--others", "--exclude-standard", "--", CONTROL_ROOT)
    if visible.returncode != 0:
        failures.append(f"could not inspect untracked control state: {visible.stderr.strip()}")
    elif visible.stdout.strip():
        paths = ", ".join(visible.stdout.splitlines())
        failures.append(f"local control state remains visible to Git: {paths}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1

    print("PASS: local .rb-safe-operation control state is recursively ignored and untracked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
