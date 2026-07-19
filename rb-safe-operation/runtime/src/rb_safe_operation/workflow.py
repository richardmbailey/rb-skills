from __future__ import annotations

import hashlib
import os
import posixpath
import re
import secrets
import subprocess
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter, ValidationError

from .audit import AuditLog
from .canonical import artifact_hash, canonical_bytes, parse_json_strict
from .fakes import FakeAgentHost, FakeFilesystem, FakeSubprocess
from .models import (
    Assessment,
    DeterministicPreflight,
    ActivePolicy,
    EventPayload,
    ExecutionReport,
    Finding,
    HashRef,
    HostCapabilities,
    LowLevelPlan,
    RepairAttempt,
    RunManifest,
    RepositorySnapshot,
    SemanticAssessmentProposal,
    VerificationProposal,
    VerificationReport,
)
from .paths import resolve_contained
from .planning import COMMAND_CLASSIFICATIONS, classify_command, discover_instruction_files, select_markdown_phase
from .policy import active_policy_widening_errors, default_global_policy, deterministic_assessment_findings
from .state import acquire_lease, capture_snapshot, heartbeat_lease, release_lease, snapshot_materially_equal, transition


class WorkflowError(RuntimeError):
    pass


class ControlStateDrift(WorkflowError):
    """Protected control state changed; no further durable control writes are safe."""


def _safe_control_directory(parent: Path, name: str, *, create: bool) -> Path:
    path = parent / name
    if path.is_symlink():
        raise ControlStateDrift(f"control directory component is a symbolic link: {name}")
    if create:
        path.mkdir(mode=0o700, exist_ok=True)
    if path.exists() and not path.is_dir():
        raise ControlStateDrift(f"control directory component is not a directory: {name}")
    return path


class ResourcePause(WorkflowError):
    """Signal that execution reached a deliberate, resumable host resource boundary."""

    def __init__(self, evidence_id: str):
        super().__init__(f"resource pause: {evidence_id}")
        self.evidence_id = evidence_id


def hash_ref(artifact_type: str, payload: Any, schema_version: str = "1.0") -> HashRef:
    return HashRef(artifact_type=artifact_type, schema_version=schema_version, value=artifact_hash(artifact_type, schema_version, payload))


def _boundary_copy(value: Any, model_type):
    """Revalidate an in-process object through the same canonical boundary as a file artifact."""
    payload = value.model_dump(mode="json") if hasattr(value, "model_dump") else value
    return model_type.model_validate(parse_json_strict(canonical_bytes(payload)))


def _omitted_text(value: str) -> str:
    if not value:
        return ""
    if re.fullmatch(r"\[OMITTED: untrusted free text sha256=[0-9a-f]{64}\]", value):
        return value
    return f"[OMITTED: untrusted free text sha256={hashlib.sha256(value.encode('utf-8')).hexdigest()}]"


def _sanitize_finding(finding: Finding) -> Finding:
    if re.fullmatch(r"finding-[0-9a-f]{32}", finding.finding_id):
        finding_id = finding.finding_id
    else:
        finding_id = "finding-" + hashlib.sha256(canonical_bytes(finding.model_dump(mode="json"))).hexdigest()[:32]
    return finding.model_copy(update={
        "finding_id": finding_id,
        "finding_provenance": "agent_reported",
        "explanation": (
            f"typed agent finding {finding_id}: invariant={finding.invariant_id}; "
            f"category={finding.category}; severity={finding.severity}; blocking={str(finding.blocking).lower()}"
        ),
        "remediation_or_human_decision": "review the structured finding and its bounded evidence, then revise and reassess or leave the constrained pipeline",
    })


def canonical_semantic_proposal(proposal: SemanticAssessmentProposal) -> SemanticAssessmentProposal:
    return proposal.model_copy(update={
        "findings": [_sanitize_finding(item) for item in proposal.findings],
        "enforcement_disclosures": ["untrusted assessor prose omitted; coordinator derives capability disclosures"],
    })


def _partition_agent_findings(
    findings: list[Finding],
    operation_ids: set[str],
    effect_ids: set[str],
    evidence_provenance: dict[str, str],
) -> tuple[list[Finding], list[str]]:
    valid: list[Finding] = []
    errors: list[str] = []
    for finding in findings:
        finding_errors: list[str] = []
        if finding.finding_provenance != "agent_reported":
            finding_errors.append("finding_provenance")
        if not set(finding.operation_ids).issubset(operation_ids):
            finding_errors.append("operation_reference")
        if not set(finding.effect_ids).issubset(effect_ids):
            finding_errors.append("effect_reference")
        if not set(finding.evidence_ids).issubset(evidence_provenance):
            finding_errors.append("evidence_reference")
        else:
            expected = {evidence_provenance[item] for item in finding.evidence_ids}
            if set(finding.evidence_provenance) != expected:
                finding_errors.append("evidence_provenance")
        if finding_errors:
            errors.extend(finding_errors)
        else:
            valid.append(finding)
    return valid, errors


def canonical_semantic_proposal_for_plan(
    plan: LowLevelPlan, proposal: SemanticAssessmentProposal
) -> tuple[SemanticAssessmentProposal, list[str]]:
    raw = _boundary_copy(proposal, SemanticAssessmentProposal)
    operation_ids = {operation.operation_id for operation in plan.operations}
    effect_ids = {effect.effect_id for operation in plan.operations for effect in operation.effects}
    evidence_provenance = {item.evidence_id: item.provenance for item in plan.evidence}
    valid_findings, errors = _partition_agent_findings(
        raw.findings, operation_ids, effect_ids, evidence_provenance
    )
    required_evidence_ids = set(evidence_provenance)
    supplied_coverage = raw.covered_evidence_ids
    if len(supplied_coverage) != len(set(supplied_coverage)) or set(supplied_coverage) != required_evidence_ids:
        errors.append("covered_evidence_set")
    canonical = canonical_semantic_proposal(raw.model_copy(update={
        "semantic_pass": raw.semantic_pass and not errors,
        "findings": valid_findings,
        "covered_evidence_ids": sorted(set(supplied_coverage) & required_evidence_ids),
    }))
    return canonical, errors


def default_host_capabilities() -> HostCapabilities:
    """Return the immutable capabilities actually probed for the first Codex release."""
    return HostCapabilities(
        profile="semi_formal",
        role_read_only="instruction_only",
        product_state_observation="coordinator_observed",
        complete_child_trace=False,
        atomic_path_enforcement=False,
        atomic_lease_create=True,
        bounded_resource_enforcement="instruction_only",
        fresh_context_enforcement="instruction_only",
    )


def _capability_disclosures(capabilities: HostCapabilities) -> list[str]:
    disclosures = [
        f"role read-only enforcement: {capabilities.role_read_only}",
        f"fresh role-context enforcement: {capabilities.fresh_context_enforcement}",
        f"bounded resource enforcement: {capabilities.bounded_resource_enforcement}",
        f"product-state observation: {capabilities.product_state_observation}",
        f"complete child-process trace: {str(capabilities.complete_child_trace).lower()}",
        f"atomic path enforcement: {str(capabilities.atomic_path_enforcement).lower()}",
    ]
    return disclosures


def _sanitize_execution_report(report: ExecutionReport) -> ExecutionReport:
    for item in report.evidence:
        if item.provenance != "agent_reported" or item.locator != f"agent-report:{item.evidence_id}":
            raise WorkflowError("executor evidence must use an agent-reported structural locator")
    return report.model_copy(update={
        "evidence": [item.model_copy(update={"summary": _omitted_text(item.summary)}) for item in report.evidence],
        "next_strategy": None if report.next_strategy is None else _omitted_text(report.next_strategy),
    })


def _sanitize_repair_attempt(attempt: RepairAttempt) -> RepairAttempt:
    return attempt.model_copy(update={
        "hypothesis": _omitted_text(attempt.hypothesis),
        "observed_result": _omitted_text(attempt.observed_result),
        "reconsidered_assumption": _omitted_text(attempt.reconsidered_assumption),
        "materially_different_next_strategy": _omitted_text(attempt.materially_different_next_strategy),
        "fresh_idempotency_proof": (
            None if attempt.fresh_idempotency_proof is None else _omitted_text(attempt.fresh_idempotency_proof)
        ),
    })


def _plan_instruction_targets(plan: LowLevelPlan) -> list[str]:
    targets = {plan.source_phase.plan_path}
    for operation in plan.operations:
        contract = operation.path_contract
        for field in ("read_roots", "create_roots", "modify_roots", "delete_roots", "working_directories"):
            targets.update(getattr(contract, field))
        if operation.kind == "exact_action" and operation.adapter == "read_file":
            targets.add(operation.path)
        elif operation.kind == "exact_action" and operation.adapter == "apply_patch":
            targets.update(operation.expected_created_paths + operation.expected_modified_paths + operation.expected_deleted_paths)
        elif operation.kind == "exact_action" and operation.adapter in {"exec_argv", "check"}:
            targets.update(operation.input_hashes)
            if operation.adapter == "check":
                targets.update(operation.declared_generated_paths)
    return sorted(targets)


