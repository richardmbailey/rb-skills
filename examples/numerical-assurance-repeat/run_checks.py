"""Small local command recorder; native tools retain responsibility for checks."""

import hashlib
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def capture(command, directory, name, env=None):
    """Keep command failures, unavailable tools and partial timeout output visible."""
    try:
        result = subprocess.run(
            command, cwd=ROOT, env=env, check=False, capture_output=True, timeout=120
        )
        code, stdout, stderr = result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired as exc:
        code, stdout, stderr = 124, exc.stdout or b"", exc.stderr or b""
    except OSError as exc:
        code, stdout, stderr = 127, b"", str(exc).encode()
    (directory / f"{name}.log").write_bytes(stdout + b"\nSTDERR\n" + stderr)
    return {"command": command, "exit": code}


def manifest():
    return {
        str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(ROOT.rglob("*"))
        if p.is_file()
        and (
            p.suffix in {".py", ".toml"}
            or p.name in {"REQUIREMENTS.md", "expected-tests.json"}
        )
        and "evidence" not in p.relative_to(ROOT).parts
        and not any(part.startswith(".") for part in p.relative_to(ROOT).parts)
    }


def main():
    directory = ROOT / "evidence" / datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    directory.mkdir(parents=True)
    before = manifest()
    (directory / "candidate-before.json").write_text(json.dumps(before, indent=2))
    python = sys.executable
    env = dict(
        os.environ,
        IDENTITY_OUTPUT=str(directory / "identities.json"),
        COVERAGE_FILE=str(directory / ".coverage"),
    )
    commands = [
        ("environment", [python, "-m", "pip", "freeze"]),
        (
            "tests",
            [
                python,
                "-m",
                "coverage",
                "run",
                "-m",
                "pytest",
                "-c",
                str(ROOT / "pyproject.toml"),
                "--confcutdir",
                str(ROOT),
                f"--junitxml={directory / 'junit.xml'}",
                f"--basetemp={directory / 'pytest-temp'}",
            ],
        ),
        (
            "coverage",
            [python, "-m", "coverage", "json", "-o", str(directory / "coverage.json")],
        ),
        ("coverage-text", [python, "-m", "coverage", "report", "-m"]),
        ("lint", [python, "-m", "ruff", "check", "--no-fix", "--no-fix-only", "."]),
        ("format", [python, "-m", "ruff", "format", "--check", "."]),
        ("types", [python, "-m", "mypy", "model.py"]),
        (
            "ruff-settings",
            [python, "-m", "ruff", "check", "--show-settings", "model.py"],
        ),
        ("ruff-files", [python, "-m", "ruff", "check", "--show-files", "."]),
    ]
    results = {
        name: capture(command, directory, name, env) for name, command in commands
    }
    after = manifest()
    (directory / "candidate-after.json").write_text(json.dumps(after, indent=2))
    results["unchanged"] = before == after
    identity_path = directory / "identities.json"
    if identity_path.exists():
        identity = json.loads(identity_path.read_text())
        ids = identity["selected"]
        expected = json.loads((ROOT / "expected-tests.json").read_text())
        outcomes = identity["outcomes"]
        results["identity_valid"] = (
            bool(ids)
            and sorted(ids) == sorted(expected)
            and len(ids) == len(set(ids))
            and (sorted(ids) == sorted(x["id"] for x in outcomes))
            and all(x["outcome"] == "passed" and x["phase"] == "call" for x in outcomes)
            and (identity["model_origin"] == str(ROOT / "model.py"))
            and (identity["model_sha256"] == before["model.py"])
        )
    else:
        results["identity_valid"] = False
    (directory / "results.json").write_text(json.dumps(results, indent=2))
    print(directory)
    return int(
        not (
            results["unchanged"]
            and results["identity_valid"]
            and all(results[name]["exit"] == 0 for name, _ in commands)
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
