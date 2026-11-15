"""Run six predeclared scientific faults in disposable copies, preserving evidence."""

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from xml.etree import ElementTree

from tools.run_suite import run_command

ROOT = Path(__file__).resolve().parents[1]
MUTATIONS = {
    "wrong_direction": (
        "previous.a_kg - transfer, previous.b_kg + transfer",
        "previous.a_kg + transfer, previous.b_kg - transfer",
        "Reversed transfer conserves total but violates direction and the solution.",
    ),
    "wrong_receiver": (
        "previous.b_kg + transfer",
        "previous.b_kg - transfer",
        "Both stores lose mass, violating conservation.",
    ),
    "wrong_rate": (
        "transfer = rate * step * previous.a_kg",
        "transfer = 0.5 * rate * step * previous.a_kg",
        "Half the specified rate conserves mass but gives incorrect trajectories.",
    ),
    "wrong_final_step": (
        "step = min(dt, time - previous.time_days)",
        "step = dt",
        "A full final step overshoots when duration is not a multiple of dt.",
    ),
    "wrong_units": (
        "return (self.a_kg + self.b_kg) / 1000",
        "return (self.a_kg + self.b_kg) / 100",
        "A tenfold error in exported tonnes leaves in-memory mass conservation intact.",
    ),
    "missing_stability": (
        "if rate * dt > 1:",
        "if False:",
        "Unstable Euler steps are accepted instead of rejected.",
    ),
}


def replace_once(source, old, new):
    if source.count(old) != 1:
        raise ValueError(f"Mutation anchor must occur once: {old}")
    return source.replace(old, new, 1)


def failure_ids(path):
    """Parse only this bounded local pytest output, rejecting errors as kills."""
    if not path.exists() or path.stat().st_size > 2_000_000:
        return [], -1
    tree = ElementTree.parse(path)
    failed = []
    errors = 0
    for case in tree.iter("testcase"):
        if case.find("failure") is not None:
            failed.append(f"{case.get('classname')}::{case.get('name')}")
        errors += case.find("error") is not None
    return failed, errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    original = (ROOT / "model.py").read_text()
    results = []
    controls = []
    weak = None
    with tempfile.TemporaryDirectory(prefix="rb numerical mutants ") as directory:
        parent = Path(directory)
        for name, (old, new, reason) in MUTATIONS.items():
            workspace = parent / name
            workspace.mkdir()
            (workspace / "model.py").write_text(replace_once(original, old, new))
            shutil.copy(ROOT / "pyproject.toml", workspace)
            shutil.copytree(
                ROOT / "tests",
                workspace / "tests",
                ignore=shutil.ignore_patterns("__pycache__"),
            )
            env = {
                "PATH": os.environ.get("PATH", ""),
                "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
                "PYTHONDONTWRITEBYTECODE": "1",
            }
            commands = {
                "pytest": [
                    "pytest",
                    "tests/test_model.py",
                    "tests/test_independent.py",
                    "-q",
                    f"--basetemp={workspace / 'tmp'}",
                    f"--junitxml={output / (name + '.xml')}",
                ],
                "lint": [
                    "ruff",
                    "check",
                    "--no-fix",
                    "--no-fix-only",
                    "--no-cache",
                    "model.py",
                ],
                "typing": [
                    "mypy",
                    "--strict",
                    "--no-incremental",
                    "--cache-dir",
                    str(workspace / "mypy-cache"),
                    "model.py",
                ],
            }
            row = {"id": name, "expected_fault": reason}
            for tool, command in commands.items():
                row[tool] = run_command(
                    f"{name}-{tool}",
                    [sys.executable, "-m", *command],
                    workspace,
                    output,
                    env,
                    timeout=60,
                )
            failed, errors = failure_ids(output / (name + ".xml"))
            row.update(
                failures=failed,
                collection_errors=errors,
                detected=row["pytest"]["returncode"] == 1
                and bool(failed)
                and errors == 0
                and not row["pytest"]["timed_out"],
            )
            results.append(row)
            if name == "wrong_direction":
                (workspace / "test_weak.py").write_text(
                    "from model import simulate\n"
                    "def test_total_only():\n"
                    "    rows = simulate(1000,1000,.1,1,.1)\n"
                    "    assert all(abs(r.a_kg+r.b_kg-2000)<1e-9 for r in rows)\n"
                )
                weak = run_command(
                    "weak-conservation-control",
                    [
                        sys.executable,
                        "-m",
                        "pytest",
                        "test_weak.py",
                        "-q",
                        f"--basetemp={workspace / 'weak-tmp'}",
                    ],
                    workspace,
                    output,
                    env,
                )
        for name, code, command in [
            (
                "unused-import",
                original + "\nimport statistics\n",
                [
                    "ruff",
                    "check",
                    "--no-fix",
                    "--no-fix-only",
                    "--no-cache",
                    "model.py",
                ],
            ),
            (
                "wrong-return-type",
                replace_once(
                    original,
                    "return (self.a_kg + self.b_kg) / 1000",
                    'return "not a number"',
                ),
                ["mypy", "--strict", "--no-incremental", "model.py"],
            ),
            (
                "bad-formatting",
                replace_once(
                    original,
                    "return (self.a_kg + self.b_kg) / 1000",
                    "return(self.a_kg+self.b_kg)/1000",
                ),
                ["ruff", "format", "--check", "model.py"],
            ),
        ]:
            workspace = parent / name
            workspace.mkdir()
            (workspace / "model.py").write_text(code)
            shutil.copy(ROOT / "pyproject.toml", workspace)
            receipt = run_command(
                name, [sys.executable, "-m", *command], workspace, output, env
            )
            controls.append(
                {
                    "id": name,
                    "detected": receipt["returncode"] == 1 and not receipt["timed_out"],
                    "receipt": receipt,
                }
            )
    result = {
        "format": "fault-injection-v1",
        "baseline_model_sha256": hashlib.sha256(original.encode()).hexdigest(),
        "cases": results,
        "all_detected": all(row["detected"] for row in results),
        "weak_control": weak,
        "tool_controls": controls,
        "limitations": [
            "Six selected non-equivalent faults; not exhaustive mutation coverage.",
            "No matched no-skill agent baseline; cannot estimate skill lift.",
        ],
    }
    (output / "result.json").write_text(json.dumps(result, indent=2))
    print(
        json.dumps(
            {
                "detected": sum(row["detected"] for row in results),
                "total": len(results),
                "tool_controls": controls,
                "weak_control_passed": weak["returncode"] == 0,
            },
            indent=2,
        )
    )
    return (
        0 if result["all_detected"] and all(row["detected"] for row in controls) else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