def assess_plan(
    plan: LowLevelPlan,
    global_policy: Any,
    active_policy: Any,
    current_snapshot: RepositorySnapshot,
    capabilities: HostCapabilities,
    semantic_proposal: SemanticAssessmentProposal,
    approvals: list[Any],
    *,
    now: datetime | None = None,
    prior_assessment_hash: HashRef | None = None,
) -> Assessment:
    plan = _boundary_copy(plan, LowLevelPlan)
    global_policy = _boundary_copy(global_policy, ActivePolicy)
    active_policy = _boundary_copy(active_policy, ActivePolicy)
    current_snapshot = _boundary_copy(current_snapshot, RepositorySnapshot)
    requested_capabilities = _boundary_copy(capabilities, HostCapabilities)
    capabilities = default_host_capabilities()
    semantic_proposal, semantic_integrity_errors = canonical_semantic_proposal_for_plan(plan, semantic_proposal)
    validated_approvals = [_boundary_copy(item, type(item)) for item in approvals]
    duplicate_approval_ids = sorted({
        item.approval_id for item in validated_approvals
        if sum(candidate.approval_id == item.approval_id for candidate in validated_approvals) > 1
    })
    approvals = []
    seen_approval_ids: set[str] = set()
    for approval in validated_approvals:
        if approval.approval_id not in seen_approval_ids:
            approvals.append(approval)
            seen_approval_ids.add(approval.approval_id)
    observed_at = now or datetime.now(timezone.utc)
    covered = set(semantic_proposal.covered_evidence_ids)
    plan_hash = hash_ref("low-level-plan", plan.model_dump(mode="json"))
    policy_hash = hash_ref("active-policy", active_policy.model_dump(mode="json"))
    snapshot_hash = hash_ref("repository-snapshot", plan.snapshot.model_dump(mode="json"))
    operation_hashes = {
        operation.operation_id: hash_ref("operation", operation.model_dump(mode="json")) for operation in plan.operations
    }
    identity_findings = _identity_findings(plan, global_policy, active_policy, current_snapshot)
    if duplicate_approval_ids:
        identity_findings.append(_blocking_finding(
            "approval-identity-duplicate", "O-007", "approval_scope",
            f"approval IDs must be unique within an assessment: {len(duplicate_approval_ids)} duplicate(s)",
        ))
    if semantic_integrity_errors:
        identity_findings.append(_blocking_finding(
            "semantic-reference-integrity", "E-004", "finding_identity",
            f"semantic proposal has invalid typed references or coverage: {sorted(set(semantic_integrity_errors))}",
        ))
    if requested_capabilities != capabilities:
        identity_findings.append(_blocking_finding(
            "identity-host-capabilities", "A-008", "unsupported_host_capability",
            "caller-supplied host capabilities differ from the immutable probed first-release profile",
        ))
    installed_global_policy = default_global_policy(plan.snapshot.project_root)
    if global_policy != installed_global_policy:
        identity_findings.append(_blocking_finding(
            "identity-global-policy-source", "P-001", "artifact_identity",
            "caller-supplied global policy differs from the immutable installed baseline",
        ))
    widening = active_policy_widening_errors(installed_global_policy, active_policy)
    if widening:
        identity_findings.append(_blocking_finding(
            "identity-policy-widening", "P-003", "policy_widening",
            f"active policy is wider than the immutable global policy: {widening}",
        ))
    approved_effects: set[str] = set()
    approval_findings: list[Finding] = []
    for operation in plan.operations:
        operation_hash = operation_hashes[operation.operation_id]
        for effect in operation.effects:
            required_classes = _required_effect_approval_classes(operation, effect, active_policy)
            review_class = _effect_requires_review(effect)
            if review_class and not required_classes:
                approval_findings.append(_blocking_finding(
                    f"approval-class-{effect.effect_id}", "E-002", "approval_scope",
                    "review-class effect has no deterministically derived or declared approval class", [operation.operation_id], [effect.effect_id],
                ))
                continue
            required_targets = set(effect.targets)
            if required_classes and not required_targets:
                approval_findings.append(_blocking_finding(
                    f"approval-target-{effect.effect_id}", "O-007", "approval_scope",
                    "approval-gated effect does not declare exact targets", [operation.operation_id], [effect.effect_id],
                ))
                continue
            idempotency_required = (
                effect.exposure in {"project_external", "multi_party", "systemic"}
                or effect.reversibility in {"uncertain", "none"}
                or effect.effect_class == "external_write"
            )
            missing_pairs: list[str] = []
            for approval_class in sorted(required_classes):
                for target in sorted(required_targets):
                    matches = [
                        approval for approval in approvals
                        if (
                        approval.plan_hash == plan_hash
                        and approval.operation_hash == operation_hash
                        and approval.policy_hash == policy_hash
                        and approval.snapshot_hash == snapshot_hash
                        and approval.effect_id == effect.effect_id
                        and approval.effect_class == effect.effect_class
                        and approval.approval_class == approval_class
                        and approval.target == target
                        and not approval.consumed
                        and (approval.expires_at is None or datetime.strptime(approval.expires_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc) > observed_at)
                        and (not idempotency_required or bool(approval.idempotency_key))
                        )
                    ]
                    if len(matches) != 1:
                        status = "missing" if not matches else "ambiguous"
                        missing_pairs.append(f"{status}:{approval_class}:{target}")
            if missing_pairs:
                approval_findings.append(_blocking_finding(
                    f"approval-{effect.effect_id}", "O-007", "approval_scope",
                    f"missing exact current approval bindings: {missing_pairs}", [operation.operation_id], [effect.effect_id],
                ))
            elif required_classes:
                approved_effects.add(effect.effect_id)
    deterministic = deterministic_assessment_findings(plan, active_policy, capabilities, covered, approved_effects)
    deterministic = identity_findings + approval_findings + deterministic
    deterministic_ids = {item.finding_id for item in deterministic}
    semantic_collisions = sorted(
        item.finding_id for item in semantic_proposal.findings if item.finding_id in deterministic_ids
    )
    semantic_findings = [
        item for item in semantic_proposal.findings if item.finding_id not in deterministic_ids
    ]
    if semantic_collisions:
        deterministic.append(_blocking_finding(
            "semantic-finding-id-collision", "E-004", "finding_identity",
            f"semantic finding IDs collide with deterministic findings: {semantic_collisions}",
        ))
    findings = deterministic + semantic_findings
    expected_evidence = {item.evidence_id for item in plan.evidence}
    missing = sorted(expected_evidence - covered)
    deterministic_pass = not deterministic and not missing
    semantic_pass = semantic_proposal.semantic_pass and not any(item.blocking for item in semantic_proposal.findings)
    safe = deterministic_pass and semantic_pass
    return Assessment(
        schema_version="1.0",
        assessment_id=f"assessment-{plan_hash.value[:32]}",
        plan_hash=plan_hash,
        policy_hash=policy_hash,
        snapshot_hash=snapshot_hash,
        deterministic_pass=deterministic_pass,
        semantic_pass=semantic_pass,
        safe=safe,
        status="approved" if safe else "rejected",
        profile=capabilities.profile,
        findings=findings,
        covered_evidence_ids=sorted(covered),
        missing_evidence_ids=missing,
        approvals=approvals,
        enforcement_disclosures=_capability_disclosures(capabilities),
        prior_assessment_hash=prior_assessment_hash,
    )


def deterministic_preflight(
    plan: LowLevelPlan,
    global_policy: ActivePolicy,
    active_policy: ActivePolicy,
    current_snapshot: RepositorySnapshot,
    capabilities: HostCapabilities,
    approvals: list[Any],
    *,
    now: datetime | None = None,
) -> DeterministicPreflight:
    """Run every non-semantic gate without invoking or accepting an assessor response."""
    required_evidence = sorted(item.evidence_id for item in plan.evidence)
    placeholder = SemanticAssessmentProposal(
        schema_version="1.0",
        semantic_pass=True,
        findings=[],
        covered_evidence_ids=required_evidence,
        enforcement_disclosures=[],
    )
    assessment = assess_plan(
        plan, global_policy, active_policy, current_snapshot, capabilities, placeholder, approvals, now=now
    )
    return DeterministicPreflight(
        schema_version="1.0",
        preflight_id=f"preflight-{assessment.plan_hash.value[:32]}",
        plan_hash=assessment.plan_hash,
        policy_hash=assessment.policy_hash,
        snapshot_hash=assessment.snapshot_hash,
        deterministic_pass=assessment.deterministic_pass,
        semantic_assessment_required=assessment.deterministic_pass,
        findings=assessment.findings,
        approvals=assessment.approvals,
        enforcement_disclosures=assessment.enforcement_disclosures,
        required_semantic_evidence_ids=required_evidence,
    )


def _effect_requires_review(effect: Any) -> bool:
    severity = {name: index for index, name in enumerate(("none", "low", "medium", "high", "critical"))}
    return (
        severity[effect.residual_severity] >= severity["medium"]
        or effect.likelihood in {"likely", "almost_certain"}
        or effect.exposure in {"project_external", "multi_party", "systemic"}
        or effect.data_classification in {"personal", "sensitive", "secret"}
        or effect.reversibility in {"uncertain", "none"}
        or effect.detectability in {"weak", "unknown"}
        or effect.cost_impact in {"medium", "high"}
        or effect.availability_impact in {"medium", "high"}
    )


def _derived_approval_classes(effect: Any) -> set[str]:
    required: set[str] = set()
    if effect.effect_class == "repository_delete":
        required.add("destructive")
    if effect.effect_class == "external_write":
        required.add("external_write")
    if effect.data_classification in {"personal", "sensitive", "secret"}:
        required.add("privacy_sensitive")
    if effect.security_sensitive:
        required.add("security_sensitive")
    if effect.cost_impact in {"medium", "high"}:
        required.add("material_cost")
    if effect.reversibility == "none":
        required.add("irreversible")
    return required


def _required_effect_approval_classes(operation: Any, effect: Any, active_policy: ActivePolicy) -> set[str]:
    classes = _derived_approval_classes(effect)
    classes.update(set(operation.approval_classes) & set(active_policy.required_approvals))
    if effect.approval_class is not None:
        classes.add(effect.approval_class)
    return classes


def _blocking_finding(
    finding_id: str,
    invariant_id: str,
    category: str,
    explanation: str,
    operation_ids: list[str] | None = None,
    effect_ids: list[str] | None = None,
) -> Finding:
    return Finding(
        finding_id=finding_id,
        invariant_id=invariant_id,
        operation_ids=operation_ids or [],
        effect_ids=effect_ids or [],
        category=category,
        severity="high",
        evidence_ids=[],
        evidence_provenance=[],
        finding_provenance="coordinator_observed",
        explanation=explanation,
        remediation_or_human_decision="regenerate the plan or obtain a newly bound approval, then reassess",
        blocking=True,
    )


def _identity_findings(plan: LowLevelPlan, global_policy: Any, active_policy: Any, current_snapshot: RepositorySnapshot) -> list[Finding]:
    findings: list[Finding] = []
    expected_global = hash_ref("active-policy", global_policy.model_dump(mode="json"))
    expected_active = hash_ref("active-policy", active_policy.model_dump(mode="json"))
    if plan.global_policy_hash != expected_global:
        findings.append(_blocking_finding("identity-global-policy", "P-001", "artifact_identity", "global policy hash differs from the installed immutable baseline"))
    if plan.merged_policy_hash != expected_active:
        findings.append(_blocking_finding("identity-active-policy", "P-001", "artifact_identity", "merged policy hash differs from the active policy assessed"))
    direct_text_hash = hashlib.sha256(plan.source_phase.selected_text.encode("utf-8")).hexdigest()
    if plan.source_phase.selected_text_hash != direct_text_hash:
        findings.append(_blocking_finding("identity-selected-text", "R-001", "artifact_identity", "selected phase text hash does not match the embedded text"))
    try:
        selected = select_markdown_phase(plan.source_phase.plan_path, plan.source_phase.phase_id)
        if selected.source != plan.source_phase:
            findings.append(_blocking_finding("identity-source-phase", "R-002", "artifact_identity", "authoritative phase file no longer matches the selected phase"))
        if selected.later_phase_ids != plan.later_phase_ids:
            findings.append(_blocking_finding("identity-continuity", "R-001", "phase_continuity", "later-phase continuity differs from the authoritative plan"))
    except Exception as exc:
        findings.append(_blocking_finding("identity-source-phase", "R-002", "artifact_identity", f"authoritative phase cannot be reselected: {type(exc).__name__}"))
    equal, differences = snapshot_materially_equal(plan.snapshot, current_snapshot)
    if not equal:
        findings.append(_blocking_finding("identity-snapshot", "R-002", "snapshot_drift", f"current repository snapshot differs: {differences}"))
    try:
        discovered = discover_instruction_files(plan.snapshot.project_root, _plan_instruction_targets(plan))
        if discovered != plan.snapshot.instruction_hashes:
            findings.append(_blocking_finding("identity-instructions", "A-005", "instruction_scope", "applicable repository instructions are omitted, stale, or over-declared"))
    except Exception as exc:
        findings.append(_blocking_finding("identity-instructions", "A-005", "instruction_scope", f"applicable instruction discovery failed: {type(exc).__name__}"))
    return findings


