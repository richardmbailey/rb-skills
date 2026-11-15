"""Check failure propagation and capture without recursive suite runs."""

import os
import sys
from pathlib import Path

import pytest

from tools.run_suite import (
    manifest,
    pytest_issues,
    read_capture,
    render_report,
    run_command,
)


def capture(ids):
    return {
        "collected_ids": ids,
        "model_origin": "model.py",
        "model_sha256": "digest",
        "phases": [
            {"nodeid": nodeid, "when": phase, "outcome": "passed", "wasxfail": None}
            for nodeid in ids
            for phase in ("setup", "call", "teardown")
        ],
    }


def test_exact_collection_and_origin():
    assert pytest_issues(["test_a"], capture(["test_a"]), "digest") == []


@pytest.mark.parametrize(
    "change",
    ["empty", "substitute", "origin", "hash", "skip", "xfail", "phase", "extra"],
)
def test_reject_incomplete_evidence(change):
    data = capture(["test_a"])
    expected = ["test_a"]
    if change == "empty":
        expected = []
        data = capture([])
    elif change == "substitute":
        data = capture(["test_b"])
    elif change == "origin":
        data["model_origin"] = "/old-install/model.py"
    elif change == "hash":
        data["model_sha256"] = "stale"
    elif change == "skip":
        data["phases"][1]["outcome"] = "skipped"
    elif change == "xfail":
        data["phases"][1]["wasxfail"] = "known failure"
    elif change == "phase":
        data["phases"].pop()
    else:
        data["phases"].append(
            {"nodeid": "test_extra", "when": "call", "outcome": "passed"}
        )
    assert pytest_issues(expected, data, "digest")


@pytest.mark.parametrize("exit_code", [0, 7])
def test_real_process_exit_and_log(tmp_path, exit_code):
    receipt = run_command(
        "fixture",
        [sys.executable, "-c", f"print('raw evidence'); raise SystemExit({exit_code})"],
        tmp_path,
        tmp_path,
        dict(os.environ),
        timeout=5,
    )
    assert receipt["returncode"] == exit_code
    assert receipt["timed_out"] is False
    assert (tmp_path / "fixture.log").read_text().strip() == "raw evidence"


def test_timeout_retains_partial_log(tmp_path):
    receipt = run_command(
        "slow",
        [
            sys.executable,
            "-c",
            "import time; print('started', flush=True); time.sleep(20)",
        ],
        tmp_path,
        tmp_path,
        dict(os.environ),
        timeout=0.3,
    )
    assert receipt["timed_out"] is True
    assert receipt["returncode"] != 0
    assert "started" in (tmp_path / "slow.log").read_text()


def test_spawn_failure_retains_receipt(tmp_path):
    receipt = run_command(
        "missing",
        [str(tmp_path / "absent-executable")],
        tmp_path,
        tmp_path,
        {},
        timeout=1,
    )
    assert receipt["returncode"] is None
    assert receipt["error"]
    assert (tmp_path / "missing.log").stat().st_size > 0


def test_manifest_detects_changes_and_ignores_artifacts(tmp_path):
    source = tmp_path / "model.py"
    source.write_text("old")
    first = manifest(tmp_path)
    (tmp_path / "artifacts").mkdir()
    (tmp_path / "artifacts" / "report.html").write_text("output")
    assert manifest(tmp_path) == first
    source.write_text("new")
    assert manifest(tmp_path) != first
    source.write_text("old")
    (tmp_path / "requirements.txt").write_text("pytest")
    assert manifest(tmp_path) != first


def test_html_escapes_untrusted_values_and_works_offline():
    page = render_report(
        {"passed": False, "issues": ['<script src="https://evil">&</script>']}
    )
    assert "<script" not in page
    assert "&lt;script" in page
    assert "&amp;" in page
    assert "Checks incomplete or failed" in page
    assert "<link" not in page
    assert "Checks passed" in render_report({"passed": True})


def test_corrupt_or_missing_capture_is_not_evidence(tmp_path):
    target = tmp_path / "capture.json"
    assert read_capture(target) == {}
    target.write_text("{broken")
    assert read_capture(target) == {}
    target.write_text("[]")
    assert read_capture(target) == {}
    assert pytest_issues(["test_a"], read_capture(target), "digest")


def test_capture_records_actual_import_in_pytest_process(tmp_path):
    project = Path(__file__).resolve().parents[1]
    (tmp_path / "conftest.py").write_bytes((project / "conftest.py").read_bytes())
    (tmp_path / "model.py").write_text("VALUE = 7\n")
    (tmp_path / "pytest.ini").write_text("[pytest]\n")
    (tmp_path / "test_example.py").write_text(
        "import model\ndef test_value():\n    assert model.VALUE == 7\n"
    )
    env = dict(
        os.environ,
        RB_TRIAL_CAPTURE=str(tmp_path / "capture.json"),
        PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
    )
    receipt = run_command(
        "capture",
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-c",
            str(tmp_path / "pytest.ini"),
            f"--confcutdir={tmp_path}",
            f"--basetemp={tmp_path / 'pytest-tmp'}",
        ],
        tmp_path,
        tmp_path,
        env,
        timeout=10,
    )
    assert receipt["returncode"] == 0
    data = read_capture(tmp_path / "capture.json")
    assert (
        pytest_issues(
            ["test_example.py::test_value"], data, manifest(tmp_path)["model.py"]
        )
        == []
    )


def test_output_limit_retains_bounded_log(tmp_path):
    receipt = run_command(
        "noisy",
        [sys.executable, "-c", "print('x' * 100000)"],
        tmp_path,
        tmp_path,
        dict(os.environ),
        timeout=5,
        max_output_bytes=1000,
    )
    assert receipt["output_limit_exceeded"] is True
    assert (tmp_path / "noisy.log").stat().st_size == 1000
