"""Bounded fault experiments with retained native evidence."""

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SUPPORT = REPO / "rb-audit-test-suite/examples/numerical/audit/support.py"
spec = importlib.util.spec_from_file_location("existing_audit_support", SUPPORT)
assert spec and spec.loader
support = importlib.util.module_from_spec(spec)
spec.loader.exec_module(support)
(HERE / "evidence/audit").mkdir(parents=True, exist_ok=True)
EVIDENCE = Path(tempfile.mkdtemp(prefix="attempt-", dir=HERE / "evidence/audit"))
print(f"AUDIT_EVIDENCE={EVIDENCE}")

# IDs are pytest node IDs; native JUnit removes the .py suffix.
FAULTS = {
    "sequential_update": (
        (
            "        temperatures = tuple(\n"
            "            temperatures[i]\n"
            "            + r\n"
            "            * (\n"
            "                temperatures[(i - 1) % n]\n"
            "                - 2 * temperatures[i]\n"
            "                + temperatures[(i + 1) % n]\n"
            "            )\n"
            "            for i in range(n)\n"
            "        )"
        ),
        (
            "        changed = list(temperatures)\n"
            "        for i in range(n):\n"
            "            changed[i] += r * (changed[(i-1)%n] - 2*changed[i]"
            " + changed[(i+1)%n])\n"
            "        temperatures = tuple(changed)"
        ),
        "test_hand_worked_periodic_simultaneous_step",
        "assert",
    ),
    "last_step": (
        "range(steps)",
        "range(max(0, steps - 1))",
        "test_hand_worked_periodic_simultaneous_step",
        "assert",
    ),
    "wrong_speed": (
        "+ r\n",
        "+ 0.5 * r\n",
        "test_discrete_fourier[37-0.2-7]",
        "assert",
    ),
    "wrong_sign": (
        "+ r\n",
        "- r\n",
        "test_hand_worked_periodic_simultaneous_step",
        "assert",
    ),
    "missing_wrap": (
        "temperatures[(i - 1) % n]",
        "temperatures[max(i - 1, 0)]",
        "test_hand_worked_periodic_simultaneous_step",
        "assert",
    ),
    "stability_omitted": (
        "if r > 0.5:",
        "if False:",
        "test_stability_rejected[0]",
        "raises",
    ),
    "nan_accepted": (
        "if not math.isfinite(number) or not lower <= number <= upper:",
        "if number < lower or number > upper:",
        "test_invalid_scalar[diffusivity_m2_s-nan]",
        "raises",
    ),
    "csv_spatial_units": (
        "i * solution.dx_m, solution.time_s",
        "1000 * i * solution.dx_m, solution.time_s",
        "test_csv_roundtrip",
        "assert",
    ),
    "csv_time": (
        "i * solution.dx_m, solution.time_s",
        "i * solution.dx_m, 0",
        "test_csv_roundtrip",
        "assert",
    ),
    "cli_suppresses_error": (
        "    write_csv(solution, args.output)",
        (
            "    try:\n"
            "        write_csv(solution, args.output)\n"
            "    except OSError:\n"
            "        pass"
        ),
        "test_cli_roundtrip_and_failure",
        "assert",
    ),
}


def execute(argv, cwd, folder, timeout=20):
    folder.mkdir(parents=True, exist_ok=False)
    (folder / "command.json").write_text(
        json.dumps({"argv": argv, "cwd": str(cwd), "timeout": timeout}, indent=2)
    )
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    for key in ("PYTHONPATH", "PYTEST_ADDOPTS", "PYTEST_PLUGINS"):
        env.pop(key, None)
    try:
        result = subprocess.run(
            argv, cwd=cwd, env=env, capture_output=True, timeout=timeout
        )
    except subprocess.TimeoutExpired as exc:
        (folder / "stdout.log").write_bytes(exc.stdout or b"")
        (folder / "stderr.log").write_bytes(exc.stderr or b"")
        (folder / "exit.txt").write_text("timeout")
        pytest.fail("timeout is not a detected mutation")
    (folder / "stdout.log").write_bytes(result.stdout)
    (folder / "stderr.log").write_bytes(result.stderr)
    (folder / "exit.txt").write_text(str(result.returncode))
    return result


def run_project(project, folder, target):
    command = [
        sys.executable,
        "-m",
        "pytest",
        f"test_heat.py::{target}",
        "test_heat.py::test_import_origin",
        "-q",
        "-s",
        "-c",
        str(project / "pytest.ini"),
        "--confcutdir",
        str(project),
        "--basetemp",
        str(folder / "tmp"),
        "--junitxml",
        str(folder / "junit.xml"),
    ]
    result = execute(command, project, folder)
    return result.returncode, folder / "junit.xml"


def inspect_missing_value_error(result, expected, target):
    # pytest.raises emits native Failed, not AssertionError. Validate this
    # additional substantive failure type without accepting arbitrary exits.
    code, xml = result
    root = ET.parse(xml).getroot()
    cases = list(root.iter("testcase"))
    assert {f"{c.get('classname')}::{c.get('name')}" for c in cases} == expected
    assert len(cases) == 2
    assert not list(root.iter("error")) and not list(root.iter("skipped"))
    failures = [
        (c.get("name"), c.find("failure"))
        for c in cases
        if c.find("failure") is not None
    ]
    assert code == 1 and len(failures) == 1
    name, failure = failures[0]
    assert name == target and failure is not None
    assert failure.get("message") == "Failed: DID NOT RAISE ValueError"