def execute_fake(
    plan: LowLevelPlan,
    assessment: Assessment,
    filesystem: FakeFilesystem,
    subprocess_host: FakeSubprocess,
    agent_host: FakeAgentHost | None = None,
) -> list[ExecutionReport]:
    plan = _boundary_copy(plan, LowLevelPlan)
    assessment = _boundary_copy(assessment, Assessment)
    if not assessment.safe:
        raise WorkflowError("rejected assessment cannot execute")
    if assessment.plan_hash.value != artifact_hash("low-level-plan", "1.0", plan.model_dump(mode="json")):
        raise WorkflowError("plan identity differs from approved assessment")
    reports: list[ExecutionReport] = []
    for operation in plan.operations:
        evidence = []
        if operation.kind == "exact_action" and operation.adapter == "read_file":
            content = filesystem.read(operation.path)[operation.byte_start:operation.byte_end]
            if operation.expected_hash and hashlib.sha256(content).hexdigest() != operation.expected_hash:
                raise WorkflowError("read_file content hash mismatch")
        elif operation.kind == "exact_action" and operation.adapter == "apply_patch":
            for path in operation.expected_modified_paths + operation.expected_created_paths:
                filesystem.write(path, operation.patch.encode("utf-8"))
        elif operation.kind == "exact_action" and operation.adapter in {"exec_argv", "check"}:
            environment = {entry.name: entry.literal_value for entry in operation.environment if entry.literal_value is not None}
            code, stdout, stderr = subprocess_host.run(operation.argv, environment, operation.path_contract.working_directories[0])
            if operation.adapter == "check" and code not in operation.expected_exit_codes:
                raise WorkflowError(f"check failed: {code}: {stderr[:200]}")
            if operation.adapter == "exec_argv" and code != 0:
                raise WorkflowError(f"exec_argv failed: {code}: {stderr[:200]}")
        elif operation.kind == "bounded_agent_task":
            if agent_host is None:
                raise WorkflowError("bounded tasks require an explicit agent host")
            report = ExecutionReport.model_validate(agent_host.invoke("executor", {
                "operation": operation.model_dump(mode="json"),
                "evidence": [item.model_dump(mode="json") for item in plan.evidence if item.evidence_id in operation.evidence_ids],
            }))
            if report.operation_id != operation.operation_id:
                raise WorkflowError("agent report operation identity mismatch")
            report = _sanitize_execution_report(report)
            if not report.success or report.unexpected_effects:
                raise WorkflowError("bounded executor reported failure or unexpected effects")
            if not set(operation.completion_evidence).issubset({item.evidence_id for item in report.evidence}):
                raise WorkflowError("bounded executor report lacks required completion evidence")
            reports.append(report)
            continue
        else:
            raise WorkflowError("unsupported operation")
        reports.append(ExecutionReport(
            schema_version="1.0", operation_id=operation.operation_id, success=True, evidence=evidence,
            expected_effect_ids_observed=[item.effect_id for item in operation.effects], unexpected_effects=[], next_strategy=None,
        ))
    return reports


def _execute_exact_actions(plan: LowLevelPlan, assessment: Assessment, operations: list[Any] | None = None) -> list[ExecutionReport]:
    """Dispatch exact adapters. Only ExecutionCoordinator may call this mutation boundary."""
    plan = _boundary_copy(plan, LowLevelPlan)
    assessment = _boundary_copy(assessment, Assessment)
    if not assessment.safe:
        raise WorkflowError("rejected assessment cannot execute")
    if assessment.plan_hash != hash_ref("low-level-plan", plan.model_dump(mode="json")):
        raise WorkflowError("plan identity differs from approved assessment")
    reports: list[ExecutionReport] = []
    selected_operations = plan.operations
    if operations is not None:
        requested_ids = [item.operation_id for item in operations]
        by_id = {item.operation_id: item for item in plan.operations}
        if len(requested_ids) != len(set(requested_ids)) or not set(requested_ids).issubset(by_id):
            raise WorkflowError("requested exact operation selection is not in the approved plan")
        selected_operations = [by_id[item] for item in requested_ids]
    for operation in selected_operations:
        if operation.kind != "exact_action":
            raise WorkflowError("bounded tasks require the fresh executor host")
        if operation.adapter == "read_file":
            resolved = resolve_contained(operation.path, operation.path_contract.read_roots, operation.path_contract.protected_roots)
            data = Path(resolved.resolved).read_bytes()[operation.byte_start:operation.byte_end]
            if operation.expected_hash and hashlib.sha256(data).hexdigest() != operation.expected_hash:
                raise WorkflowError("read_file content hash mismatch")
        elif operation.adapter == "apply_patch":
            _apply_patch(operation)
        else:
            if operation.environment and any(entry.literal_value is None for entry in operation.environment):
                raise WorkflowError("real executable adapter cannot resolve secret handles or hashed values")
            executable = Path(operation.executable_path).resolve(strict=True)
            if hashlib.sha256(executable.read_bytes()).hexdigest() != operation.executable_hash:
                raise WorkflowError("executable identity mismatch")
            if not operation.argv or Path(operation.argv[0]).resolve(strict=False) != executable:
                raise WorkflowError("argv[0] must be the resolved executable identity")
            classifications = classify_command(str(executable), operation.argv, operation.child_processes_declared)
            prohibited = COMMAND_CLASSIFICATIONS
            if prohibited.intersection(classifications):
                raise WorkflowError(f"complex or transitive command belongs in bounded_agent_task: {classifications}")
            for path_value, expected_hash in operation.input_hashes.items():
                resolved_input = resolve_contained(path_value, operation.path_contract.read_roots, operation.path_contract.protected_roots)
                if hashlib.sha256(Path(resolved_input.resolved).read_bytes()).hexdigest() != expected_hash:
                    raise WorkflowError(f"command input identity mismatch: {path_value}")
            environment = {entry.name: entry.literal_value or "" for entry in operation.environment}
            cwd = operation.path_contract.working_directories[0]
            resolve_contained(cwd, operation.path_contract.read_roots, operation.path_contract.protected_roots)
            result = subprocess.run(operation.argv, cwd=cwd, env=environment, check=False, capture_output=True, text=True, timeout=operation.resource_limits.max_seconds)
            expected_codes = operation.expected_exit_codes if operation.adapter == "check" else [0]
            if result.returncode not in expected_codes:
                raise WorkflowError(f"check failed: {result.returncode}: {result.stderr[:200]}")
        reports.append(ExecutionReport(
            schema_version="1.0", operation_id=operation.operation_id, success=True, evidence=[],
            expected_effect_ids_observed=[item.effect_id for item in operation.effects], unexpected_effects=[], next_strategy=None,
        ))
    return reports


@dataclass(frozen=True)
class VerificationContext:
    context_id: str
    token: str
    plan_hash: HashRef
    assessment_hash: HashRef
    snapshot_hash: HashRef


_VERIFICATION_CONTEXTS: dict[str, tuple[str, str, str, str]] = {}


def begin_verification_context(
    plan: LowLevelPlan,
    assessment: Assessment,
    context_id: str,
    observed_snapshot: RepositorySnapshot,
) -> VerificationContext:
    """Coordinator-only hook used when it has started a genuinely fresh verifier context."""
    plan = _boundary_copy(plan, LowLevelPlan)
    assessment = _boundary_copy(assessment, Assessment)
    observed_snapshot = _boundary_copy(observed_snapshot, RepositorySnapshot)
    if not assessment.safe:
        raise WorkflowError("rejected assessment cannot enter verification")
    plan_hash = hash_ref("low-level-plan", plan.model_dump(mode="json"))
    assessment_hash = hash_ref("assessment", assessment.model_dump(mode="json"))
    snapshot_hash = hash_ref("repository-snapshot", observed_snapshot.model_dump(mode="json"))
    if assessment.plan_hash != plan_hash:
        raise WorkflowError("plan identity differs from approved assessment")
    token = secrets.token_hex(32)
    _VERIFICATION_CONTEXTS[token] = (plan_hash.value, assessment_hash.value, context_id, snapshot_hash.value)
    return VerificationContext(
        context_id=context_id, token=token, plan_hash=plan_hash,
        assessment_hash=assessment_hash, snapshot_hash=snapshot_hash,
    )


