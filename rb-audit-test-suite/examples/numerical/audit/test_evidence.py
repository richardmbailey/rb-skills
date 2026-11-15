"""Prove bad evidence fails the audit, using native pytest child reports."""
import pytest
from support import AuditError, inspect_result, run_suite

ID = "test_model::test_target"


@pytest.mark.parametrize("source, expected, target", [
    ("def test_target(): assert False", {ID}, None),  # unhealthy baseline
    ("def test_target(): return", {ID}, ID),  # surviving fault
    ("def test_target(): raise RuntimeError('broken')", {ID}, ID),
    ("import no_such_audit_example_module", {ID}, ID),  # import failure
    ("def syntax error", {ID}, ID),  # collection failure
    ("import pytest\n@pytest.mark.skip\ndef test_target(): pass", {ID}, ID),
    ("def test_other(): assert False", {ID}, ID),  # missing identity
    ("# no tests", {ID}, ID),
    ("def test_target(): pass\ndef test_other(): assert False",
     {ID, "test_model::test_other"}, ID),  # wrong assertion fails
])
def test_invalid_run_is_rejected(tmp_path, source, expected, target):
    project = tmp_path / "project"
    project.mkdir()
    (project / "pytest.ini").write_text("[pytest]\n")
    (project / "test_model.py").write_text(source + "\n")
    result = run_suite(project, tmp_path / "evidence")
    with pytest.raises(AuditError):
        inspect_result(result, expected, target)


@pytest.mark.parametrize("damage", ["malformed", "missing", "duplicate", "exit"])
def test_damaged_report_is_rejected(tmp_path, damage):
    project = tmp_path / "project"
    project.mkdir()
    (project / "pytest.ini").write_text("[pytest]\n")
    (project / "test_model.py").write_text("def test_target(): assert False\n")
    code, xml = run_suite(project, tmp_path / "evidence")
    inspect_result((code, xml), {ID}, ID)  # valid native assertion report first
    if damage == "malformed":
        xml.write_text("<bad xml")
    elif damage == "missing":
        xml.unlink()
    elif damage == "duplicate":
        from xml.etree import ElementTree as ET
        tree = ET.parse(xml)
        suite = tree.getroot().find("testsuite")
        suite.append(suite.find("testcase"))
        tree.write(xml)
    else:
        code = 2
    with pytest.raises(AuditError):
        inspect_result((code, xml), {ID}, ID)


def test_timeout_is_rejected(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    (project / "pytest.ini").write_text("[pytest]\n")
    (project / "test_model.py").write_text(
        "import time\ndef test_target():\n    time.sleep(60)\n    assert False\n")
    with pytest.raises(AuditError, match="timeout"):
        run_suite(project, tmp_path / "evidence", timeout=1)
    assert (tmp_path / "evidence" / "exit.txt").read_text() == "timeout\n"
