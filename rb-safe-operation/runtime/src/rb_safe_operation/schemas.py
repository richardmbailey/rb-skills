from __future__ import annotations

import json
from pathlib import Path

from pydantic import TypeAdapter

from . import __version__
from .acceptance import AcceptanceRunSummary
from .canonical import artifact_hash, canonical_bytes, source_tree_hash
from .models import ActivePolicy, Approval, Assessment, AssessmentBundle, AuditEvent, DeterministicPreflight, ExecutionReport, HostCapabilities, HumanIntervention, LowLevelPlan, ProjectPolicy, RepairAttempt, RepositorySnapshot, RunManifest, SemanticAssessmentProposal, VerificationProposal, VerificationReport
from .proposal_models import (
    AgentPatchProposal,
    ApplyIntent,
    ApprovalV2,
    AssessmentBundleV2,
    AssessmentV2,
    AuditEventV2,
    BoundedPatchProposal,
    CoordinatorBundleV2,
    DeterministicPreflightV2,
    ExecutionReportV2,
    HostCapabilitiesV2,
    HumanInterventionV2,
    LowLevelPlanV2,
    PatchAssessment,
    PatchAssessmentRequest,
    PatchProposalPreflight,
    PatchSemanticAssessmentProposal,
    PlanAssessmentRequest,
    PlanAssessmentResponse,
    ProposalContext,
    ProposalCycleRecord,
    ProposalRequest,
    ProviderGrant,
    ReadToolResult,
    RepairAttemptV2,
    RepairOutcomeV2,
    RoleCallRecord,
    RepositorySnapshotV2,
    RunManifestV2,
    RunResourceGrant,
    SemanticAssessmentProposalV2,
    VerificationProposalV2,
    VerificationReportV2,
    VerificationFileState,
    VerificationRoleRequest,
    VerificationRoleResponse,
    SemanticRoleContext,
)
from .readiness_models import (
    DoctorRequest,
    ReadinessDiagnostic,
    ReadinessResult,
    RunPreparationConfirmation,
    RunPreparationPreview,
    RunPreparationRequest,
)
from .policy_models import (
    ActivePolicyV2,
    PathPolicyDecision,
    PathRule,
    PolicyAuthoringIntent,
    PolicyAuthoringRecord,
    PolicyBinding,
    PolicyConfirmation,
    PolicyPreview,
    PolicyTranslationRequest,
    ProjectPolicyProposal,
    ProjectPolicyV2,
    RepositorySnapshotV3,
)


