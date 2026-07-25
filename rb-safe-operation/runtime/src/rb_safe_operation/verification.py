from __future__ import annotations

from dataclasses import dataclass
from functools import wraps
import hashlib
from typing import Literal

from .models import Finding, LowLevelPlan

VerificationMode = Literal[
    "static_file_state",
    "executable_test",
    "runtime_observation",
    "external_observation",
]

SEPARATOR = "::"
KNOWN_MODES = {
    "static_file_state",
    "executable_test",
    "runtime_observation",
    "external_observation",
}
FIRST_RELEASE_SUPPORTED_MODES = {"static_file_state"}


@dataclass(frozen=True)
class VerificationRequirement:
    raw: str
    mode: str | None
    description: str
    valid: bool

    @classmethod
    def parse(cls, value: str) -> "VerificationRequirement":
        mode, separator, description = value.partition(SEPARATOR)
        mode = mode.strip()
        description = description.strip()
        valid = bool(separator and mode in KNOWN_MODES and description)
        return cls(
            raw=value,
            mode=mode if separator else None,
            description=description if valid else value,
            valid=valid,
        )


def _finding(
    *,
    operation_id: str,
    field: str,
    index: int,
    requirement: VerificationRequirement,
) -> Finding:
    identity = hashlib.sha256(
        f"{operation_id}\0{field}\0{index}\0{requirement.raw}".encode("utf-8")
    ).hexdigest()[:24]
    if not requirement.valid:
        explanation = (
            "verification requirements must use the closed '<mode>::<description>' syntax; "
            f"received {requirement.raw!r}"
        )
        finding_id = f"verification-format-{identity}"
    else:
        explanation = (
            f"verification mode {requirement.mode!r} is unsupported by the first-release "
            "static-only capability profile"
        )
        finding_id = f"verification-mode-{identity}"
    return Finding(
        finding_id=finding_id,
        invariant_id="E-003",
        operation_ids=[operation_id],
        effect_ids=[],
        category="incomplete_verification",
        severity="high",
        evidence_ids=[],
        evidence_provenance=[],
        finding_provenance="coordinator_observed",
        explanation=explanation,
        remediation_or_human_decision=(
            "use static_file_state criteria, move the phase to the standard route, "
            "or wait for a reviewed runtime that supports the required observation mode"
        ),
        blocking=True,
    )


def verification_mode_findings(plan: LowLevelPlan) -> list[Finding]:
    findings: list[Finding] = []
    for operation in plan.operations:
        for field in ("success_criteria", "verifier_checks"):
            for index, raw in enumerate(getattr(operation, field)):
                requirement = VerificationRequirement.parse(raw)
                if not requirement.valid or requirement.mode not in FIRST_RELEASE_SUPPORTED_MODES:
                    findings.append(
                        _finding(
                            operation_id=operation.operation_id,
                            field=field,
                            index=index,
                            requirement=requirement,
                        )
                    )
    return findings


def _normalized_plan(plan: LowLevelPlan) -> LowLevelPlan:
    """Strip mode prefixes for legacy policy feature-name checks.

    The artifact keeps the closed observation-mode syntax. The existing policy checker
    still recognises feature names such as product_diff and undeclared_effects, so this
    compatibility view exposes each parsed description to that checker.
    """

    operations = []
    for operation in plan.operations:
        updates: dict[str, list[str]] = {}
        for field in ("success_criteria", "verifier_checks"):
            updates[field] = [
                VerificationRequirement.parse(value).description
                for value in getattr(operation, field)
            ]
        operations.append(operation.model_copy(update=updates))
    return plan.model_copy(update={"operations": operations})


def install_policy_guard() -> None:
    """Install deterministic verification-mode enforcement before workflow imports.

    This compatibility guard keeps schema 1.0 while making observation modes
    machine-enforced. It can be removed when a future schema represents requirements as
    dedicated typed objects.
    """

    from . import policy

    original = policy.deterministic_assessment_findings
    if getattr(original, "_rb_verification_guard", False):
        return

    @wraps(original)
    def guarded(plan, active_policy, capabilities, covered_evidence_ids, approved_effect_ids):
        findings = original(
            _normalized_plan(plan),
            active_policy,
            capabilities,
            covered_evidence_ids,
            approved_effect_ids,
        )
        findings.extend(verification_mode_findings(plan))
        return findings

    guarded._rb_verification_guard = True  # type: ignore[attr-defined]
    policy.deterministic_assessment_findings = guarded
