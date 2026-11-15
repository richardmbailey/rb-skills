"""These tests test the project suite, rather than importing the project model."""
import pytest
from support import FAULTS, audit_fault


@pytest.mark.parametrize("fault", FAULTS)
def test_suite_exposes_fault(fault, tmp_path, evidence_root, request):
    audit_fault(tmp_path, evidence_root / fault, fault,
                weak=request.config.getoption("--suite") == "weak")


@pytest.mark.parametrize("fault", ["rounded_step", "quotient_underflow"])
def test_weak_suite_is_rejected(fault, tmp_path, evidence_root):
    from support import AuditError
    with pytest.raises(AuditError, match="intended assertion did not fail"):
        audit_fault(tmp_path, evidence_root / ("weak-control-" + fault), fault, weak=True)