class ExecutionCoordinator:
    """Hold one lease and audit chain across approved execution and context-separated verification."""

    def __init__(
        self,
        plan: LowLevelPlan,
        assessment: Assessment,
        global_policy: Any,
        active_policy: Any,
        capabilities: HostCapabilities,
        semantic_proposal: SemanticAssessmentProposal | None = None,
        agent_host: Any | None = None,
    ):
        self.plan = _boundary_copy(plan, LowLevelPlan)
        self.assessment = _boundary_copy(assessment, Assessment)
        self.global_policy = _boundary_copy(global_policy, ActivePolicy)
        self.active_policy = _boundary_copy(active_policy, ActivePolicy)
        self.capabilities = _boundary_copy(capabilities, HostCapabilities)
        if semantic_proposal is None:
            raise WorkflowError("execution requires the original typed semantic assessment proposal")
        self.semantic_proposal = canonical_semantic_proposal(_boundary_copy(semantic_proposal, SemanticAssessmentProposal))
        self.agent_host = agent_host
        plan = self.plan
        assessment = self.assessment
        global_policy = self.global_policy
        active_policy = self.active_policy
        capabilities = self.capabilities
        self.plan_hash = hash_ref("low-level-plan", plan.model_dump(mode="json"))
        self.assessment_hash = hash_ref("assessment", assessment.model_dump(mode="json"))
        if not assessment.safe:
            raise WorkflowError("rejected assessment cannot execute")
        if assessment.plan_hash != self.plan_hash:
            raise WorkflowError("plan identity differs from approved assessment")
        if assessment.policy_hash != hash_ref("active-policy", active_policy.model_dump(mode="json")):
            raise WorkflowError("policy identity differs from approved assessment")
        if assessment.snapshot_hash != hash_ref("repository-snapshot", plan.snapshot.model_dump(mode="json")):
            raise WorkflowError("snapshot identity differs from approved assessment")
        current = self._capture()
        equal, differences = snapshot_materially_equal(plan.snapshot, current)
        if not equal:
            raise WorkflowError(f"repository changed since assessment: {differences}")
        revalidation = assess_plan(
            plan,
            global_policy,
            active_policy,
            current,
            capabilities,
            self.semantic_proposal,
            assessment.approvals,
            prior_assessment_hash=assessment.prior_assessment_hash,
        )
        if revalidation != assessment:
            raise WorkflowError("execution-time reassessment does not reproduce the approved assessment")
        control_root = Path(plan.snapshot.control_plane_roots[0])
        if control_root.is_symlink():
            raise ControlStateDrift("canonical control root is a symbolic link")
        control_root.mkdir(mode=0o700, exist_ok=True)
        if not control_root.is_dir():
            raise ControlStateDrift("canonical control root is not a directory")
        runs_root = _safe_control_directory(control_root, "runs", create=True)
        audit_root = runs_root / plan.run_id
        if audit_root.is_symlink():
            raise ControlStateDrift("run directory is a symbolic link")
        if audit_root.exists():
            raise WorkflowError("run identity already exists; reload an eligible paused run instead")
        self.lease = acquire_lease(plan.snapshot.project_root, plan.run_id, plan.snapshot.device_identity, None)
        try:
            audit_root.mkdir(mode=0o700, exist_ok=False)
            self.audit = AuditLog(str(audit_root), plan.run_id)
        except Exception:
            release_lease(self.lease)
            self.lease = None
            raise
        self.run_root = audit_root
        self.bundle_path = audit_root / "coordinator-bundle.json"
        self._control_root_identity = self._read_control_root_identity()
        try:
            self.manifest = RunManifest(
                schema_version="1.0", run_id=plan.run_id, state="approved", suspended_from=None,
                plan_hash=self.plan_hash, assessment_hash=self.assessment_hash,
                policy_hash=assessment.policy_hash, snapshot_hash=assessment.snapshot_hash, event_head_hash=None,
            )
            self.reports: list[ExecutionReport] = []
            self.next_operation_index = 0
            self.repair_attempts: list[RepairAttempt] = []
            self.bounded_invocation_counts: dict[str, int] = {}
            self.pending_repair_attempt: RepairAttempt | None = None
            self._persisted_bundle_hash: str | None = None
            self._closed = False
            self._verification_context: VerificationContext | None = None
            self._verification_control_inventory: dict[str, str] | None = None
            self.last_verification: VerificationReport | None = None
            self.post_execution_snapshot: RepositorySnapshot | None = None
            self._append_event(
                "execution_started", "approved", "executing", "approved bundle acquired project lease",
                evidence_ids=[
                    f"low-level-plan:{self.plan_hash.value}",
                    f"assessment:{self.assessment_hash.value}",
                    f"active-policy:{assessment.policy_hash.value}",
                    f"host-capabilities:{artifact_hash('host-capabilities', '1.0', capabilities.model_dump(mode='json'))}",
                ],
            )
            self.manifest = transition(self.manifest, "executing", ["audit:execution_started"])
            self._persist_bundle()
        except Exception:
            release_lease(self.lease)
            self.lease = None
            raise

    @classmethod
    def reload(
        cls,
        project_root: str,
        run_id: str,
        capabilities: HostCapabilities,
        agent_host: Any | None = None,
    ) -> "ExecutionCoordinator":
        """Reload a durably paused coordinator after validating every persisted identity."""
        capabilities = _boundary_copy(capabilities, HostCapabilities)
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", run_id) or ".." in run_id:
            raise WorkflowError("invalid run identity")
        root = Path(project_root).resolve(strict=True)
        control_root = root / ".rb-safe-operation"
        if control_root.is_symlink() or not control_root.is_dir():
            raise WorkflowError("paused coordinator control root is missing, non-directory, or a symbolic link")
        runs_root = control_root / "runs"
        if runs_root.is_symlink() or not runs_root.is_dir():
            raise WorkflowError("paused coordinator runs root is missing, non-directory, or a symbolic link")
        run_root = runs_root / run_id
        if run_root.is_symlink():
            raise WorkflowError("paused coordinator run root is a symbolic link")
        bundle_path = run_root / "coordinator-bundle.json"
        try:
            persisted = bundle_path.read_bytes()
            payload = parse_json_strict(persisted)
        except Exception:
            raise WorkflowError("paused coordinator bundle is missing or invalid") from exc
        if persisted != canonical_bytes(payload) + b"\n":
            raise WorkflowError("paused coordinator bundle is not canonical")
        expected_keys = {
            "schema_version", "plan", "assessment", "semantic_proposal", "global_policy", "active_policy", "capabilities",
            "manifest", "reports", "next_operation_index", "last_verification", "post_execution_snapshot",
            "repair_attempts", "pending_repair_attempt",
            "bounded_invocation_counts",
        }
        if not isinstance(payload, dict) or set(payload) != expected_keys or payload.get("schema_version") != "1.0":
            raise WorkflowError("paused coordinator bundle has an unsupported shape")
        try:
            plan = LowLevelPlan.model_validate(payload["plan"])
            assessment = Assessment.model_validate(payload["assessment"])
            semantic_proposal = SemanticAssessmentProposal.model_validate(payload["semantic_proposal"])
            global_policy = ActivePolicy.model_validate(payload["global_policy"])
            active_policy = ActivePolicy.model_validate(payload["active_policy"])
            persisted_capabilities = HostCapabilities.model_validate(payload["capabilities"])
            manifest = RunManifest.model_validate(payload["manifest"])
            reports = TypeAdapter(list[ExecutionReport]).validate_python(payload["reports"])
            last_verification = (
                None if payload["last_verification"] is None
                else VerificationReport.model_validate(payload["last_verification"])
            )
            post_execution_snapshot = (
                None if payload["post_execution_snapshot"] is None
                else RepositorySnapshot.model_validate(payload["post_execution_snapshot"])
            )
            repair_attempts = TypeAdapter(list[RepairAttempt]).validate_python(payload["repair_attempts"])
            bounded_invocation_counts = payload["bounded_invocation_counts"]
            pending_repair_attempt = (
                None if payload["pending_repair_attempt"] is None
                else RepairAttempt.model_validate(payload["pending_repair_attempt"])
            )
            next_operation_index = payload["next_operation_index"]
        except Exception as exc:
            raise WorkflowError("paused coordinator bundle failed typed validation") from exc
        if plan.run_id != run_id or manifest.run_id != run_id or Path(plan.snapshot.project_root) != root:
            raise WorkflowError("paused coordinator bundle project or run identity mismatch")
        canonical_control = str(root / ".rb-safe-operation")
        if plan.snapshot.control_plane_roots != [canonical_control] or run_root.resolve() != Path(canonical_control) / "runs" / run_id:
            raise WorkflowError("paused coordinator bundle control-plane identity mismatch")
        plan_hash = hash_ref("low-level-plan", plan.model_dump(mode="json"))
        assessment_hash = hash_ref("assessment", assessment.model_dump(mode="json"))
        policy_hash = hash_ref("active-policy", active_policy.model_dump(mode="json"))
        if (
            manifest.plan_hash != plan_hash
            or manifest.assessment_hash != assessment_hash
            or manifest.policy_hash != policy_hash
            or manifest.snapshot_hash != assessment.snapshot_hash
            or assessment.plan_hash != plan_hash
            or assessment.policy_hash != policy_hash
            or assessment.snapshot_hash != hash_ref("repository-snapshot", plan.snapshot.model_dump(mode="json"))
            or plan.global_policy_hash != hash_ref("active-policy", global_policy.model_dump(mode="json"))
            or plan.merged_policy_hash != policy_hash
        ):
            raise WorkflowError("paused coordinator bundle artifact identity mismatch")
        if persisted_capabilities != capabilities:
            raise WorkflowError("current host capabilities differ from the assessed restart bundle")
        if not assessment.safe or assessment.profile != capabilities.profile:
            raise WorkflowError("paused coordinator assessment or capability profile is not executable")
        if manifest.state != "paused_resource" or manifest.suspended_from is None:
            if manifest.state in {"verified", "failed", "abandoned", "rejected"}:
                raise WorkflowError("terminal coordinator run cannot be restarted")
            raise WorkflowError("only a paused_resource coordinator run can be reloaded")
        if type(next_operation_index) is not int or not 0 <= next_operation_index <= len(plan.operations):
            raise WorkflowError("paused coordinator next-operation index is invalid")
        bounded_ids = {item.operation_id for item in plan.operations if item.kind == "bounded_agent_task"}
        if (
            not isinstance(bounded_invocation_counts, dict)
            or not set(bounded_invocation_counts).issubset(bounded_ids)
            or any(type(value) is not int or value < 0 for value in bounded_invocation_counts.values())
        ):
            raise WorkflowError("paused coordinator bounded invocation ledger is invalid")
        expected_prefix = [item.operation_id for item in plan.operations[:next_operation_index]]
        if [item.operation_id for item in reports] != expected_prefix or any(not item.success for item in reports):
            raise WorkflowError("paused coordinator report prefix does not match the next-operation index")
        for operation, report in zip(plan.operations, reports):
            if set(report.expected_effect_ids_observed) != {item.effect_id for item in operation.effects} or report.unexpected_effects:
                raise WorkflowError("paused coordinator report evidence does not match the assessed effect inventory")
        if manifest.suspended_from in {"verifying", "repairing"} and next_operation_index != len(plan.operations):
            raise WorkflowError("post-execution pause is missing completed operation reports")
        if manifest.suspended_from == "verifying" and post_execution_snapshot is None:
            raise WorkflowError("verification pause is missing its observed product snapshot")
        if post_execution_snapshot is not None and (
            post_execution_snapshot.project_root != str(root)
            or post_execution_snapshot.control_plane_roots != [canonical_control]
        ):
            raise WorkflowError("paused coordinator product snapshot has the wrong project identity")
        if last_verification is not None and (
            last_verification.plan_hash != plan_hash or last_verification.assessment_hash != assessment_hash
        ):
            raise WorkflowError("paused coordinator verification report identity mismatch")
        audit = AuditLog(str(run_root), run_id)
        try:
            events = audit.validate_chain()
        except Exception as exc:
            raise WorkflowError("paused coordinator audit chain is invalid") from exc
        observed_head = events[-1].event_record_hash if events else None
        if observed_head != manifest.event_head_hash:
            raise WorkflowError("paused coordinator manifest does not bind the audit head")
        if not events or events[-1].payload.lifecycle_to != manifest.state:
            raise WorkflowError("paused coordinator manifest does not bind the audited lifecycle")
        expected_start_bindings = [
            f"low-level-plan:{plan_hash.value}",
            f"assessment:{assessment_hash.value}",
            f"active-policy:{policy_hash.value}",
            f"host-capabilities:{artifact_hash('host-capabilities', '1.0', capabilities.model_dump(mode='json'))}",
        ]
        if events[0].payload.event_type != "execution_started" or events[0].payload.evidence_ids != expected_start_bindings:
            raise WorkflowError("paused coordinator artifacts differ from the audited execution start")
        lifecycle = "approved"
        for event in events:
            if event.payload.lifecycle_from != lifecycle or event.payload.lifecycle_to is None:
                raise WorkflowError("paused coordinator audit lifecycle is discontinuous")
            lifecycle = event.payload.lifecycle_to
        cycle_starts = [
            index for index, event in enumerate(events)
            if event.payload.event_type in {"execution_started", "repair_started"}
        ]
        if not cycle_starts:
            raise WorkflowError("paused coordinator audit has no execution-cycle start")
        cycle_events = events[cycle_starts[-1] + 1:]
        operation_events = [
            event for event in cycle_events
            if event.payload.event_type in {"operation_completed", "operation_retained"}
        ]
        if len(operation_events) != len(reports):
            raise WorkflowError("paused coordinator report prefix is not committed to the audit chain")
        for report, event in zip(reports, operation_events):
            report_binding = f"execution-report:{artifact_hash('execution-report', '1.0', report.model_dump(mode='json'))}"
            if event.payload.operation_id != report.operation_id or event.payload.evidence_ids != [report_binding]:
                raise WorkflowError("paused coordinator report identity differs from its audit commitment")
        completed_events = [event for event in cycle_events if event.payload.event_type == "execution_completed"]
        if manifest.suspended_from in {"verifying", "repairing"}:
            if len(completed_events) != 1 or post_execution_snapshot is None:
                raise WorkflowError("post-execution pause has no unique audited product snapshot")
            snapshot_binding = f"repository-snapshot:{artifact_hash('repository-snapshot', '1.0', post_execution_snapshot.model_dump(mode='json'))}"
            if completed_events[0].payload.evidence_ids != [snapshot_binding]:
                raise WorkflowError("paused coordinator product snapshot differs from its audit commitment")
        if manifest.suspended_from == "repairing":
            failed_events = [event for event in cycle_events if event.payload.event_type == "verification_failed"]
            if len(failed_events) != 1 or last_verification is None:
                raise WorkflowError("repair pause has no unique audited verification report")
            verification_binding = f"verification-report:{artifact_hash('verification-report', '1.0', last_verification.model_dump(mode='json'))}"
            if failed_events[0].payload.evidence_ids != [verification_binding]:
                raise WorkflowError("paused coordinator verification report differs from its audit commitment")
        repair_events = [event for event in events if event.payload.event_type == "repair_started"]
        if len(repair_events) != len(repair_attempts):
            raise WorkflowError("repair-attempt history is not committed to the audit chain")
        for attempt, event in zip(repair_attempts, repair_events):
            binding = f"repair-attempt:{artifact_hash('repair-attempt', '1.0', attempt.model_dump(mode='json'))}"
            if event.payload.evidence_ids != [binding]:
                raise WorkflowError("repair-attempt identity differs from its audit commitment")
        if pending_repair_attempt is not None and (
            not repair_attempts or pending_repair_attempt != repair_attempts[-1]
        ):
            raise WorkflowError("pending repair strategy is not the latest audited attempt")

        self = cls.__new__(cls)
        self.plan = plan
        self.assessment = assessment
        self.global_policy = global_policy
        self.active_policy = active_policy
        self.capabilities = capabilities
        self.semantic_proposal = semantic_proposal
        self.agent_host = agent_host
        self.plan_hash = plan_hash
        self.assessment_hash = assessment_hash
        self.lease = None
        self.audit = audit
        self.run_root = run_root
        self.bundle_path = bundle_path
        self.manifest = manifest
        self.reports = reports
        self.next_operation_index = next_operation_index
        self.repair_attempts = repair_attempts
        self.bounded_invocation_counts = bounded_invocation_counts
        self.pending_repair_attempt = pending_repair_attempt
        self._persisted_bundle_hash = hashlib.sha256(persisted).hexdigest()
        self._closed = False
        self._verification_context = None
        self._verification_control_inventory = None
        self.last_verification = last_verification
        self.post_execution_snapshot = post_execution_snapshot
        self._control_root_identity = self._read_control_root_identity()
        current = self._capture()
        equal, differences = snapshot_materially_equal(self.plan.snapshot, current, self._declared_paths(current))
        if not equal:
            raise WorkflowError(f"paused coordinator repository state differs: {differences}")
        revalidation = assess_plan(
            self.plan,
            self.global_policy,
            self.active_policy,
            self.plan.snapshot,
            self.capabilities,
            self.semantic_proposal,
            self.assessment.approvals,
            prior_assessment_hash=self.assessment.prior_assessment_hash,
        )
        if revalidation != self.assessment:
            raise WorkflowError("paused coordinator reassessment does not reproduce the approved assessment")
        self._validate_approval_control_state()
        return self

    def _bundle_payload(self) -> dict[str, Any]:
        return {
            "schema_version": "1.0",
            "plan": self.plan.model_dump(mode="json"),
            "assessment": self.assessment.model_dump(mode="json"),
            "semantic_proposal": self.semantic_proposal.model_dump(mode="json"),
            "global_policy": self.global_policy.model_dump(mode="json"),
            "active_policy": self.active_policy.model_dump(mode="json"),
            "capabilities": self.capabilities.model_dump(mode="json"),
            "manifest": self.manifest.model_dump(mode="json"),
            "reports": [item.model_dump(mode="json") for item in self.reports],
            "next_operation_index": self.next_operation_index,
            "repair_attempts": [item.model_dump(mode="json") for item in self.repair_attempts],
            "bounded_invocation_counts": dict(sorted(self.bounded_invocation_counts.items())),
            "pending_repair_attempt": None if self.pending_repair_attempt is None else self.pending_repair_attempt.model_dump(mode="json"),
            "last_verification": None if self.last_verification is None else self.last_verification.model_dump(mode="json"),
            "post_execution_snapshot": None if self.post_execution_snapshot is None else self.post_execution_snapshot.model_dump(mode="json"),
        }

    def _persist_bundle(self) -> None:
        self._validate_approval_control_state()
        data = canonical_bytes(self._bundle_payload()) + b"\n"
        if self.bundle_path.exists():
            existing = self.bundle_path.read_bytes()
            if self._persisted_bundle_hash is None or hashlib.sha256(existing).hexdigest() != self._persisted_bundle_hash:
                raise WorkflowError("coordinator bundle changed outside the live coordinator")
        descriptor, temporary = tempfile.mkstemp(prefix=".coordinator-", suffix=".tmp", dir=self.run_root)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.bundle_path)
            self._persisted_bundle_hash = hashlib.sha256(data).hexdigest()
            directory = os.open(self.run_root, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass

    def _validate_internal_artifacts(self) -> None:
        plan = _boundary_copy(self.plan, LowLevelPlan)
        assessment = _boundary_copy(self.assessment, Assessment)
        global_policy = _boundary_copy(self.global_policy, ActivePolicy)
        active_policy = _boundary_copy(self.active_policy, ActivePolicy)
        capabilities = _boundary_copy(self.capabilities, HostCapabilities)
        manifest = _boundary_copy(self.manifest, RunManifest)
        reports = TypeAdapter(list[ExecutionReport]).validate_python(parse_json_strict(canonical_bytes([
            item.model_dump(mode="json") for item in self.reports
        ])))
        repair_attempts = TypeAdapter(list[RepairAttempt]).validate_python(parse_json_strict(canonical_bytes([
            item.model_dump(mode="json") for item in self.repair_attempts
        ])))
        if hash_ref("low-level-plan", plan.model_dump(mode="json")) != self.plan_hash:
            raise WorkflowError("live coordinator plan changed after construction")
        if hash_ref("assessment", assessment.model_dump(mode="json")) != self.assessment_hash:
            raise WorkflowError("live coordinator assessment changed after construction")
        if assessment.plan_hash != self.plan_hash or assessment.policy_hash != hash_ref("active-policy", active_policy.model_dump(mode="json")):
            raise WorkflowError("live coordinator artifact identities no longer agree")
        if plan.global_policy_hash != hash_ref("active-policy", global_policy.model_dump(mode="json")):
            raise WorkflowError("live coordinator global policy identity changed")
        if manifest.plan_hash != self.plan_hash or manifest.assessment_hash != self.assessment_hash:
            raise WorkflowError("live coordinator manifest identity changed")
        self.plan, self.assessment = plan, assessment
        self.global_policy, self.active_policy, self.capabilities = global_policy, active_policy, capabilities
        self.manifest, self.reports, self.repair_attempts = manifest, reports, repair_attempts
        if self.pending_repair_attempt is not None:
            self.pending_repair_attempt = _boundary_copy(self.pending_repair_attempt, RepairAttempt)
        if self.last_verification is not None:
            self.last_verification = _boundary_copy(self.last_verification, VerificationReport)
        if self.post_execution_snapshot is not None:
            self.post_execution_snapshot = _boundary_copy(self.post_execution_snapshot, RepositorySnapshot)

    def _validate_live_control_state(self) -> None:
        self._validate_internal_artifacts()
        self._assert_control_root_identity()
        try:
            events = self.audit.validate_chain()
            observed_head = events[-1].event_record_hash if events else None
            if observed_head != self.manifest.event_head_hash:
                raise ControlStateDrift("live audit head differs from the manifest")
            if self.bundle_path.exists():
                current_hash = hashlib.sha256(self.bundle_path.read_bytes()).hexdigest()
                if self._persisted_bundle_hash is None or current_hash != self._persisted_bundle_hash:
                    raise ControlStateDrift("coordinator bundle changed outside the live coordinator")
            self._validate_approval_control_state()
        except ControlStateDrift:
            raise
        except Exception:
            raise ControlStateDrift("protected control-plane state failed identity validation") from None

    def _read_control_root_identity(self) -> tuple[int, int, int]:
        control = Path(self.plan.snapshot.control_plane_roots[0])
        if control.is_symlink() or not control.is_dir():
            raise ControlStateDrift("canonical control root is missing, non-directory, or a symbolic link")
        observed = control.lstat()
        return observed.st_dev, observed.st_ino, observed.st_mode

    def _assert_control_root_identity(self) -> None:
        if self._read_control_root_identity() != self._control_root_identity:
            raise ControlStateDrift("canonical control root identity changed")

    def _stop_after_control_drift(self) -> None:
        try:
            self.manifest = transition(self.manifest, "human_required", ["control-state-drift-unrecorded"])
        except Exception:
            pass
        if self.lease is not None:
            try:
                self._assert_control_root_identity()
                release_lease(self.lease)
            except Exception:
                pass
            self.lease = None
        self._closed = True

    def _control_inventory(self) -> dict[str, str]:
        self._assert_control_root_identity()
        control = Path(self.plan.snapshot.control_plane_roots[0])
        inventory: dict[str, str] = {}
        for path in sorted(control.rglob("*")):
            relative = path.relative_to(control).as_posix()
            stat = path.lstat()
            metadata = {
                "mode": stat.st_mode,
                "uid": stat.st_uid,
                "gid": stat.st_gid,
                "device": stat.st_dev,
                "inode": stat.st_ino,
                "links": stat.st_nlink,
            }
            if path.is_symlink():
                metadata["kind"] = "symlink"
                metadata["target"] = os.readlink(path)
            elif path.is_file():
                metadata["kind"] = "file"
                metadata["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
            elif path.is_dir():
                metadata["kind"] = "directory"
            else:
                metadata["kind"] = "other"
            inventory[relative] = artifact_hash("control-entry", "1.0", metadata)
        return inventory

    def _capture(self) -> RepositorySnapshot:
        instruction_paths = sorted(discover_instruction_files(
            self.plan.snapshot.project_root, _plan_instruction_targets(self.plan)
        ))
        return capture_snapshot(
            self.plan.snapshot.project_root,
            list(self.plan.snapshot.selected_file_hashes),
            instruction_paths,
            self.plan.snapshot.expected_product_changes,
            self.plan.snapshot.control_plane_roots,
        )

    def _append_event(
        self,
        event_type: str,
        lifecycle_from: str,
        lifecycle_to: str,
        summary: str,
        *,
        operation_id: str | None = None,
        evidence_ids: list[str] | None = None,
    ) -> None:
        self._assert_control_root_identity()
        event = self.audit.append(
            EventPayload(
                event_type=event_type, lifecycle_from=lifecycle_from, lifecycle_to=lifecycle_to,
                operation_id=operation_id, summary=summary,
                evidence_ids=evidence_ids or [f"coordinator:{event_type}"],
            ),
            "coordinator_observed",
            {"status": event_type, "run_id": self.plan.run_id},
        )
        self.manifest = self.manifest.model_copy(update={"event_head_hash": event.event_record_hash})

    def _declared_paths(self, current_snapshot: RepositorySnapshot | None = None) -> set[str]:
        declared: set[str] = set()
        completed = {report.operation_id for report in self.reports if report.success}
        for operation in self.plan.operations:
            if operation.operation_id not in completed or operation.kind != "exact_action":
                continue
            if operation.adapter == "apply_patch":
                declared.update(operation.expected_created_paths)
                declared.update(operation.expected_modified_paths)
                declared.update(operation.expected_deleted_paths)
            if operation.adapter == "check":
                declared.update(operation.declared_generated_paths)
        if current_snapshot is not None:
            root = Path(self.plan.snapshot.project_root)
            for index, operation in enumerate(self.plan.operations):
                repair_target = self.pending_repair_attempt is not None and index >= self.next_operation_index
                if (operation.operation_id not in completed and not repair_target) or operation.kind != "bounded_agent_task":
                    continue
                candidates = [
                    (path, operation.path_contract.create_roots)
                    for path in current_snapshot.untracked_paths
                ]
                candidates.extend(
                    (path, operation.path_contract.create_roots + operation.path_contract.modify_roots + operation.path_contract.delete_roots)
                    for mapping in (current_snapshot.staged_paths, current_snapshot.unstaged_paths)
                    for path in mapping
                )
                changed_inventory = {
                    path
                    for path in set(self.plan.snapshot.full_file_inventory) | set(current_snapshot.full_file_inventory)
                    if self.plan.snapshot.full_file_inventory.get(path) != current_snapshot.full_file_inventory.get(path)
                }
                candidates.extend(
                    (path.rstrip("/"), operation.path_contract.create_roots + operation.path_contract.modify_roots + operation.path_contract.delete_roots)
                    for path in changed_inventory
                )
                for path_value, allowed_roots in candidates:
                    candidate = Path(path_value)
                    if not candidate.is_absolute():
                        candidate = root / candidate
                    try:
                        resolved = resolve_contained(
                            str(candidate), allowed_roots, operation.path_contract.protected_roots, mutation=True
                        )
                    except Exception:
                        continue
                    declared.add(resolved.resolved)
        return declared

    def _required_approval_bindings(self, operation: Any) -> list[tuple[Any, str, str]]:
        required: list[tuple[Any, str, str]] = []
        for effect in operation.effects:
            classes = _required_effect_approval_classes(operation, effect, self.active_policy)
            required.extend(
                (effect, approval_class, target)
                for approval_class in sorted(classes)
                for target in sorted(effect.targets)
            )
        return required

    def _selected_operation_approvals(self, operation: Any, *, require_current: bool = True) -> list[tuple[Any, Any, str, str]]:
        now = datetime.now(timezone.utc)
        operation_hash = hash_ref("operation", operation.model_dump(mode="json"))
        selected: list[tuple[Any, Any, str, str]] = []
        for effect, approval_class, target in self._required_approval_bindings(operation):
            idempotency_required = (
                effect.exposure in {"project_external", "multi_party", "systemic"}
                or effect.reversibility in {"uncertain", "none"}
                or effect.effect_class == "external_write"
            )
            matches = []
            for approval in self.assessment.approvals:
                expiry_valid = True
                if approval.expires_at is not None:
                    expiry = datetime.strptime(approval.expires_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                    expiry_valid = expiry > now
                if (
                    approval.plan_hash == self.plan_hash
                    and approval.operation_hash == operation_hash
                    and approval.policy_hash == self.assessment.policy_hash
                    and approval.snapshot_hash == self.assessment.snapshot_hash
                    and approval.effect_id == effect.effect_id
                    and approval.effect_class == effect.effect_class
                    and approval.approval_class == approval_class
                    and approval.target == target
                    and not approval.consumed
                    and (expiry_valid or not require_current)
                    and (not idempotency_required or bool(approval.idempotency_key))
                ):
                    matches.append(approval)
            if len(matches) != 1:
                raise WorkflowError("required approval binding is missing, stale, or ambiguous before execution")
            selected.append((matches[0], effect, approval_class, target))
        if len({item[0].approval_id for item in selected}) != len(selected):
            raise WorkflowError("one approval identity cannot authorize multiple exact bindings")
        return selected

    def _approval_receipt(self, approval: Any, operation: Any, effect: Any, approval_class: str, target: str) -> dict[str, Any]:
        return {
            "approval_id": approval.approval_id,
            "plan_hash": self.plan_hash.value,
            "operation_hash": hash_ref("operation", operation.model_dump(mode="json")).value,
            "policy_hash": self.assessment.policy_hash.value,
            "snapshot_hash": self.assessment.snapshot_hash.value,
            "effect_id": effect.effect_id,
            "effect_class": effect.effect_class,
            "approval_class": approval_class,
            "target": target,
            "idempotency_key_hash": (
                None if approval.idempotency_key is None
                else hashlib.sha256(approval.idempotency_key.encode("utf-8")).hexdigest()
            ),
        }

    def _approval_root(self, *, create: bool) -> Path:
        self._assert_control_root_identity()
        control = Path(self.plan.snapshot.control_plane_roots[0])
        approvals = _safe_control_directory(control, "approvals", create=create)
        run_root = _safe_control_directory(approvals, self.plan.run_id, create=create) if approvals.exists() else approvals / self.plan.run_id
        return run_root

    def _consume_operation_approvals(self, operation: Any) -> None:
        self._validate_approval_control_state()
        relevant = self._selected_operation_approvals(operation)
        root = self._approval_root(create=True)
        for approval, effect, approval_class, approval_target in relevant:
            target = root / f"{approval.approval_id}.consumed"
            payload = self._approval_receipt(approval, operation, effect, approval_class, approval_target)
            descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "wb") as handle:
                from .canonical import canonical_bytes

                handle.write(canonical_bytes(payload) + b"\n")
                handle.flush()
                os.fsync(handle.fileno())

    def _validate_approval_control_state(self) -> None:
        root = self._approval_root(create=False)
        expected_approval_ids: set[str] = set()
        for operation_index, operation in enumerate(self.plan.operations):
            expected_consumed = operation_index < self.next_operation_index
            for approval, effect, approval_class, approval_target in self._selected_operation_approvals(
                operation, require_current=not expected_consumed
            ):
                expected_approval_ids.add(approval.approval_id)
                target = root / f"{approval.approval_id}.consumed"
                if target.is_symlink():
                    raise WorkflowError("approval consumption record must not be a symbolic link")
                if target.exists() != expected_consumed:
                    raise WorkflowError("approval consumption record disagrees with the committed operation prefix")
                if expected_consumed:
                    expected = canonical_bytes(self._approval_receipt(approval, operation, effect, approval_class, approval_target)) + b"\n"
                    if not target.is_file() or target.read_bytes() != expected:
                        raise WorkflowError("approval consumption record identity mismatch")
        if root.exists():
            observed = {path.name.removesuffix(".consumed") for path in root.glob("*.consumed")}
            if not observed.issubset(expected_approval_ids):
                raise WorkflowError("approval control state contains an unbound consumption record")

    def _heartbeat(self) -> None:
        if self.lease is None:
            raise WorkflowError("coordinator does not hold the project lease")
        heartbeat_lease(self.lease)

    def _bounded_packet(self, operation: Any) -> dict[str, Any]:
        packet = {
            "operation": operation.model_dump(mode="json"),
            "evidence": [
                item.model_dump(mode="json")
                for item in self.plan.evidence
                if item.evidence_id in operation.evidence_ids
            ],
        }
        if self.pending_repair_attempt is not None:
            finding = None
            if self.last_verification is not None:
                finding = next(
                    (item for item in self.last_verification.findings if item.finding_id == self.pending_repair_attempt.finding_id),
                    None,
                )
            packet["repair_context"] = {
                "attempt_id": self.pending_repair_attempt.attempt_id,
                "finding_id": self.pending_repair_attempt.finding_id,
                "strategy_code": self.pending_repair_attempt.strategy_code,
                "finding": None if finding is None else {
                    "invariant_id": finding.invariant_id,
                    "category": finding.category,
                    "severity": finding.severity,
                    "operation_ids": finding.operation_ids,
                    "effect_ids": finding.effect_ids,
                    "evidence_ids": finding.evidence_ids,
                },
            }
        return packet

    def _preflight_operation_resources(self, operation: Any, packet: dict[str, Any] | None) -> None:
        limits = operation.resource_limits
        if limits.max_calls < 1:
            raise WorkflowError(f"immutable max_calls ceiling forbids operation {operation.operation_id}; reassessment required")
        if operation.kind == "bounded_agent_task":
            used = self.bounded_invocation_counts.get(operation.operation_id, 0)
            if isinstance(limits.attempt_limit, int) and used >= limits.attempt_limit:
                raise WorkflowError(f"immutable attempt_limit exhausted for {operation.operation_id}; reassessment required")
            if packet is None or len(canonical_bytes(packet)) > limits.max_bytes:
                raise WorkflowError(f"serialized protocol packet exceeds max_bytes for {operation.operation_id}; reassessment required")
        elif operation.adapter == "read_file" and operation.byte_end - operation.byte_start > limits.max_bytes:
            raise WorkflowError(f"read range exceeds immutable max_bytes for {operation.operation_id}; reassessment required")
        elif operation.adapter == "apply_patch" and len(operation.patch.encode("utf-8")) > limits.max_bytes:
            raise WorkflowError(f"patch exceeds immutable max_bytes for {operation.operation_id}; reassessment required")

    def execute(self) -> list[ExecutionReport]:
        if self.manifest.state != "executing" or self._closed:
            raise WorkflowError("coordinator is not in an executable state")
        try:
            self._validate_live_control_state()
        except ControlStateDrift:
            self._stop_after_control_drift()
            raise
        mutation_dispatched = False
        try:
            for operation_index in range(self.next_operation_index, len(self.plan.operations)):
                operation = self.plan.operations[operation_index]
                current = self._capture()
                equal, differences = snapshot_materially_equal(self.plan.snapshot, current, self._declared_paths(current))
                if not equal:
                    raise WorkflowError(f"repository changed before operation {operation.operation_id}: {differences}")
                self._heartbeat()
                packet = self._bounded_packet(operation) if operation.kind == "bounded_agent_task" else None
                self._preflight_operation_resources(operation, packet)
                self._consume_operation_approvals(operation)
                control_before_dispatch = self._control_inventory()
                mutation_dispatched = True
                if operation.kind == "bounded_agent_task":
                    if self.agent_host is None:
                        raise WorkflowError("bounded tasks require an explicit fresh executor host")
                    self.bounded_invocation_counts[operation.operation_id] = self.bounded_invocation_counts.get(operation.operation_id, 0) + 1
                    started = time.monotonic()
                    raw_report = self.agent_host.invoke("executor", packet)
                    elapsed = time.monotonic() - started
                    if elapsed > operation.resource_limits.max_seconds:
                        raise ResourcePause(f"resource-max-seconds-{operation.operation_id}")
                    if len(canonical_bytes(raw_report)) + len(canonical_bytes(packet)) > operation.resource_limits.max_bytes:
                        raise WorkflowError("bounded executor exceeded the serialized byte ceiling")
                    try:
                        report = _sanitize_execution_report(ExecutionReport.model_validate(raw_report))
                    except (ValidationError, ValueError, TypeError):
                        raise WorkflowError("bounded executor response failed typed validation") from None
                    expected_effects = {effect.effect_id for effect in operation.effects}
                    if report.operation_id != operation.operation_id:
                        raise WorkflowError("bounded executor report operation identity mismatch")
                    if not report.success or report.unexpected_effects:
                        raise WorkflowError("bounded executor reported failure or unexpected effects")
                    if set(report.expected_effect_ids_observed) != expected_effects:
                        raise WorkflowError("bounded executor report effect inventory mismatch")
                    report_evidence_ids = {item.evidence_id for item in report.evidence}
                    if not set(operation.completion_evidence).issubset(report_evidence_ids):
                        raise WorkflowError("bounded executor report lacks required completion evidence")
                    self.reports.append(report)
                else:
                    self.reports.extend(_execute_exact_actions(self.plan, self.assessment, [operation]))
                if self._control_inventory() != control_before_dispatch:
                    raise ControlStateDrift("executor or subprocess changed protected control-plane state")
                after = self._capture()
                equal, differences = snapshot_materially_equal(self.plan.snapshot, after, self._declared_paths(after))
                if not equal:
                    raise WorkflowError(f"operation {operation.operation_id} produced undeclared repository changes: {differences}")
                self.next_operation_index = operation_index + 1
                report = self.reports[operation_index]
                self._append_event(
                    "operation_completed", "executing", "executing",
                    "operation completed with an assessed effect report",
                    operation_id=operation.operation_id,
                    evidence_ids=[f"execution-report:{artifact_hash('execution-report', '1.0', report.model_dump(mode='json'))}"],
                )
                self._persist_bundle()
                mutation_dispatched = False
        except ControlStateDrift:
            self._stop_after_control_drift()
            raise
        except ResourcePause as exc:
            if not mutation_dispatched:
                self.pause_resource(exc.evidence_id)
            else:
                try:
                    self._append_event(
                        "execution_stopped", "executing", "human_required",
                        "resource boundary occurred after mutation dispatch; outcome is indeterminate",
                    )
                    self.manifest = transition(self.manifest, "human_required", ["audit:execution_stopped"])
                    self._persist_bundle()
                finally:
                    if self.lease is not None:
                        release_lease(self.lease)
                        self.lease = None
                    self._closed = True
            raise
        except Exception as exc:
            try:
                self._append_event("execution_stopped", "executing", "human_required", "execution stopped at a failed preflight, operation, or observation gate")
                self.manifest = transition(self.manifest, "human_required", ["audit:execution_stopped"])
                self._persist_bundle()
            finally:
                if self.lease is not None:
                    release_lease(self.lease)
                    self.lease = None
                self._closed = True
            raise
        self.pending_repair_attempt = None
        self.post_execution_snapshot = self._capture()
        self._append_event(
            "execution_completed", "executing", "verifying", "all assessed operations reported completion",
            evidence_ids=[f"repository-snapshot:{artifact_hash('repository-snapshot', '1.0', self.post_execution_snapshot.model_dump(mode='json'))}"],
        )
        self.manifest = transition(self.manifest, "verifying", ["audit:execution_completed"])
        self._persist_bundle()
        return list(self.reports)

    def open_verification(self, context_id: str) -> VerificationContext:
        if self.manifest.state != "verifying" or self._closed:
            raise WorkflowError("verification context requires completed execution")
        self._validate_live_control_state()
        self._heartbeat()
        current = self._capture()
        if self.post_execution_snapshot is None:
            raise WorkflowError("verification requires a coordinator-observed post-execution snapshot")
        equal, differences = snapshot_materially_equal(self.post_execution_snapshot, current)
        if not equal:
            raise WorkflowError(f"repository changed before verifier handoff: {differences}")
        self._verification_context = begin_verification_context(
            self.plan, self.assessment, context_id, current
        )
        self._verification_control_inventory = self._control_inventory()
        return self._verification_context

    def verify(self, proposal: VerificationProposal, context: VerificationContext) -> VerificationReport:
        try:
            proposal = _boundary_copy(proposal, VerificationProposal)
            if context is not self._verification_context:
                raise WorkflowError("verification context was not opened by this coordinator")
            if self._verification_control_inventory is None or self._control_inventory() != self._verification_control_inventory:
                raise ControlStateDrift("verifier changed protected control-plane state")
            self._validate_live_control_state()
            current = self._capture()
            if self.post_execution_snapshot is None:
                raise WorkflowError("verification requires a coordinator-observed post-execution snapshot")
            equal, differences = snapshot_materially_equal(self.post_execution_snapshot, current)
            if not equal:
                raise WorkflowError(f"repository changed during verification: {differences}")
            if context.snapshot_hash != hash_ref("repository-snapshot", current.model_dump(mode="json")):
                raise WorkflowError("verification context snapshot identity is stale")
            report = verify_reports(self.plan, self.assessment, self.reports, proposal, context)
        except ControlStateDrift:
            self._stop_after_control_drift()
            raise
        except Exception as exc:
            try:
                self._append_event(
                    "verification_stopped", "verifying", "human_required",
                    "verification stopped at an identity, control-state, or evidence gate",
                )
                self.manifest = transition(self.manifest, "human_required", ["audit:verification_stopped"])
                self._persist_bundle()
            finally:
                if self.lease is not None:
                    try:
                        release_lease(self.lease)
                        self.lease = None
                    except Exception:
                        pass
                self._closed = True
            if isinstance(exc, ValidationError):
                raise WorkflowError("verification proposal failed typed validation") from None
            raise
        self.last_verification = report
        report_binding = f"verification-report:{artifact_hash('verification-report', '1.0', report.model_dump(mode='json'))}"
        if report.verified:
            self._append_event(
                "verification_completed", "verifying", "verified",
                "fresh verifier proposal satisfied every declared gate", evidence_ids=[report_binding],
            )
            self.manifest = transition(self.manifest, "verified", ["audit:verification_completed"])
            try:
                self._persist_bundle()
            finally:
                if self.lease is not None:
                    release_lease(self.lease)
                    self.lease = None
                self._closed = True
        else:
            self._append_event(
                "verification_failed", "verifying", "repairing",
                "verification found an unmet or conflicting gate", evidence_ids=[report_binding],
            )
            self.manifest = transition(self.manifest, "repairing", ["audit:verification_failed"])
            self._persist_bundle()
        return report

    def resume_repair(self, attempt: RepairAttempt) -> None:
        attempt = _sanitize_repair_attempt(_boundary_copy(attempt, RepairAttempt))
        if self.manifest.state != "repairing" or self._closed or self.last_verification is None:
            raise WorkflowError("repair resume requires a live failed-verification state")
        self._validate_live_control_state()
        findings = {finding.finding_id: finding for finding in self.last_verification.findings}
        if attempt.finding_id not in findings:
            raise WorkflowError("repair attempt does not name a current verifier finding")
        if attempt.attempt_id in {item.attempt_id for item in self.repair_attempts}:
            raise WorkflowError("repair attempt identity was already used")
        if attempt.high_risk_replay:
            raise WorkflowError("high-risk replay requires a newly assessed approval bundle")
        for operation in self.plan.operations:
            for effect in operation.effects:
                if _effect_requires_review(effect) or effect.approval_class in self.active_policy.required_approvals:
                    raise WorkflowError("approval-gated operation cannot replay without reassessment")
        operation_ids = set(findings[attempt.finding_id].operation_ids)
        repair_indexes = [
            index for index, operation in enumerate(self.plan.operations)
            if operation.operation_id in operation_ids
        ]
        if not repair_indexes:
            raise WorkflowError("repair finding does not identify an in-plan operation")
        restart_index = min(repair_indexes)
        retained_reports = self.reports[:restart_index]
        self._heartbeat()
        self.repair_attempts.append(attempt)
        self.pending_repair_attempt = attempt
        self._append_event(
            "repair_started", "repairing", "executing", "materially different in-envelope repair strategy accepted",
            evidence_ids=[f"repair-attempt:{artifact_hash('repair-attempt', '1.0', attempt.model_dump(mode='json'))}"],
        )
        self.manifest = transition(self.manifest, "executing", ["audit:repair_started"])
        self.reports = retained_reports
        self.next_operation_index = restart_index
        for report in retained_reports:
            self._append_event(
                "operation_retained", "executing", "executing",
                "unaffected completed operation retained for the bounded repair cycle",
                operation_id=report.operation_id,
                evidence_ids=[f"execution-report:{artifact_hash('execution-report', '1.0', report.model_dump(mode='json'))}"],
            )
        self._verification_context = None
        self.post_execution_snapshot = None
        self._persist_bundle()

    def pause_resource(self, evidence_id: str) -> None:
        if self.manifest.state not in {"executing", "verifying", "repairing"} or self._closed:
            raise WorkflowError("resource pause requires a live active run")
        self._validate_live_control_state()
        prior = self.manifest.state
        self._append_event("resource_paused", prior, "paused_resource", "host resource boundary reached at a safe stop point")
        self.manifest = transition(self.manifest, "paused_resource", [evidence_id])
        self._verification_context = None
        try:
            self._persist_bundle()
        finally:
            if self.lease is not None:
                release_lease(self.lease)
                self.lease = None

    def resume_after_pause(self, evidence_id: str) -> None:
        if self.manifest.state != "paused_resource" or self.manifest.suspended_from is None or self._closed:
            raise WorkflowError("resume requires a paused_resource run")
        self._validate_live_control_state()
        self.audit.validate_chain()
        current = self._capture()
        equal, differences = snapshot_materially_equal(self.plan.snapshot, current, self._declared_paths(current))
        if not equal:
            raise WorkflowError(f"resume snapshot differs from the approved operation sequence: {differences}")
        if self.assessment.plan_hash != self.plan_hash:
            raise WorkflowError("resume plan identity mismatch")
        if self.assessment.policy_hash != hash_ref("active-policy", self.active_policy.model_dump(mode="json")):
            raise WorkflowError("resume policy identity mismatch")
        target = self.manifest.suspended_from
        self.lease = acquire_lease(
            self.plan.snapshot.project_root,
            self.plan.run_id,
            self.plan.snapshot.device_identity,
            self.manifest.event_head_hash,
        )
        try:
            self._append_event("resource_resumed", "paused_resource", target, "event chain and artifact identities revalidated")
            self.manifest = transition(self.manifest, target, [evidence_id], resumed_state=target)
            self._persist_bundle()
        except Exception:
            release_lease(self.lease)
            self.lease = None
            raise

    def abandon(self) -> None:
        if self._closed:
            return
        self._validate_live_control_state()
        target = "abandoned"
        self._append_event("execution_abandoned", self.manifest.state, target, "coordinator closed without verification")
        self.manifest = transition(self.manifest, target, ["audit:execution_abandoned"])
        try:
            self._persist_bundle()
        finally:
            if self.lease is not None:
                release_lease(self.lease)
                self.lease = None
            self._closed = True


def _apply_patch(operation: Any) -> None:
    patch_bytes = operation.patch.encode("utf-8")
    if hashlib.sha256(patch_bytes).hexdigest() != operation.patch_hash:
        raise WorkflowError("patch hash mismatch")
    observed_created, observed_modified, observed_deleted = _patch_paths(operation.patch)
    cwd_path = Path(operation.path_contract.working_directories[0]).resolve(strict=True)
    observed_created = {str((cwd_path / value).resolve(strict=False)) for value in observed_created}
    observed_modified = {str((cwd_path / value).resolve(strict=False)) for value in observed_modified}
    observed_deleted = {str((cwd_path / value).resolve(strict=False)) for value in observed_deleted}
    if observed_created != set(operation.expected_created_paths) or observed_modified != set(operation.expected_modified_paths) or observed_deleted != set(operation.expected_deleted_paths):
        raise WorkflowError("patch target inventory differs from assessed paths")
    for path_value, expected_hash in operation.preimage_hashes.items():
        resolved = resolve_contained(path_value, operation.path_contract.modify_roots + operation.path_contract.delete_roots, operation.path_contract.protected_roots, mutation=True)
        if hashlib.sha256(Path(resolved.resolved).read_bytes()).hexdigest() != expected_hash:
            raise WorkflowError(f"patch preimage mismatch: {path_value}")
    for path_value in operation.expected_created_paths:
        resolve_contained(path_value, operation.path_contract.create_roots, operation.path_contract.protected_roots, mutation=True)
    for path_value in operation.expected_modified_paths:
        resolve_contained(path_value, operation.path_contract.modify_roots, operation.path_contract.protected_roots, mutation=True)
    for path_value in operation.expected_deleted_paths:
        resolve_contained(path_value, operation.path_contract.delete_roots, operation.path_contract.protected_roots, mutation=True)
    prepared = _prepare_text_patch(operation.patch, cwd_path)
    expected_actions = {
        **{path: "create" for path in operation.expected_created_paths},
        **{path: "modify" for path in operation.expected_modified_paths},
        **{path: "delete" for path in operation.expected_deleted_paths},
    }
    if {str(item.path): item.action for item in prepared} != expected_actions:
        raise WorkflowError("prepared patch actions differ from assessed path inventory")
    _commit_text_patch(prepared, operation.preimage_hashes)


@dataclass(frozen=True)
class _PreparedPatch:
    path: Path
    action: str
    content: bytes
    original_mode: int | None


def _prepare_text_patch(patch: str, cwd: Path) -> list[_PreparedPatch]:
    lines = patch.splitlines(keepends=True)
    prepared: list[_PreparedPatch] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.startswith("diff --git ") or line.startswith("index ") or not line.strip():
            index += 1
            continue
        if not line.startswith("--- ") or index + 1 >= len(lines) or not lines[index + 1].startswith("+++ "):
            raise WorkflowError("patch contains unsupported metadata or malformed file headers")
        old_name = line[4:].strip()
        new_name = lines[index + 1][4:].strip()
        old_relative = None if old_name == "/dev/null" else re.sub(r"^a/", "", old_name)
        new_relative = None if new_name == "/dev/null" else re.sub(r"^b/", "", new_name)
        relative = new_relative or old_relative
        if relative is None:
            raise WorkflowError("patch file header cannot use /dev/null on both sides")
        path = (cwd / relative).resolve(strict=False)
        action = "create" if old_relative is None else "delete" if new_relative is None else "modify"
        if action == "create":
            if path.exists() or path.is_symlink():
                raise WorkflowError(f"patch create target already exists: {path}")
            original_lines: list[str] = []
            original_mode = None
        else:
            if not path.is_file() or path.is_symlink():
                raise WorkflowError(f"patch source is missing, non-file, or a symlink: {path}")
            try:
                original_lines = path.read_bytes().decode("utf-8").splitlines(keepends=True)
            except UnicodeDecodeError as exc:
                raise WorkflowError(f"exact patch supports UTF-8 text only: {path}") from exc
            original_mode = path.stat().st_mode & 0o777
        output: list[str] = []
        source_index = 0
        index += 2
        saw_hunk = False
        while index < len(lines) and not lines[index].startswith(("diff --git ", "--- ")):
            header = lines[index]
            if header.startswith("index ") or not header.strip():
                index += 1
                continue
            match = re.match(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", header)
            if not match:
                raise WorkflowError("patch contains unsupported metadata or malformed hunk header")
            saw_hunk = True
            old_start = int(match.group(1))
            old_count = int(match.group(2) or "1")
            new_count = int(match.group(4) or "1")
            hunk_source = 0 if old_start == 0 else old_start - 1
            if hunk_source < source_index or hunk_source > len(original_lines):
                raise WorkflowError("patch hunk source range is invalid or overlaps")
            output.extend(original_lines[source_index:hunk_source])
            source_index = hunk_source
            index += 1
            observed_old = 0
            observed_new = 0
            while index < len(lines) and not lines[index].startswith(("@@ ", "diff --git ", "--- ")):
                item = lines[index]
                if item.startswith("\\ No newline at end of file"):
                    if not output:
                        raise WorkflowError("no-newline marker has no preceding patch line")
                    output[-1] = output[-1].rstrip("\r\n")
                    index += 1
                    continue
                if not item or item[0] not in {" ", "+", "-"}:
                    raise WorkflowError("patch hunk contains an unsupported line")
                content = item[1:]
                if item[0] in {" ", "-"}:
                    if source_index >= len(original_lines) or original_lines[source_index] != content:
                        raise WorkflowError("patch preimage text differs from the current file")
                    source_index += 1
                    observed_old += 1
                if item[0] in {" ", "+"}:
                    output.append(content)
                    observed_new += 1
                index += 1
            if observed_old != old_count or observed_new != new_count:
                raise WorkflowError("patch hunk line counts differ from its header")
        if not saw_hunk:
            raise WorkflowError("patch file has no hunks")
        output.extend(original_lines[source_index:])
        content = "".join(output).encode("utf-8")
        if action == "delete" and content:
            raise WorkflowError("delete patch did not remove the complete file")
        prepared.append(_PreparedPatch(path=path, action=action, content=content, original_mode=original_mode))
    if not prepared:
        raise WorkflowError("patch contains no files")
    return prepared


def _commit_text_patch(prepared: list[_PreparedPatch], preimage_hashes: dict[str, str]) -> None:
    staged: list[tuple[_PreparedPatch, Path]] = []
    try:
        for item in prepared:
            if item.action == "delete":
                continue
            descriptor, temp_name = tempfile.mkstemp(prefix=".rb-safe-patch-", dir=item.path.parent)
            temporary = Path(temp_name)
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(item.content)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temporary, item.original_mode if item.original_mode is not None else 0o600)
            staged.append((item, temporary))
        for item, temporary in staged:
            if item.action == "modify":
                expected = preimage_hashes[str(item.path)]
                if hashlib.sha256(item.path.read_bytes()).hexdigest() != expected:
                    raise WorkflowError(f"patch preimage changed before commit: {item.path}")
                os.replace(temporary, item.path)
            else:
                try:
                    os.link(temporary, item.path)
                except FileExistsError as exc:
                    raise WorkflowError(f"patch create target appeared before commit: {item.path}") from exc
                temporary.unlink()
        for item in prepared:
            if item.action != "delete":
                continue
            expected = preimage_hashes[str(item.path)]
            if hashlib.sha256(item.path.read_bytes()).hexdigest() != expected:
                raise WorkflowError(f"patch delete preimage changed before commit: {item.path}")
            item.path.unlink()
    finally:
        for _, temporary in staged:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass


def _patch_paths(patch: str) -> tuple[set[str], set[str], set[str]]:
    forbidden_metadata = (
        "GIT binary patch", "Binary files ", "old mode ", "new mode ", "new file mode ",
        "deleted file mode ", "similarity index ", "dissimilarity index ", "rename from ",
        "rename to ", "copy from ", "copy to ", "diff --cc ", "diff --combined ",
    )
    if any(line.startswith(forbidden_metadata) for line in patch.splitlines()):
        raise WorkflowError("patch contains unmodelled binary, mode, link, rename, copy, or combined-diff metadata")
    old_paths = re.findall(r"^--- (?:a/)?(.+)$", patch, flags=re.MULTILINE)
    new_paths = re.findall(r"^\+\+\+ (?:b/)?(.+)$", patch, flags=re.MULTILINE)
    if len(old_paths) != len(new_paths) or not old_paths:
        raise WorkflowError("patch must be a standard unified diff")
    created: set[str] = set()
    modified: set[str] = set()
    deleted: set[str] = set()
    seen_targets: dict[str, str] = {}
    for old, new in zip(old_paths, new_paths):
        if old == "/dev/null":
            action, target = "create", new
        elif new == "/dev/null":
            action, target = "delete", old
        elif old == new:
            action, target = "modify", new
        else:
            raise WorkflowError("renames are unsupported in apply_patch exact actions")
        target = posixpath.normpath(target)
        if target in {"", ".", ".."} or target.startswith("../") or target.startswith("/"):
            raise WorkflowError("patch paths must be normalized project-relative paths")
        prior_action = seen_targets.get(target)
        if prior_action is not None:
            raise WorkflowError(
                f"patch target appears more than once or across actions: {target} ({prior_action}, {action})"
            )
        seen_targets[target] = action
        {"create": created, "modify": modified, "delete": deleted}[action].add(target)
    return created, modified, deleted


def verify_reports(
    plan: LowLevelPlan,
    assessment: Assessment,
    reports: list[ExecutionReport],
    proposal: VerificationProposal,
    context: VerificationContext,
) -> VerificationReport:
    plan = _boundary_copy(plan, LowLevelPlan)
    assessment = _boundary_copy(assessment, Assessment)
    reports = TypeAdapter(list[ExecutionReport]).validate_python(parse_json_strict(canonical_bytes([
        item.model_dump(mode="json") if hasattr(item, "model_dump") else item for item in reports
    ])))
    proposal = _boundary_copy(proposal, VerificationProposal)
    registered = _VERIFICATION_CONTEXTS.pop(context.token, None)
    plan_hash = hash_ref("low-level-plan", plan.model_dump(mode="json"))
    assessment_hash = hash_ref("assessment", assessment.model_dump(mode="json"))
    if registered != (plan_hash.value, assessment_hash.value, context.context_id, context.snapshot_hash.value):
        raise WorkflowError("verification context is absent, stale, or bound to another artifact")
    if not assessment.safe or assessment.plan_hash != plan_hash:
        raise WorkflowError("only the exact approved assessment may be verified")
    if context.plan_hash != plan_hash or context.assessment_hash != assessment_hash:
        raise WorkflowError("verification context artifact binding mismatch")
    if (
        proposal.plan_hash != plan_hash
        or proposal.assessment_hash != assessment_hash
        or proposal.snapshot_hash != context.snapshot_hash
        or proposal.verifier_context_id != context.context_id
    ):
        raise WorkflowError("verification proposal artifact binding mismatch")
    completed = {report.operation_id for report in reports if report.success}
    expected = {operation.operation_id for operation in plan.operations}
    unexpected = [item for report in reports for item in report.unexpected_effects]
    expected_criteria = {criterion for operation in plan.operations for criterion in operation.success_criteria}
    expected_checks = {check for operation in plan.operations for check in operation.verifier_checks}
    expected_effects = {effect.effect_id for operation in plan.operations for effect in operation.effects}
    observed_report_effects = {effect_id for report in reports for effect_id in report.expected_effect_ids_observed}
    evidence_ids = {item.evidence_id for item in proposal.evidence}
    valid_verifier_findings, verifier_integrity_errors = _partition_agent_findings(
        proposal.findings,
        expected,
        expected_effects,
        {item.evidence_id: item.provenance for item in proposal.evidence},
    )
    proposal = proposal.model_copy(update={"findings": valid_verifier_findings})
    integrity_finding = None
    if verifier_integrity_errors:
        integrity_finding = _blocking_finding(
            "verification-reference-integrity", "E-004", "finding_identity",
            f"verification proposal has invalid typed references: {sorted(set(verifier_integrity_errors))}",
        )
    verifier_evidence_valid = (
        len(evidence_ids) == len(proposal.evidence)
        and all(
            item.provenance == "agent_reported"
            and item.locator == f"agent-report:{item.evidence_id}"
            for item in proposal.evidence
        )
        and integrity_finding is None
    )
    coordinator_snapshot_evidence_id = f"snapshot-{context.snapshot_hash.value[:32]}"
    criterion_keys = set(proposal.criterion_evidence)
    check_keys = set(proposal.check_evidence)
    effect_keys = set(proposal.effect_evidence)
    evidence_bindings = [
        evidence_id
        for mapping in (proposal.criterion_evidence, proposal.check_evidence, proposal.effect_evidence)
        for values in mapping.values()
        for evidence_id in values
    ]
    evidence_complete = (
        bool(evidence_ids)
        and verifier_evidence_valid
        and criterion_keys == expected_criteria
        and check_keys == expected_checks
        and effect_keys == expected_effects
        and all(proposal.criterion_evidence[key] for key in criterion_keys)
        and all(proposal.check_evidence[key] for key in check_keys)
        and all(proposal.effect_evidence[key] for key in effect_keys)
        and set(evidence_bindings).issubset(evidence_ids)
    )
    verified = (
        completed == expected
        and not unexpected
        and set(proposal.success_criteria_met) == expected_criteria
        and set(proposal.verifier_checks_passed) == expected_checks
        and set(proposal.observed_effect_ids) == expected_effects
        and observed_report_effects == expected_effects
        and evidence_complete
        and not any(item.blocking for item in proposal.findings)
        and integrity_finding is None
    )
    return VerificationReport(
        schema_version="1.0",
        verification_id=f"verification-{plan_hash.value[:32]}",
        plan_hash=assessment.plan_hash,
        assessment_hash=assessment_hash,
        snapshot_hash=proposal.snapshot_hash,
        independent_context=False,
        independence_assurance="instruction_only",
        coordinator_evidence_ids=[coordinator_snapshot_evidence_id],
        verifier_evidence_ids=sorted(evidence_ids),
        success_criteria_met=sorted(set(proposal.success_criteria_met) & expected_criteria),
        verifier_checks_passed=sorted(set(proposal.verifier_checks_passed) & expected_checks),
        findings=[_sanitize_finding(item) for item in proposal.findings] + ([] if integrity_finding is None else [integrity_finding]),
        verified=verified,
        provenance="coordinator_observed",
    )


def record_workflow(audit_root: str, run_id: str, event_type: str, lifecycle_from: str | None, lifecycle_to: str | None, summary: str, evidence_ids: list[str]) -> str:
    log = AuditLog(audit_root, run_id)
    event = log.append(
        EventPayload(event_type=event_type, lifecycle_from=lifecycle_from, lifecycle_to=lifecycle_to, operation_id=None, summary=summary, evidence_ids=evidence_ids),
        "coordinator_observed",
        {"summary": summary},
    )
    return event.event_record_hash