@pytest.mark.parametrize("fault", list(FAULTS))
def test_fault_detected(fault):
    folder = EVIDENCE / fault
    folder.mkdir()
    healthy, faulty = folder / "healthy", folder / "faulty"
    healthy.mkdir()
    for name in ("heat.py", "test_heat.py", "pytest.ini", "pyproject.toml"):
        shutil.copy2(HERE / name, healthy / name)
    shutil.copytree(healthy, faulty)
    old, new, target, failure_kind = FAULTS[fault]
    (faulty / "heat.py").write_text(
        support.replace_once((faulty / "heat.py").read_text(), old, new)
    )
    expected = {f"test_heat::{target}", "test_heat::test_import_origin"}
    support.inspect_result(
        run_project(healthy, folder / "healthy-result", target), expected
    )
    result = run_project(faulty, folder / "faulty-result", target)
    if failure_kind == "assert":
        support.inspect_result(result, expected, f"test_heat::{target}")
    else:
        inspect_missing_value_error(result, expected, target)


@pytest.mark.parametrize(
    "scenario",
    [
        "healthy",
        "early_failure",
        "lint_failure",
        "type_failure",
        "missing_tool",
        "timeout",
    ],
)
def test_coordinator_propagation(scenario):
    folder = EVIDENCE / f"coordinator-{scenario}"
    folder.mkdir()
    project = folder / "project"
    project.mkdir()
    (project / "candidate.txt").write_text("healthy fixture\n")
    (project / "requirements.txt").write_text("Every declared command must pass.\n")
    argv = [sys.executable, "-c", "print('healthy')"]
    if scenario in {"early_failure", "lint_failure", "type_failure"}:
        argv = [sys.executable, "-c", "raise SystemExit(7)"]
    elif scenario == "missing_tool":
        argv = [str(project / "unavailable-required-tool")]
    elif scenario == "timeout":
        argv = [
            sys.executable,
            "-u",
            "-c",
            "import time; print('partial receipt', flush=True); time.sleep(30)",
        ]
    plan = {
        "version": 1,
        "builder_id": "fixture-builder",
        "max_rounds": 3,
        "input_paths": ["candidate.txt"],
        "protected_paths": ["requirements.txt"],
        "checks": [
            {
                "id": scenario,
                "kind": "project",
                "argv": argv,
                "timeout_seconds": 0.2 if scenario == "timeout" else 10,
            },
            {
                "id": "later-success",
                "kind": "audit",
                "argv": [sys.executable, "-c", "assert 2+2 == 4"],
                "timeout_seconds": 10,
            },
        ],
    }
    plan_path = folder / "plan.json"
    plan_path.write_text(json.dumps(plan, indent=2))
    script = REPO / "rb-audit-test-suite/scripts/test_loop.py"
    state = folder / "state"
    base = [sys.executable, str(script)]
    initialized = execute(
        base
        + [
            "init",
            "--project",
            str(project),
            "--plan",
            str(plan_path),
            "--state-dir",
            str(state),
        ],
        REPO,
        folder / "init",
    )
    assert initialized.returncode == 0
    run = execute(base + ["run", "--state-dir", str(state)], REPO, folder / "run")
    data = json.loads((state / "state.json").read_text())
    assert run.returncode == (3 if scenario == "healthy" else 1)
    assert data["status"] == (
        "awaiting_review" if scenario == "healthy" else "needs_repair"
    )
    checks = data["rounds"][0]["checks"]
    assert checks[-1]["exit_code"] == 0
    assert checks[0]["exit_code"] != 0 or scenario == "healthy"
    acceptance = execute(
        base + ["status", "--state-dir", str(state), "--require-verified"],
        REPO,
        folder / "acceptance",
    )
    assert acceptance.returncode != 0


@pytest.mark.parametrize(
    "defect",
    ["healthy", "empty", "duplicate", "error", "skip", "wrong_failure", "wrong_exit"],
)
def test_missing_exception_receipt_contract(tmp_path, defect):
    root = ET.Element("testsuite")
    target = ET.SubElement(root, "testcase", classname="test_heat", name="target")
    ET.SubElement(target, "failure", message="Failed: DID NOT RAISE ValueError")
    ET.SubElement(root, "testcase", classname="test_heat", name="test_import_origin")
    if defect == "empty":
        root.clear()
    elif defect == "duplicate":
        ET.SubElement(root, "testcase", classname="test_heat", name="target")
    elif defect in {"error", "skip"}:
        ET.SubElement(target, "error" if defect == "error" else "skipped")
    elif defect == "wrong_failure":
        target.find("failure").set("message", "ValueError: broken import")
    xml = tmp_path / "receipt.xml"
    ET.ElementTree(root).write(xml)
    args = (
        (2 if defect == "wrong_exit" else 1, xml),
        {"test_heat::target", "test_heat::test_import_origin"},
        "target",
    )
    if defect == "healthy":
        inspect_missing_value_error(*args)
    else:
        with pytest.raises(AssertionError):
            inspect_missing_value_error(*args)
