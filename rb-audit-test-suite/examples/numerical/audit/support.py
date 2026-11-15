"""Narrow adapter: disposable copies and exact native JUnit assertion evidence."""
import os
import shutil
import subprocess
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
FAULTS = {
    "wrong_direction": (
        "previous.a_kg - transfer, previous.b_kg + transfer",
        "previous.a_kg + transfer, previous.b_kg - transfer", "test_direction"),
    "wrong_receiver": (
        "previous.b_kg + transfer", "previous.b_kg - transfer", "test_conservation"),
    "wrong_rate": (
        "transfer = rate * step * previous.a_kg",
        "transfer = 0.5 * rate * step * previous.a_kg", "test_specified_rate"),
    "wrong_final_step": (
        "step = min(dt, time - previous.time_days)", "step = dt",
        "test_fractional_endpoint"),
    "wrong_units": (
        "return (self.a_kg + self.b_kg) / 1000",
        "return (self.a_kg + self.b_kg) / 100", "test_exported_units"),
    "missing_stability": (
        "if rate * dt > 1:", "if False:", "test_stability_rejected"),
    "rounded_step": (
        "step = min(dt, time - previous.time_days)",
        "step = time - previous.time_days", "test_rounded_step_nonnegative"),
    "quotient_underflow": (
        "count = 0 if duration == 0 else max(1, math.ceil(steps))",
        "count = math.ceil(steps)", "test_underflow_final_time"),
}
EXPECTED = {f"test_model::{case[2]}" for case in FAULTS.values()}


class AuditError(AssertionError):
    """Invalid evidence or a suite that does not expose the intended fault."""


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise AuditError(f"Mutation anchor does not occur exactly once: {old}")
    return text.replace(old, new, 1)


def make_project(path, weak=False):
    shutil.copytree(ROOT / "project", path, ignore=shutil.ignore_patterns("__pycache__"))
    (path / "pytest.ini").write_text("[pytest]\n")
    if weak:
        tests = (path / "test_model.py").read_text()
        tests = replace_once(tests,
            "assert all(r.a_kg >= 0 and r.b_kg >= 0 for r in rows)",
            "assert len(rows) >= 1")
        tests = replace_once(tests,
            "assert len(rows) == 2\n    assert rows[-1].time_days == 1e-308\n"
            "    assert (rows[-1].a_kg, rows[-1].b_kg) == (1, 0)",
            "assert len(rows) >= 1")
        (path / "test_model.py").write_text(tests)


def run_suite(project, evidence, timeout=15):
    """Preserve raw child stdout, exit and XML, including timeout output."""
    evidence.mkdir(parents=True, exist_ok=False)
    command = [sys.executable, "-m", "pytest", "test_model.py", "-q",
               "-c", str(project / "pytest.ini"), "--confcutdir", str(project),
               "--basetemp", str(evidence / "tmp"),
               "--junitxml", str(evidence / "junit.xml")]
    env = dict(os.environ)
    for key in ("PYTHONPATH", "PYTEST_ADDOPTS", "PYTEST_PLUGINS"):
        env.pop(key, None)
    # This standalone example needs pytest only; real projects retain their plugins.
    env.update(PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", PYTHONDONTWRITEBYTECODE="1")
    (evidence / "command.txt").write_text(repr(command) + "\ncwd=" + str(project))
    try:
        result = subprocess.run(command, cwd=project, env=env, capture_output=True,
                                text=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired as exc:
        output = (exc.stdout or b"") + (exc.stderr or b"")
        (evidence / "output.log").write_bytes(output)
        (evidence / "exit.txt").write_text("timeout\n")
        raise AuditError("timeout is not a detected fault") from exc
    (evidence / "output.log").write_text(result.stdout + result.stderr)
    (evidence / "exit.txt").write_text(str(result.returncode) + "\n")
    return result.returncode, evidence / "junit.xml"


def inspect_result(result, expected, target=None):
    """A kill needs the intended assertion, never an error or missing test."""
    exit_code, xml = result
    try:
        root = ET.parse(xml).getroot()
    except (OSError, ET.ParseError) as exc:
        raise AuditError("missing or malformed JUnit") from exc
    cases = list(root.iter("testcase"))
    identities = [f"{c.get('classname')}::{c.get('name')}" for c in cases]
    if not cases or len(identities) != len(set(identities)) or set(identities) != expected:
        raise AuditError(f"missing, duplicate or unexpected tests: {identities}")
    if list(root.iter("error")) or list(root.iter("skipped")):
        raise AuditError("error or skipped test is not a detected fault")
    failures = {identity: c.find("failure") for identity, c in zip(identities, cases)
                if c.find("failure") is not None}
    if target is None:
        if exit_code != 0 or failures:
            raise AuditError("healthy control did not pass")
    elif exit_code != 1 or target not in failures:
        raise AuditError(f"intended assertion did not fail: {target}")
    elif any(not failure.get("message", "").startswith(("assert ", "AssertionError"))
             for failure in failures.values()):
        raise AuditError("intended test failed without assertion evidence")


def audit_fault(work, evidence, name, weak=False):
    healthy, faulty = work / "healthy", work / "faulty"
    make_project(healthy, weak)
    shutil.copytree(healthy, faulty)
    old, new, test_name = FAULTS[name]
    source = (faulty / "model.py").read_text()
    (faulty / "model.py").write_text(replace_once(source, old, new))
    inspect_result(run_suite(healthy, evidence / "healthy"), EXPECTED)
    inspect_result(run_suite(faulty, evidence / "faulty"), EXPECTED,
                   f"test_model::{test_name}")
