"""Six predeclared scientific faults in disposable, bounded standalone copies."""

import json
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FAULTS = {
    "direction": (
        "a, b = a - transfer, b + transfer",
        "a, b = a + transfer, b - transfer",
        "test_exact_steps",
    ),
    "receiver": (
        "a, b = a - transfer, b + transfer",
        "a, b = a - transfer, b",
        "test_exact_steps",
    ),
    "rate": ("a * (rate * step)", "a * (0.5 * rate * step)", "test_exact_steps"),
    "final_step": (
        "step = min(dt, float(span - (count - 1) * stride)) if last else dt",
        "step = dt",
        "test_exact_steps",
    ),
    "tonnes": ("/ 1000", "/ 100", "test_exact_steps"),
    "stability": ("if rate * dt > 1:", "if False:", "test_invalid_combinations[args1]"),
}


def main():
    out = (
        ROOT
        / "evidence"
        / ("mutants-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ"))
    )
    out.mkdir()
    results = {}
    source = (ROOT / "model.py").read_text()
    for name in ["healthy", *FAULTS]:
        target = out / name
        (target / "tests").mkdir(parents=True)
        text = source
        selector = "test_exact_steps"
        if name in FAULTS:
            old, new, selector = FAULTS[name]
            assert source.count(old) == 1, (name, old)
            text = source.replace(old, new)
        (target / "model.py").write_text(text)
        shutil.copy(ROOT / "tests/test_model.py", target / "tests/test_model.py")
        shutil.copy(ROOT / "pyproject.toml", target / "pyproject.toml")
        command = [
            sys.executable,
            "-m",
            "pytest",
            "-c",
            str(target / "pyproject.toml"),
            "--confcutdir",
            str(target),
            "--basetemp",
            str(target / "temp"),
            f"--junitxml={target / 'junit.xml'}",
            f"tests/test_model.py::{selector}",
        ]
        run = subprocess.run(
            command, cwd=target, check=False, capture_output=True, timeout=30
        )
        (target / "pytest.log").write_bytes(run.stdout + run.stderr)
        cases = ET.parse(target / "junit.xml").findall(".//testcase")
        failures = [case.find("failure") for case in cases]
        # A behavioural assertion and pytest exit 1 distinguish a kill from broken collection.
        detected = run.returncode == 1 and any(
            node is not None
            and (
                "assert" in (node.text or "").lower()
                or "DID NOT RAISE" in (node.text or "")
            )
            for node in failures
        )
        results[name] = {
            "command": command,
            "exit": run.returncode,
            "detected": detected,
            "cases": len(cases),
        }
    (out / "results.json").write_text(json.dumps(results, indent=2))
    print(out)
    return int(
        not (
            results["healthy"]["exit"] == 0
            and all(results[name]["detected"] for name in FAULTS)
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
