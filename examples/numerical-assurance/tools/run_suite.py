"""Bounded, project-local trial runner; not a normalized skill-schema runner."""

from __future__ import annotations

import argparse
import hashlib
import html
import importlib.metadata
import json
import os
import platform
import selectors
import signal
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {
    "artifacts",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".hypothesis",
}


def manifest(root: Path) -> dict[str, str]:
    """Freeze authored inputs, including newly added source or configuration."""
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
        and not (set(path.relative_to(root).parts) & EXCLUDED)
        and not path.name.startswith(".coverage")
    }


def run_command(
    name: str,
    argv: list[str],
    root: Path,
    output: Path,
    env: dict[str, str],
    timeout: float = 120,
    max_output_bytes: int = 2_000_000,
) -> dict:
    start = time.monotonic()
    started_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    timed_out = False
    output_limit_exceeded = False
    error = None
    with (output / f"{name}.log").open("wb") as log:
        try:
            process = subprocess.Popen(
                argv,
                cwd=root,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            assert process.stdout is not None
            size = 0
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ)
                while selector.get_map():
                    if time.monotonic() - start >= timeout:
                        timed_out = True
                        break
                    for key, _ in selector.select(timeout=0.05):
                        chunk = os.read(key.fd, 65536)
                        if not chunk:
                            selector.unregister(key.fileobj)
                            continue
                        remaining = max_output_bytes - size
                        log.write(chunk[:remaining])
                        size += min(len(chunk), remaining)
                        if len(chunk) > remaining:
                            output_limit_exceeded = True
                            break
                    if output_limit_exceeded:
                        break
            if timed_out or output_limit_exceeded:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            try:
                returncode = process.wait(
                    timeout=max(0.01, timeout - (time.monotonic() - start))
                )
            except subprocess.TimeoutExpired:
                timed_out = True
                os.killpg(process.pid, signal.SIGKILL)
                returncode = process.wait()
            process.stdout.close()
        except OSError as exc:
            error = str(exc)
            log.write(error.encode())
            returncode = None
    return {
        "name": name,
        "started_at": started_at,
        "finished_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "argv": argv,
        "cwd": ".",
        "returncode": returncode,
        "timed_out": timed_out,
        "output_limit_exceeded": output_limit_exceeded,
        "max_output_bytes": max_output_bytes,
        "duration_seconds": time.monotonic() - start,
        "timeout_seconds": timeout,
        "log": f"{name}.log",
        "error": error,
    }


def pytest_issues(
    expected: list[str],
    captured: dict,
    expected_hash: str,
    expected_origin: str = "model.py",
) -> list[str]:
    issues = []
    ids = captured.get("collected_ids", [])
    if not expected or len(expected) != len(set(expected)) or ids != expected:
        issues.append("Empty, duplicate or changed pytest collection")
    if (
        captured.get("model_origin") != expected_origin
        or captured.get("model_sha256") != expected_hash
    ):
        issues.append("Model import identity missing or mismatched")
    phases = captured.get("phases", [])
    for nodeid in expected:
        rows = [row for row in phases if row.get("nodeid") == nodeid]
        if sorted(row.get("when", "") for row in rows) != [
            "call",
            "setup",
            "teardown",
        ] or any(row.get("outcome") != "passed" or row.get("wasxfail") for row in rows):
            issues.append(f"Incomplete or unsuccessful required test: {nodeid}")
    if any(row.get("nodeid") not in expected for row in phases):
        issues.append("Unexpected executed test ID")
    return issues


def render_report(receipt: dict) -> str:
    payload = html.escape(json.dumps(receipt, indent=2), quote=True)
    status = "Checks passed" if receipt["passed"] else "Checks incomplete or failed"
    return (
        "<!doctype html><html lang='en'><meta charset='utf-8'>"
        "<title>Numerical assurance trial</title><body>"
        f"<h1>{status}</h1><p>Custom raw trial receipts. This is not the full "
        "skill evidence schema or assurance gate. "
        "No empirical validation is claimed.</p>"
        f"<pre>{payload}</pre></body></html>"
    )


