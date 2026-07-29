from __future__ import annotations

import hashlib
import os
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
from .compatibility import LegacyArtifactNotExecutable
from .fakes import FakeAgentHost, FakeFilesystem, FakeSubprocess
from .models import (
    Approval,
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
from .patches import (
    PatchContractError,
    capture_file_metadata,
    commit_prepared_text_patch,
    inspect_patch_paths,
    metadata_fingerprint_hash,
    prepare_text_patch,
)
from .proposal_cycle import ProposalCycleArtifacts, ProposalCycleService, ProposalSafetyRejected
from .proposal_models import (
    ApplyIntent,
    ApprovalV2,
    AssessmentBundleV2,
    AssessmentV2,
    CoordinatorBundleV2,
    DeterministicPreflightV2,
    EventPayloadV2,
    ExactProposedChange,
    ExecutionReportV2,
    HostCapabilitiesV2,
    HumanInterventionV2,
    LowLevelPlanV2,
    PatchAssessment,
    PatchAssessmentRequest,
    PatchSemanticAssessmentProposal,
    PlanAssessmentRequest,
    PlanAssessmentResponse,
    ProviderGrant,
    ProposalRequest,
    AgentPatchProposal,
    ProposalCycleRecord,
    RepositorySnapshotV2,
    RepairAttemptV2,
    RepairOutcomeV2,
    RunManifestV2,
    RunResourceGrant,
    RoleCallRecord,
    SemanticRoleContext,
    SemanticAssessmentProposalV2,
    VerificationFileState,
    VerificationProposalV2,
    VerificationReportV2,
    VerificationRoleRequest,
    VerificationRoleResponse,
)
from .role_hosts import RoleHostResourceExhausted
from .planning import COMMAND_CLASSIFICATIONS, classify_command, discover_instruction_files, discover_instruction_files_policy, select_markdown_phase
from .policy import active_policy_widening_errors, default_global_policy, deterministic_assessment_findings
from .policy_models import ActivePolicyV2
from .project_policy import evaluate_path, load_project_policy, require_path, revalidate_decision
from .state import acquire_lease, capture_policy_snapshot, capture_snapshot, heartbeat_lease, release_lease, snapshot_materially_equal, transition


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


def default_host_capabilities_v2(adapter: str = "pydantic_ai") -> HostCapabilitiesV2:
    if adapter == "pydantic_ai":
        return HostCapabilitiesV2(
            schema_version="3.0", profile="semi_formal", role_read_only="host_enforced",
            role_tool_allocation="framework_enforced",
            product_state_observation="coordinator_observed", complete_child_trace=False,
            atomic_path_enforcement=False, atomic_lease_create=True,
            bounded_resource_enforcement="framework_enforced",
            fresh_context_enforcement="host_enforced",
            provider_identity_observation="coordinator_observed",
            policy_aware_role_allocation=True,
        )
    if adapter == "json_line":
        return HostCapabilitiesV2(
            schema_version="3.0", profile="semi_formal", role_read_only="instruction_only",
            role_tool_allocation="instruction_only",
            product_state_observation="coordinator_observed", complete_child_trace=False,
            atomic_path_enforcement=False, atomic_lease_create=True,
            bounded_resource_enforcement="instruction_only",
            fresh_context_enforcement="instruction_only",
            provider_identity_observation="unknown",
            policy_aware_role_allocation=True,
        )
    raise ValueError("unsupported proposal role adapter")


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


def _assess_plan_legacy_compatible(
    plan: LowLevelPlan | LowLevelPlanV2,
    global_policy: Any,
    active_policy: Any,
    current_snapshot: RepositorySnapshot | RepositorySnapshotV2,
    capabilities: HostCapabilities | HostCapabilitiesV2,
    semantic_proposal: SemanticAssessmentProposal | SemanticAssessmentProposalV2,
    approvals: list[Any],
    *,
    now: datetime | None = None,
    prior_assessment_hash: HashRef | None = None,
    provider_grant: ProviderGrant | None = None,
    run_resource_grant: RunResourceGrant | None = None,
) -> Assessment | AssessmentV2:
    if getattr(plan, "schema_version", None) == "3.0":
        return _assess_plan_v2(
            plan, global_policy, active_policy, current_snapshot, capabilities,
            semantic_proposal, approvals, now=now,
            prior_assessment_hash=prior_assessment_hash,
            provider_grant=provider_grant, run_resource_grant=run_resource_grant,
        )
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


def _assess_plan_v2(
    plan: Any,
    global_policy: Any,
    active_policy: Any,
    current_snapshot: Any,
    capabilities: Any,
    semantic_proposal: Any,
    approvals: list[Any],
    *,
    now: datetime | None,
    prior_assessment_hash: HashRef | None,
    provider_grant: ProviderGrant | None,
    run_resource_grant: RunResourceGrant | None,
) -> AssessmentV2:
    plan = _boundary_copy(plan, LowLevelPlanV2)
    global_policy = _boundary_copy(global_policy, ActivePolicy)
    active_policy = _boundary_copy(active_policy, ActivePolicyV2)
    current_snapshot = _boundary_copy(current_snapshot, RepositorySnapshotV2)
    capabilities = _boundary_copy(capabilities, HostCapabilitiesV2)
    semantic_proposal = _boundary_copy(semantic_proposal, SemanticAssessmentProposalV2)
    if provider_grant is None or run_resource_grant is None:
        raise WorkflowError("schema-3.0 assessment requires explicit provider and run resource grants")
    provider_grant = _boundary_copy(provider_grant, ProviderGrant)
    run_resource_grant = _boundary_copy(run_resource_grant, RunResourceGrant)
    validated_approvals = [_boundary_copy(item, ApprovalV2) for item in approvals]
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
    plan_hash = hash_ref("low-level-plan", plan.model_dump(mode="json"), "3.0")
    policy_hash = hash_ref("active-policy", active_policy.model_dump(mode="json"), "2.0")
    snapshot_hash = hash_ref("repository-snapshot", plan.snapshot.model_dump(mode="json"), "3.0")
    provider_hash = hash_ref("provider-grant", provider_grant.model_dump(mode="json"), "1.0")
    resource_hash = hash_ref("run-resource-grant", run_resource_grant.model_dump(mode="json"), "1.0")
    findings = _identity_findings(plan, global_policy, active_policy, current_snapshot)
    installed_global_policy = default_global_policy(plan.snapshot.project_root)
    loaded_policy = load_project_policy(plan.snapshot.project_root, installed_global_policy)
    if global_policy != installed_global_policy:
        findings.append(_blocking_finding(
            "identity-global-policy-source", "P-001", "artifact_identity",
            "caller-supplied global policy differs from the immutable installed baseline",
        ))
    if (
        loaded_policy.binding != plan.policy_binding
        or loaded_policy.binding != current_snapshot.policy_binding
        or active_policy != loaded_policy.effective_policy
    ):
        findings.append(_blocking_finding(
            "identity-project-policy", "P-001", "artifact_identity",
            "fixed project policy source or effective identity differs from the plan and snapshot",
        ))
    for operation in plan.operations:
        checks: list[tuple[str, str]] = []
        if operation.kind == "exact_action" and operation.adapter == "read_file":
            checks.append((operation.path, "read"))
        elif operation.kind == "exact_action" and operation.adapter == "apply_patch":
            checks.extend((path, "create") for path in operation.expected_created_paths)
            checks.extend((path, "read") for path in operation.expected_modified_paths)
            checks.extend((path, "modify") for path in operation.expected_modified_paths)
            checks.extend((path, "read") for path in operation.expected_deleted_paths)
            checks.extend((path, "delete") for path in operation.expected_deleted_paths)
        for path, capability in checks:
            decision = evaluate_path(loaded_policy, path, capability)
            if not decision.allowed:
                findings.append(_blocking_finding(
                    f"project-policy-{operation.operation_id}-{capability}-{hashlib.sha256(path.encode()).hexdigest()[:12]}",
                    "P-001", "path_escape",
                    f"fixed project policy denies {capability} for a concrete operation path; "
                    f"rule IDs: {decision.matched_rule_ids or ['uncertain-path-identity']}",
                    [operation.operation_id],
                ))
    widening = active_policy_widening_errors(installed_global_policy, active_policy)
    if widening:
        findings.append(_blocking_finding(
            "identity-policy-widening", "P-003", "policy_widening",
            f"active policy is wider than the immutable global policy: {widening}",
        ))
    if duplicate_approval_ids:
        findings.append(_blocking_finding(
            "approval-identity-duplicate", "O-007", "approval_scope",
            f"approval IDs must be unique within an assessment: {len(duplicate_approval_ids)} duplicate(s)",
        ))
    operation_ids = {item.operation_id for item in plan.operations}
    effect_ids = {effect.effect_id for item in plan.operations for effect in item.effects}
    evidence_provenance = {item.evidence_id: item.provenance for item in plan.evidence}
    valid_semantic_findings, semantic_integrity_errors = _partition_agent_findings(
        semantic_proposal.findings, operation_ids, effect_ids, evidence_provenance
    )
    required_evidence_ids = set(evidence_provenance)
    supplied_coverage = semantic_proposal.covered_evidence_ids
    if len(supplied_coverage) != len(set(supplied_coverage)) or set(supplied_coverage) != required_evidence_ids:
        semantic_integrity_errors.append("covered_evidence_set")
    semantic_proposal = semantic_proposal.model_copy(update={
        "semantic_pass": semantic_proposal.semantic_pass and not semantic_integrity_errors,
        "findings": [_sanitize_finding(item) for item in valid_semantic_findings],
        "covered_evidence_ids": sorted(set(supplied_coverage) & required_evidence_ids),
        "enforcement_disclosures": [
            "untrusted assessor prose omitted; coordinator derives capability disclosures"
        ],
    })
    if semantic_integrity_errors:
        findings.append(_blocking_finding(
            "semantic-reference-integrity", "E-004", "finding_identity",
            f"semantic proposal has invalid typed references or coverage: {sorted(set(semantic_integrity_errors))}",
        ))
    if plan.provider_grant_hash != provider_hash or semantic_proposal.provider_grant_hash != provider_hash:
        findings.append(_blocking_finding(
            "identity-provider-grant", "O-005", "artifact_identity",
            "provider grant differs from the plan or semantic assessment proposal",
        ))
    if plan.run_resource_grant_hash != resource_hash:
        findings.append(_blocking_finding(
            "identity-resource-grant", "P-002", "artifact_identity",
            "run resource grant differs from the plan",
        ))
    expected_capabilities = default_host_capabilities_v2(provider_grant.adapter)
    if capabilities != expected_capabilities:
        findings.append(_blocking_finding(
            "identity-host-capabilities", "A-008", "unsupported_host_capability",
            "caller-supplied host capabilities differ from the selected adapter profile",
        ))
    if plan.snapshot.selected_file_metadata_hashes != current_snapshot.selected_file_metadata_hashes:
        findings.append(_blocking_finding(
            "identity-file-metadata", "R-002", "snapshot_drift",
            "selected file metadata differs from the assessed snapshot",
        ))
    provider_expiry = datetime.strptime(provider_grant.expires_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    resource_expiry = datetime.strptime(run_resource_grant.expires_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    if observed_at >= provider_expiry or observed_at >= resource_expiry:
        findings.append(_blocking_finding(
            "grant-expired", "P-002", "policy_limit", "provider or run resource grant is expired",
        ))
    if provider_grant.cost_accounting == "unavailable":
        findings.append(_blocking_finding(
            "provider-cost-accounting", "P-002", "unobservable_risk",
            "selected provider adapter cannot account for the granted cost ceiling",
        ))
    operation_profiles = sorted({
        item.required_assurance_profile for item in plan.operations if item.kind == "bounded_agent_task"
    })
    if sorted(semantic_proposal.required_role_assurance_profiles) != operation_profiles:
        findings.append(_blocking_finding(
            "role-assurance-profile", "A-008", "unsupported_host_capability",
            "semantic assessment role assurance coverage differs from bounded operations",
        ))
    approved_effects: set[str] = set()
    operation_hashes = {
        item.operation_id: hash_ref("operation", item.model_dump(mode="json"), "2.0")
        for item in plan.operations
    }
    classification_order = ["public", "internal", "personal", "sensitive", "secret"]
    for operation in plan.operations:
        if operation.kind == "bounded_agent_task":
            if operation.required_adapter != provider_grant.adapter:
                findings.append(_blocking_finding(
                    f"provider-adapter-{operation.operation_id}", "O-005", "unsupported_host_capability",
                    "bounded operation adapter differs from the provider grant", [operation.operation_id],
                ))
            if not {"proposer", "patch_assessor"}.issubset(provider_grant.roles):
                findings.append(_blocking_finding(
                    f"provider-roles-{operation.operation_id}", "O-005", "unsupported_host_capability",
                    "provider grant lacks proposer or patch-assessor authority", [operation.operation_id],
                ))
            if classification_order.index(provider_grant.maximum_data_classification) < classification_order.index(
                operation.source_data_classification
            ):
                findings.append(_blocking_finding(
                    f"provider-classification-{operation.operation_id}", "O-005", "policy_limit",
                    "provider grant classification ceiling is below the declared source context",
                    [operation.operation_id],
                ))
            if f"{operation.source_data_classification}_source" not in provider_grant.request_data_classes:
                findings.append(_blocking_finding(
                    f"provider-data-class-{operation.operation_id}", "O-005", "policy_limit",
                    "provider grant omits the operation source-data class", [operation.operation_id],
                ))
            if operation.allowed_read_tools and (
                run_resource_grant.max_read_tool_calls < 1 or run_resource_grant.max_read_tool_bytes < 1
            ):
                findings.append(_blocking_finding(
                    f"read-resource-{operation.operation_id}", "P-002", "policy_limit",
                    "bounded read tools require positive call and byte grants", [operation.operation_id],
                ))
            if operation.required_adapter == "json_line" and operation.allowed_read_tools:
                findings.append(_blocking_finding(
                    f"json-line-read-tool-{operation.operation_id}", "A-008", "unsupported_host_capability",
                    "the JSON-line compatibility adapter cannot mediate interactive read tools",
                    [operation.operation_id],
                ))
            if "choose_file_within_root" in operation.permitted_adaptations and "read_file" not in operation.allowed_read_tools:
                findings.append(_blocking_finding(
                    f"adaptation-read-tool-{operation.operation_id}", "O-003", "incomplete_operation",
                    "choosing a file within a root requires the bounded read tool", [operation.operation_id],
                ))
            if operation.resource_limits.max_bytes > run_resource_grant.max_patch_bytes:
                findings.append(_blocking_finding(
                    f"patch-byte-grant-{operation.operation_id}", "P-002", "policy_limit",
                    "operation patch-byte ceiling exceeds the active run resource grant", [operation.operation_id],
                ))
        for effect in operation.effects:
            classes = _required_effect_approval_classes(operation, effect, active_policy)
            missing: list[str] = []
            for approval_class in classes:
                for target in effect.targets:
                    matches = [item for item in approvals if (
                        item.plan_hash == plan_hash
                        and item.operation_hash == operation_hashes[operation.operation_id]
                        and item.policy_hash == policy_hash
                        and item.snapshot_hash == snapshot_hash
                        and item.effect_id == effect.effect_id
                        and item.effect_class == effect.effect_class
                        and item.approval_class == approval_class
                        and item.target == target
                        and not item.consumed
                        and (
                            item.expires_at is None
                            or datetime.strptime(item.expires_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                            > observed_at
                        )
                        and (
                            effect.exposure not in {"project_external", "multi_party", "systemic"}
                            and effect.reversibility not in {"uncertain", "none"}
                            and effect.effect_class != "external_write"
                            or bool(item.idempotency_key)
                        )
                    )]
                    if len(matches) != 1:
                        missing.append(f"{approval_class}:{target}")
            if missing:
                findings.append(_blocking_finding(
                    f"approval-{effect.effect_id}", "O-007", "approval_scope",
                    f"plan-envelope approval is missing or ambiguous: {missing}",
                    [operation.operation_id], [effect.effect_id],
                ))
            elif classes:
                approved_effects.add(effect.effect_id)
    covered = set(semantic_proposal.covered_evidence_ids)
    deterministic_findings = deterministic_assessment_findings(
        plan, active_policy, capabilities, covered, approved_effects
    )
    deterministic_ids = {item.finding_id for item in findings + deterministic_findings}
    collisions = sorted(
        item.finding_id for item in semantic_proposal.findings if item.finding_id in deterministic_ids
    )
    if collisions:
        findings.append(_blocking_finding(
            "semantic-finding-id-collision", "E-004", "finding_identity",
            f"semantic finding IDs collide with deterministic findings: {collisions}",
        ))
    findings.extend(deterministic_findings)
    findings.extend(item for item in semantic_proposal.findings if item.finding_id not in deterministic_ids)
    missing_evidence = sorted({item.evidence_id for item in plan.evidence} - covered)
    deterministic_pass = not any(
        item.blocking and item.finding_provenance == "coordinator_observed" for item in findings
    ) and not missing_evidence
    semantic_pass = semantic_proposal.semantic_pass and not any(
        item.blocking and item.finding_provenance == "agent_reported" for item in findings
    )
    safe = deterministic_pass and semantic_pass
    disclosures = [
        f"role read-only enforcement: {capabilities.role_read_only}",
        f"role tool allocation: {capabilities.role_tool_allocation}",
        f"product-state observation: {capabilities.product_state_observation}",
        f"complete child trace: {str(capabilities.complete_child_trace).lower()}",
        "semantic patch assessment can miss harmful meaning",
        "static file-state verification does not prove runtime correctness",
    ]
    return AssessmentV2(
        schema_version="3.0", assessment_id=f"assessment-{plan_hash.value[:32]}",
        plan_hash=plan_hash, policy_hash=policy_hash, snapshot_hash=snapshot_hash,
        deterministic_pass=deterministic_pass, semantic_pass=semantic_pass,
        safe=safe, status="approved" if safe else "rejected", profile=capabilities.profile,
        findings=findings, covered_evidence_ids=sorted(covered), missing_evidence_ids=missing_evidence,
        approvals=approvals, enforcement_disclosures=disclosures,
        prior_assessment_hash=prior_assessment_hash, provider_grant_hash=provider_hash,
        run_resource_grant_hash=resource_hash,
        required_role_assurance_profiles=operation_profiles,
        policy_binding=plan.policy_binding,
    )


def assess_plan(
    plan: LowLevelPlanV2,
    global_policy: Any,
    active_policy: Any,
    current_snapshot: RepositorySnapshotV2,
    capabilities: HostCapabilitiesV2,
    semantic_proposal: SemanticAssessmentProposalV2,
    approvals: list[Any],
    **kwargs: Any,
) -> AssessmentV2:
    """Assess only proposal-first plans at the public runtime boundary."""
    if getattr(plan, "schema_version", None) != "3.0":
        raise LegacyArtifactNotExecutable(
            "legacy_artifact_not_executable: plan assessment requires schema '3.0'; "
            "inspect the old artifact for audit or recompile and reassess"
        )
    return _assess_plan_legacy_compatible(
        plan, global_policy, active_policy, current_snapshot, capabilities,
        semantic_proposal, approvals, **kwargs,
    )


def _deterministic_preflight_legacy_compatible(
    plan: LowLevelPlan | LowLevelPlanV2,
    global_policy: ActivePolicy,
    active_policy: ActivePolicy,
    current_snapshot: RepositorySnapshot | RepositorySnapshotV2,
    capabilities: HostCapabilities | HostCapabilitiesV2,
    approvals: list[Any],
    *,
    now: datetime | None = None,
    provider_grant: ProviderGrant | None = None,
    run_resource_grant: RunResourceGrant | None = None,
) -> DeterministicPreflight | DeterministicPreflightV2:
    """Run every non-semantic gate without invoking or accepting an assessor response."""
    required_evidence = sorted(item.evidence_id for item in plan.evidence)
    if getattr(plan, "schema_version", None) == "3.0":
        if provider_grant is None or run_resource_grant is None:
            raise WorkflowError("schema-3.0 preflight requires explicit provider and run resource grants")
        profiles = sorted({
            item.required_assurance_profile for item in plan.operations if item.kind == "bounded_agent_task"
        })
        placeholder = SemanticAssessmentProposalV2(
            schema_version="3.0", semantic_pass=True, findings=[],
            covered_evidence_ids=required_evidence, enforcement_disclosures=[],
            provider_grant_hash=hash_ref(
                "provider-grant", provider_grant.model_dump(mode="json"), "1.0"
            ),
            required_role_assurance_profiles=profiles,
            policy_binding=plan.policy_binding,
        )
        assessment = _assess_plan_legacy_compatible(
            plan, global_policy, active_policy, current_snapshot, capabilities, placeholder,
            approvals, now=now, provider_grant=provider_grant,
            run_resource_grant=run_resource_grant,
        )
        return DeterministicPreflightV2(
            schema_version="3.0", preflight_id=f"preflight-{assessment.plan_hash.value[:32]}",
            plan_hash=assessment.plan_hash, policy_hash=assessment.policy_hash,
            snapshot_hash=assessment.snapshot_hash,
            deterministic_pass=assessment.deterministic_pass,
            semantic_assessment_required=assessment.deterministic_pass,
            findings=[item for item in assessment.findings if item.finding_provenance == "coordinator_observed"],
            approvals=assessment.approvals,
            enforcement_disclosures=assessment.enforcement_disclosures,
            required_semantic_evidence_ids=required_evidence,
            provider_grant_hash=assessment.provider_grant_hash,
            run_resource_grant_hash=assessment.run_resource_grant_hash,
            policy_binding=plan.policy_binding,
        )
    placeholder = SemanticAssessmentProposal(
        schema_version="1.0", semantic_pass=True, findings=[],
        covered_evidence_ids=required_evidence, enforcement_disclosures=[],
    )
    assessment = _assess_plan_legacy_compatible(
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


def deterministic_preflight(
    plan: LowLevelPlanV2,
    global_policy: ActivePolicy,
    active_policy: ActivePolicy,
    current_snapshot: RepositorySnapshotV2,
    capabilities: HostCapabilitiesV2,
    approvals: list[Any],
    **kwargs: Any,
) -> DeterministicPreflightV2:
    """Run public deterministic preflight only for proposal-first plans."""
    if getattr(plan, "schema_version", None) != "3.0":
        raise LegacyArtifactNotExecutable(
            "legacy_artifact_not_executable: deterministic preflight requires schema '3.0'; "
            "inspect the old artifact for audit or recompile and reassess"
        )
    return _deterministic_preflight_legacy_compatible(
        plan, global_policy, active_policy, current_snapshot, capabilities,
        approvals, **kwargs,
    )


@dataclass(frozen=True)
class PlanAssessmentOutcome:
    request: PlanAssessmentRequest
    response: PlanAssessmentResponse
    assessment: AssessmentV2
    bundle: AssessmentBundleV2
    role_call_record: RoleCallRecord


def assess_plan_with_host(
    plan: LowLevelPlanV2,
    global_policy: ActivePolicy,
    active_policy: ActivePolicyV2,
    current_snapshot: RepositorySnapshotV2,
    capabilities: HostCapabilitiesV2,
    approvals: list[Any],
    *,
    provider_grant: ProviderGrant,
    run_resource_grant: RunResourceGrant,
    role_host: Any,
    state_guard: Any,
    now: datetime,
    prior_assessment_hash: HashRef | None = None,
    request_checkpoint: Any | None = None,
    completed_call_loader: Any | None = None,
    completed_call_checkpoint: Any | None = None,
) -> PlanAssessmentOutcome:
    """Build, invoke, and cross-check one owned plan-assessor call."""

    preflight = deterministic_preflight(
        plan, global_policy, active_policy, current_snapshot, capabilities, approvals,
        now=now, provider_grant=provider_grant, run_resource_grant=run_resource_grant,
    )
    if not preflight.deterministic_pass:
        raise WorkflowError("deterministic preflight rejected the plan before semantic assessment")
    plan_hash = hash_ref("low-level-plan", plan.model_dump(mode="json"), "3.0")
    preflight_hash = hash_ref(
        "deterministic-preflight", preflight.model_dump(mode="json"), "3.0"
    )
    policy_hash = hash_ref("active-policy", active_policy.model_dump(mode="json"), "2.0")
    capability_hash = hash_ref(
        "host-capabilities", capabilities.model_dump(mode="json"), "3.0"
    )
    provider_hash = hash_ref(
        "provider-grant", provider_grant.model_dump(mode="json"), "1.0"
    )
    resource_hash = hash_ref(
        "run-resource-grant", run_resource_grant.model_dump(mode="json"), "1.0"
    )
    input_hashes = [
        plan_hash, preflight_hash, policy_hash, capability_hash, provider_hash, resource_hash,
    ]
    prompt_packet_hash = hashlib.sha256(canonical_bytes({
        "input_artifact_hashes": [item.model_dump(mode="json") for item in input_hashes],
        "approvals": [item.model_dump(mode="json") for item in preflight.approvals],
        "prior_assessment_hash": (
            None if prior_assessment_hash is None else prior_assessment_hash.model_dump(mode="json")
        ),
    })).hexdigest()
    timestamp = now.astimezone(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")
    context = SemanticRoleContext(
        schema_version="1.0", context_id=f"plan-assessor-{plan_hash.value[:24]}",
        request_token=f"request-{prompt_packet_hash[:32]}", role="plan_assessor",
        adapter=provider_grant.adapter,
        assurance_profile=(
            "framework_tool_enforced_no_tools"
            if provider_grant.adapter == "pydantic_ai" else "instruction_only_proposal_host"
        ),
        provider_grant_hash=provider_hash, run_resource_grant_hash=resource_hash,
        policy_binding=plan.policy_binding,
        input_artifact_hashes=input_hashes, prompt_packet_hash=prompt_packet_hash,
        created_at=timestamp,
    )
    request = PlanAssessmentRequest(
        schema_version="1.0", context=context, plan=plan, preflight=preflight,
        active_policy=active_policy, capabilities=capabilities,
        provider_grant=provider_grant, run_resource_grant=run_resource_grant,
        approvals=preflight.approvals, prior_assessment_hash=prior_assessment_hash,
    )
    before_records = len(getattr(role_host, "call_records", []))
    recovered = completed_call_loader(request) if completed_call_loader is not None else None
    if recovered is None:
        if request_checkpoint is not None:
            request_checkpoint(request)
        state_guard("before_plan_assessor")
        response = PlanAssessmentResponse.model_validate(
            role_host.assess_plan(request).model_dump(mode="json")
        )
        state_guard("after_plan_assessor")
        records = getattr(role_host, "call_records", [])
        if len(records) != before_records + 1:
            raise WorkflowError("plan assessor did not produce exactly one role-call record")
        record = RoleCallRecord.model_validate(records[-1].model_dump(mode="json"))
    else:
        response = PlanAssessmentResponse.model_validate(
            recovered[0].model_dump(mode="json")
        )
        record = RoleCallRecord.model_validate(recovered[1].model_dump(mode="json"))
        adopt_call_record = getattr(role_host, "adopt_call_record", None)
        if adopt_call_record is None:
            raise WorkflowError("recovered semantic call cannot be rebound to host resource accounting")
        adopt_call_record(record)
    if (
        response.request_token != context.request_token
        or response.plan_hash != plan_hash
        or response.preflight_hash != preflight_hash
        or response.policy_hash != policy_hash
        or response.snapshot_hash != preflight.snapshot_hash
        or response.semantic_proposal.provider_grant_hash != provider_hash
        or response.policy_binding != plan.policy_binding
        or response.semantic_proposal.policy_binding != plan.policy_binding
    ):
        raise WorkflowError("plan assessor response differs from the complete coordinator request")
    expected_profiles = sorted({
        item.required_assurance_profile for item in plan.operations
        if item.kind == "bounded_agent_task"
    })
    if response.semantic_proposal.required_role_assurance_profiles != expected_profiles:
        raise WorkflowError("plan assessor response changes required role assurance profiles")
    if (
        record.role != "plan_assessor"
        or record.outcome != "success"
        or not record.usage_complete
        or record.adapter != provider_grant.adapter
        or record.assurance_profile != context.assurance_profile
        or record.provider_grant_hash != provider_hash
        or record.policy_binding != plan.policy_binding
        or record.provider != provider_grant.provider
        or record.endpoint != provider_grant.endpoint
        or record.model != provider_grant.model
        or record.model_revision != provider_grant.model_revision
    ):
        raise WorkflowError("plan assessor role-call record is incomplete or unsuccessful")
    if completed_call_checkpoint is not None and recovered is None:
        completed_call_checkpoint(request, response, record)
    assessment = assess_plan(
        plan, global_policy, active_policy, current_snapshot, capabilities,
        response.semantic_proposal, approvals, now=now,
        provider_grant=provider_grant, run_resource_grant=run_resource_grant,
        prior_assessment_hash=prior_assessment_hash,
    )
    bundle = AssessmentBundleV2(
        schema_version="3.0", assessment=assessment,
        semantic_proposal=response.semantic_proposal,
    )
    return PlanAssessmentOutcome(
        request=request, response=response, assessment=assessment,
        bundle=bundle, role_call_record=record,
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
    expected_global = hash_ref("active-policy", global_policy.model_dump(mode="json"), "1.0")
    expected_active = hash_ref(
        "active-policy", active_policy.model_dump(mode="json"),
        "2.0" if getattr(plan, "schema_version", None) == "3.0" else "1.0",
    )
    if plan.global_policy_hash != expected_global:
        findings.append(_blocking_finding("identity-global-policy", "P-001", "artifact_identity", "global policy hash differs from the installed immutable baseline"))
    if plan.merged_policy_hash != expected_active:
        findings.append(_blocking_finding("identity-active-policy", "P-001", "artifact_identity", "merged policy hash differs from the active policy assessed"))
    direct_text_hash = hashlib.sha256(plan.source_phase.selected_text.encode("utf-8")).hexdigest()
    if plan.source_phase.selected_text_hash != direct_text_hash:
        findings.append(_blocking_finding("identity-selected-text", "R-001", "artifact_identity", "selected phase text hash does not match the embedded text"))
    try:
        if getattr(plan, "schema_version", None) == "3.0":
            loaded = load_project_policy(plan.snapshot.project_root, global_policy)
            require_path(loaded, plan.source_phase.plan_path, "read")
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
        if getattr(plan, "schema_version", None) == "3.0":
            loaded = load_project_policy(plan.snapshot.project_root, global_policy)
            discovered = discover_instruction_files_policy(loaded, _plan_instruction_targets(plan))
        else:
            discovered = discover_instruction_files(plan.snapshot.project_root, _plan_instruction_targets(plan))
        if discovered != plan.snapshot.instruction_hashes:
            findings.append(_blocking_finding("identity-instructions", "A-005", "instruction_scope", "applicable repository instructions are omitted, stale, or over-declared"))
    except Exception as exc:
        findings.append(_blocking_finding("identity-instructions", "A-005", "instruction_scope", f"applicable instruction discovery failed: {type(exc).__name__}"))
    return findings


def _execute_fake_legacy(
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


def execute_fake(*args: Any, **kwargs: Any) -> list[ExecutionReport]:
    """Reject the retired direct executor-to-report mutation path."""

    raise LegacyArtifactNotExecutable(
        "legacy_artifact_not_executable: direct executor reports cannot execute in runtime 0.3; "
        "recompile and reassess as a proposal-first schema-3 run"
    )


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


def _begin_verification_context_legacy(
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


def begin_verification_context(*args: Any, **kwargs: Any) -> VerificationContext:
    """Reject the retired standalone schema-1 verification entry point."""
    raise LegacyArtifactNotExecutable(
        "legacy_artifact_not_executable: standalone schema-1 verification is audit-only; "
        "use a proposal-first ExecutionCoordinator"
    )


class _CoordinatorRuntime:
    """Hold one lease and audit chain across approved execution and context-separated verification."""

    def __init__(
        self,
        plan: LowLevelPlan | LowLevelPlanV2,
        assessment: Assessment | AssessmentV2,
        global_policy: Any,
        active_policy: Any,
        capabilities: HostCapabilities | HostCapabilitiesV2,
        semantic_proposal: SemanticAssessmentProposal | None = None,
        agent_host: Any | None = None,
        provider_grant: ProviderGrant | None = None,
        run_resource_grant: RunResourceGrant | None = None,
        metadata_loader: Any | None = None,
        proposal_approvals: list[ApprovalV2] | None = None,
    ):
        if getattr(plan, "schema_version", None) == "3.0":
            self._initialize_v2(
                plan=plan,
                assessment=assessment,
                global_policy=global_policy,
                active_policy=active_policy,
                capabilities=capabilities,
                role_host=agent_host,
                provider_grant=provider_grant,
                run_resource_grant=run_resource_grant,
                metadata_loader=metadata_loader,
                proposal_approvals=proposal_approvals,
                semantic_proposal=semantic_proposal,
            )
            return
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
        revalidation = _assess_plan_legacy_compatible(
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

    def _initialize_v2(
        self,
        *,
        plan: Any,
        assessment: Any,
        global_policy: Any,
        active_policy: Any,
        capabilities: Any,
        role_host: Any,
        provider_grant: ProviderGrant | None,
        run_resource_grant: RunResourceGrant | None,
        metadata_loader: Any | None,
        proposal_approvals: list[ApprovalV2] | None,
        semantic_proposal: SemanticAssessmentProposalV2 | None,
    ) -> None:
        """Initialise the proposal-first branch of this same coordinator state machine."""

        self._proposal_first = True
        self.plan = _boundary_copy(plan, LowLevelPlanV2)
        self.assessment = _boundary_copy(assessment, AssessmentV2)
        self.global_policy = _boundary_copy(global_policy, ActivePolicy)
        self.active_policy = _boundary_copy(active_policy, ActivePolicyV2)
        self.capabilities = _boundary_copy(capabilities, HostCapabilitiesV2)
        self.loaded_project_policy = load_project_policy(
            self.plan.snapshot.project_root, self.global_policy
        )
        if self.active_policy != self.loaded_project_policy.effective_policy:
            raise WorkflowError("active policy differs from the fixed-root project policy")
        if self.plan.policy_binding != self.loaded_project_policy.binding:
            raise WorkflowError("plan policy identity differs from the fixed-root project policy")
        if self.assessment.policy_binding != self.loaded_project_policy.binding:
            raise WorkflowError("assessment policy identity differs from the fixed-root project policy")
        if self.plan.snapshot.policy_binding != self.loaded_project_policy.binding:
            raise WorkflowError("snapshot policy identity differs from the fixed-root project policy")
        if provider_grant is None or run_resource_grant is None or role_host is None:
            raise WorkflowError("proposal-first execution requires explicit provider, resource, and role-host authority")
        self.provider_grant = _boundary_copy(provider_grant, ProviderGrant)
        self.run_resource_grant = _boundary_copy(run_resource_grant, RunResourceGrant)
        self.resource_grant_history = [self.run_resource_grant]
        self.agent_host = role_host
        self._metadata_loader = metadata_loader or capture_file_metadata
        self.proposal_approvals = [
            _boundary_copy(item, ApprovalV2) for item in (proposal_approvals or [])
        ]
        if semantic_proposal is None:
            raise WorkflowError("proposal-first execution requires the original typed plan semantic proposal")
        self.semantic_proposal = _boundary_copy(semantic_proposal, SemanticAssessmentProposalV2)
        self.policy_binding = self.loaded_project_policy.binding
        self.plan_hash = hash_ref("low-level-plan", self.plan.model_dump(mode="json"), "3.0")
        self.assessment_hash = hash_ref("assessment", self.assessment.model_dump(mode="json"), "3.0")
        self.policy_hash = hash_ref("active-policy", self.active_policy.model_dump(mode="json"), "2.0")
        self.snapshot_hash = hash_ref("repository-snapshot", self.plan.snapshot.model_dump(mode="json"), "3.0")
        self.provider_grant_hash = hash_ref("provider-grant", self.provider_grant.model_dump(mode="json"), "1.0")
        self.run_resource_grant_hash = hash_ref(
            "run-resource-grant", self.run_resource_grant.model_dump(mode="json"), "1.0"
        )
        if not self.assessment.safe:
            raise WorkflowError("rejected plan assessment cannot execute")
        bindings = (
            (self.assessment.plan_hash, self.plan_hash, "plan"),
            (self.assessment.policy_hash, self.policy_hash, "policy"),
            (self.assessment.snapshot_hash, self.snapshot_hash, "snapshot"),
            (self.assessment.provider_grant_hash, self.provider_grant_hash, "provider grant"),
            (self.assessment.run_resource_grant_hash, self.run_resource_grant_hash, "resource grant"),
            (self.plan.provider_grant_hash, self.provider_grant_hash, "plan provider grant"),
            (self.plan.run_resource_grant_hash, self.run_resource_grant_hash, "plan resource grant"),
        )
        mismatches = [name for observed, expected, name in bindings if observed != expected]
        if mismatches:
            raise WorkflowError(f"proposal-first authority bindings differ: {mismatches}")
        if self.assessment.profile != self.capabilities.profile:
            raise WorkflowError("host capability profile differs from the plan assessment")
        required_profiles = set(self.assessment.required_role_assurance_profiles)
        operation_profiles = {
            item.required_assurance_profile
            for item in self.plan.operations
            if item.kind == "bounded_agent_task"
        }
        if operation_profiles != required_profiles:
            raise WorkflowError("assessed role assurance profiles differ from bounded operations")
        reproduced = _assess_plan_legacy_compatible(
            self.plan, self.global_policy, self.active_policy, self.plan.snapshot,
            self.capabilities, self.semantic_proposal, self.assessment.approvals,
            provider_grant=self.provider_grant,
            run_resource_grant=self.run_resource_grant,
        )
        if reproduced != self.assessment:
            raise WorkflowError("execution-time plan reassessment does not reproduce the approved assessment")
        current = self._capture_v2()
        equal, differences = snapshot_materially_equal(self.plan.snapshot, current)
        if self.plan.snapshot.selected_file_metadata_hashes != current.selected_file_metadata_hashes:
            differences.append("selected_file_metadata_hashes")
            equal = False
        if not equal:
            raise WorkflowError(f"repository changed since proposal-first assessment: {differences}")

        control_root = Path(self.plan.snapshot.control_plane_roots[0])
        if control_root.is_symlink():
            raise ControlStateDrift("canonical control root is a symbolic link")
        control_root.mkdir(mode=0o700, exist_ok=True)
        runs_root = _safe_control_directory(control_root, "runs", create=True)
        self.run_root = runs_root / self.plan.run_id
        if self.run_root.is_symlink() or self.run_root.exists():
            raise WorkflowError("run identity already exists; recover an eligible proposal-first run instead")
        self.lease = acquire_lease(
            self.plan.snapshot.project_root, self.plan.run_id, self.plan.snapshot.device_identity, None
        )
        try:
            self.run_root.mkdir(mode=0o700, exist_ok=False)
            self.audit = AuditLog(
                str(self.run_root), self.plan.run_id,
                schema_version="3.0", policy_binding=self.policy_binding,
            )
        except Exception:
            release_lease(self.lease)
            self.lease = None
            raise
        self.bundle_path = self.run_root / "coordinator-bundle.json"
        self._control_root_identity = self._read_control_root_identity()
        self.reports: list[ExecutionReportV2] = []
        self.repair_attempts = []
        self.repair_outcomes = []
        self.pending_repair_attempt = None
        self.proposal_base_snapshot = self.plan.snapshot
        self.repair_base_declared_paths = set()
        self.next_operation_index = 0
        self.current_proposal_context = None
        self.current_agent_proposal = None
        self.current_prepared_patch = None
        self.current_proposal = None
        self.current_preflight = None
        self.current_assessment_context = None
        self.current_exact_changes = []
        self.current_source_inputs = []
        self.current_semantic_patch_proposal = None
        self.current_patch_assessment = None
        self.current_metadata = {}
        self.current_apply_intent = None
        self.role_call_records = []
        self.active_semantic_request_token = None
        self.completed_semantic_request_tokens = []
        self.proposal_history = []
        self.proposal_cycle_history = []
        self.patch_assessment_history = []
        self.apply_intent_history = []
        self.post_execution_snapshot = None
        self.last_verification = None
        self.human_interventions = []
        self._persisted_bundle_hash = None
        self._closed = False
        self._verification_context = None
        self._verification_control_inventory = None
        self._verification_policy_denied_rule_ids = []
        self.manifest = RunManifestV2(
            schema_version="3.0", run_id=self.plan.run_id, state="approved", suspended_from=None,
            plan_hash=self.plan_hash, assessment_hash=self.assessment_hash, policy_hash=self.policy_hash,
            snapshot_hash=self.snapshot_hash, provider_grant_hash=self.provider_grant_hash,
            run_resource_grant_hash=self.run_resource_grant_hash, policy_binding=self.policy_binding,
            current_operation_id=None,
            current_proposal_hash=None, current_patch_assessment_hash=None,
            current_apply_intent_hash=None, event_head_hash=None,
        )
        self._append_event_v2(
            "execution_started", "approved", "executing", "proposal-first coordinator acquired the lease"
        )
        self.manifest = transition(self.manifest, "executing", ["audit:execution_started"])
        self._persist_bundle_v2()

    def _capture_v2(self) -> RepositorySnapshotV2:
        current_policy = load_project_policy(self.plan.snapshot.project_root, self.global_policy)
        if current_policy.binding != self.policy_binding:
            raise WorkflowError("fixed-root project policy changed since assessment")
        self.loaded_project_policy = current_policy
        selected_paths = list(self.plan.snapshot.selected_file_hashes)
        instruction_paths = list(self.plan.snapshot.instruction_hashes)
        base = capture_policy_snapshot(
            self.loaded_project_policy,
            selected_paths,
            instruction_paths,
            self.plan.snapshot.expected_product_changes,
            self.plan.snapshot.control_plane_roots,
            self._metadata_loader,
        )
        return RepositorySnapshotV2.model_validate(base.model_dump(mode="json") | {
            "schema_version": "3.0",
            "proposal_context_observation_hashes": dict(
                self.plan.snapshot.proposal_context_observation_hashes
            ),
        })

    def _append_event_v2(
        self,
        event_type: str,
        lifecycle_from: str | None,
        lifecycle_to: str | None,
        summary: str,
        *,
        operation_id: str | None = None,
        proposal_id: str | None = None,
        attempt_id: str | None = None,
        evidence_ids: list[str] | None = None,
    ) -> None:
        event = self.audit.append(
            EventPayloadV2(
                event_type=event_type, lifecycle_from=lifecycle_from, lifecycle_to=lifecycle_to,
                operation_id=operation_id, proposal_id=proposal_id, attempt_id=attempt_id,
                summary=summary, evidence_ids=evidence_ids or [f"coordinator:{event_type}"],
            ),
            "coordinator_observed",
            {"status": event_type, "run_id": self.plan.run_id, "operation_id": operation_id},
        )
        self.manifest = self.manifest.model_copy(update={"event_head_hash": event.event_record_hash})

    def _bundle_model_v2(self) -> CoordinatorBundleV2:
        host_records = list(self.role_call_records)
        for record in getattr(self.agent_host, "call_records", []):
            if record.call_id not in {item.call_id for item in host_records}:
                host_records.append(record)
        return CoordinatorBundleV2(
            schema_version="3.0", project_root=self.plan.snapshot.project_root, run_id=self.plan.run_id,
            next_operation_index=self.next_operation_index,
            plan=self.plan, plan_assessment=self.assessment,
            plan_semantic_proposal=self.semantic_proposal,
            global_policy=self.global_policy,
            active_policy=self.active_policy, host_capabilities=self.capabilities,
            provider_grant=self.provider_grant, run_resource_grant=self.run_resource_grant,
            resource_grant_history=self.resource_grant_history,
            manifest=self.manifest, plan_hash=self.plan_hash, assessment_hash=self.assessment_hash,
            policy_hash=self.policy_hash, policy_binding=self.policy_binding,
            base_snapshot_hash=self.snapshot_hash,
            host_capabilities_hash=hash_ref(
                "host-capabilities", self.capabilities.model_dump(mode="json"), "3.0"
            ),
            provider_grant_hash=self.provider_grant_hash,
            run_resource_grant_hash=self.run_resource_grant_hash,
            proposal_hash=self.manifest.current_proposal_hash,
            proposal_preflight_hash=(
                None if self.current_preflight is None else hash_ref(
                    "patch-proposal-preflight", self.current_preflight.model_dump(mode="json"), "2.0"
                )
            ),
            patch_assessment_hash=self.manifest.current_patch_assessment_hash,
            proposal_context=self.current_proposal_context,
            agent_proposal=self.current_agent_proposal,
            proposal=self.current_proposal,
            proposal_preflight=self.current_preflight,
            assessment_context=self.current_assessment_context,
            semantic_patch_proposal=self.current_semantic_patch_proposal,
            patch_assessment=self.current_patch_assessment,
            exact_changes=self.current_exact_changes,
            source_inputs=self.current_source_inputs,
            proposal_approvals=self.proposal_approvals,
            apply_intent=self.current_apply_intent,
            proposal_history=self.proposal_history,
            patch_assessment_history=self.patch_assessment_history,
            apply_intent_history=self.apply_intent_history,
            execution_reports=self.reports, repair_attempts=self.repair_attempts,
            repair_outcomes=self.repair_outcomes,
            proposal_cycle_history=self.proposal_cycle_history,
            role_call_records=host_records,
            active_semantic_request_token=self.active_semantic_request_token,
            completed_semantic_request_tokens=self.completed_semantic_request_tokens,
            post_execution_snapshot=self.post_execution_snapshot,
            proposal_base_snapshot=self.proposal_base_snapshot,
            last_verification=self.last_verification,
            human_interventions=self.human_interventions,
        )

    def _persist_bundle_v2(self) -> None:
        data = canonical_bytes(self._bundle_model_v2().model_dump(mode="json")) + b"\n"
        if self.bundle_path.exists():
            existing = self.bundle_path.read_bytes()
            if self._persisted_bundle_hash is None or hashlib.sha256(existing).hexdigest() != self._persisted_bundle_hash:
                raise ControlStateDrift("proposal-first coordinator bundle changed outside the live coordinator")
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

    @classmethod
    def _reload_v2(
        cls,
        *,
        project_root: str,
        run_id: str,
        capabilities: Any,
        role_host: Any,
        provider_grant: ProviderGrant | None,
        run_resource_grant: RunResourceGrant | None,
        metadata_loader: Any | None,
    ) -> "ExecutionCoordinator":
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", run_id) or ".." in run_id:
            raise WorkflowError("invalid proposal-first run identity")
        root = Path(project_root).resolve(strict=True)
        installed_global_policy = default_global_policy(str(root))
        loaded_project_policy = load_project_policy(root, installed_global_policy)
        run_root = root / ".rb-safe-operation" / "runs" / run_id
        if run_root.is_symlink() or not run_root.is_dir():
            raise WorkflowError("proposal-first run directory is missing or unsafe")
        lease_path = root / ".rb-safe-operation" / "execution.lease"
        if lease_path.exists() or lease_path.is_symlink():
            raise WorkflowError("proposal-first recovery cannot take over while a lease exists")
        bundle_path = run_root / "coordinator-bundle.json"
        try:
            persisted = bundle_path.read_bytes()
            payload = parse_json_strict(persisted)
            bundle = CoordinatorBundleV2.model_validate(payload)
        except Exception as exc:
            raise WorkflowError("proposal-first coordinator bundle is missing, invalid, or inconsistent") from exc
        if persisted != canonical_bytes(bundle.model_dump(mode="json")) + b"\n":
            raise WorkflowError("proposal-first coordinator bundle is not canonical")
        if bundle.project_root != str(root) or bundle.run_id != run_id:
            raise WorkflowError("proposal-first bundle project or run identity differs")
        if bundle.global_policy != installed_global_policy:
            raise WorkflowError("persisted global policy differs from the installed baseline")
        if bundle.policy_binding != loaded_project_policy.binding:
            raise WorkflowError("fixed-root project policy changed since the run was assessed")
        if bundle.active_policy != loaded_project_policy.effective_policy:
            raise WorkflowError("persisted effective policy differs from fixed-root policy")
        required = (
            bundle.plan, bundle.plan_assessment, bundle.plan_semantic_proposal,
            bundle.global_policy, bundle.active_policy,
            bundle.host_capabilities, bundle.provider_grant, bundle.run_resource_grant,
        )
        if any(item is None for item in required):
            raise WorkflowError("proposal-first bundle lacks reload authority artifacts")
        supplied_capabilities = _boundary_copy(capabilities, HostCapabilitiesV2)
        if supplied_capabilities != bundle.host_capabilities:
            raise WorkflowError("current host capabilities differ from the persisted proposal-first run")
        if provider_grant is None or _boundary_copy(provider_grant, ProviderGrant) != bundle.provider_grant:
            raise WorkflowError("current provider grant differs from the persisted proposal-first run")
        if run_resource_grant is None:
            raise WorkflowError("proposal-first recovery requires an explicit run resource grant")
        supplied_resource_grant = _boundary_copy(run_resource_grant, RunResourceGrant)
        replenishing = supplied_resource_grant != bundle.run_resource_grant
        if replenishing and not (
            bundle.manifest.state == "paused_resource"
            and supplied_resource_grant.replenishes_grant_id == bundle.run_resource_grant.grant_id
            and supplied_resource_grant.issued_at >= bundle.run_resource_grant.issued_at
        ):
            raise WorkflowError("replacement resource grant is not a valid paused-run replenishment")
        if bundle.manifest.state in {"human_required", "verified", "failed", "abandoned", "rejected"}:
            raise WorkflowError("terminal proposal-first run cannot be resumed")
        audit = AuditLog(
            str(run_root), run_id, schema_version="3.0",
            policy_binding=loaded_project_policy.binding,
        )
        events = audit.validate_chain()
        observed_head = events[-1].event_record_hash if events else None
        audit_head_mismatch = observed_head != bundle.manifest.event_head_hash

        self = cls.__new__(cls)
        self._proposal_first = True
        self.plan = bundle.plan
        self.assessment = bundle.plan_assessment
        self.global_policy = bundle.global_policy
        self.active_policy = bundle.active_policy
        self.loaded_project_policy = loaded_project_policy
        self.policy_binding = loaded_project_policy.binding
        self.capabilities = bundle.host_capabilities
        self.provider_grant = bundle.provider_grant
        self.run_resource_grant = supplied_resource_grant
        self.resource_grant_history = list(bundle.resource_grant_history) or [bundle.run_resource_grant]
        if replenishing:
            self.resource_grant_history.append(supplied_resource_grant)
        self.agent_host = role_host
        self._metadata_loader = metadata_loader or capture_file_metadata
        self.proposal_approvals = bundle.proposal_approvals
        self.role_call_records = list(bundle.role_call_records)
        if self.role_call_records:
            adopt_call_record = getattr(role_host, "adopt_call_record", None)
            if adopt_call_record is None:
                raise WorkflowError("reloaded semantic usage cannot be rebound to host resource accounting")
            for record in self.role_call_records:
                adopt_call_record(record)
        self.active_semantic_request_token = bundle.active_semantic_request_token
        self.completed_semantic_request_tokens = list(bundle.completed_semantic_request_tokens)
        self.semantic_proposal = bundle.plan_semantic_proposal
        self.plan_hash = bundle.plan_hash
        self.assessment_hash = bundle.assessment_hash
        self.policy_hash = bundle.policy_hash
        self.snapshot_hash = bundle.base_snapshot_hash
        self.provider_grant_hash = bundle.provider_grant_hash
        self.run_resource_grant_hash = (
            hash_ref("run-resource-grant", supplied_resource_grant.model_dump(mode="json"), "1.0")
            if replenishing else bundle.run_resource_grant_hash
        )
        self.run_root = run_root
        self.bundle_path = bundle_path
        self.audit = audit
        self.manifest = bundle.manifest.model_copy(update={
            "run_resource_grant_hash": self.run_resource_grant_hash
        })
        self.reports = list(bundle.execution_reports)
        self.repair_attempts = list(bundle.repair_attempts)
        self.repair_outcomes = list(bundle.repair_outcomes)
        self.next_operation_index = bundle.next_operation_index
        self.current_proposal_context = bundle.proposal_context
        self.current_agent_proposal = bundle.agent_proposal
        self.current_proposal = bundle.proposal
        self.current_preflight = bundle.proposal_preflight
        self.current_assessment_context = bundle.assessment_context
        self.current_semantic_patch_proposal = bundle.semantic_patch_proposal
        self.current_patch_assessment = bundle.patch_assessment
        self.current_exact_changes = list(bundle.exact_changes)
        self.current_source_inputs = list(bundle.source_inputs)
        self.current_apply_intent = bundle.apply_intent
        self.proposal_history = list(bundle.proposal_history)
        self.proposal_cycle_history = list(bundle.proposal_cycle_history)
        self.patch_assessment_history = list(bundle.patch_assessment_history)
        self.apply_intent_history = list(bundle.apply_intent_history)
        self.post_execution_snapshot = bundle.post_execution_snapshot
        self.proposal_base_snapshot = bundle.proposal_base_snapshot or self.plan.snapshot
        self.last_verification = bundle.last_verification
        self.human_interventions = list(bundle.human_interventions)
        self.pending_repair_attempt = None
        self.repair_base_declared_paths = set()
        self._verification_context = None
        self._verification_control_inventory = None
        self._verification_policy_denied_rule_ids = []
        self._persisted_bundle_hash = hashlib.sha256(persisted).hexdigest()
        self._closed = False
        self.lease = acquire_lease(
            self.plan.snapshot.project_root, self.plan.run_id,
            self.plan.snapshot.device_identity, self.manifest.event_head_hash,
        )
        self._control_root_identity = self._read_control_root_identity()
        if audit_head_mismatch:
            self._record_unknown_recovery_v2(
                "the append-only audit chain advanced beyond the last durable coordinator bundle; the partial checkpoint will not be replayed"
            )
            raise WorkflowError(
                "proposal-first recovery entered human_required after an interrupted event-to-bundle checkpoint"
            )
        if self.active_semantic_request_token is not None:
            token = self.active_semantic_request_token
            call_root = self.run_root / "semantic-calls" / token
            request_path = call_root / "request.json"
            response_path = call_root / "response.json"
            try:
                if call_root.is_symlink() or not call_root.is_dir() or request_path.is_symlink():
                    raise ValueError("semantic call directory or request is unsafe")
                request_raw = request_path.read_bytes()
                request_payload = parse_json_strict(request_raw)
                role = (
                    request_payload.get("context", {}).get("role")
                    if isinstance(request_payload, dict) else None
                )
                request_type = {
                    "proposer": ProposalRequest,
                    "patch_assessor": PatchAssessmentRequest,
                    "verifier": VerificationRoleRequest,
                }.get(role)
                if request_type is None:
                    raise ValueError("semantic request role is unsupported")
                request = request_type.model_validate(request_payload)
                if request_raw != canonical_bytes(request.model_dump(mode="json")) + b"\n":
                    raise ValueError("semantic request is not canonical")
                if request.context.request_token != token:
                    raise ValueError("semantic request token differs from the active bundle binding")
                if role != "verifier":
                    if response_path.is_file() and not response_path.is_symlink():
                        response_type = (
                            AgentPatchProposal if role == "proposer"
                            else PatchSemanticAssessmentProposal
                        )
                        response_raw = response_path.read_bytes()
                        response = response_type.model_validate(parse_json_strict(response_raw))
                        if response_raw != canonical_bytes(response.model_dump(mode="json")) + b"\n":
                            raise ValueError("semantic response is not canonical")
                        if response.request_token != token:
                            raise ValueError("semantic response token differs from its request")
                        summary = (
                            f"a durable {role} response exists but its lifecycle checkpoint was interrupted; "
                            "the provider call will not be repeated and this run requires human review"
                        )
                    else:
                        summary = (
                            f"a durable {role} request has no durable typed response; "
                            "the provider call will not be repeated"
                        )
                    self._record_unknown_recovery_v2(summary)
                    raise WorkflowError(
                        f"proposal-first recovery entered human_required at an incomplete {role} call"
                    )
                if not response_path.is_file() or response_path.is_symlink():
                    self._record_unknown_recovery_v2(
                        "a durable verifier request has no durable typed response; the provider call will not be repeated"
                    )
                    raise WorkflowError(
                        "proposal-first recovery entered human_required at an incomplete verifier call"
                    )
                response_raw = response_path.read_bytes()
                response = VerificationRoleResponse.model_validate(parse_json_strict(response_raw))
                if response_raw != canonical_bytes(response.model_dump(mode="json")) + b"\n":
                    raise ValueError("semantic response is not canonical")
                if response.request_token != token:
                    raise ValueError("semantic response token differs from the active bundle binding")
                if (
                    request.plan != self.plan
                    or request.assessment != self.assessment
                    or request.active_policy != self.active_policy
                    or request.provider_grant != self.provider_grant
                    or request.run_resource_grant != self.run_resource_grant
                ):
                    raise ValueError("persisted verifier packet differs from recovered run authority")
                if self.manifest.state != "verifying":
                    raise ValueError("completed semantic response is not bound to a verifying lifecycle")
                context = VerificationContext(
                    context_id=request.verifier_context_id,
                    token=token,
                    plan_hash=self.plan_hash,
                    assessment_hash=self.assessment_hash,
                    snapshot_hash=hash_ref(
                        "repository-snapshot",
                        request.post_execution_snapshot.model_dump(mode="json"),
                        "3.0",
                    ),
                )
                _VERIFICATION_CONTEXTS[token] = (
                    self.plan_hash.value, self.assessment_hash.value,
                    context.context_id, context.snapshot_hash.value,
                )
                self._verification_context = context
                self._verification_control_inventory = self._control_inventory()
                self.active_semantic_request_token = None
                self.completed_semantic_request_tokens.append(token)
                self._verify_v2(response.verification_proposal, context)
                return self
            except WorkflowError:
                raise
            except Exception as exc:
                self._record_unknown_recovery_v2(
                    "persisted verifier call records are malformed, stale, or inconsistent"
                )
                raise WorkflowError(
                    "proposal-first recovery entered human_required at an invalid verifier call"
                ) from exc
        if replenishing:
            self._append_event_v2(
                "resource_replenished", "paused_resource", "paused_resource",
                "a newly identified finite resource grant replenished the paused run",
                operation_id=self.manifest.current_operation_id,
                evidence_ids=[f"run-resource-grant:{self.run_resource_grant_hash.value}"],
            )
            self._persist_bundle_v2()

        recoverable_current_proposal = (
            self.current_proposal is not None
            and self.next_operation_index < len(self.plan.operations)
            and self.manifest.state in {"proposal_approved", "applying_proposal", "paused_resource"}
        )
        if recoverable_current_proposal:
            if self.current_agent_proposal is None or not self.current_exact_changes:
                self._record_unknown_recovery_v2("current proposal lacks exact persisted patch material")
                raise WorkflowError("proposal-first recovery entered human_required: incomplete patch material")
            preimages = {
                item.path: item.preimage.encode("utf-8")
                for item in self.current_exact_changes if item.preimage is not None
            }
            self.current_prepared_patch = prepare_text_patch(
                self.current_agent_proposal.unified_diff,
                Path(self.plan.operations[self.next_operation_index].path_contract.working_directories[0]),
                preimages,
            )
            if self.current_prepared_patch.patch_hash != self.current_proposal.patch_hash:
                self._record_unknown_recovery_v2("persisted patch bytes differ from the proposal hash")
                raise WorkflowError("proposal-first recovery entered human_required: patch hash conflict")
        else:
            self.current_prepared_patch = None
        recoverable_exact_apply = (
            self.current_apply_intent is not None
            and self.current_apply_intent.execution_kind == "exact"
            and self.manifest.state in {"executing", "paused_resource"}
            and self.next_operation_index < len(self.plan.operations)
        )
        if recoverable_exact_apply:
            operation = self.plan.operations[self.next_operation_index]
            if (
                operation.kind != "exact_action"
                or operation.adapter != "apply_patch"
                or self.current_apply_intent.operation_id != operation.operation_id
                or self.current_apply_intent.operation_hash != hash_ref(
                    "operation", operation.model_dump(mode="json"), "2.0"
                )
            ):
                self._record_unknown_recovery_v2("exact apply intent differs from the selected operation")
                raise WorkflowError("proposal-first recovery entered human_required: exact operation conflict")
            preimages = {
                item.path: item.preimage.encode("utf-8")
                for item in self.current_exact_changes if item.preimage is not None
            }
            self.current_prepared_patch = prepare_text_patch(
                operation.patch,
                Path(operation.path_contract.working_directories[0]),
                preimages,
            )
        self.current_metadata = {}

        recovering_apply = self.current_apply_intent is not None and (
            self.manifest.state == "applying_proposal"
            or recoverable_exact_apply
            or (
                self.manifest.state == "paused_resource"
                and self.manifest.suspended_from == "applying_proposal"
            )
        )
        if recovering_apply:
            states = self._classify_apply_targets_v2()
            prefix = 0
            while prefix < len(states) and states[prefix] == "postimage":
                prefix += 1
            if any(value != "preimage" for value in states[prefix:]):
                self._record_unknown_recovery_v2(f"target states are not a known committed prefix: {states}")
                raise WorkflowError("proposal-first recovery entered human_required: unknown target state")
            if self.current_apply_intent.committed_targets != self.current_apply_intent.ordered_targets[:prefix]:
                self.current_apply_intent = self.current_apply_intent.model_copy(update={
                    "committed_targets": self.current_apply_intent.ordered_targets[:prefix],
                    "state": "committing" if prefix else "prepared",
                })
                self.manifest = self.manifest.model_copy(update={
                    "current_apply_intent_hash": hash_ref(
                        "apply-intent", self.current_apply_intent.model_dump(mode="json"), "2.0"
                    )
                })
            remaining = self.current_prepared_patch.targets[prefix:]
            self.current_metadata = {
                str(item.path): self._metadata_loader(item.path)
                for item in remaining if item.action in {"modify", "delete"}
            }
            self._append_event_v2(
                "recovery_classified", self.manifest.state, self.manifest.state,
                "recovery found an exact committed postimage prefix followed by exact preimages",
                operation_id=self.current_apply_intent.operation_id,
                proposal_id=None if self.current_proposal is None else self.current_proposal.proposal_id,
                evidence_ids=[f"committed-prefix:{prefix}"],
            )
            self._persist_bundle_v2()
        elif self.manifest.state == "proposal_approved" or (
            self.manifest.state == "paused_resource"
            and self.manifest.suspended_from in {"assessing_proposal", "proposal_approved"}
        ):
            self.current_metadata = {
                str(item.path): self._metadata_loader(item.path)
                for item in self.current_prepared_patch.targets if item.action in {"modify", "delete"}
            }
        elif self.manifest.state not in {"executing", "verifying", "repairing", "paused_resource"}:
            self._record_unknown_recovery_v2(
                f"interrupted lifecycle {self.manifest.state} has no safely resumable checkpoint"
            )
            raise WorkflowError("proposal-first recovery entered human_required at an incomplete semantic call")
        return self

    def _classify_apply_targets_v2(self) -> list[str]:
        if self.current_apply_intent is None:
            raise WorkflowError("recovery classification requires an apply intent")
        states: list[str] = []
        for path in self.current_apply_intent.ordered_targets:
            target = Path(path)
            action = (
                "create" if self.current_apply_intent.preimage_hashes[path] is None
                else "delete" if self.current_apply_intent.postimage_hashes[path] is None
                else "modify"
            )
            if action != "create":
                read_decision = require_path(self.loaded_project_policy, target, "read")
                revalidate_decision(self.loaded_project_policy, read_decision)
            require_path(self.loaded_project_policy, target, action)
            if target.exists() and target.is_file() and not target.is_symlink():
                observed = hashlib.sha256(target.read_bytes()).hexdigest()
            elif not target.exists() and not target.is_symlink():
                observed = None
            else:
                states.append("unknown")
                continue
            preimage = self.current_apply_intent.preimage_hashes[path]
            postimage = self.current_apply_intent.postimage_hashes[path]
            if observed == postimage:
                states.append("postimage")
            elif observed == preimage:
                states.append("preimage")
            else:
                states.append("unknown")
        return states

    def _record_unknown_recovery_v2(self, summary: str) -> None:
        prior = self.manifest.state
        self._append_event_v2(
            "recovery_classified", prior, "human_required", summary,
            operation_id=self.manifest.current_operation_id,
            proposal_id=None if self.current_proposal is None else self.current_proposal.proposal_id,
            evidence_ids=["recovery:unknown-state"],
        )
        self.manifest = transition(self.manifest, "human_required", ["audit:recovery_classified"])
        self._append_human_intervention_v2(
            "inspect_indeterminate_state" if self.current_apply_intent is not None else "revise_and_reassess",
            summary,
        )
        self._persist_bundle_v2()
        if self.lease is not None:
            release_lease(self.lease)
            self.lease = None
        self._closed = True

    def _append_human_intervention_v2(self, decision_type: str, rationale: str) -> None:
        proposal_hash = (
            None if self.current_proposal is None
            else hash_ref("bounded-patch-proposal", self.current_proposal.model_dump(mode="json"), "2.0")
        )
        assessment_hash = (
            None if self.current_patch_assessment is None
            else hash_ref("patch-assessment", self.current_patch_assessment.model_dump(mode="json"), "2.0")
        )
        intent_hash = (
            None if self.current_apply_intent is None
            else hash_ref("apply-intent", self.current_apply_intent.model_dump(mode="json"), "2.0")
        )
        timestamp = datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")
        record = HumanInterventionV2(
            schema_version="3.0", decision_type=decision_type,
            plan_hash=self.plan_hash, assessment_hash=self.assessment_hash,
            policy_hash=self.policy_hash, snapshot_hash=self.snapshot_hash,
            proposal_hash=proposal_hash, patch_assessment_hash=assessment_hash,
            apply_intent_hash=intent_hash, operation_id=self.manifest.current_operation_id,
            effect_id=None, timestamp=timestamp, rationale=rationale,
            resulting_version_or_outcome="same run is terminal; a new assessed run is required",
            approval_expiry=None, idempotency_key=None, principal=None,
            identity_verification="unavailable",
            policy_binding=self.policy_binding,
        )
        record_hash = artifact_hash("human-intervention", "3.0", record.model_dump(mode="json"))
        if record_hash not in {
            artifact_hash("human-intervention", "3.0", item.model_dump(mode="json"))
            for item in self.human_interventions
        }:
            self.human_interventions.append(record)

    @classmethod
    def reload(
        cls,
        project_root: str,
        run_id: str,
        capabilities: HostCapabilities | HostCapabilitiesV2,
        agent_host: Any | None = None,
        provider_grant: ProviderGrant | None = None,
        run_resource_grant: RunResourceGrant | None = None,
        metadata_loader: Any | None = None,
    ) -> "ExecutionCoordinator":
        """Reload a durably paused coordinator after validating every persisted identity."""
        if getattr(capabilities, "schema_version", None) == "3.0":
            return cls._reload_v2(
                project_root=project_root, run_id=run_id, capabilities=capabilities,
                role_host=agent_host, provider_grant=provider_grant,
                run_resource_grant=run_resource_grant, metadata_loader=metadata_loader,
            )
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
        except Exception as exc:
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
        revalidation = _assess_plan_legacy_compatible(
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

    def _declared_paths_v2(self) -> set[str]:
        declared: set[str] = set(getattr(self, "repair_base_declared_paths", set()))
        for report in self.reports:
            declared.update(report.committed_postimage_hashes)
        for intent in self.apply_intent_history:
            for path, postimage in intent.postimage_hashes.items():
                if postimage is None and path in intent.committed_targets:
                    declared.add(path)
        return declared

    def _proposal_state_guard_v2(self, baseline: RepositorySnapshotV2, control: dict[str, str], stage: str) -> None:
        current = self._capture_v2()
        equal, differences = snapshot_materially_equal(baseline, current)
        if not equal:
            raise ProposalSafetyRejected(f"proposal-only role changed product state during {stage}: {differences}")
        if self._control_inventory() != control:
            raise ControlStateDrift("proposal-only role changed protected control state")

    def _proposal_checkpoint_v2(self, operation: Any, stage: str, payload: object) -> None:
        attempt_id = "attempt-initial" if self.pending_repair_attempt is None else self.pending_repair_attempt.attempt_id
        if stage == "proposer_requested":
            request = payload
            self._persist_semantic_call_artifact(
                request.context.request_token, "request.json", request
            )
            self.active_semantic_request_token = request.context.request_token
        elif stage == "proposal_received":
            context, agent, prepared, proposal, metadata, exact_changes, source_inputs = payload
            self._persist_semantic_call_artifact(
                context.request_token, "response.json", agent
            )
            if self.active_semantic_request_token != context.request_token:
                raise WorkflowError("proposer response differs from the active semantic request")
            self.active_semantic_request_token = None
            self.completed_semantic_request_tokens.append(context.request_token)
            self.current_proposal_context = context
            self.current_agent_proposal = agent
            self.current_prepared_patch = prepared
            self.current_proposal = proposal
            self.current_metadata = metadata
            self.current_exact_changes = exact_changes
            self.current_source_inputs = source_inputs
            proposal_hash = hash_ref("bounded-patch-proposal", proposal.model_dump(mode="json"), "2.0")
            self.manifest = self.manifest.model_copy(update={
                "current_operation_id": operation.operation_id,
                "current_proposal_hash": proposal_hash,
            })
            self._append_event_v2(
                "proposal_received", "proposing", "validating_proposal",
                "coordinator accepted one canonical proposal for deterministic validation",
                operation_id=operation.operation_id, proposal_id=proposal.proposal_id, attempt_id=attempt_id,
                evidence_ids=[f"bounded-patch-proposal:{proposal_hash.value}"],
            )
            self.manifest = transition(self.manifest, "validating_proposal", ["audit:proposal_received"])
        elif stage == "preflight_complete":
            _, proposal, preflight, metadata = payload
            self.current_proposal = proposal
            self.current_preflight = preflight
            self.current_metadata = metadata
            preflight_hash = hash_ref(
                "patch-proposal-preflight", preflight.model_dump(mode="json"), "2.0"
            )
            event_type = "proposal_preflight_passed" if preflight.deterministic_pass else "proposal_preflight_failed"
            target = "assessing_proposal" if preflight.deterministic_pass else "human_required"
            self._append_event_v2(
                event_type, "validating_proposal", target,
                "deterministic proposal preflight completed",
                operation_id=operation.operation_id, proposal_id=proposal.proposal_id, attempt_id=attempt_id,
                evidence_ids=[f"patch-proposal-preflight:{preflight_hash.value}"],
            )
            self.manifest = transition(self.manifest, target, [f"audit:{event_type}"])
        elif stage == "assessment_requested":
            self.current_assessment_context, self.current_exact_changes, request = payload
            self._persist_semantic_call_artifact(
                request.context.request_token, "request.json", request
            )
            self.active_semantic_request_token = request.context.request_token
            self._append_event_v2(
                "semantic_assessment_requested", "assessing_proposal", "assessing_proposal",
                "fresh no-tool semantic patch assessment requested",
                operation_id=operation.operation_id, proposal_id=self.current_proposal.proposal_id,
                attempt_id=attempt_id,
            )
        elif stage == "assessment_complete":
            semantic, assessment = payload
            if self.current_assessment_context is None:
                raise WorkflowError("patch assessor response lacks a durable request context")
            token = self.current_assessment_context.request_token
            self._persist_semantic_call_artifact(token, "response.json", semantic)
            if self.active_semantic_request_token != token:
                raise WorkflowError("patch assessor response differs from the active semantic request")
            self.active_semantic_request_token = None
            self.completed_semantic_request_tokens.append(token)
            self.current_semantic_patch_proposal = semantic
            self.current_patch_assessment = assessment
            assessment_hash = hash_ref("patch-assessment", assessment.model_dump(mode="json"), "2.0")
            self.manifest = self.manifest.model_copy(update={"current_patch_assessment_hash": assessment_hash})
            event_type = "proposal_approved" if assessment.safe else "proposal_assessment_rejected"
            target = "proposal_approved" if assessment.safe else "human_required"
            self._append_event_v2(
                event_type, "assessing_proposal", target, "semantic patch assessment completed",
                operation_id=operation.operation_id, proposal_id=self.current_proposal.proposal_id,
                attempt_id=attempt_id, evidence_ids=[f"patch-assessment:{assessment_hash.value}"],
            )
            self.manifest = transition(self.manifest, target, [f"audit:{event_type}"])
        else:
            raise WorkflowError(f"unknown proposal checkpoint: {stage}")
        self._persist_bundle_v2()

    def _selected_proposal_approvals_v2(self, operation: Any) -> list[ApprovalV2]:
        if self.current_proposal is None or self.current_patch_assessment is None:
            raise WorkflowError("proposal approvals require an accepted proposal and patch assessment")
        required = self._required_approval_bindings(operation)
        if not required:
            return []
        proposal_hash = hash_ref("bounded-patch-proposal", self.current_proposal.model_dump(mode="json"), "2.0")
        assessment_hash = hash_ref("patch-assessment", self.current_patch_assessment.model_dump(mode="json"), "2.0")
        operation_hash = hash_ref("operation", operation.model_dump(mode="json"), "2.0")
        now = datetime.now(timezone.utc)
        selected: list[ApprovalV2] = []
        for effect, approval_class, target in required:
            matches = []
            for approval in self.proposal_approvals:
                expiry_valid = approval.expires_at is None or datetime.strptime(
                    approval.expires_at, "%Y-%m-%dT%H:%M:%SZ"
                ).replace(tzinfo=timezone.utc) > now
                if (
                    approval.plan_hash == self.plan_hash
                    and approval.operation_hash == operation_hash
                    and approval.policy_hash == self.policy_hash
                    and approval.snapshot_hash == self.snapshot_hash
                    and approval.proposal_hash == proposal_hash
                    and approval.patch_assessment_hash == assessment_hash
                    and approval.effect_id == effect.effect_id
                    and approval.effect_class == effect.effect_class
                    and approval.approval_class == approval_class
                    and approval.target == target
                    and not approval.consumed
                    and approval.idempotency_key is not None
                    and expiry_valid
                ):
                    matches.append(approval)
            if len(matches) != 1:
                raise WorkflowError("proposal-bound approval is missing, stale, or ambiguous at commit")
            selected.append(matches[0])
        if len({item.approval_id for item in selected}) != len(selected):
            raise WorkflowError("one proposal approval cannot authorize multiple exact bindings")
        if len({item.idempotency_key for item in selected}) != len(selected):
            raise WorkflowError("proposal approval idempotency keys must be unique")
        return selected

    def _selected_exact_approvals_v2(self, operation: Any) -> list[Approval]:
        operation_hash = hash_ref("operation", operation.model_dump(mode="json"), "2.0")
        now = datetime.now(timezone.utc)
        selected: list[Approval] = []
        for effect, approval_class, target in self._required_approval_bindings(operation):
            idempotency_required = (
                effect.exposure in {"project_external", "multi_party", "systemic"}
                or effect.reversibility in {"uncertain", "none"}
                or effect.effect_class == "external_write"
            )
            matches = [approval for approval in self.assessment.approvals if (
                approval.plan_hash == self.plan_hash
                and approval.operation_hash == operation_hash
                and approval.policy_hash == self.policy_hash
                and approval.snapshot_hash == self.snapshot_hash
                and approval.effect_id == effect.effect_id
                and approval.effect_class == effect.effect_class
                and approval.approval_class == approval_class
                and approval.target == target
                and not approval.consumed
                and (
                    approval.expires_at is None
                    or datetime.strptime(approval.expires_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                    > now
                )
                and (not idempotency_required or bool(approval.idempotency_key))
            )]
            if len(matches) != 1:
                raise WorkflowError("exact-operation approval is missing, stale, or ambiguous at commit")
            selected.append(matches[0])
        if len({item.approval_id for item in selected}) != len(selected):
            raise WorkflowError("one exact-operation approval cannot authorize multiple bindings")
        idempotency_keys = [item.idempotency_key for item in selected if item.idempotency_key is not None]
        if len(idempotency_keys) != len(set(idempotency_keys)):
            raise WorkflowError("exact-operation approval idempotency keys must be unique")
        return selected

    def _consume_exact_approvals_v2(self, approvals: list[Approval]) -> None:
        if not approvals:
            return
        root = self._approval_root(create=True)
        for approval in approvals:
            payload = approval.model_dump(mode="json") | {"consumed_for_apply_intent": True}
            target = root / f"{approval.approval_id}.consumed"
            expected = canonical_bytes(payload) + b"\n"
            if target.exists():
                if target.is_symlink() or not target.is_file() or target.read_bytes() != expected:
                    raise WorkflowError("exact-operation approval consumption record is conflicting or corrupt")
                continue
            descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(expected)
                handle.flush()
                os.fsync(handle.fileno())
        directory = os.open(root, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)

    def _consume_proposal_approvals_v2(self, operation: Any, approvals: list[ApprovalV2]) -> None:
        if not approvals:
            return
        root = self._approval_root(create=True)
        for approval in approvals:
            payload = approval.model_dump(mode="json") | {"consumed_for_apply_intent": True}
            target = root / f"{approval.approval_id}.consumed"
            expected = canonical_bytes(payload) + b"\n"
            if target.exists():
                if target.is_symlink() or not target.is_file() or target.read_bytes() != expected:
                    raise WorkflowError("proposal approval consumption record is conflicting or corrupt")
                continue
            descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(expected)
                handle.flush()
                os.fsync(handle.fileno())
        directory = os.open(root, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)

    def _refresh_policy_binding_v2(self) -> None:
        loaded = load_project_policy(self.plan.snapshot.project_root, self.global_policy)
        if loaded.binding != self.policy_binding or loaded.effective_policy != self.active_policy:
            raise WorkflowError("fixed-root project policy changed before an observation or action")
        self.loaded_project_policy = loaded

    def _require_operation_paths_v2(self, operation: Any) -> None:
        self._refresh_policy_binding_v2()
        if operation.adapter == "read_file":
            require_path(self.loaded_project_policy, operation.path, "read")
            return
        if operation.adapter != "apply_patch":
            return
        for path in operation.expected_created_paths:
            require_path(self.loaded_project_policy, path, "create")
        for path in operation.expected_modified_paths:
            require_path(self.loaded_project_policy, path, "read")
            require_path(self.loaded_project_policy, path, "modify")
        for path in operation.expected_deleted_paths:
            require_path(self.loaded_project_policy, path, "read")
            require_path(self.loaded_project_policy, path, "delete")

    def _execute_exact_v2(self, operation: Any) -> ExecutionReportV2:
        self._require_operation_paths_v2(operation)
        if operation.adapter == "read_file":
            resolved = resolve_contained(
                operation.path, operation.path_contract.read_roots,
                operation.path_contract.protected_roots,
            )
            read_decision = require_path(
                self.loaded_project_policy, resolved.resolved, "read"
            )
            revalidate_decision(self.loaded_project_policy, read_decision)
            content = Path(resolved.resolved).read_bytes()[operation.byte_start:operation.byte_end]
            if operation.expected_hash and hashlib.sha256(content).hexdigest() != operation.expected_hash:
                raise WorkflowError("read_file content hash mismatch")
            committed = {}
        elif operation.adapter == "apply_patch":
            cwd = Path(operation.path_contract.working_directories[0])
            approvals = self._selected_exact_approvals_v2(operation)
            if self.current_apply_intent is None:
                preimages: dict[str, bytes] = {}
                for path in operation.preimage_hashes:
                    read_decision = require_path(self.loaded_project_policy, path, "read")
                    revalidate_decision(self.loaded_project_policy, read_decision)
                    preimages[path] = Path(path).read_bytes()
                prepared = prepare_text_patch(operation.patch, cwd, preimages)
                metadata = {
                    path: self._metadata_loader(Path(path))
                    for path in set(prepared.modified_paths) | set(prepared.deleted_paths)
                }
                self.current_prepared_patch = prepared
                self.current_metadata = metadata
                self.current_exact_changes = [ExactProposedChange(
                    path=str(item.path), action=item.action,
                    preimage=None if item.preimage is None else item.preimage.decode("utf-8"),
                    postimage=None if item.postimage is None else item.postimage.decode("utf-8"),
                    preimage_hash=item.preimage_hash, postimage_hash=item.postimage_hash,
                    metadata_hash=(
                        None if item.action == "create"
                        else metadata_fingerprint_hash(metadata[str(item.path)])
                    ),
                ) for item in prepared.targets]
                operation_hash = hash_ref("operation", operation.model_dump(mode="json"), "2.0")
                self.current_apply_intent = ApplyIntent(
                    schema_version="2.0", intent_id=f"intent-{operation_hash.value[:24]}",
                    operation_id=operation.operation_id, execution_kind="exact",
                    operation_hash=operation_hash, proposal_hash=None, patch_assessment_hash=None,
                    approval_hashes=[
                        hash_ref("approval", item.model_dump(mode="json"), "3.0")
                        for item in approvals
                    ],
                    ordered_targets=[str(item.path) for item in prepared.targets],
                    preimage_hashes={str(item.path): item.preimage_hash for item in prepared.targets},
                    postimage_hashes={str(item.path): item.postimage_hash for item in prepared.targets},
                    committed_targets=[], state="prepared", policy_binding=self.policy_binding,
                )
                self.manifest = self.manifest.model_copy(update={
                    "current_operation_id": operation.operation_id,
                    "current_apply_intent_hash": hash_ref(
                        "apply-intent", self.current_apply_intent.model_dump(mode="json"), "2.0"
                    ),
                })
                self._append_event_v2(
                    "apply_intent_recorded", "executing", "executing",
                    "durable exact-patch apply intent recorded before mutation",
                    operation_id=operation.operation_id,
                    evidence_ids=[f"apply-intent:{self.manifest.current_apply_intent_hash.value}"],
                )
                self._persist_bundle_v2()
            else:
                if (
                    self.current_apply_intent.execution_kind != "exact"
                    or self.current_apply_intent.operation_id != operation.operation_id
                    or self.current_prepared_patch is None
                ):
                    raise WorkflowError("current exact apply intent differs from the selected operation")
                prepared = self.current_prepared_patch
                metadata = self.current_metadata

            self._consume_exact_approvals_v2(approvals)
            self._require_operation_paths_v2(operation)

            def exact_committed_target(target):
                self.current_apply_intent = self.current_apply_intent.model_copy(update={
                    "committed_targets": self.current_apply_intent.committed_targets + [str(target.path)],
                    "state": "committing",
                })
                self.manifest = self.manifest.model_copy(update={
                    "current_apply_intent_hash": hash_ref(
                        "apply-intent", self.current_apply_intent.model_dump(mode="json"), "2.0"
                    )
                })
                self._append_event_v2(
                    "target_committed", "executing", "executing",
                    "one ordered exact-patch target reached its postimage",
                    operation_id=operation.operation_id,
                    evidence_ids=[f"postimage:{target.postimage_hash or 'deleted'}"],
                )
                self._persist_bundle_v2()

            def exact_policy_check(path: Path, capability: str) -> None:
                self._refresh_policy_binding_v2()
                require_path(self.loaded_project_policy, path, capability)

            commit_prepared_text_patch(
                prepared, metadata, created_file_mode=operation.created_file_mode,
                metadata_loader=self._metadata_loader,
                policy_check=exact_policy_check,
                start_index=len(self.current_apply_intent.committed_targets),
                checkpoint=exact_committed_target,
            )
            self.current_apply_intent = self.current_apply_intent.model_copy(update={"state": "committed"})
            self.manifest = self.manifest.model_copy(update={
                "current_apply_intent_hash": hash_ref(
                    "apply-intent", self.current_apply_intent.model_dump(mode="json"), "2.0"
                )
            })
            if self.current_apply_intent.intent_id not in {item.intent_id for item in self.apply_intent_history}:
                self.apply_intent_history.append(self.current_apply_intent)
            committed = {
                str(item.path): item.postimage_hash for item in prepared.targets if item.postimage_hash
            }
        else:
            raise WorkflowError("proposal-first runtime supports exact read_file and apply_patch only")
        return ExecutionReportV2(
            schema_version="3.0", operation_id=operation.operation_id, execution_kind="exact",
            proposal_hash=None, patch_assessment_hash=None, success=True, evidence=[],
            expected_effect_ids_observed=[item.effect_id for item in operation.effects],
            unexpected_effects=[], committed_postimage_hashes=committed,
            provenance="coordinator_observed", next_strategy=None,
            policy_binding=self.policy_binding,
        )

    def _clear_current_operation_v2(self) -> None:
        self.current_proposal_context = None
        self.current_agent_proposal = None
        self.current_prepared_patch = None
        self.current_proposal = None
        self.current_preflight = None
        self.current_assessment_context = None
        self.current_exact_changes = []
        self.current_source_inputs = []
        self.current_semantic_patch_proposal = None
        self.current_patch_assessment = None
        self.current_metadata = {}
        self.current_apply_intent = None
        self.manifest = self.manifest.model_copy(update={
            "current_operation_id": None,
            "current_proposal_hash": None,
            "current_patch_assessment_hash": None,
            "current_apply_intent_hash": None,
        })

    def _commit_current_proposal_v2(self, operation: Any) -> ExecutionReportV2:
        if (
            self.current_proposal is None
            or self.current_patch_assessment is None
            or self.current_prepared_patch is None
            or not self.current_patch_assessment.safe
        ):
            raise WorkflowError("commit requires one complete approved prepared proposal")
        self._revalidate_current_proposal_v2(operation)
        proposal_hash = hash_ref(
            "bounded-patch-proposal", self.current_proposal.model_dump(mode="json"), "2.0"
        )
        patch_assessment_hash = hash_ref(
            "patch-assessment", self.current_patch_assessment.model_dump(mode="json"), "2.0"
        )
        approvals = self._selected_proposal_approvals_v2(operation)
        if self.current_apply_intent is None:
            intent = ApplyIntent(
                schema_version="2.0", intent_id=f"intent-{proposal_hash.value[:24]}",
                operation_id=operation.operation_id, execution_kind="bounded_proposal",
                operation_hash=hash_ref("operation", operation.model_dump(mode="json"), "2.0"),
                proposal_hash=proposal_hash,
                patch_assessment_hash=patch_assessment_hash,
                approval_hashes=[hash_ref("approval", item.model_dump(mode="json"), "3.0") for item in approvals],
                ordered_targets=[str(item.path) for item in self.current_prepared_patch.targets],
                preimage_hashes={str(item.path): item.preimage_hash for item in self.current_prepared_patch.targets},
                postimage_hashes={str(item.path): item.postimage_hash for item in self.current_prepared_patch.targets},
                committed_targets=[], state="prepared", policy_binding=self.policy_binding,
            )
            self.current_apply_intent = intent
            intent_hash = hash_ref("apply-intent", intent.model_dump(mode="json"), "2.0")
            self.manifest = self.manifest.model_copy(update={"current_apply_intent_hash": intent_hash})
            self._append_event_v2(
                "apply_intent_recorded", "proposal_approved", "applying_proposal",
                "durable apply intent recorded before mutation", operation_id=operation.operation_id,
                proposal_id=self.current_proposal.proposal_id,
                evidence_ids=[f"apply-intent:{intent_hash.value}"],
            )
            self.manifest = transition(self.manifest, "applying_proposal", ["audit:apply_intent_recorded"])
            self._persist_bundle_v2()
        elif self.manifest.state != "applying_proposal":
            raise WorkflowError("persisted apply intent is not in the applying lifecycle state")
        self._consume_proposal_approvals_v2(operation, approvals)
        self._refresh_policy_binding_v2()
        for target in self.current_prepared_patch.targets:
            if target.action != "create":
                require_path(self.loaded_project_policy, target.path, "read")
            require_path(self.loaded_project_policy, target.path, target.action)
        start_index = len(self.current_apply_intent.committed_targets)

        def committed_target(target):
            self.current_apply_intent = self.current_apply_intent.model_copy(update={
                "committed_targets": self.current_apply_intent.committed_targets + [str(target.path)],
                "state": "committing",
            })
            self.manifest = self.manifest.model_copy(update={
                "current_apply_intent_hash": hash_ref(
                    "apply-intent", self.current_apply_intent.model_dump(mode="json"), "2.0"
                )
            })
            self._append_event_v2(
                "target_committed", "applying_proposal", "applying_proposal",
                "one ordered proposal target reached its postimage", operation_id=operation.operation_id,
                proposal_id=self.current_proposal.proposal_id,
                evidence_ids=[f"postimage:{target.postimage_hash or 'deleted'}"],
            )
            self._persist_bundle_v2()

        def proposal_policy_check(path: Path, capability: str) -> None:
            self._refresh_policy_binding_v2()
            require_path(self.loaded_project_policy, path, capability)

        commit_prepared_text_patch(
            self.current_prepared_patch, self.current_metadata,
            created_file_mode=operation.created_file_mode, checkpoint=committed_target,
            policy_check=proposal_policy_check,
            metadata_loader=self._metadata_loader, start_index=start_index,
        )
        self.current_apply_intent = self.current_apply_intent.model_copy(update={"state": "committed"})
        self.manifest = self.manifest.model_copy(update={
            "current_apply_intent_hash": hash_ref(
                "apply-intent", self.current_apply_intent.model_dump(mode="json"), "2.0"
            )
        })
        report = ExecutionReportV2(
            schema_version="3.0", operation_id=operation.operation_id,
            execution_kind="bounded_proposal", proposal_hash=proposal_hash,
            patch_assessment_hash=patch_assessment_hash, success=True,
            evidence=self.current_proposal.evidence,
            expected_effect_ids_observed=self.current_proposal.expected_effect_ids,
            unexpected_effects=[], committed_postimage_hashes=self.current_proposal.postimage_hashes,
            provenance="coordinator_observed", next_strategy=None,
            policy_binding=self.policy_binding,
        )
        if self.current_proposal.proposal_id not in {item.proposal_id for item in self.proposal_history}:
            required_cycle = (
                self.current_proposal_context,
                self.current_agent_proposal,
                self.current_preflight,
                self.current_assessment_context,
                self.current_semantic_patch_proposal,
            )
            if any(item is None for item in required_cycle):
                raise WorkflowError("committed proposal lacks complete durable proposal-cycle evidence")
            self.proposal_cycle_history.append(ProposalCycleRecord(
                schema_version="2.0",
                cycle_id=f"cycle-{proposal_hash.value[:24]}",
                operation_id=operation.operation_id,
                attempt_id=self.current_proposal_context.attempt_id,
                proposal_context=self.current_proposal_context,
                agent_proposal=self.current_agent_proposal,
                proposal=self.current_proposal,
                proposal_preflight=self.current_preflight,
                assessment_context=self.current_assessment_context,
                semantic_patch_proposal=self.current_semantic_patch_proposal,
                patch_assessment=self.current_patch_assessment,
                exact_changes=list(self.current_exact_changes),
                source_inputs=list(self.current_source_inputs),
                apply_intent=self.current_apply_intent,
                execution_report=report,
                policy_binding=self.policy_binding,
            ))
            self.proposal_history.append(self.current_proposal)
            self.patch_assessment_history.append(self.current_patch_assessment)
            self.apply_intent_history.append(self.current_apply_intent)
        self.manifest = transition(self.manifest, "executing", ["coordinator:commit-complete"])
        return report

    def _revalidate_current_proposal_v2(self, operation: Any) -> None:
        """Recheck every proposal authority and source observation at commit time."""

        if self.lease is None:
            raise WorkflowError("proposal commit requires the live project lease")
        self._heartbeat()
        self._assert_control_root_identity()
        self._refresh_policy_binding_v2()
        if self.current_proposal_context is None or self.current_agent_proposal is None:
            raise WorkflowError("proposal commit lacks the exact proposer context and response")
        context = self.current_proposal_context
        expected = {
            "plan_hash": self.plan_hash,
            "plan_assessment_hash": self.assessment_hash,
            "operation_hash": hash_ref("operation", operation.model_dump(mode="json"), "2.0"),
            "active_policy_hash": self.policy_hash,
            "base_snapshot_hash": hash_ref(
                "repository-snapshot", self.proposal_base_snapshot.model_dump(mode="json"), "3.0"
            ),
            "provider_grant_hash": self.provider_grant_hash,
        }
        for field, value in expected.items():
            if getattr(context, field) != value:
                raise WorkflowError(f"proposal context {field} changed before commit")
        authorised_resource_hashes = {
            hash_ref("run-resource-grant", item.model_dump(mode="json"), "1.0").value
            for item in self.resource_grant_history
        }
        if context.run_resource_grant_hash.value not in authorised_resource_hashes:
            raise WorkflowError("proposal context resource grant is outside the authorised replenishment chain")
        if self.current_proposal.context_hash != hash_ref(
            "proposal-context", context.model_dump(mode="json"), "2.0"
        ):
            raise WorkflowError("proposal no longer binds the current proposal context")
        if self.current_proposal.agent_proposal_hash != hash_ref(
            "agent-patch-proposal", self.current_agent_proposal.model_dump(mode="json"), "1.0"
        ):
            raise WorkflowError("proposal no longer binds the exact agent response")
        for path, expected_hash in context.instruction_hashes.items():
            read_decision = require_path(self.loaded_project_policy, path, "read")
            revalidate_decision(self.loaded_project_policy, read_decision)
            try:
                content = Path(path).read_bytes()
            except OSError as exc:
                raise WorkflowError(f"proposal instruction cannot be re-read before commit: {path}") from exc
            if hashlib.sha256(content).hexdigest() != expected_hash:
                raise WorkflowError(f"proposal instruction changed before commit: {path}")
        if {item.observation_id for item in self.current_source_inputs} != {
            item.observation_id for item in context.source_observations
        }:
            raise WorkflowError("persisted proposal source inputs are incomplete")
        observations = {item.observation_id: item for item in context.source_observations}
        for item in self.current_source_inputs:
            observation = observations[item.observation_id]
            if (
                item.path != observation.path
                or item.byte_start != observation.byte_start
                or item.byte_end != observation.byte_end
                or item.content_hash != observation.content_hash
                or item.metadata_hash != observation.metadata_hash
            ):
                raise WorkflowError("proposal source input differs from its observation binding")
            target = Path(item.path)
            read_decision = require_path(self.loaded_project_policy, target, "read")
            revalidate_decision(self.loaded_project_policy, read_decision)
            try:
                raw = target.read_bytes()
            except OSError as exc:
                raise WorkflowError(f"proposal source cannot be re-read before commit: {item.path}") from exc
            if item.byte_end > len(raw) or hashlib.sha256(raw[item.byte_start:item.byte_end]).hexdigest() != item.content_hash:
                raise WorkflowError(f"proposal source content changed before commit: {item.path}")
            if metadata_fingerprint_hash(self._metadata_loader(target)) != item.metadata_hash:
                raise WorkflowError(f"proposal source metadata changed before commit: {item.path}")
        if self.current_preflight is None or not self.current_preflight.deterministic_pass:
            raise WorkflowError("proposal deterministic preflight is absent or no longer passing")
        if self.current_patch_assessment is None or not self.current_patch_assessment.safe:
            raise WorkflowError("proposal semantic assessment is absent or no longer safe")
        for target in self.current_prepared_patch.targets:
            if target.action != "create":
                require_path(self.loaded_project_policy, target.path, "read")
            require_path(self.loaded_project_policy, target.path, target.action)

    def _execute_v2(self) -> list[ExecutionReportV2]:
        if self._closed:
            raise WorkflowError("proposal-first coordinator is not executable")
        if (
            self.current_apply_intent is not None
            and self.current_apply_intent.execution_kind == "exact"
            and self.manifest.state == "executing"
        ):
            operation = self.plan.operations[self.next_operation_index]
            report = self._execute_exact_v2(operation)
            self.reports.append(report)
            self.next_operation_index += 1
            report_hash = hash_ref("execution-report", report.model_dump(mode="json"), "3.0")
            self._append_event_v2(
                "operation_completed", "executing", "executing",
                "recovered exact patch reached its coordinator-observed result",
                operation_id=operation.operation_id,
                evidence_ids=[f"execution-report:{report_hash.value}"],
            )
            self._clear_current_operation_v2()
            self._persist_bundle_v2()
        if self.manifest.state in {"proposal_approved", "applying_proposal"}:
            operation = self.plan.operations[self.next_operation_index]
            report = self._commit_current_proposal_v2(operation)
            self.reports.append(report)
            self.next_operation_index += 1
            report_hash = hash_ref("execution-report", report.model_dump(mode="json"), "3.0")
            self._append_event_v2(
                "operation_completed", "executing", "executing",
                "recovered approved proposal reached its coordinator-observed result",
                operation_id=operation.operation_id,
                proposal_id=self.current_proposal.proposal_id,
                evidence_ids=[f"execution-report:{report_hash.value}"],
            )
            self._clear_current_operation_v2()
            self._persist_bundle_v2()
        if self.manifest.state == "assessing_proposal":
            operation = self.plan.operations[self.next_operation_index]
            guard_snapshot = self._capture_v2()
            guard_control = self._control_inventory()
            service = ProposalCycleService(
                plan=self.plan, assessment=self.assessment, active_policy=self.active_policy,
                provider_grant=self.provider_grant, resource_grant=self.run_resource_grant,
                role_host=self.agent_host, metadata_loader=self._metadata_loader,
                loaded_project_policy=self.loaded_project_policy,
                base_snapshot=self.proposal_base_snapshot,
                root_resource_grant_hash=self.plan.run_resource_grant_hash,
                authorized_resource_grants=self.resource_grant_history,
            )
            service.assess_existing(
                operation.operation_id, context=self.current_assessment_context,
                proposal=self.current_proposal, preflight=self.current_preflight,
                exact_changes=self.current_exact_changes,
                source_inputs=self.current_source_inputs,
                state_guard=lambda stage: self._proposal_state_guard_v2(
                    guard_snapshot, guard_control, stage
                ),
                artifact_checkpoint=lambda stage, payload: self._proposal_checkpoint_v2(
                    operation, stage, payload
                ),
            )
            report = self._commit_current_proposal_v2(operation)
            self.reports.append(report)
            self.next_operation_index += 1
            report_hash = hash_ref("execution-report", report.model_dump(mode="json"), "3.0")
            self._append_event_v2(
                "operation_completed", "executing", "executing",
                "resumed semantic assessment reached its coordinator-observed result",
                operation_id=operation.operation_id, proposal_id=self.current_proposal.proposal_id,
                evidence_ids=[f"execution-report:{report_hash.value}"],
            )
            self._clear_current_operation_v2()
            self._persist_bundle_v2()
        if self.manifest.state not in {"executing", "proposing"}:
            raise WorkflowError("proposal-first coordinator is not in an executable or recoverable commit state")
        try:
            for operation_index in range(self.next_operation_index, len(self.plan.operations)):
                operation = self.plan.operations[operation_index]
                self._heartbeat()
                current = self._capture_v2()
                equal, differences = snapshot_materially_equal(
                    self.plan.snapshot, current, self._declared_paths_v2()
                )
                if not equal:
                    raise WorkflowError(f"repository changed before {operation.operation_id}: {differences}")
                if operation.kind == "exact_action":
                    report = self._execute_exact_v2(operation)
                else:
                    if self.manifest.state == "executing":
                        self._append_event_v2(
                            "proposal_requested", "executing", "proposing",
                            "bounded operation entered the proposal-only role boundary",
                            operation_id=operation.operation_id, attempt_id="attempt-initial",
                        )
                        self.manifest = transition(self.manifest, "proposing", ["audit:proposal_requested"])
                        self.manifest = self.manifest.model_copy(update={"current_operation_id": operation.operation_id})
                        self._persist_bundle_v2()
                    guard_state = {
                        "snapshot": self._capture_v2(),
                        "control": self._control_inventory(),
                    }

                    def state_guard(stage: str) -> None:
                        self._proposal_state_guard_v2(
                            guard_state["snapshot"], guard_state["control"], stage
                        )

                    def artifact_checkpoint(stage: str, payload: object) -> None:
                        self._proposal_checkpoint_v2(operation, stage, payload)
                        guard_state["snapshot"] = self._capture_v2()
                        guard_state["control"] = self._control_inventory()

                    service = ProposalCycleService(
                        plan=self.plan, assessment=self.assessment, active_policy=self.active_policy,
                        provider_grant=self.provider_grant, resource_grant=self.run_resource_grant,
                        role_host=self.agent_host, metadata_loader=self._metadata_loader,
                        loaded_project_policy=self.loaded_project_policy,
                        base_snapshot=self.proposal_base_snapshot,
                        root_resource_grant_hash=self.plan.run_resource_grant_hash,
                        authorized_resource_grants=self.resource_grant_history,
                    )
                    artifacts = service.run(
                        operation.operation_id,
                        attempt_id="attempt-initial" if self.pending_repair_attempt is None else self.pending_repair_attempt.attempt_id,
                        repair_attempt_hash=(
                            None if self.pending_repair_attempt is None else hash_ref(
                                "repair-attempt", self.pending_repair_attempt.model_dump(mode="json"), "3.0"
                            )
                        ),
                        state_guard=state_guard,
                        artifact_checkpoint=artifact_checkpoint,
                    )
                    if not artifacts.patch_assessment.safe or self.manifest.state != "proposal_approved":
                        raise ProposalSafetyRejected("proposal did not reach an approved commit state")
                    report = self._commit_current_proposal_v2(operation)
                self.reports.append(report)
                if self.pending_repair_attempt is not None and operation.kind == "bounded_agent_task":
                    repair_hash = hash_ref(
                        "repair-attempt", self.pending_repair_attempt.model_dump(mode="json"), "3.0"
                    )
                    self.repair_outcomes.append(RepairOutcomeV2(
                        schema_version="2.0",
                        outcome_id=f"outcome-{self.pending_repair_attempt.attempt_id}-applied",
                        repair_attempt_hash=repair_hash,
                        proposal_hash=report.proposal_hash,
                        patch_assessment_hash=report.patch_assessment_hash,
                        outcome="applied",
                        policy_binding=self.policy_binding,
                    ))
                self.next_operation_index = operation_index + 1
                report_hash = hash_ref("execution-report", report.model_dump(mode="json"), "3.0")
                self._append_event_v2(
                    "operation_completed", self.manifest.state, self.manifest.state,
                    "coordinator observed the operation result", operation_id=operation.operation_id,
                    proposal_id=None if self.current_proposal is None else self.current_proposal.proposal_id,
                    evidence_ids=[f"execution-report:{report_hash.value}"],
                )
                self._clear_current_operation_v2()
                self._persist_bundle_v2()
            self.post_execution_snapshot = self._capture_v2()
            self.pending_repair_attempt = None
            self.repair_base_declared_paths = set()
            self._append_event_v2(
                "execution_completed", "executing", "verifying",
                "all proposal-first operations reached coordinator-observed results",
                evidence_ids=[f"repository-snapshot:{hash_ref('repository-snapshot', self.post_execution_snapshot.model_dump(mode='json'), '3.0').value}"],
            )
            self.manifest = transition(self.manifest, "verifying", ["audit:execution_completed"])
            self._persist_bundle_v2()
            return list(self.reports)
        except RoleHostResourceExhausted as exc:
            observed = self._capture_v2()
            equal, differences = snapshot_materially_equal(
                self.plan.snapshot, observed, self._declared_paths_v2()
            )
            if not equal:
                self._append_event_v2(
                    "human_required", self.manifest.state, "human_required",
                    "resource failure coincided with product-state drift during a proposal-only call",
                    operation_id=self.manifest.current_operation_id,
                    evidence_ids=[f"product-drift:{','.join(differences)}"],
                )
                self.manifest = transition(self.manifest, "human_required", ["audit:human_required"])
                self._append_human_intervention_v2(
                    "revise_and_reassess",
                    "resource failure coincided with product-state drift during a proposal-only call",
                )
                self._persist_bundle_v2()
                if self.lease is not None:
                    release_lease(self.lease)
                    self.lease = None
                self._closed = True
                raise WorkflowError("proposal-only role changed product state before resource exhaustion") from exc
            if self.active_semantic_request_token is not None:
                records = getattr(self.agent_host, "call_records", [])
                uncertain_attempt = bool(records) and (
                    records[-1].outcome != "success" or not records[-1].usage_complete
                )
                if not uncertain_attempt:
                    # The owned host rejected the request before dispatch. Preserve the
                    # create-only request evidence, but do not treat it as an in-flight call.
                    self.active_semantic_request_token = None
            prior = self.manifest.state
            self._append_event_v2(
                "resource_paused", prior, "paused_resource",
                "the active finite role-call resource grant was exhausted at a pre-mutation boundary",
                operation_id=self.manifest.current_operation_id,
            )
            self.manifest = transition(self.manifest, "paused_resource", ["audit:resource_paused"])
            self._persist_bundle_v2()
            if self.lease is not None:
                release_lease(self.lease)
                self.lease = None
            raise ResourcePause(f"resource:{type(exc).__name__}") from exc
        except ProposalSafetyRejected as exc:
            if self.manifest.state != "human_required":
                self._append_event_v2(
                    "human_required", self.manifest.state, "human_required",
                    "proposal safety or identity gate rejected the run",
                    operation_id=self.manifest.current_operation_id,
                )
                self.manifest = transition(self.manifest, "human_required", ["audit:human_required"])
            self._append_human_intervention_v2(
                "revise_and_reassess", "proposal safety or identity gate rejected the run"
            )
            self._persist_bundle_v2()
            if self.lease is not None:
                release_lease(self.lease)
                self.lease = None
            self._closed = True
            raise WorkflowError(str(exc)) from exc
        except Exception:
            if self.manifest.state not in {"human_required", "verified", "failed", "abandoned"}:
                self._append_event_v2(
                    "human_required", self.manifest.state, "human_required",
                    "execution stopped at a proposal, commit, identity, or observation gate",
                    operation_id=self.manifest.current_operation_id,
                )
                self.manifest = transition(self.manifest, "human_required", ["audit:human_required"])
                self._append_human_intervention_v2(
                    "inspect_indeterminate_state" if self.current_apply_intent is not None else "revise_and_reassess",
                    "execution stopped at a proposal, commit, identity, or observation gate",
                )
                self._persist_bundle_v2()
            if self.lease is not None:
                release_lease(self.lease)
                self.lease = None
            self._closed = True
            raise

    def execute(self) -> list[ExecutionReport]:
        if getattr(self, "_proposal_first", False):
            return self._execute_v2()
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
        if getattr(self, "_proposal_first", False):
            if self.manifest.state != "verifying" or self._closed:
                raise WorkflowError("verification context requires completed proposal-first execution")
            self._heartbeat()
            current = self._capture_v2()
            if self.post_execution_snapshot is None:
                raise WorkflowError("proposal-first verification requires a committed product snapshot")
            equal, differences = snapshot_materially_equal(self.post_execution_snapshot, current)
            if not equal:
                raise WorkflowError(f"repository changed before verifier handoff: {differences}")
            snapshot_hash = hash_ref("repository-snapshot", current.model_dump(mode="json"), "3.0")
            token = secrets.token_hex(32)
            _VERIFICATION_CONTEXTS[token] = (
                self.plan_hash.value, self.assessment_hash.value, context_id, snapshot_hash.value
            )
            self._verification_context = VerificationContext(
                context_id=context_id, token=token, plan_hash=self.plan_hash,
                assessment_hash=self.assessment_hash, snapshot_hash=snapshot_hash,
            )
            self._append_event_v2(
                "verification_started", "verifying", "verifying",
                "fresh read-only verification context opened",
                evidence_ids=[f"repository-snapshot:{snapshot_hash.value}"],
            )
            self._persist_bundle_v2()
            self._verification_control_inventory = self._control_inventory()
            return self._verification_context
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
        self._verification_context = _begin_verification_context_legacy(
            self.plan, self.assessment, context_id, current
        )
        self._verification_control_inventory = self._control_inventory()
        return self._verification_context

    def build_verification_request(self, context: VerificationContext) -> VerificationRoleRequest:
        """Build the complete no-tool verifier packet from coordinator-owned state."""

        if not getattr(self, "_proposal_first", False):
            raise WorkflowError("typed verifier requests require proposal-first schema-3 execution")
        if context is not self._verification_context or self.manifest.state != "verifying":
            raise WorkflowError("typed verifier request requires the current coordinator context")
        current = self._capture_v2()
        if context.snapshot_hash != hash_ref(
            "repository-snapshot", current.model_dump(mode="json"), "3.0"
        ):
            raise WorkflowError("typed verifier request snapshot identity is stale")

        instructions: dict[str, str] = {}
        for path, expected in sorted(current.instruction_hashes.items()):
            source = Path(path)
            read_decision = require_path(self.loaded_project_policy, source, "read")
            revalidate_decision(self.loaded_project_policy, read_decision)
            if source.is_symlink() or not source.is_file():
                raise WorkflowError("verification instruction path is absent or unsafe")
            content = source.read_text(encoding="utf-8")
            if hashlib.sha256(content.encode("utf-8")).hexdigest() != expected:
                raise WorkflowError("verification instruction content changed after snapshot capture")
            instructions[path] = content

        file_states: list[VerificationFileState] = []
        denied_verification_rule_ids: set[str] = set()
        verification_paths = sorted(
            set(current.selected_file_hashes) | set(current.expected_product_changes)
        )
        for path in verification_paths:
            source = Path(path)
            decision = evaluate_path(self.loaded_project_policy, source, "read")
            if not decision.allowed:
                denied_verification_rule_ids.update(decision.matched_rule_ids)
                file_states.append(VerificationFileState(
                    path=path, state="unobserved_policy_denied", content=None,
                    content_hash=None, metadata_hash=None,
                    denied_rule_ids=decision.matched_rule_ids or ["uncertain-path-identity"],
                ))
                continue
            revalidate_decision(self.loaded_project_policy, decision)
            if source.is_symlink():
                raise WorkflowError("verification file-state path is a symbolic link")
            if not source.exists():
                file_states.append(VerificationFileState(
                    path=path, state="absent", content=None,
                    content_hash=None, metadata_hash=None,
                ))
                continue
            if not source.is_file():
                raise WorkflowError("verification file-state path is not a regular file")
            raw = source.read_bytes()
            try:
                content = raw.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise WorkflowError("verification file-state content is not UTF-8") from exc
            content_hash = hashlib.sha256(raw).hexdigest()
            expected_hash = current.selected_file_hashes.get(path)
            if expected_hash is not None and content_hash != expected_hash:
                raise WorkflowError("verification file content differs from the bound snapshot")
            metadata_hash = metadata_fingerprint_hash(self._metadata_loader(source))
            expected_metadata = current.selected_file_metadata_hashes.get(path)
            if expected_metadata is not None and metadata_hash != expected_metadata:
                raise WorkflowError("verification file metadata differs from the bound snapshot")
            file_states.append(VerificationFileState(
                path=path, state="present", content=content,
                content_hash=content_hash, metadata_hash=metadata_hash,
            ))

        artifacts: list[tuple[str, str, Any]] = [
            ("low-level-plan", "3.0", self.plan),
            ("assessment", "3.0", self.assessment),
            ("active-policy", "2.0", self.active_policy),
            ("host-capabilities", "3.0", self.capabilities),
            ("provider-grant", "1.0", self.provider_grant),
            ("run-resource-grant", "1.0", self.run_resource_grant),
            ("repository-snapshot", "3.0", current),
        ]
        artifacts.extend(("bounded-patch-proposal", "2.0", item) for item in self.proposal_history)
        artifacts.extend(("patch-assessment", "2.0", item) for item in self.patch_assessment_history)
        artifacts.extend(("execution-report", "3.0", item) for item in self.reports)
        input_hashes = [
            hash_ref(kind, artifact.model_dump(mode="json"), version)
            for kind, version, artifact in artifacts
        ]
        criteria = sorted({value for item in self.plan.operations for value in item.success_criteria})
        checks = sorted({value for item in self.plan.operations for value in item.verifier_checks})
        effects = sorted({effect.effect_id for item in self.plan.operations for effect in item.effects})
        prompt_packet = {
            "input_artifact_hashes": [item.model_dump(mode="json") for item in input_hashes],
            "file_states": [item.model_dump(mode="json") for item in file_states],
            "instruction_hashes": current.instruction_hashes,
            "success_criteria": criteria,
            "verifier_checks": checks,
            "effect_ids": effects,
        }
        semantic_context = SemanticRoleContext(
            schema_version="1.0",
            context_id=f"semantic-{context.context_id}",
            request_token=context.token,
            role="verifier",
            adapter=self.provider_grant.adapter,
            assurance_profile=(
                "framework_tool_enforced_no_tools"
                if self.provider_grant.adapter == "pydantic_ai"
                else "instruction_only_proposal_host"
            ),
            provider_grant_hash=self.provider_grant_hash,
            run_resource_grant_hash=self.run_resource_grant_hash,
            policy_binding=self.policy_binding,
            input_artifact_hashes=input_hashes,
            prompt_packet_hash=hashlib.sha256(canonical_bytes(prompt_packet)).hexdigest(),
            created_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        )
        self._verification_policy_denied_rule_ids = sorted(denied_verification_rule_ids)
        return VerificationRoleRequest(
            schema_version="1.0", context=semantic_context,
            verifier_context_id=context.context_id,
            plan=self.plan, assessment=self.assessment, active_policy=self.active_policy,
            capabilities=self.capabilities, provider_grant=self.provider_grant,
            run_resource_grant=self.run_resource_grant,
            post_execution_snapshot=current, proposals=list(self.proposal_history),
            patch_assessments=list(self.patch_assessment_history),
            execution_reports=list(self.reports), file_states=file_states,
            applicable_instructions=instructions,
            expected_success_criteria=criteria, expected_verifier_checks=checks,
            expected_effect_ids=effects,
        )

    def _persist_semantic_call_artifact(
        self,
        request_token: str,
        filename: str,
        artifact: Any,
    ) -> Path:
        semantic_root = _safe_control_directory(self.run_root, "semantic-calls", create=True)
        call_root = semantic_root / request_token
        if filename == "request.json":
            if call_root.exists() or call_root.is_symlink():
                raise WorkflowError("semantic role request identity already exists")
            call_root.mkdir(mode=0o700, exist_ok=False)
            semantic_descriptor = os.open(semantic_root, os.O_RDONLY)
            try:
                os.fsync(semantic_descriptor)
            finally:
                os.close(semantic_descriptor)
        elif call_root.is_symlink() or not call_root.is_dir():
            raise WorkflowError("semantic role call directory is missing or unsafe")
        target = call_root / filename
        data = canonical_bytes(artifact.model_dump(mode="json")) + b"\n"
        descriptor = os.open(
            target,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
            0o600,
        )
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            directory = os.open(call_root, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        except Exception:
            try:
                target.unlink()
            except OSError:
                pass
            raise
        return target

    def verify_with_host(self, context: VerificationContext) -> VerificationReportV2:
        """Invoke the owned verifier role and validate its response through the coordinator."""

        request = self.build_verification_request(context)
        self._persist_semantic_call_artifact(
            request.context.request_token, "request.json", request
        )
        self.active_semantic_request_token = request.context.request_token
        self._persist_bundle_v2()
        self._verification_control_inventory = self._control_inventory()
        product_before = self._capture_v2()
        before_records = len(getattr(self.agent_host, "call_records", []))
        try:
            response = VerificationRoleResponse.model_validate(
                self.agent_host.verify(request).model_dump(mode="json")
            )
        except RoleHostResourceExhausted as exc:
            records = getattr(self.agent_host, "call_records", [])
            if len(records) == before_records:
                self.active_semantic_request_token = None
                self.pause_resource("verifier-resource-exhausted-before-dispatch")
                raise ResourcePause("resource:verifier-not-dispatched") from exc
            self._record_unknown_recovery_v2(
                "verifier resource exhaustion followed a provider attempt with incomplete or uncertain usage; the call will not be repeated"
            )
            raise WorkflowError("verifier call usage is incomplete or uncertain") from exc
        except Exception:
            self._record_unknown_recovery_v2(
                "verifier role call failed after its durable request record; it will not be repeated"
            )
            raise
        try:
            records = getattr(self.agent_host, "call_records", [])
            if len(records) != before_records + 1:
                raise WorkflowError("verifier did not produce exactly one role-call record")
            record = RoleCallRecord.model_validate(records[-1].model_dump(mode="json"))
            if (
                record.role != "verifier"
                or record.outcome != "success"
                or not record.usage_complete
                or record.adapter != self.provider_grant.adapter
                or record.assurance_profile != request.context.assurance_profile
                or record.provider_grant_hash != self.provider_grant_hash
                or record.policy_binding != self.policy_binding
                or record.provider != self.provider_grant.provider
                or record.endpoint != self.provider_grant.endpoint
                or record.model != self.provider_grant.model
                or record.model_revision != self.provider_grant.model_revision
            ):
                raise WorkflowError("verifier role-call record is incomplete or inconsistent")
            if self._control_inventory() != self._verification_control_inventory:
                raise ControlStateDrift("verifier changed protected control state")
            product_after = self._capture_v2()
            equal, differences = snapshot_materially_equal(product_before, product_after)
            if not equal:
                raise WorkflowError(f"verifier changed product state: {differences}")
            if response.request_token != request.context.request_token:
                raise WorkflowError("verifier response request token differs from the coordinator request")
            self._persist_semantic_call_artifact(
                request.context.request_token, "response.json", response
            )
            self._verification_control_inventory = self._control_inventory()
        except ControlStateDrift:
            self._stop_after_control_drift()
            raise
        except Exception as exc:
            self._record_unknown_recovery_v2(
                "verifier response or product state was stale, malformed, duplicated, or inconsistent; no lifecycle success transition occurred"
            )
            if isinstance(exc, WorkflowError):
                raise
            raise WorkflowError("verifier response validation failed") from exc
        self.active_semantic_request_token = None
        self.completed_semantic_request_tokens.append(request.context.request_token)
        return self.verify(response.verification_proposal, context)

    def verify(self, proposal: VerificationProposal, context: VerificationContext) -> VerificationReport:
        if getattr(self, "_proposal_first", False):
            try:
                return self._verify_v2(proposal, context)
            except Exception as exc:
                if self.manifest.state not in {
                    "human_required", "verified", "failed", "abandoned", "rejected"
                }:
                    prior = self.manifest.state
                    self._append_event_v2(
                        "human_required", prior, "human_required",
                        "verification stopped at an identity, control-state, or typed-evidence gate",
                    )
                    self.manifest = transition(self.manifest, "human_required", ["audit:human_required"])
                    self._append_human_intervention_v2(
                        "revise_and_reassess",
                        "verification stopped at an identity, control-state, or typed-evidence gate",
                    )
                    self._persist_bundle_v2()
                if self.lease is not None:
                    try:
                        release_lease(self.lease)
                    finally:
                        self.lease = None
                self._closed = True
                if isinstance(exc, ValidationError):
                    raise WorkflowError("verification proposal failed typed validation") from None
                raise
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
            report = _verify_reports_legacy(self.plan, self.assessment, self.reports, proposal, context)
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

    def _verify_v2(self, proposal: Any, context: VerificationContext) -> VerificationReportV2:
        proposal = _boundary_copy(proposal, VerificationProposalV2)
        if context is not self._verification_context:
            raise WorkflowError("verification context was not opened by this coordinator")
        registered = _VERIFICATION_CONTEXTS.pop(context.token, None)
        if registered != (
            self.plan_hash.value, self.assessment_hash.value, context.context_id, context.snapshot_hash.value
        ):
            raise WorkflowError("verification context is stale, reused, or not coordinator-issued")
        if self._verification_control_inventory != self._control_inventory():
            raise ControlStateDrift("verifier changed protected control state")
        current = self._capture_v2()
        if context.snapshot_hash != hash_ref("repository-snapshot", current.model_dump(mode="json"), "3.0"):
            raise WorkflowError("verification product snapshot changed during verifier work")
        if proposal.policy_binding != self.policy_binding:
            raise WorkflowError("verification proposal policy identity differs from the active binding")
        expected_proposals = [
            hash_ref("bounded-patch-proposal", item.model_dump(mode="json"), "2.0")
            for item in self.proposal_history
        ]
        expected_assessments = [
            hash_ref("patch-assessment", item.model_dump(mode="json"), "2.0")
            for item in self.patch_assessment_history
        ]
        expected_reports = [
            hash_ref("execution-report", item.model_dump(mode="json"), "3.0")
            for item in self.reports
        ]
        expected_criteria = sorted({value for item in self.plan.operations for value in item.success_criteria})
        expected_checks = sorted({value for item in self.plan.operations for value in item.verifier_checks})
        expected_effects = sorted({effect.effect_id for item in self.plan.operations for effect in item.effects})
        evidence_ids = {item.evidence_id for item in proposal.evidence}
        maps = (proposal.criterion_evidence, proposal.check_evidence, proposal.effect_evidence)
        map_values = {value for mapping in maps for values in mapping.values() for value in values}
        binding_ok = (
            proposal.plan_hash == self.plan_hash
            and proposal.assessment_hash == self.assessment_hash
            and proposal.snapshot_hash == context.snapshot_hash
            and proposal.verifier_context_id == context.context_id
            and proposal.proposal_hashes == expected_proposals
            and proposal.patch_assessment_hashes == expected_assessments
            and proposal.execution_report_hashes == expected_reports
        )
        coverage_ok = (
            not getattr(self, "_verification_policy_denied_rule_ids", [])
            and
            sorted(proposal.success_criteria_met) == expected_criteria
            and sorted(proposal.verifier_checks_passed) == expected_checks
            and sorted(proposal.observed_effect_ids) == expected_effects
            and set(proposal.criterion_evidence) == set(expected_criteria)
            and set(proposal.check_evidence) == set(expected_checks)
            and set(proposal.effect_evidence) == set(expected_effects)
            and map_values.issubset(evidence_ids)
            and all(values for mapping in maps for values in mapping.values())
        )
        evidence_ok = bool(evidence_ids) and all(
            item.provenance == "agent_reported" and item.locator == f"agent-report:{item.evidence_id}"
            for item in proposal.evidence
        )
        valid_findings, finding_errors = _partition_agent_findings(
            proposal.findings,
            {item.operation_id for item in self.plan.operations},
            expected_effects,
            {item.evidence_id: item.provenance for item in proposal.evidence},
        )
        if finding_errors:
            raise WorkflowError("verification proposal contains invalid finding references")
        proposal = proposal.model_copy(update={"findings": valid_findings})
        finding_ids = [item.finding_id for item in proposal.findings]
        findings_ok = len(finding_ids) == len(set(finding_ids)) and not any(
            item.blocking for item in proposal.findings
        )
        if not binding_ok:
            raise WorkflowError("verification proposal does not bind the complete committed proposal cycle")
        if not coverage_ok or not evidence_ok:
            raise WorkflowError("verification proposal lacks complete typed criteria, effect, or evidence coverage")
        verified = binding_ok and coverage_ok and evidence_ok and findings_ok
        findings = [_sanitize_finding(item) for item in proposal.findings]
        report = VerificationReportV2(
            schema_version="3.0", verification_id=f"verification-{context.snapshot_hash.value[:24]}",
            plan_hash=self.plan_hash, assessment_hash=self.assessment_hash,
            snapshot_hash=context.snapshot_hash, proposal_hashes=expected_proposals,
            patch_assessment_hashes=expected_assessments, execution_report_hashes=expected_reports,
            independent_context=self.capabilities.fresh_context_enforcement == "host_enforced",
            independence_assurance=(
                "host_enforced" if self.capabilities.fresh_context_enforcement == "host_enforced"
                else "instruction_only"
            ),
            coordinator_evidence_ids=[
                f"execution-report-{item.value}"
                for item in expected_reports
            ],
            verifier_evidence_ids=sorted(evidence_ids),
            success_criteria_met=proposal.success_criteria_met,
            verifier_checks_passed=proposal.verifier_checks_passed,
            findings=findings, verified=verified, provenance="coordinator_observed",
            policy_binding=self.policy_binding,
        )
        self.last_verification = report
        report_hash = hash_ref("verification-report", report.model_dump(mode="json"), "3.0")
        event_type = "verification_completed" if verified else "verification_failed"
        target = "verified" if verified else "repairing"
        self._append_event_v2(
            event_type, "verifying", target,
            "separated static verification completed",
            evidence_ids=[f"verification-report:{report_hash.value}"],
        )
        self.manifest = transition(self.manifest, target, [f"audit:{event_type}"])
        if verified and self.repair_attempts:
            latest = self.repair_attempts[-1]
            latest_hash = hash_ref("repair-attempt", latest.model_dump(mode="json"), "3.0")
            applied = next(
                (
                    item for item in reversed(self.repair_outcomes)
                    if item.repair_attempt_hash == latest_hash and item.outcome == "applied"
                ),
                None,
            )
            already_verified = any(
                item.repair_attempt_hash == latest_hash and item.outcome == "verified"
                for item in self.repair_outcomes
            )
            if applied is not None and not already_verified:
                self.repair_outcomes.append(RepairOutcomeV2(
                    schema_version="2.0",
                    outcome_id=f"outcome-{latest.attempt_id}-verified",
                    repair_attempt_hash=latest_hash,
                    proposal_hash=applied.proposal_hash,
                    patch_assessment_hash=applied.patch_assessment_hash,
                    outcome="verified",
                    policy_binding=self.policy_binding,
                ))
        self._persist_bundle_v2()
        if verified:
            if self.lease is not None:
                release_lease(self.lease)
                self.lease = None
            self._closed = True
        return report

    def resume_repair(self, attempt: RepairAttempt) -> None:
        if getattr(self, "_proposal_first", False):
            attempt = _boundary_copy(attempt, RepairAttemptV2)
            if self.manifest.state != "repairing" or self._closed or self.last_verification is None:
                raise WorkflowError("proposal-first repair requires a live failed verification")
            findings = {item.finding_id: item for item in self.last_verification.findings}
            finding = findings.get(attempt.finding_id)
            if finding is None:
                raise WorkflowError("repair attempt does not name a current verifier finding")
            if attempt.attempt_id in {item.attempt_id for item in self.repair_attempts}:
                raise WorkflowError("repair attempt identity was already used")
            if attempt.high_risk_replay:
                raise WorkflowError("high-risk replay requires a newly assessed run")
            if attempt.resource_grant_hash != self.run_resource_grant_hash:
                raise WorkflowError("repair attempt is not bound to the active run resource grant")
            if attempt.policy_binding != self.policy_binding:
                raise WorkflowError("repair attempt is not bound to the active project policy")
            operation_ids = set(finding.operation_ids)
            indexes = [
                index for index, item in enumerate(self.plan.operations)
                if item.operation_id in operation_ids
            ]
            if not indexes:
                raise WorkflowError("repair finding does not identify an in-plan operation")
            restart_index = min(indexes)
            self.repair_base_declared_paths = {
                path for report in self.reports[restart_index:]
                for path in report.committed_postimage_hashes
            }
            self.reports = self.reports[:restart_index]
            self.next_operation_index = restart_index
            self.proposal_base_snapshot = self._capture_v2()
            self.repair_attempts.append(attempt)
            self.pending_repair_attempt = attempt
            self.current_proposal_context = None
            self.current_agent_proposal = None
            self.current_prepared_patch = None
            self.current_proposal = None
            self.current_preflight = None
            self.current_assessment_context = None
            self.current_exact_changes = []
            self.current_semantic_patch_proposal = None
            self.current_patch_assessment = None
            self.current_metadata = {}
            self.current_apply_intent = None
            self.manifest = self.manifest.model_copy(update={
                "current_operation_id": None, "current_proposal_hash": None,
                "current_patch_assessment_hash": None, "current_apply_intent_hash": None,
            })
            attempt_hash = hash_ref("repair-attempt", attempt.model_dump(mode="json"), "3.0")
            self._append_event_v2(
                "repair_started", "repairing", "executing",
                "new repair attempt entered the same proposal-first safety cycle",
                attempt_id=attempt.attempt_id,
                evidence_ids=[f"repair-attempt:{attempt_hash.value}"],
            )
            self.manifest = transition(self.manifest, "executing", ["audit:repair_started"])
            self._persist_bundle_v2()
            return
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
        if getattr(self, "_proposal_first", False):
            if self.manifest.state not in {
                "executing", "proposing", "validating_proposal", "assessing_proposal",
                "proposal_approved", "verifying", "repairing",
            } or self._closed:
                raise WorkflowError("resource pause requires a live proposal-first run at a safe boundary")
            prior = self.manifest.state
            self._append_event_v2(
                "resource_paused", prior, "paused_resource",
                "proposal-first run stopped at a durable resource boundary",
                operation_id=self.manifest.current_operation_id, evidence_ids=[evidence_id],
            )
            self.manifest = transition(self.manifest, "paused_resource", [evidence_id])
            self._persist_bundle_v2()
            if self.lease is not None:
                release_lease(self.lease)
                self.lease = None
            return
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
        if getattr(self, "_proposal_first", False):
            if self.manifest.state != "paused_resource" or self.manifest.suspended_from is None or self._closed:
                raise WorkflowError("resume requires a live reloaded proposal-first resource pause")
            if self.lease is None:
                raise WorkflowError("proposal-first resume requires the recovery lease")
            target = self.manifest.suspended_from
            self._append_event_v2(
                "lifecycle_transition", "paused_resource", target,
                "resource replenishment and artifact identities were revalidated",
                operation_id=self.manifest.current_operation_id, evidence_ids=[evidence_id],
            )
            self.manifest = transition(self.manifest, target, [evidence_id], resumed_state=target)
            self._persist_bundle_v2()
            return
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
        if getattr(self, "_proposal_first", False):
            if self._closed:
                return
            prior = self.manifest.state
            self._append_event_v2(
                "execution_abandoned", prior, "abandoned",
                "proposal-first coordinator closed before successful verification",
                operation_id=self.manifest.current_operation_id,
            )
            self.manifest = transition(self.manifest, "abandoned", ["audit:execution_abandoned"])
            try:
                self._persist_bundle_v2()
            finally:
                if self.lease is not None:
                    release_lease(self.lease)
                    self.lease = None
                self._closed = True
            return
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


class ExecutionCoordinator(_CoordinatorRuntime):
    """Public schema-3 execution boundary.

    The implementation retains frozen schema-1 code only so historical tests
    and audit tooling can parse old evidence.  Public construction and recovery
    never enter that branch.
    """

    def __init__(self, plan: Any, *args: Any, **kwargs: Any):
        if getattr(plan, "schema_version", None) != "3.0":
            raise LegacyArtifactNotExecutable(
                "legacy_artifact_not_executable: low-level-plan requires schema '3.0'; "
                "recompile and reassess as a new run"
            )
        super().__init__(plan, *args, **kwargs)

    @classmethod
    def reload(cls, project_root: str, run_id: str, capabilities: Any, **kwargs: Any):
        bundle_path = Path(project_root) / ".rb-safe-operation" / "runs" / run_id / "coordinator-bundle.json"
        try:
            payload = parse_json_strict(bundle_path.read_bytes())
        except Exception as exc:
            raise WorkflowError("coordinator bundle is missing or unreadable") from exc
        manifest = payload.get("manifest") if isinstance(payload, dict) else None
        if not isinstance(manifest, dict) or manifest.get("schema_version") != "3.0":
            raise LegacyArtifactNotExecutable(
                "legacy_artifact_not_executable: run-manifest requires schema '3.0'; "
                "recompile and reassess as a new run"
            )
        return super().reload(
            project_root, run_id, capabilities,
            **kwargs,
        )


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
    try:
        return inspect_patch_paths(patch)
    except PatchContractError as exc:
        raise WorkflowError(str(exc)) from exc


def _verify_reports_legacy(
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


def verify_reports(*args: Any, **kwargs: Any) -> VerificationReport:
    """Reject the retired standalone schema-1 verification report path."""
    raise LegacyArtifactNotExecutable(
        "legacy_artifact_not_executable: standalone schema-1 verification is audit-only; "
        "use a proposal-first ExecutionCoordinator"
    )


def record_workflow(audit_root: str, run_id: str, event_type: str, lifecycle_from: str | None, lifecycle_to: str | None, summary: str, evidence_ids: list[str]) -> str:
    log = AuditLog(audit_root, run_id)
    event = log.append(
        EventPayload(event_type=event_type, lifecycle_from=lifecycle_from, lifecycle_to=lifecycle_to, operation_id=None, summary=summary, evidence_ids=evidence_ids),
        "coordinator_observed",
        {"summary": summary},
    )
    return event.event_record_hash
