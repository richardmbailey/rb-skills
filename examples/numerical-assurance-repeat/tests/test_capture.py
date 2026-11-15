import sys

import pytest

from run_checks import capture


def test_capture_healthy(tmp_path):
    result = capture([sys.executable, "-c", 'print("healthy")'], tmp_path, "healthy")
    assert result["exit"] == 0
    assert "healthy" in (tmp_path / "healthy.log").read_text()


def test_capture_failure(tmp_path):
    result = capture(
        [sys.executable, "-c", 'print("partial"); raise SystemExit(7)'],
        tmp_path,
        "failure",
    )
    assert result["exit"] == 7
    assert "partial" in (tmp_path / "failure.log").read_text()


def test_capture_missing(tmp_path):
    assert capture(["/nonexistent-rb-repeat-tool"], tmp_path, "missing")["exit"] == 127


def test_capture_timeout_keeps_partial_output(tmp_path, monkeypatch):
    import subprocess

    import run_checks

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], 120, output=b"partial")

    monkeypatch.setattr(run_checks.subprocess, "run", timeout)
    assert capture(["slow"], tmp_path, "timeout")["exit"] == 124
    assert "partial" in (tmp_path / "timeout.log").read_text()


@pytest.mark.parametrize("failure", [0, 7, 127])
@pytest.mark.parametrize(
    "identity_fault", [None, "wrong_id", "wrong_origin", "missing", "changed"]
)
def test_main_preserves_earlier_failure(tmp_path, monkeypatch, failure, identity_fault):
    import hashlib
    import json

    import run_checks

    (tmp_path / "model.py").write_text("# fixture\n")
    (tmp_path / "expected-tests.json").write_text(json.dumps(["test_fixture"]))
    monkeypatch.setattr(run_checks, "ROOT", tmp_path)

    def fake_capture(command, directory, name, env):
        if name == "tests":
            (directory / "identities.json").write_text(
                json.dumps(
                    {
                        "selected": ["test_fixture"],
                        "outcomes": [
                            {"id": "test_fixture", "phase": "call", "outcome": "passed"}
                        ],
                        "model_origin": str(tmp_path / "model.py"),
                        "model_sha256": hashlib.sha256(
                            (tmp_path / "model.py").read_bytes()
                        ).hexdigest(),
                    }
                )
            )
        if name == "tests":
            path = directory / "identities.json"
            record = json.loads(path.read_text())
            if identity_fault == "wrong_id":
                record["outcomes"][0]["id"] = "substituted"
            if identity_fault == "wrong_origin":
                record["model_origin"] = "/elsewhere/model.py"
            path.write_text(json.dumps(record))
            if identity_fault == "missing":
                path.unlink()
            if identity_fault == "changed":
                (tmp_path / "model.py").write_text("# changed\n")
        return {"command": command, "exit": failure if name == "tests" else 0}

    monkeypatch.setattr(run_checks, "capture", fake_capture)
    assert run_checks.main() == (0 if failure == 0 and identity_fault is None else 1)