def read_capture(path: Path) -> dict:
    try:
        value = json.loads(path.read_text())
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    output = (args.output or ROOT / "artifacts" / "runs" / uuid.uuid4().hex).resolve()
    # Outputs inside source must use the excluded artifacts tree.
    if output.is_relative_to(ROOT) and not output.is_relative_to(ROOT / "artifacts"):
        parser.error("In-project outputs must be beneath artifacts/")
    output.mkdir(parents=True, exist_ok=False)
    started_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    before = manifest(ROOT)
    (output / "before-manifest.json").write_text(json.dumps(before, indent=2))
    env = {
        key: value
        for key, value in os.environ.items()
        if key in {"PATH", "HOME", "TMPDIR", "LANG", "LC_ALL", "SYSTEMROOT"}
    }
    env.update(
        {
            "COVERAGE_FILE": str(output / ".coverage"),
            "RB_TRIAL_CAPTURE": str(output / "collection.json"),
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        }
    )
    commands = []

    def execute(name: str, argv: list[str]) -> None:
        commands.append(
            run_command(name, [sys.executable, "-m", *argv], ROOT, output, env)
        )

    execute(
        "collect",
        ["pytest", "--collect-only", "-q", f"--basetemp={output / 'collect-tmp'}"],
    )
    expected = read_capture(output / "collection.json").get("collected_ids", [])
    (output / "expected-test-ids.json").write_text(json.dumps(expected, indent=2))
    env["RB_TRIAL_CAPTURE"] = str(output / "pytest.json")
    execute(
        "pytest",
        [
            "coverage",
            "run",
            "--branch",
            "--source=model",
            "-m",
            "pytest",
            "-q",
            f"--junitxml={output / 'junit.xml'}",
            f"--basetemp={output / 'pytest-tmp'}",
        ],
    )
    execute("coverage", ["coverage", "json", "-o", str(output / "coverage.json")])
    execute(
        "ruff",
        ["ruff", "check", "--no-fix", "--no-fix-only", "--output-format=json", "."],
    )
    execute("format", ["ruff", "format", "--check", "."])
    execute("mypy", ["mypy", "--strict", "model.py"])
    execute("ruff-files", ["ruff", "check", "--show-files", "."])
    execute("ruff-settings", ["ruff", "check", "--show-settings", "model.py"])
    after = manifest(ROOT)
    captured = read_capture(output / "pytest.json")
    issues = pytest_issues(expected, captured, before.get("model.py", ""))
    if before != after:
        issues.append("Source or control input changed during checks")
    issues.extend(
        f"Command unsuccessful: {row['name']}"
        for row in commands
        if row["returncode"] != 0 or row["timed_out"] or row["output_limit_exceeded"]
    )
    versions = {}
    for tool in ("pytest", "coverage", "hypothesis", "ruff", "mypy"):
        try:
            versions[tool] = importlib.metadata.version(tool)
        except importlib.metadata.PackageNotFoundError:
            versions[tool] = "missing"
    receipt = {
        "format": "trial-raw-v1",
        "started_at": started_at,
        "finished_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "passed": not issues,
        "issues": issues,
        "before_manifest": before,
        "after_manifest": after,
        "commands": commands,
        "tool_versions": versions,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "pytest": captured,
        "expected_test_ids": expected,
        "limitations": [
            "No full skill-schema conformance or protected gate",
            "Local process execution, no runner-enforced network sandbox",
            "No mutation or independent-review aggregation in this runner",
        ],
    }
    (output / "receipts.json").write_text(json.dumps(receipt, indent=2))
    (output / "report.html").write_text(render_report(receipt))
    print(f"{'PASS' if not issues else 'FAIL'}: {output}")
    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