MODEL_SCHEMAS = {
    ("acceptance-run-summary", "1.0"): AcceptanceRunSummary,
    ("path-rule", "1.0"): PathRule,
    ("policy-binding", "1.0"): PolicyBinding,
    ("path-policy-decision", "1.0"): PathPolicyDecision,
    ("project-policy-proposal", "1.0"): ProjectPolicyProposal,
    ("policy-translation-request", "1.0"): PolicyTranslationRequest,
    ("policy-preview", "1.0"): PolicyPreview,
    ("policy-confirmation", "1.0"): PolicyConfirmation,
    ("policy-authoring-intent", "1.0"): PolicyAuthoringIntent,
    ("policy-authoring-record", "1.0"): PolicyAuthoringRecord,
    ("doctor-request", "1.0"): DoctorRequest,
    ("readiness-diagnostic", "1.0"): ReadinessDiagnostic,
    ("readiness-result", "1.0"): ReadinessResult,
    ("run-preparation-request", "1.0"): RunPreparationRequest,
    ("run-preparation-preview", "1.0"): RunPreparationPreview,
    ("run-preparation-confirmation", "1.0"): RunPreparationConfirmation,
    ("active-policy", "1.0"): ActivePolicy,
    ("active-policy", "2.0"): ActivePolicyV2,
    ("approval", "1.0"): Approval,
    ("approval", "3.0"): ApprovalV2,
    ("assessment", "1.0"): Assessment,
    ("assessment", "3.0"): AssessmentV2,
    ("assessment-bundle", "1.0"): AssessmentBundle,
    ("assessment-bundle", "3.0"): AssessmentBundleV2,
    ("deterministic-preflight", "1.0"): DeterministicPreflight,
    ("deterministic-preflight", "3.0"): DeterministicPreflightV2,
    ("audit-event", "1.0"): AuditEvent,
    ("audit-event", "3.0"): AuditEventV2,
    ("execution-report", "1.0"): ExecutionReport,
    ("execution-report", "3.0"): ExecutionReportV2,
    ("host-capabilities", "1.0"): HostCapabilities,
    ("host-capabilities", "3.0"): HostCapabilitiesV2,
    ("low-level-plan", "1.0"): LowLevelPlan,
    ("low-level-plan", "3.0"): LowLevelPlanV2,
    ("human-intervention", "1.0"): HumanIntervention,
    ("human-intervention", "3.0"): HumanInterventionV2,
    ("project-policy", "1.0"): ProjectPolicy,
    ("project-policy", "2.0"): ProjectPolicyV2,
    ("repository-snapshot", "1.0"): RepositorySnapshot,
    ("repository-snapshot", "3.0"): RepositorySnapshotV2,
    ("repair-attempt", "1.0"): RepairAttempt,
    ("repair-attempt", "3.0"): RepairAttemptV2,
    ("repair-outcome", "2.0"): RepairOutcomeV2,
    ("run-manifest", "1.0"): RunManifest,
    ("run-manifest", "3.0"): RunManifestV2,
    ("semantic-assessment-proposal", "1.0"): SemanticAssessmentProposal,
    ("semantic-assessment-proposal", "3.0"): SemanticAssessmentProposalV2,
    ("verification-proposal", "1.0"): VerificationProposal,
    ("verification-proposal", "3.0"): VerificationProposalV2,
    ("verification-report", "1.0"): VerificationReport,
    ("verification-report", "3.0"): VerificationReportV2,
    ("proposal-context", "2.0"): ProposalContext,
    ("proposal-cycle-record", "2.0"): ProposalCycleRecord,
    ("proposal-request", "2.0"): ProposalRequest,
    ("agent-patch-proposal", "1.0"): AgentPatchProposal,
    ("bounded-patch-proposal", "2.0"): BoundedPatchProposal,
    ("patch-proposal-preflight", "2.0"): PatchProposalPreflight,
    ("patch-semantic-assessment-proposal", "2.0"): PatchSemanticAssessmentProposal,
    ("patch-assessment", "2.0"): PatchAssessment,
    ("patch-assessment-request", "2.0"): PatchAssessmentRequest,
    ("provider-grant", "1.0"): ProviderGrant,
    ("read-tool-result", "2.0"): ReadToolResult,
    ("run-resource-grant", "1.0"): RunResourceGrant,
    ("role-call-record", "2.0"): RoleCallRecord,
    ("semantic-role-context", "1.0"): SemanticRoleContext,
    ("plan-assessment-request", "1.0"): PlanAssessmentRequest,
    ("plan-assessment-response", "1.0"): PlanAssessmentResponse,
    ("verification-file-state", "1.0"): VerificationFileState,
    ("verification-role-request", "1.0"): VerificationRoleRequest,
    ("verification-role-response", "1.0"): VerificationRoleResponse,
    ("apply-intent", "2.0"): ApplyIntent,
    ("coordinator-bundle", "3.0"): CoordinatorBundleV2,
}


MODELS = {
    name: model
    for name, version, model in sorted(
        ((name, version, model) for (name, version), model in MODEL_SCHEMAS.items()),
        key=lambda item: (item[0], tuple(int(part) for part in item[1].split("."))),
    )
}


def model_for(artifact_type: str, schema_version: str):
    try:
        return MODEL_SCHEMAS[(artifact_type, schema_version)]
    except KeyError as exc:
        raise ValueError(
            f"unsupported_artifact_version: {artifact_type} schema {schema_version}"
        ) from exc


def export_schemas(destination: Path, runtime_root: Path, runtime_source_hash: str | None = None) -> list[Path]:
    destination.mkdir(parents=True, exist_ok=True)
    source_hash = runtime_source_hash or source_tree_hash(runtime_root)
    written: list[Path] = []
    for (name, version), model in sorted(MODEL_SCHEMAS.items()):
        schema = model.model_json_schema()
        envelope = {
            "generator_version": __version__,
            "model_schema_version": version,
            "runtime_source_hash": source_hash,
            "schema_payload_hash": artifact_hash("json-schema", version, schema),
            "schema": schema,
        }
        path = destination / f"{name}-{version}.schema.json"
        path.write_bytes(canonical_bytes(envelope) + b"\n")
        written.append(path)
    return written


def _comparable_schema_bytes(path: Path) -> bytes:
    """Return the schema identity used for drift checks.

    `runtime_source_hash` records which reviewed runtime exported a file, but it is not
    itself part of the JSON-schema contract. Ignoring only that provenance field avoids
    invalidating every generated schema after unrelated runtime implementation changes.
    Generator version, model schema version, payload hash, and the complete schema remain
    compared exactly.
    """

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return path.read_bytes()
    if isinstance(payload, dict):
        payload = dict(payload)
        payload.pop("runtime_source_hash", None)
    return canonical_bytes(payload) + b"\n"


def check_drift(expected: Path, generated: Path) -> list[str]:
    differences: list[str] = []
    expected_names = {path.name for path in expected.glob("*.json")}
    generated_names = {path.name for path in generated.glob("*.json")}
    for name in sorted(expected_names | generated_names):
        left, right = expected / name, generated / name
        if (
            not left.exists()
            or not right.exists()
            or _comparable_schema_bytes(left) != _comparable_schema_bytes(right)
        ):
            differences.append(name)
    return differences
