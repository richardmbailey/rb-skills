from __future__ import annotations

from datetime import datetime
import hashlib
from pathlib import PurePosixPath
import re
from typing import Annotated, Literal, Union

from pydantic import Field, model_serializer, model_validator

from .canonical import artifact_hash, canonical_decimal
from .models import (
    Approval,
    ActivePolicy,
    ApplyPatchAction,
    Assessment,
    AssessmentBundle,
    AuditEvent,
    DeterministicPreflight,
    EvidenceRef,
    EventPayload,
    ExactAction,
    Finding,
    HashRef,
    LowLevelPlan,
    OperationCommon,
    RepairAttempt,
    ReadFileAction,
    RepositorySnapshot,
    SafeIdentifier,
    StrictModel,
    SemanticAssessmentProposal,
    UtcTimestamp,
    VerificationProposal,
    VerificationReport,
)
from .policy_models import ActivePolicyV2, PolicyBinding, PathPolicyDecision, RepositorySnapshotV3


DataClassification = Literal["public", "internal", "personal", "sensitive", "secret"]
ProposalAssuranceProfile = Literal[
    "instruction_only_proposal_host",
    "framework_tool_enforced_proposer",
    "framework_tool_enforced_no_tools",
]
ProposalAdapter = Literal["json_line", "pydantic_ai"]
ProposalRole = Literal["plan_assessor", "proposer", "patch_assessor", "verifier", "policy_translator"]
AutomaticRetryClass = Literal["proposal_format_error"]


def _unique(values: list[object], field: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"{field} values must be unique")


def _absolute_path(value: str, field: str) -> None:
    path = PurePosixPath(value)
    if not path.is_absolute() or ".." in path.parts or "\0" in value:
        raise ValueError(f"{field} requires an absolute literal path")


def _ordered_time(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")


def _require_ref(value: HashRef, artifact_type: str, version: str, field: str) -> None:
    if value.artifact_type != artifact_type or value.schema_version != version:
        raise ValueError(f"{field} must reference {artifact_type} schema {version}")


class SourceObservation(StrictModel):
    observation_id: SafeIdentifier
    path: str
    byte_start: int = Field(ge=0)
    byte_end: int = Field(ge=0)
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    metadata_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    data_classification: DataClassification
    policy_decision: PathPolicyDecision

    @model_validator(mode="after")
    def valid_range(self) -> "SourceObservation":
        _absolute_path(self.path, "source observation path")
        if self.byte_end < self.byte_start:
            raise ValueError("source observation byte range is reversed")
        if not self.policy_decision.allowed or self.policy_decision.capability != "read":
            raise ValueError("source observations require an allowed read policy decision")
        if self.policy_decision.requested_path != self.path:
            raise ValueError("source observation policy decision names another path")
        return self


class FileMetadataFingerprint(StrictModel):
    file_type: Literal["regular"]
    device: int = Field(ge=0)
    inode: int = Field(gt=0)
    link_count: Literal[1]
    mode: int = Field(ge=0, le=0o7777)
    uid: int = Field(ge=0)
    gid: int = Field(ge=0)
    flags: int | None
    acl_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    extended_attribute_hashes: dict[str, str]
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    size: int = Field(ge=0)

    @model_validator(mode="after")
    def valid_xattrs(self) -> "FileMetadataFingerprint":
        for name, value in self.extended_attribute_hashes.items():
            if not name or "\0" in name or not re.fullmatch(r"[0-9a-f]{64}", value):
                raise ValueError("extended attributes require non-empty names and SHA-256 values")
        return self


class ProposalContext(StrictModel):
    schema_version: Literal["2.0"]
    context_id: SafeIdentifier
    request_token: SafeIdentifier
    operation_id: SafeIdentifier
    attempt_id: SafeIdentifier
    role: ProposalRole
    adapter: ProposalAdapter
    assurance_profile: ProposalAssuranceProfile
    plan_hash: HashRef
    plan_assessment_hash: HashRef
    operation_hash: HashRef
    active_policy_hash: HashRef
    policy_binding: PolicyBinding
    base_snapshot_hash: HashRef
    provider_grant_hash: HashRef
    run_resource_grant_hash: HashRef
    repair_attempt_hash: HashRef | None
    input_artifact_hashes: list[HashRef]
    instruction_hashes: dict[str, str]
    source_observations: list[SourceObservation]
    prompt_packet_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    toolset_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    created_at: UtcTimestamp

    @model_validator(mode="after")
    def closed_bindings(self) -> "ProposalContext":
        expected = (
            (self.plan_hash, "low-level-plan", "3.0", "plan_hash"),
            (self.plan_assessment_hash, "assessment", "3.0", "plan_assessment_hash"),
            (self.operation_hash, "operation", "2.0", "operation_hash"),
            (self.active_policy_hash, "active-policy", "2.0", "active_policy_hash"),
            (self.base_snapshot_hash, "repository-snapshot", "3.0", "base_snapshot_hash"),
            (self.provider_grant_hash, "provider-grant", "1.0", "provider_grant_hash"),
            (self.run_resource_grant_hash, "run-resource-grant", "1.0", "run_resource_grant_hash"),
        )
        for item in expected:
            _require_ref(*item)
        if self.repair_attempt_hash is not None:
            _require_ref(self.repair_attempt_hash, "repair-attempt", "3.0", "repair_attempt_hash")
        if self.policy_binding.effective_policy_hash != self.active_policy_hash:
            raise ValueError("proposal context policy binding differs from its active policy hash")
        _unique([(item.artifact_type, item.schema_version, item.value) for item in self.input_artifact_hashes], "input artifact hashes")
        for path, value in self.instruction_hashes.items():
            _absolute_path(path, "instruction hash path")
            if not re.fullmatch(r"[0-9a-f]{64}", value):
                raise ValueError("instruction hashes must be lowercase SHA-256")
        identities = [(item.observation_id, item.path, item.byte_start, item.byte_end) for item in self.source_observations]
        _unique(identities, "source observation identities")
        if self.adapter == "pydantic_ai":
            expected = (
                "framework_tool_enforced_proposer"
                if self.role == "proposer" else "framework_tool_enforced_no_tools"
            )
            if self.assurance_profile != expected:
                raise ValueError("PydanticAI role and framework-tool assurance profile contradict")
        if self.adapter == "json_line" and self.assurance_profile != "instruction_only_proposal_host":
            raise ValueError("JSON-line hosts require the instruction-only assurance profile")
        return self


class AgentPatchProposal(StrictModel):
    schema_version: Literal["1.0"]
    request_token: SafeIdentifier
    operation_id: SafeIdentifier
    attempt_id: SafeIdentifier
    intent_summary: str = Field(min_length=1, max_length=2000)
    unified_diff: str = Field(
        min_length=1,
        max_length=2_000_000,
        pattern=r"^(?:--- |diff --git )",
    )
    claimed_created_paths: list[str]
    claimed_modified_paths: list[str]
    claimed_deleted_paths: list[str]
    claimed_effect_ids: list[SafeIdentifier]
    evidence: list[EvidenceRef]
    no_other_changes: Literal[True]

    @model_validator(mode="after")
    def closed_claims(self) -> "AgentPatchProposal":
        path_sets = []
        for field in ("claimed_created_paths", "claimed_modified_paths", "claimed_deleted_paths"):
            values = getattr(self, field)
            _unique(values, field)
            for value in values:
                _absolute_path(value, field)
            path_sets.append(set(values))
        if any(path_sets[left] & path_sets[right] for left in range(3) for right in range(left + 1, 3)):
            raise ValueError("claimed create, modify, and delete paths must be disjoint")
        _unique(self.claimed_effect_ids, "claimed effect IDs")
        evidence_ids = [item.evidence_id for item in self.evidence]
        _unique(evidence_ids, "proposal evidence IDs")
        for item in self.evidence:
            if item.provenance != "agent_reported" or item.locator != f"agent-report:{item.evidence_id}":
                raise ValueError("proposal evidence must be structural agent-reported evidence")
        return self


class BoundedPatchProposal(StrictModel):
    schema_version: Literal["2.0"]
    proposal_id: SafeIdentifier
    context_hash: HashRef
    agent_proposal_hash: HashRef
    plan_hash: HashRef
    plan_assessment_hash: HashRef
    operation_hash: HashRef
    active_policy_hash: HashRef
    policy_binding: PolicyBinding
    base_snapshot_hash: HashRef
    repair_attempt_hash: HashRef | None
    patch_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    created_paths: list[str]
    modified_paths: list[str]
    deleted_paths: list[str]
    preimage_hashes: dict[str, str]
    postimage_hashes: dict[str, str]
    metadata_hashes: dict[str, str]
    expected_effect_ids: list[SafeIdentifier]
    proposer_role: Literal["proposer"]
    assurance_profile: ProposalAssuranceProfile
    evidence: list[EvidenceRef]

    @model_validator(mode="after")
    def exact_inventory(self) -> "BoundedPatchProposal":
        expected = (
            (self.context_hash, "proposal-context", "2.0", "context_hash"),
            (self.agent_proposal_hash, "agent-patch-proposal", "1.0", "agent_proposal_hash"),
            (self.plan_hash, "low-level-plan", "3.0", "plan_hash"),
            (self.plan_assessment_hash, "assessment", "3.0", "plan_assessment_hash"),
            (self.operation_hash, "operation", "2.0", "operation_hash"),
            (self.active_policy_hash, "active-policy", "2.0", "active_policy_hash"),
            (self.base_snapshot_hash, "repository-snapshot", "3.0", "base_snapshot_hash"),
        )
        for item in expected:
            _require_ref(*item)
        if self.repair_attempt_hash is not None:
            _require_ref(self.repair_attempt_hash, "repair-attempt", "3.0", "repair_attempt_hash")
        if self.policy_binding.effective_policy_hash != self.active_policy_hash:
            raise ValueError("bounded proposal policy binding differs from its active policy hash")
        inventories = [self.created_paths, self.modified_paths, self.deleted_paths]
        for name, values in zip(("created", "modified", "deleted"), inventories):
            _unique(values, f"{name} paths")
            for value in values:
                _absolute_path(value, f"{name} paths")
        sets = [set(item) for item in inventories]
        if any(sets[left] & sets[right] for left in range(3) for right in range(left + 1, 3)):
            raise ValueError("derived create, modify, and delete paths must be disjoint")
        existing = sets[1] | sets[2]
        resulting = sets[0] | sets[1]
        if set(self.preimage_hashes) != existing:
            raise ValueError("preimage hashes must exactly cover modified and deleted paths")
        if set(self.postimage_hashes) != resulting:
            raise ValueError("postimage hashes must exactly cover created and modified paths")
        if set(self.metadata_hashes) != existing:
            raise ValueError("metadata hashes must exactly cover existing targets")
        for mapping in (self.preimage_hashes, self.postimage_hashes, self.metadata_hashes):
            for path, value in mapping.items():
                _absolute_path(path, "proposal hash path")
                if not re.fullmatch(r"[0-9a-f]{64}", value):
                    raise ValueError("proposal inventories require lowercase SHA-256 values")
        _unique(self.expected_effect_ids, "expected effect IDs")
        return self


class PatchProposalPreflight(StrictModel):
    schema_version: Literal["2.0"]
    preflight_id: SafeIdentifier
    proposal_hash: HashRef
    plan_hash: HashRef
    policy_hash: HashRef
    snapshot_hash: HashRef
    policy_binding: PolicyBinding
    deterministic_pass: bool
    semantic_assessment_required: bool
    findings: list[Finding]

    @model_validator(mode="after")
    def verdict_consistency(self) -> "PatchProposalPreflight":
        _require_ref(self.proposal_hash, "bounded-patch-proposal", "2.0", "proposal_hash")
        _require_ref(self.plan_hash, "low-level-plan", "3.0", "plan_hash")
        _require_ref(self.policy_hash, "active-policy", "2.0", "policy_hash")
        _require_ref(self.snapshot_hash, "repository-snapshot", "3.0", "snapshot_hash")
        if self.policy_binding.effective_policy_hash != self.policy_hash:
            raise ValueError("patch preflight policy binding differs from its policy hash")
        _unique([item.finding_id for item in self.findings], "preflight finding IDs")
        expected = not any(item.blocking for item in self.findings)
        if self.deterministic_pass != expected or self.semantic_assessment_required != expected:
            raise ValueError("preflight verdict contradicts blocking findings")
        return self


class PatchSemanticAssessmentProposal(StrictModel):
    schema_version: Literal["2.0"]
    request_token: SafeIdentifier
    proposal_hash: HashRef
    semantic_pass: bool
    findings: list[Finding]
    covered_paths: list[str]
    covered_effect_ids: list[SafeIdentifier]
    policy_binding: PolicyBinding
    no_uncontrolled_detrimental_side_effects: bool

    @model_validator(mode="after")
    def coverage_consistency(self) -> "PatchSemanticAssessmentProposal":
        _require_ref(self.proposal_hash, "bounded-patch-proposal", "2.0", "proposal_hash")
        _unique([item.finding_id for item in self.findings], "semantic finding IDs")
        _unique(self.covered_paths, "covered paths")
        for value in self.covered_paths:
            _absolute_path(value, "covered paths")
        _unique(self.covered_effect_ids, "covered effect IDs")
        expected = not any(item.blocking for item in self.findings) and self.no_uncontrolled_detrimental_side_effects
        if self.semantic_pass != expected:
            raise ValueError("semantic verdict contradicts findings or detrimental-side-effect verdict")
        return self


class PatchAssessment(StrictModel):
    schema_version: Literal["2.0"]
    assessment_id: SafeIdentifier
    proposal_hash: HashRef
    preflight_hash: HashRef
    semantic_proposal_hash: HashRef
    complete_context: bool
    deterministic_pass: bool
    semantic_pass: bool
    safe: bool
    status: Literal["approved", "rejected"]
    findings: list[Finding]
    policy_binding: PolicyBinding

    @model_validator(mode="after")
    def verdict_consistency(self) -> "PatchAssessment":
        _require_ref(self.proposal_hash, "bounded-patch-proposal", "2.0", "proposal_hash")
        _require_ref(self.preflight_hash, "patch-proposal-preflight", "2.0", "preflight_hash")
        _require_ref(self.semantic_proposal_hash, "patch-semantic-assessment-proposal", "2.0", "semantic_proposal_hash")
        _unique([item.finding_id for item in self.findings], "patch assessment finding IDs")
        expected = self.complete_context and self.deterministic_pass and self.semantic_pass and not any(
            item.blocking for item in self.findings
        )
        if self.safe != expected or self.status != ("approved" if expected else "rejected"):
            raise ValueError("patch assessment verdict fields contradict")
        return self


class ProviderGrant(StrictModel):
    schema_version: Literal["1.0"]
    grant_id: SafeIdentifier
    issued_at: UtcTimestamp
    expires_at: UtcTimestamp
    roles: list[ProposalRole]
    adapter: ProposalAdapter
    provider: str = Field(min_length=1, max_length=200)
    endpoint: str = Field(min_length=1, max_length=1000)
    model: str = Field(min_length=1, max_length=300)
    model_revision: str | None = Field(max_length=300)
    host_revision: str | None = Field(default=None, max_length=300)
    credential_audience: str = Field(min_length=1, max_length=300)
    request_data_classes: list[str]
    response_data_classes: list[str]
    maximum_data_classification: DataClassification
    retention_disclosure: str = Field(min_length=1, max_length=2000)
    training_use: Literal["allowed", "disallowed", "unknown"]
    max_calls: int = Field(gt=0)
    max_request_bytes: int = Field(gt=0)
    max_input_tokens: int = Field(gt=0)
    max_output_tokens: int = Field(gt=0)
    max_seconds: int = Field(gt=0)
    max_cost_decimal: str
    cost_accounting: Literal["observed", "declared_zero", "unavailable"]
    temperature_decimal: str
    seed: int | None
    structured_output_mode: Literal["tool", "native", "prompted"]
    redirect_endpoints: list[str]
    approval_hash: HashRef | None

    @model_validator(mode="after")
    def finite_explicit_grant(self) -> "ProviderGrant":
        if _ordered_time(self.expires_at) <= _ordered_time(self.issued_at):
            raise ValueError("provider grant must expire after it is issued")
        for field in ("roles", "request_data_classes", "response_data_classes", "redirect_endpoints"):
            _unique(getattr(self, field), f"provider grant {field}")
        if not self.roles or not self.request_data_classes or not self.response_data_classes:
            raise ValueError("provider grant roles and data classes cannot be empty")
        canonical_decimal(self.max_cost_decimal)
        canonical_decimal(self.temperature_decimal)
        if self.cost_accounting == "declared_zero" and canonical_decimal(self.max_cost_decimal) != "0":
            raise ValueError("declared-zero cost accounting requires a zero cost ceiling")
        if self.endpoint.startswith("in-memory://"):
            if self.provider != "test-provider" or self.credential_audience != "none:test-only":
                raise ValueError("in-memory endpoints are reserved for explicit test grants")
        elif self.adapter == "json_line" and self.endpoint.startswith("host-mediated://"):
            pass
        elif not self.endpoint.startswith("https://"):
            raise ValueError("external provider endpoints must use https")
        if self.approval_hash is not None:
            _require_ref(self.approval_hash, "approval", "2.0", "approval_hash")
        return self


class RunResourceGrant(StrictModel):
    schema_version: Literal["1.0"]
    grant_id: SafeIdentifier
    issued_at: UtcTimestamp
    expires_at: UtcTimestamp
    max_proposer_calls: int = Field(gt=0)
    max_assessor_calls: int = Field(gt=0)
    max_model_requests: int = Field(gt=0)
    max_read_tool_calls: int = Field(ge=0)
    max_read_tool_bytes: int = Field(ge=0)
    max_patch_bytes: int = Field(gt=0)
    max_input_tokens: int = Field(gt=0)
    max_output_tokens: int = Field(gt=0)
    max_request_bytes: int = Field(gt=0)
    max_response_bytes: int = Field(gt=0)
    max_elapsed_seconds: int = Field(gt=0)
    max_cost_decimal: str
    automatic_retry_attempt_limit: Union[int, Literal["unbounded"]] = 0
    automatic_retry_classes: list[AutomaticRetryClass] = Field(default_factory=list)
    replenishes_grant_id: SafeIdentifier | None
    authorization_hash: HashRef

    @model_validator(mode="after")
    def finite_grant(self) -> "RunResourceGrant":
        if _ordered_time(self.expires_at) <= _ordered_time(self.issued_at):
            raise ValueError("run resource grant must expire after it is issued")
        canonical_decimal(self.max_cost_decimal)
        _require_ref(self.authorization_hash, "human-authorization", "1.0", "authorization_hash")
        if isinstance(self.automatic_retry_attempt_limit, int) and self.automatic_retry_attempt_limit < 0:
            raise ValueError("automatic retry attempt limit must be non-negative or unbounded")
        _unique(self.automatic_retry_classes, "automatic retry classes")
        retries_enabled = self.automatic_retry_attempt_limit == "unbounded" or self.automatic_retry_attempt_limit > 0
        if retries_enabled != bool(self.automatic_retry_classes):
            raise ValueError(
                "automatic retry classes must be present exactly when automatic retries are enabled"
            )
        if self.replenishes_grant_id == self.grant_id:
            raise ValueError("a resource grant cannot replenish itself")
        return self

    @model_serializer(mode="wrap")
    def preserve_legacy_disabled_retry_shape(self, handler):
        """Keep pre-retry schema-1 grants canonically hash-compatible."""

        data = handler(self)
        if self.automatic_retry_attempt_limit == 0 and not self.automatic_retry_classes:
            data.pop("automatic_retry_attempt_limit", None)
            data.pop("automatic_retry_classes", None)
        return data


class AutomaticRetryRecord(StrictModel):
    schema_version: Literal["1.0"]
    retry_id: SafeIdentifier
    retry_index: int = Field(gt=0)
    role: Literal["proposer"]
    failure_class: AutomaticRetryClass
    operation_id: SafeIdentifier
    operation_attempt_id: SafeIdentifier
    failed_request_token: SafeIdentifier
    rejected_response_hash: HashRef
    role_call_record_hash: HashRef
    request_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    response_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    resource_grant_hash: HashRef
    product_state_unchanged: Literal[True]
    protected_control_state_unchanged: Literal[True]
    usage_complete: Literal[True]
    recorded_at: UtcTimestamp
    policy_binding: PolicyBinding

    @model_validator(mode="after")
    def retry_authority_bindings(self) -> "AutomaticRetryRecord":
        _require_ref(
            self.rejected_response_hash,
            "agent-patch-proposal",
            "1.0",
            "rejected_response_hash",
        )
        _require_ref(
            self.role_call_record_hash,
            "role-call-record",
            "2.0",
            "role_call_record_hash",
        )
        _require_ref(
            self.resource_grant_hash,
            "run-resource-grant",
            "1.0",
            "resource_grant_hash",
        )
        return self


class RoleCallRecord(StrictModel):
    schema_version: Literal["2.0"]
    call_id: SafeIdentifier
    role: ProposalRole
    adapter: ProposalAdapter
    assurance_profile: ProposalAssuranceProfile
    provider_grant_hash: HashRef
    policy_binding: PolicyBinding
    request_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    response_hash: str | None = Field(pattern=r"^[0-9a-f]{64}$")
    outcome: Literal["success", "timeout", "protocol_error", "resource_exhausted", "role_error"]
    usage_complete: bool
    provider: str
    endpoint: str
    model: str
    model_revision: str | None
    host_revision: str | None = None
    requests: int = Field(ge=0)
    tool_calls: int = Field(ge=0)
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    request_bytes: int = Field(ge=0)
    response_bytes: int = Field(ge=0)
    elapsed_milliseconds: int = Field(ge=0)
    cost_decimal: str | None
    cost_provenance: Literal["adapter_observed", "provider_declared_zero", "unavailable_after_failure"]

    @model_validator(mode="after")
    def provider_binding(self) -> "RoleCallRecord":
        _require_ref(self.provider_grant_hash, "provider-grant", "1.0", "provider_grant_hash")
        if self.cost_decimal is not None:
            canonical_decimal(self.cost_decimal)
        if self.cost_provenance == "provider_declared_zero" and canonical_decimal(self.cost_decimal) != "0":
            raise ValueError("provider-declared-zero cost records must record zero")
        if (self.cost_decimal is None) != (self.cost_provenance == "unavailable_after_failure"):
            raise ValueError("unknown failed-call cost must use unavailable-after-failure provenance")
        if (self.outcome == "success") != (self.response_hash is not None):
            raise ValueError("only successful role calls may contain a response hash")
        if self.outcome == "success" and not self.usage_complete:
            raise ValueError("successful role calls require complete usage accounting")
        return self


class ApprovalV2(Approval):
    proposal_hash: HashRef | None
    patch_assessment_hash: HashRef | None
    policy_binding: PolicyBinding
    schema_version: Literal["3.0"] = "3.0"

    @model_validator(mode="after")
    def proposal_binding(self) -> "ApprovalV2":
        if (self.proposal_hash is None) != (self.patch_assessment_hash is None):
            raise ValueError("proposal and patch-assessment approval bindings must both be present or absent")
        if self.proposal_hash is not None:
            _require_ref(self.proposal_hash, "bounded-patch-proposal", "2.0", "proposal_hash")
            _require_ref(self.patch_assessment_hash, "patch-assessment", "2.0", "patch_assessment_hash")
        if self.policy_binding.effective_policy_hash != self.policy_hash:
            raise ValueError("approval policy binding differs from its policy hash")
        return self


class DeterministicPreflightV2(DeterministicPreflight):
    schema_version: Literal["3.0"]
    provider_grant_hash: HashRef
    run_resource_grant_hash: HashRef
    policy_binding: PolicyBinding
    approvals: list[ApprovalV2]

    @model_validator(mode="after")
    def provider_bindings(self) -> "DeterministicPreflightV2":
        _require_ref(self.plan_hash, "low-level-plan", "3.0", "plan_hash")
        _require_ref(self.policy_hash, "active-policy", "2.0", "policy_hash")
        _require_ref(self.snapshot_hash, "repository-snapshot", "3.0", "snapshot_hash")
        _require_ref(self.provider_grant_hash, "provider-grant", "1.0", "provider_grant_hash")
        _require_ref(self.run_resource_grant_hash, "run-resource-grant", "1.0", "run_resource_grant_hash")
        if self.policy_binding.effective_policy_hash != self.policy_hash:
            raise ValueError("deterministic preflight policy binding differs from its policy hash")
        return self


class SemanticAssessmentProposalV2(SemanticAssessmentProposal):
    schema_version: Literal["3.0"]
    provider_grant_hash: HashRef
    required_role_assurance_profiles: list[ProposalAssuranceProfile]
    policy_binding: PolicyBinding

    @model_validator(mode="after")
    def role_assurance_bindings(self) -> "SemanticAssessmentProposalV2":
        _require_ref(self.provider_grant_hash, "provider-grant", "1.0", "provider_grant_hash")
        _unique(self.required_role_assurance_profiles, "required role assurance profiles")
        return self


class AssessmentV2(Assessment):
    schema_version: Literal["3.0"]
    provider_grant_hash: HashRef
    run_resource_grant_hash: HashRef
    required_role_assurance_profiles: list[ProposalAssuranceProfile]
    policy_binding: PolicyBinding
    approvals: list[ApprovalV2]

    @model_validator(mode="after")
    def proposal_runtime_bindings(self) -> "AssessmentV2":
        _require_ref(self.plan_hash, "low-level-plan", "3.0", "plan_hash")
        _require_ref(self.policy_hash, "active-policy", "2.0", "policy_hash")
        _require_ref(self.snapshot_hash, "repository-snapshot", "3.0", "snapshot_hash")
        _require_ref(self.provider_grant_hash, "provider-grant", "1.0", "provider_grant_hash")
        _require_ref(self.run_resource_grant_hash, "run-resource-grant", "1.0", "run_resource_grant_hash")
        _unique(self.required_role_assurance_profiles, "required role assurance profiles")
        if self.policy_binding.effective_policy_hash != self.policy_hash:
            raise ValueError("assessment policy binding differs from its policy hash")
        return self


class AssessmentBundleV2(StrictModel):
    schema_version: Literal["3.0"]
    assessment: AssessmentV2
    semantic_proposal: SemanticAssessmentProposalV2

    @model_validator(mode="after")
    def matching_semantic_authority(self) -> "AssessmentBundleV2":
        if self.assessment.provider_grant_hash != self.semantic_proposal.provider_grant_hash:
            raise ValueError("assessment bundle provider grant bindings differ")
        if self.assessment.required_role_assurance_profiles != self.semantic_proposal.required_role_assurance_profiles:
            raise ValueError("assessment bundle role assurance requirements differ")
        return self


class ExecutionReportV2(StrictModel):
    schema_version: Literal["3.0"]
    operation_id: SafeIdentifier
    execution_kind: Literal["exact", "bounded_proposal"]
    proposal_hash: HashRef | None
    patch_assessment_hash: HashRef | None
    success: bool
    evidence: list[EvidenceRef]
    expected_effect_ids_observed: list[SafeIdentifier]
    unexpected_effects: list[str]
    committed_postimage_hashes: dict[str, str]
    provenance: Literal["coordinator_observed"]
    next_strategy: str | None
    policy_binding: PolicyBinding

    @model_validator(mode="after")
    def authoritative_bindings(self) -> "ExecutionReportV2":
        if self.execution_kind == "bounded_proposal":
            if self.proposal_hash is None or self.patch_assessment_hash is None:
                raise ValueError("bounded execution reports require proposal and patch assessment bindings")
            _require_ref(self.proposal_hash, "bounded-patch-proposal", "2.0", "proposal_hash")
            _require_ref(self.patch_assessment_hash, "patch-assessment", "2.0", "patch_assessment_hash")
        elif self.proposal_hash is not None or self.patch_assessment_hash is not None:
            raise ValueError("exact execution reports cannot claim a bounded proposal")
        _unique(self.expected_effect_ids_observed, "observed effect IDs")
        for path, value in self.committed_postimage_hashes.items():
            _absolute_path(path, "committed postimage path")
            if not re.fullmatch(r"[0-9a-f]{64}", value):
                raise ValueError("committed postimage hashes must be lowercase SHA-256")
        if self.success and self.unexpected_effects:
            raise ValueError("successful execution reports cannot contain unexpected effects")
        return self


ProposalLifecycleState = Literal[
    "drafting",
    "validating",
    "rejected",
    "approved",
    "executing",
    "proposing",
    "validating_proposal",
    "assessing_proposal",
    "proposal_approved",
    "applying_proposal",
    "verifying",
    "repairing",
    "paused_resource",
    "human_required",
    "verified",
    "failed",
    "abandoned",
]


class RunManifestV2(StrictModel):
    schema_version: Literal["3.0"]
    run_id: SafeIdentifier
    state: ProposalLifecycleState
    suspended_from: ProposalLifecycleState | None
    plan_hash: HashRef
    assessment_hash: HashRef
    policy_hash: HashRef
    snapshot_hash: HashRef
    provider_grant_hash: HashRef
    run_resource_grant_hash: HashRef
    policy_binding: PolicyBinding
    current_operation_id: SafeIdentifier | None
    current_proposal_hash: HashRef | None
    current_patch_assessment_hash: HashRef | None
    current_apply_intent_hash: HashRef | None
    event_head_hash: str | None

    @model_validator(mode="after")
    def valid_state_bindings(self) -> "RunManifestV2":
        _require_ref(self.plan_hash, "low-level-plan", "3.0", "plan_hash")
        _require_ref(self.assessment_hash, "assessment", "3.0", "assessment_hash")
        _require_ref(self.policy_hash, "active-policy", "2.0", "policy_hash")
        _require_ref(self.snapshot_hash, "repository-snapshot", "3.0", "snapshot_hash")
        _require_ref(self.provider_grant_hash, "provider-grant", "1.0", "provider_grant_hash")
        _require_ref(self.run_resource_grant_hash, "run-resource-grant", "1.0", "run_resource_grant_hash")
        if self.current_proposal_hash is not None:
            _require_ref(self.current_proposal_hash, "bounded-patch-proposal", "2.0", "current_proposal_hash")
        if self.current_patch_assessment_hash is not None:
            _require_ref(self.current_patch_assessment_hash, "patch-assessment", "2.0", "current_patch_assessment_hash")
        if self.current_apply_intent_hash is not None:
            _require_ref(self.current_apply_intent_hash, "apply-intent", "2.0", "current_apply_intent_hash")
        if self.policy_binding.effective_policy_hash != self.policy_hash:
            raise ValueError("run manifest policy binding differs from its policy hash")
        requires_origin = self.state == "paused_resource"
        if requires_origin != (self.suspended_from is not None):
            raise ValueError("only paused_resource retains a resumable suspended state")
        if self.state == "human_required" and self.suspended_from is not None:
            raise ValueError("human_required is terminal and cannot retain a resumable origin")
        proposal_states = {
            "validating_proposal", "assessing_proposal", "proposal_approved", "applying_proposal"
        }
        if self.state in proposal_states and (self.current_operation_id is None or self.current_proposal_hash is None):
            raise ValueError("proposal lifecycle states require current operation and proposal bindings")
        if self.event_head_hash is not None and not re.fullmatch(r"[0-9a-f]{64}", self.event_head_hash):
            raise ValueError("event head hash must be lowercase SHA-256")
        return self


class EventPayloadV2(StrictModel):
    event_type: Literal[
        "execution_started",
        "proposal_requested",
        "automatic_retry_scheduled",
        "proposal_received",
        "proposal_rejected",
        "proposal_preflight_passed",
        "proposal_preflight_failed",
        "semantic_assessment_requested",
        "proposal_approved",
        "proposal_assessment_rejected",
        "apply_intent_recorded",
        "target_committed",
        "operation_completed",
        "execution_completed",
        "verification_started",
        "verification_completed",
        "verification_failed",
        "repair_started",
        "resource_paused",
        "resource_replenished",
        "recovery_classified",
        "human_required",
        "execution_abandoned",
        "lifecycle_transition",
    ]
    lifecycle_from: ProposalLifecycleState | None
    lifecycle_to: ProposalLifecycleState | None
    operation_id: SafeIdentifier | None
    proposal_id: SafeIdentifier | None
    attempt_id: SafeIdentifier | None
    summary: str
    evidence_ids: list[str]


class AuditEventV2(AuditEvent):
    schema_version: Literal["3.0"]
    payload: EventPayloadV2
    policy_binding: PolicyBinding


class ApplyIntent(StrictModel):
    schema_version: Literal["2.0"]
    intent_id: SafeIdentifier
    operation_id: SafeIdentifier
    execution_kind: Literal["exact", "bounded_proposal"]
    operation_hash: HashRef
    proposal_hash: HashRef | None
    patch_assessment_hash: HashRef | None
    approval_hashes: list[HashRef]
    ordered_targets: list[str]
    preimage_hashes: dict[str, str | None]
    postimage_hashes: dict[str, str | None]
    committed_targets: list[str]
    state: Literal["prepared", "committing", "committed", "indeterminate"]
    policy_binding: PolicyBinding

    @model_validator(mode="after")
    def journal_consistency(self) -> "ApplyIntent":
        _require_ref(self.operation_hash, "operation", "2.0", "operation_hash")
        if self.execution_kind == "bounded_proposal":
            if self.proposal_hash is None or self.patch_assessment_hash is None:
                raise ValueError("bounded apply intents require proposal and assessment bindings")
            _require_ref(self.proposal_hash, "bounded-patch-proposal", "2.0", "proposal_hash")
            _require_ref(self.patch_assessment_hash, "patch-assessment", "2.0", "patch_assessment_hash")
        elif self.proposal_hash is not None or self.patch_assessment_hash is not None:
            raise ValueError("exact apply intents cannot claim bounded proposal bindings")
        approval_schema_version = "3.0"
        for value in self.approval_hashes:
            _require_ref(value, "approval", approval_schema_version, "approval_hashes")
        _unique(self.ordered_targets, "ordered targets")
        for value in self.ordered_targets:
            _absolute_path(value, "ordered targets")
        if set(self.preimage_hashes) != set(self.ordered_targets) or set(self.postimage_hashes) != set(self.ordered_targets):
            raise ValueError("apply intent hashes must exactly cover ordered targets")
        if self.committed_targets != self.ordered_targets[: len(self.committed_targets)]:
            raise ValueError("committed targets must form an ordered prefix")
        for mapping in (self.preimage_hashes, self.postimage_hashes):
            for value in mapping.values():
                if value is not None and not re.fullmatch(r"[0-9a-f]{64}", value):
                    raise ValueError("apply intent hashes must be lowercase SHA-256 or null")
        if self.state == "prepared" and self.committed_targets:
            raise ValueError("a prepared intent cannot contain committed targets")
        if self.state == "committed" and self.committed_targets != self.ordered_targets:
            raise ValueError("a committed intent requires every ordered target")
        return self


class RepairAttemptV2(RepairAttempt):
    """Immutable authority for one repair proposal cycle.

    The proposal binds the hash of this artifact.  Mutable progress is recorded
    separately in ``RepairOutcomeV2`` so applying a patch cannot retroactively
    change the authority hash that the patch was assessed against.
    """

    schema_version: Literal["3.0"]
    prior_proposal_hash: HashRef | None
    resource_grant_hash: HashRef
    outcome: Literal["proposing"]
    policy_binding: PolicyBinding

    @model_validator(mode="after")
    def proposal_cycle(self) -> "RepairAttemptV2":
        if self.prior_proposal_hash is not None:
            _require_ref(self.prior_proposal_hash, "bounded-patch-proposal", "2.0", "prior_proposal_hash")
        _require_ref(self.resource_grant_hash, "run-resource-grant", "1.0", "resource_grant_hash")
        return self


class RepairOutcomeV2(StrictModel):
    schema_version: Literal["2.0"]
    outcome_id: SafeIdentifier
    repair_attempt_hash: HashRef
    proposal_hash: HashRef | None
    patch_assessment_hash: HashRef | None
    outcome: Literal["proposal_rejected", "applied", "verified", "paused_resource", "human_required"]
    policy_binding: PolicyBinding

    @model_validator(mode="after")
    def immutable_authority_binding(self) -> "RepairOutcomeV2":
        _require_ref(self.repair_attempt_hash, "repair-attempt", "3.0", "repair_attempt_hash")
        if self.proposal_hash is not None:
            _require_ref(self.proposal_hash, "bounded-patch-proposal", "2.0", "proposal_hash")
        if self.patch_assessment_hash is not None:
            _require_ref(self.patch_assessment_hash, "patch-assessment", "2.0", "patch_assessment_hash")
        if self.outcome in {"applied", "verified"} and (
            self.proposal_hash is None or self.patch_assessment_hash is None
        ):
            raise ValueError("applied and verified repair outcomes require proposal and assessment bindings")
        return self


class VerificationProposalV2(VerificationProposal):
    schema_version: Literal["3.0"]
    proposal_hashes: list[HashRef]
    patch_assessment_hashes: list[HashRef]
    execution_report_hashes: list[HashRef]
    policy_binding: PolicyBinding

    @model_validator(mode="after")
    def proposal_bindings(self) -> "VerificationProposalV2":
        _require_ref(self.plan_hash, "low-level-plan", "3.0", "plan_hash")
        _require_ref(self.assessment_hash, "assessment", "3.0", "assessment_hash")
        _require_ref(self.snapshot_hash, "repository-snapshot", "3.0", "snapshot_hash")
        for value in self.proposal_hashes:
            _require_ref(value, "bounded-patch-proposal", "2.0", "proposal_hashes")
        for value in self.patch_assessment_hashes:
            _require_ref(value, "patch-assessment", "2.0", "patch_assessment_hashes")
        for value in self.execution_report_hashes:
            _require_ref(value, "execution-report", "3.0", "execution_report_hashes")
        _unique([(item.artifact_type, item.schema_version, item.value) for item in self.proposal_hashes], "proposal hashes")
        _unique([(item.artifact_type, item.schema_version, item.value) for item in self.patch_assessment_hashes], "patch assessment hashes")
        _unique([(item.artifact_type, item.schema_version, item.value) for item in self.execution_report_hashes], "execution report hashes")
        return self


class VerificationReportV2(VerificationReport):
    schema_version: Literal["3.0"]
    proposal_hashes: list[HashRef]
    patch_assessment_hashes: list[HashRef]
    execution_report_hashes: list[HashRef]
    policy_binding: PolicyBinding

    @model_validator(mode="after")
    def proposal_bindings(self) -> "VerificationReportV2":
        _require_ref(self.plan_hash, "low-level-plan", "3.0", "plan_hash")
        _require_ref(self.assessment_hash, "assessment", "3.0", "assessment_hash")
        _require_ref(self.snapshot_hash, "repository-snapshot", "3.0", "snapshot_hash")
        for value in self.proposal_hashes:
            _require_ref(value, "bounded-patch-proposal", "2.0", "proposal_hashes")
        for value in self.patch_assessment_hashes:
            _require_ref(value, "patch-assessment", "2.0", "patch_assessment_hashes")
        for value in self.execution_report_hashes:
            _require_ref(value, "execution-report", "3.0", "execution_report_hashes")
        return self


class HumanInterventionV2(StrictModel):
    schema_version: Literal["3.0"]
    decision_type: Literal[
        "revise_and_reassess",
        "leave_constrained_pipeline",
        "approve_declared_gate",
        "abandon",
        "inspect_indeterminate_state",
        "replenish_resource_grant",
    ]
    plan_hash: HashRef
    assessment_hash: HashRef
    policy_hash: HashRef
    snapshot_hash: HashRef
    proposal_hash: HashRef | None
    patch_assessment_hash: HashRef | None
    apply_intent_hash: HashRef | None
    operation_id: SafeIdentifier | None
    effect_id: SafeIdentifier | None
    timestamp: UtcTimestamp
    rationale: str
    resulting_version_or_outcome: str
    approval_expiry: UtcTimestamp | None
    idempotency_key: str | None
    principal: str | None
    identity_verification: Literal["unavailable"]
    policy_binding: PolicyBinding

    @model_validator(mode="after")
    def authority_bindings(self) -> "HumanInterventionV2":
        _require_ref(self.plan_hash, "low-level-plan", "3.0", "plan_hash")
        _require_ref(self.assessment_hash, "assessment", "3.0", "assessment_hash")
        _require_ref(self.policy_hash, "active-policy", "2.0", "policy_hash")
        _require_ref(self.snapshot_hash, "repository-snapshot", "3.0", "snapshot_hash")
        if self.proposal_hash is not None:
            _require_ref(self.proposal_hash, "bounded-patch-proposal", "2.0", "proposal_hash")
        if self.patch_assessment_hash is not None:
            _require_ref(self.patch_assessment_hash, "patch-assessment", "2.0", "patch_assessment_hash")
        if self.apply_intent_hash is not None:
            _require_ref(self.apply_intent_hash, "apply-intent", "2.0", "apply_intent_hash")
        if self.policy_binding.effective_policy_hash != self.policy_hash:
            raise ValueError("human intervention policy binding differs from its policy hash")
        if self.decision_type == "inspect_indeterminate_state" and self.apply_intent_hash is None:
            raise ValueError("indeterminate-state intervention requires an apply intent")
        return self


class HostCapabilitiesV2(StrictModel):
    schema_version: Literal["3.0"]
    profile: Literal["semi_formal", "strict_isolation"]
    role_read_only: Literal["host_enforced", "instruction_only", "unknown"]
    role_tool_allocation: Literal["framework_enforced", "instruction_only", "unknown"]
    product_state_observation: Literal["host_observed", "coordinator_observed", "agent_reported", "unknown"]
    complete_child_trace: bool
    atomic_path_enforcement: bool
    atomic_lease_create: bool
    bounded_resource_enforcement: Literal["framework_enforced", "host_enforced", "instruction_only", "unknown"]
    fresh_context_enforcement: Literal["host_enforced", "instruction_only", "unknown"]
    provider_identity_observation: Literal["provider_reported", "coordinator_observed", "host_observed", "unknown"]
    policy_aware_role_allocation: bool


class CoordinatorBundleV2(StrictModel):
    schema_version: Literal["3.0"]
    project_root: str
    run_id: SafeIdentifier
    next_operation_index: int = Field(ge=0)
    plan: LowLevelPlanV2 | None = None
    plan_assessment: AssessmentV2 | None = None
    plan_semantic_proposal: SemanticAssessmentProposalV2 | None = None
    global_policy: ActivePolicy | None = None
    active_policy: ActivePolicyV2 | None = None
    host_capabilities: HostCapabilitiesV2 | None = None
    provider_grant: ProviderGrant | None = None
    run_resource_grant: RunResourceGrant | None = None
    resource_grant_history: list[RunResourceGrant] = Field(default_factory=list)
    manifest: RunManifestV2
    plan_hash: HashRef
    assessment_hash: HashRef
    policy_hash: HashRef
    policy_binding: PolicyBinding
    base_snapshot_hash: HashRef
    host_capabilities_hash: HashRef
    provider_grant_hash: HashRef
    run_resource_grant_hash: HashRef
    proposal_hash: HashRef | None
    proposal_preflight_hash: HashRef | None
    patch_assessment_hash: HashRef | None
    proposal_context: ProposalContext | None = None
    agent_proposal: AgentPatchProposal | None = None
    proposal: BoundedPatchProposal | None = None
    proposal_preflight: PatchProposalPreflight | None = None
    assessment_context: ProposalContext | None = None
    semantic_patch_proposal: PatchSemanticAssessmentProposal | None = None
    patch_assessment: PatchAssessment | None = None
    exact_changes: list[ExactProposedChange] = Field(default_factory=list)
    source_inputs: list[ExactTextInput] = Field(default_factory=list)
    proposal_approvals: list[ApprovalV2] = Field(default_factory=list)
    apply_intent: ApplyIntent | None
    proposal_history: list[BoundedPatchProposal] = Field(default_factory=list)
    patch_assessment_history: list[PatchAssessment] = Field(default_factory=list)
    apply_intent_history: list[ApplyIntent] = Field(default_factory=list)
    execution_reports: list[ExecutionReportV2]
    repair_attempts: list[RepairAttemptV2]
    repair_outcomes: list[RepairOutcomeV2] = Field(default_factory=list)
    proposal_cycle_history: list[ProposalCycleRecord] = Field(default_factory=list)
    role_call_records: list[RoleCallRecord] = Field(default_factory=list)
    automatic_retry_history: list[AutomaticRetryRecord] = Field(default_factory=list)
    active_semantic_request_token: SafeIdentifier | None = None
    completed_semantic_request_tokens: list[SafeIdentifier] = Field(default_factory=list)
    post_execution_snapshot: RepositorySnapshotV3 | None = None
    proposal_base_snapshot: RepositorySnapshotV3 | None = None
    last_verification: VerificationReportV2 | None = None
    human_interventions: list[HumanInterventionV2] = Field(default_factory=list)

    @model_validator(mode="after")
    def bundle_bindings(self) -> "CoordinatorBundleV2":
        _absolute_path(self.project_root, "project_root")
        if self.manifest.run_id != self.run_id:
            raise ValueError("coordinator bundle and manifest run IDs differ")
        pairs = (
            (self.plan_hash, self.manifest.plan_hash, "plan_hash"),
            (self.assessment_hash, self.manifest.assessment_hash, "assessment_hash"),
            (self.policy_hash, self.manifest.policy_hash, "policy_hash"),
            (self.base_snapshot_hash, self.manifest.snapshot_hash, "base_snapshot_hash"),
            (self.provider_grant_hash, self.manifest.provider_grant_hash, "provider_grant_hash"),
            (self.run_resource_grant_hash, self.manifest.run_resource_grant_hash, "run_resource_grant_hash"),
            (self.proposal_hash, self.manifest.current_proposal_hash, "proposal_hash"),
            (self.patch_assessment_hash, self.manifest.current_patch_assessment_hash, "patch_assessment_hash"),
        )
        for left, right, field in pairs:
            if left != right:
                raise ValueError(f"coordinator bundle {field} differs from manifest")
        _require_ref(self.host_capabilities_hash, "host-capabilities", "3.0", "host_capabilities_hash")
        if self.policy_binding != self.manifest.policy_binding or self.policy_binding.effective_policy_hash != self.policy_hash:
            raise ValueError("coordinator policy binding differs from its manifest or policy hash")
        bound_artifacts = (
            (self.plan, "low-level-plan", "3.0", self.plan_hash),
            (self.plan_assessment, "assessment", "3.0", self.assessment_hash),
            (self.provider_grant, "provider-grant", "1.0", self.provider_grant_hash),
            (self.run_resource_grant, "run-resource-grant", "1.0", self.run_resource_grant_hash),
            (self.host_capabilities, "host-capabilities", "3.0", self.host_capabilities_hash),
            (self.proposal, "bounded-patch-proposal", "2.0", self.proposal_hash),
            (self.proposal_preflight, "patch-proposal-preflight", "2.0", self.proposal_preflight_hash),
            (self.patch_assessment, "patch-assessment", "2.0", self.patch_assessment_hash),
        )
        for artifact, kind, version, expected_hash in bound_artifacts:
            if artifact is not None:
                observed = HashRef(
                    artifact_type=kind,
                    schema_version=version,
                    value=artifact_hash(kind, version, artifact.model_dump(mode="json")),
                )
                if observed != expected_hash:
                    raise ValueError(f"coordinator bundle embedded {kind} differs from its hash")
        if self.proposal_preflight_hash is not None:
            _require_ref(self.proposal_preflight_hash, "patch-proposal-preflight", "2.0", "proposal_preflight_hash")
        if self.apply_intent is None:
            if self.manifest.current_apply_intent_hash is not None:
                raise ValueError("manifest names an apply intent absent from the coordinator bundle")
        elif self.manifest.current_apply_intent_hash is None:
            raise ValueError("coordinator bundle apply intent lacks a manifest binding")
        elif HashRef(
            artifact_type="apply-intent", schema_version="2.0",
            value=artifact_hash("apply-intent", "2.0", self.apply_intent.model_dump(mode="json")),
        ) != self.manifest.current_apply_intent_hash:
            raise ValueError("coordinator bundle apply intent differs from the manifest binding")
        if self.plan is not None:
            if self.next_operation_index > len(self.plan.operations):
                raise ValueError("coordinator next operation index exceeds the plan")
            expected_prefix = [item.operation_id for item in self.plan.operations[:self.next_operation_index]]
            if [item.operation_id for item in self.execution_reports] != expected_prefix:
                raise ValueError("coordinator execution reports do not form the completed plan prefix")
        if self.plan_assessment is not None and self.plan_semantic_proposal is not None:
            if self.plan_assessment.provider_grant_hash != self.plan_semantic_proposal.provider_grant_hash:
                raise ValueError("coordinator plan assessment and semantic proposal provider bindings differ")
        if self.proposal is not None:
            expected_changes = {
                **{path: "create" for path in self.proposal.created_paths},
                **{path: "modify" for path in self.proposal.modified_paths},
                **{path: "delete" for path in self.proposal.deleted_paths},
            }
            if {item.path: item.action for item in self.exact_changes} != expected_changes:
                raise ValueError("coordinator exact changes differ from the current proposal")
        if self.assessment_context is not None and self.semantic_patch_proposal is not None:
            if self.semantic_patch_proposal.request_token != self.assessment_context.request_token:
                raise ValueError("coordinator semantic assessment differs from its fresh context")
        if self.patch_assessment is not None and self.proposal_preflight is not None:
            observed_preflight_hash = HashRef(
                artifact_type="patch-proposal-preflight", schema_version="2.0",
                value=artifact_hash(
                    "patch-proposal-preflight", "2.0", self.proposal_preflight.model_dump(mode="json")
                ),
            )
            if self.patch_assessment.preflight_hash != observed_preflight_hash:
                raise ValueError("coordinator patch assessment binds another deterministic preflight")
        if self.patch_assessment is not None and self.semantic_patch_proposal is not None:
            observed_semantic_hash = HashRef(
                artifact_type="patch-semantic-assessment-proposal", schema_version="2.0",
                value=artifact_hash(
                    "patch-semantic-assessment-proposal", "2.0",
                    self.semantic_patch_proposal.model_dump(mode="json"),
                ),
            )
            if self.patch_assessment.semantic_proposal_hash != observed_semantic_hash:
                raise ValueError("coordinator patch assessment binds another semantic result")
        _unique([item.operation_id for item in self.execution_reports], "execution report operation IDs")
        _unique([item.attempt_id for item in self.repair_attempts], "repair attempt IDs")
        _unique([item.outcome_id for item in self.repair_outcomes], "repair outcome IDs")
        _unique([item.cycle_id for item in self.proposal_cycle_history], "proposal cycle IDs")
        _unique([item.call_id for item in self.role_call_records], "role call record IDs")
        _unique([item.retry_id for item in self.automatic_retry_history], "automatic retry record IDs")
        _unique(self.completed_semantic_request_tokens, "completed semantic request tokens")
        if self.active_semantic_request_token in set(self.completed_semantic_request_tokens):
            raise ValueError("active semantic request cannot already be completed")
        _unique([item.approval_id for item in self.proposal_approvals], "proposal approval IDs")
        _unique([item.proposal_id for item in self.proposal_history], "proposal history IDs")
        _unique([item.assessment_id for item in self.patch_assessment_history], "patch assessment history IDs")
        _unique([item.intent_id for item in self.apply_intent_history], "apply intent history IDs")
        _unique([item.grant_id for item in self.resource_grant_history], "resource grant history IDs")
        completed_tokens = set(self.completed_semantic_request_tokens)
        call_records_by_hash = {
            artifact_hash("role-call-record", "2.0", item.model_dump(mode="json")): item
            for item in self.role_call_records
        }
        grants_by_hash = {
            artifact_hash("run-resource-grant", "1.0", item.model_dump(mode="json")): item
            for item in self.resource_grant_history
        }
        retry_counts: dict[tuple[str, str], int] = {}
        retried_tokens: set[str] = set()
        for retry in self.automatic_retry_history:
            if retry.policy_binding != self.policy_binding:
                raise ValueError("automatic retry record uses another policy binding")
            if retry.failed_request_token not in completed_tokens:
                raise ValueError("automatic retry record names a request that is not durably complete")
            if retry.failed_request_token in retried_tokens:
                raise ValueError("a completed request cannot authorise more than one automatic retry")
            retried_tokens.add(retry.failed_request_token)
            call_record = call_records_by_hash.get(retry.role_call_record_hash.value)
            if call_record is None:
                raise ValueError("automatic retry record lacks its complete role-call record")
            if (
                call_record.role != "proposer"
                or call_record.outcome != "success"
                or not call_record.usage_complete
                or call_record.policy_binding != retry.policy_binding
                or call_record.request_hash != retry.request_sha256
                or call_record.response_hash != retry.response_sha256
            ):
                raise ValueError("automatic retry record is not bound to a complete proposer call")
            grant = grants_by_hash.get(retry.resource_grant_hash.value)
            if grant is None:
                raise ValueError("automatic retry record uses an unauthorised resource grant")
            if retry.failure_class not in grant.automatic_retry_classes:
                raise ValueError("automatic retry class is absent from its resource grant")
            key = (retry.operation_id, retry.operation_attempt_id)
            expected_index = retry_counts.get(key, 0) + 1
            if retry.retry_index != expected_index:
                raise ValueError("automatic retry history is not a continuous per-attempt sequence")
            retry_counts[key] = expected_index
            if (
                grant.automatic_retry_attempt_limit != "unbounded"
                and retry.retry_index > grant.automatic_retry_attempt_limit
            ):
                raise ValueError("automatic retry history exceeds its confirmed attempt limit")
        _unique([
            artifact_hash("human-intervention", "3.0", item.model_dump(mode="json"))
            for item in self.human_interventions
        ], "human intervention records")
        for previous, current in zip(self.resource_grant_history, self.resource_grant_history[1:]):
            if current.replenishes_grant_id != previous.grant_id:
                raise ValueError("resource grant history is not a continuous replenishment chain")
        return self


class BoundedAgentTaskV2(OperationCommon):
    kind: Literal["bounded_agent_task"]
    proposal_protocol: Literal["unified_diff_v1"]
    goal: str
    non_goals: list[str]
    evidence_ids: list[str]
    source_data_classification: DataClassification
    allowed_read_tools: list[Literal["read_file"]]
    allowed_patch_actions: list[Literal["create", "modify", "delete"]]
    created_file_mode: int = Field(ge=0, le=0o7777)
    forbidden_actions: list[str]
    permitted_adaptations: list[Literal["choose_file_within_root", "revise_local_code", "diagnose_failure"]]
    diagnostic_checkpoint_rules: list[str]
    completion_evidence: list[SafeIdentifier]
    escalation_conditions: list[str]
    required_adapter: ProposalAdapter
    required_assurance_profile: ProposalAssuranceProfile
    provider_grant_id: SafeIdentifier
    run_resource_grant_id: SafeIdentifier

    @model_validator(mode="after")
    def proposal_only(self) -> "BoundedAgentTaskV2":
        for field in (
            "non_goals", "evidence_ids", "allowed_read_tools", "allowed_patch_actions", "forbidden_actions",
            "permitted_adaptations", "diagnostic_checkpoint_rules", "completion_evidence", "escalation_conditions",
        ):
            _unique(getattr(self, field), f"bounded task {self.operation_id} {field}")
        if not self.allowed_patch_actions:
            raise ValueError("proposal-first bounded tasks require at least one permitted patch action")
        expected = "framework_tool_enforced_proposer" if self.required_adapter == "pydantic_ai" else "instruction_only_proposal_host"
        if self.required_assurance_profile != expected:
            raise ValueError("bounded task adapter and assurance profile contradict")
        return self


class ReadFileActionV2(ReadFileAction):
    """Schema-2 plan form of an exact bounded read."""


class ApplyPatchActionV2(ApplyPatchAction):
    """Schema-2 exact patch with an explicit created-file mode."""

    created_file_mode: int = Field(ge=0, le=0o7777)


ExactActionV2 = Annotated[
    Union[ReadFileActionV2, ApplyPatchActionV2],
    Field(discriminator="adapter"),
]


OperationV2 = ExactActionV2 | BoundedAgentTaskV2


class ExactTextInput(StrictModel):
    input_id: SafeIdentifier
    observation_id: SafeIdentifier
    path: str
    byte_start: int = Field(ge=0)
    byte_end: int = Field(ge=0)
    content: str
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    metadata_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    data_classification: DataClassification

    @model_validator(mode="after")
    def exact_content_identity(self) -> "ExactTextInput":
        _absolute_path(self.path, "exact text input path")
        encoded = self.content.encode("utf-8")
        if self.byte_end < self.byte_start or len(encoded) != self.byte_end - self.byte_start:
            raise ValueError("exact text input range differs from its UTF-8 content length")
        if hashlib.sha256(encoded).hexdigest() != self.content_hash:
            raise ValueError("exact text input content hash differs from its content")
        return self


class ReadToolResult(StrictModel):
    schema_version: Literal["2.0"]
    request_token: SafeIdentifier
    observation_id: SafeIdentifier
    path: str
    byte_start: int = Field(ge=0)
    byte_end: int = Field(ge=0)
    content: str
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    metadata_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    data_classification: DataClassification
    policy_decision: PathPolicyDecision

    @model_validator(mode="after")
    def exact_read_identity(self) -> "ReadToolResult":
        _absolute_path(self.path, "read tool result path")
        if self.byte_end < self.byte_start:
            raise ValueError("read tool result byte range is reversed")
        encoded = self.content.encode("utf-8")
        if len(encoded) != self.byte_end - self.byte_start:
            raise ValueError("read tool result byte range differs from UTF-8 content length")
        if hashlib.sha256(encoded).hexdigest() != self.content_hash:
            raise ValueError("read tool result content hash differs from its content")
        if not self.policy_decision.allowed or self.policy_decision.capability != "read":
            raise ValueError("read tool result requires an allowed read policy decision")
        if self.policy_decision.requested_path != self.path:
            raise ValueError("read tool result policy decision names another path")
        return self


class ProposalRequest(StrictModel):
    schema_version: Literal["2.0"]
    context: ProposalContext
    operation: BoundedAgentTaskV2
    plan_evidence: list[EvidenceRef]
    applicable_instructions: dict[str, str]
    source_inputs: list[ExactTextInput]

    @model_validator(mode="after")
    def complete_proposer_packet(self) -> "ProposalRequest":
        if self.context.role != "proposer":
            raise ValueError("proposal requests require a proposer context")
        if self.context.operation_id != self.operation.operation_id:
            raise ValueError("proposal request operation differs from its context")
        if self.context.operation_hash.value != artifact_hash(
            "operation", "2.0", self.operation.model_dump(mode="json")
        ):
            raise ValueError("proposal request operation content differs from its context hash")
        _unique([item.evidence_id for item in self.plan_evidence], "proposal request evidence IDs")
        _unique([item.input_id for item in self.source_inputs], "proposal request input IDs")
        _unique([item.observation_id for item in self.source_inputs], "proposal request observation IDs")
        if {item.observation_id for item in self.source_inputs} != {
            item.observation_id for item in self.context.source_observations
        }:
            raise ValueError("proposal request exact inputs differ from context observations")
        if set(self.applicable_instructions) != set(self.context.instruction_hashes):
            raise ValueError("proposal request instructions differ from context instruction identities")
        for path, content in self.applicable_instructions.items():
            if hashlib.sha256(content.encode("utf-8")).hexdigest() != self.context.instruction_hashes[path]:
                raise ValueError("proposal request instruction content differs from its context hash")
        return self


class ExactProposedChange(StrictModel):
    path: str
    action: Literal["create", "modify", "delete"]
    preimage: str | None
    postimage: str | None
    preimage_hash: str | None
    postimage_hash: str | None
    metadata_hash: str | None

    @model_validator(mode="after")
    def exact_change_shape(self) -> "ExactProposedChange":
        _absolute_path(self.path, "proposed change path")
        if self.action == "create":
            if any(value is not None for value in (self.preimage, self.preimage_hash, self.metadata_hash)):
                raise ValueError("created changes cannot claim a preimage or prior metadata")
            if self.postimage is None or self.postimage_hash is None:
                raise ValueError("created changes require an exact postimage")
        elif self.action == "delete":
            if self.preimage is None or self.preimage_hash is None or self.metadata_hash is None:
                raise ValueError("deleted changes require exact preimage and metadata")
            if self.postimage is not None or self.postimage_hash is not None:
                raise ValueError("deleted changes cannot have a postimage")
        else:
            if any(value is None for value in (self.preimage, self.postimage, self.preimage_hash, self.postimage_hash, self.metadata_hash)):
                raise ValueError("modified changes require exact preimage, postimage, and metadata")
        if self.preimage is not None and hashlib.sha256(self.preimage.encode("utf-8")).hexdigest() != self.preimage_hash:
            raise ValueError("proposed change preimage hash differs from content")
        if self.postimage is not None and hashlib.sha256(self.postimage.encode("utf-8")).hexdigest() != self.postimage_hash:
            raise ValueError("proposed change postimage hash differs from content")
        return self


class PatchAssessmentRequest(StrictModel):
    schema_version: Literal["2.0"]
    context: ProposalContext
    operation: BoundedAgentTaskV2
    proposal: BoundedPatchProposal
    preflight: PatchProposalPreflight
    exact_changes: list[ExactProposedChange]
    source_inputs: list[ExactTextInput]
    applicable_instructions: dict[str, str]

    @model_validator(mode="after")
    def complete_assessment_packet(self) -> "PatchAssessmentRequest":
        if self.context.role != "patch_assessor":
            raise ValueError("patch assessment requests require a patch-assessor context")
        if self.context.operation_id != self.operation.operation_id:
            raise ValueError("patch assessment operation differs from its context")
        if self.context.operation_hash.value != artifact_hash(
            "operation", "2.0", self.operation.model_dump(mode="json")
        ):
            raise ValueError("patch assessment operation content differs from its context hash")
        if self.preflight.proposal_hash.value != artifact_hash(
            "bounded-patch-proposal", "2.0", self.proposal.model_dump(mode="json")
        ):
            raise ValueError("patch assessment preflight is not bound to the supplied proposal")
        if self.proposal.operation_hash != self.context.operation_hash:
            raise ValueError("patch assessment proposal and context bind different operations")
        if self.proposal.context_hash.artifact_type != "proposal-context":
            raise ValueError("patch assessment proposal has an invalid proposal-context binding")
        expected = {
            **{path: "create" for path in self.proposal.created_paths},
            **{path: "modify" for path in self.proposal.modified_paths},
            **{path: "delete" for path in self.proposal.deleted_paths},
        }
        observed = {item.path: item.action for item in self.exact_changes}
        if len(observed) != len(self.exact_changes) or observed != expected:
            raise ValueError("patch assessment exact changes differ from the proposal inventory")
        if set(self.applicable_instructions) != set(self.context.instruction_hashes):
            raise ValueError("patch assessment instructions differ from context instruction identities")
        for path, content in self.applicable_instructions.items():
            if hashlib.sha256(content.encode("utf-8")).hexdigest() != self.context.instruction_hashes[path]:
                raise ValueError("patch assessment instruction content differs from its context hash")
        if {item.observation_id for item in self.source_inputs} != {
            item.observation_id for item in self.context.source_observations
        }:
            raise ValueError("patch assessment source inputs differ from context observations")
        return self


class ProposalCycleRecord(StrictModel):
    """Complete durable evidence for one accepted and committed proposal cycle."""

    schema_version: Literal["2.0"]
    cycle_id: SafeIdentifier
    operation_id: SafeIdentifier
    attempt_id: SafeIdentifier
    proposal_context: ProposalContext
    agent_proposal: AgentPatchProposal
    proposal: BoundedPatchProposal
    proposal_preflight: PatchProposalPreflight
    assessment_context: ProposalContext
    semantic_patch_proposal: PatchSemanticAssessmentProposal
    patch_assessment: PatchAssessment
    exact_changes: list[ExactProposedChange]
    source_inputs: list[ExactTextInput]
    apply_intent: ApplyIntent
    execution_report: ExecutionReportV2
    policy_binding: PolicyBinding

    @model_validator(mode="after")
    def complete_cycle_bindings(self) -> "ProposalCycleRecord":
        if any(
            binding != self.policy_binding
            for binding in (
                self.proposal_context.policy_binding,
                self.proposal.policy_binding,
                self.proposal_preflight.policy_binding,
                self.assessment_context.policy_binding,
                self.semantic_patch_proposal.policy_binding,
                self.patch_assessment.policy_binding,
                self.apply_intent.policy_binding,
                self.execution_report.policy_binding,
            )
        ):
            raise ValueError("proposal cycle contains inconsistent policy bindings")
        if self.operation_id != self.proposal_context.operation_id or self.operation_id != self.agent_proposal.operation_id:
            raise ValueError("proposal cycle operation identities differ")
        if self.operation_id != self.apply_intent.operation_id or self.operation_id != self.execution_report.operation_id:
            raise ValueError("proposal cycle commit or report names another operation")
        if self.attempt_id != self.proposal_context.attempt_id or self.attempt_id != self.agent_proposal.attempt_id:
            raise ValueError("proposal cycle attempt identities differ")
        if self.assessment_context.attempt_id != self.attempt_id or self.assessment_context.role != "patch_assessor":
            raise ValueError("proposal cycle assessment context differs from its attempt")
        if self.semantic_patch_proposal.request_token != self.assessment_context.request_token:
            raise ValueError("proposal cycle semantic assessment differs from its fresh context")
        proposal_hash = HashRef(
            artifact_type="bounded-patch-proposal", schema_version="2.0",
            value=artifact_hash("bounded-patch-proposal", "2.0", self.proposal.model_dump(mode="json")),
        )
        assessment_hash = HashRef(
            artifact_type="patch-assessment", schema_version="2.0",
            value=artifact_hash("patch-assessment", "2.0", self.patch_assessment.model_dump(mode="json")),
        )
        if self.proposal_preflight.proposal_hash != proposal_hash or self.patch_assessment.proposal_hash != proposal_hash:
            raise ValueError("proposal cycle preflight or assessment binds another proposal")
        if self.patch_assessment.preflight_hash != HashRef(
            artifact_type="patch-proposal-preflight", schema_version="2.0",
            value=artifact_hash(
                "patch-proposal-preflight", "2.0", self.proposal_preflight.model_dump(mode="json")
            ),
        ):
            raise ValueError("proposal cycle patch assessment binds another deterministic preflight")
        if self.patch_assessment.semantic_proposal_hash != HashRef(
            artifact_type="patch-semantic-assessment-proposal", schema_version="2.0",
            value=artifact_hash(
                "patch-semantic-assessment-proposal", "2.0",
                self.semantic_patch_proposal.model_dump(mode="json"),
            ),
        ):
            raise ValueError("proposal cycle patch assessment binds another semantic result")
        if self.apply_intent.execution_kind != "bounded_proposal":
            raise ValueError("proposal cycle requires a bounded apply intent")
        if self.apply_intent.proposal_hash != proposal_hash or self.execution_report.proposal_hash != proposal_hash:
            raise ValueError("proposal cycle commit or report binds another proposal")
        if self.apply_intent.patch_assessment_hash != assessment_hash or self.execution_report.patch_assessment_hash != assessment_hash:
            raise ValueError("proposal cycle commit or report binds another patch assessment")
        expected_changes = {
            **{path: "create" for path in self.proposal.created_paths},
            **{path: "modify" for path in self.proposal.modified_paths},
            **{path: "delete" for path in self.proposal.deleted_paths},
        }
        if {item.path: item.action for item in self.exact_changes} != expected_changes:
            raise ValueError("proposal cycle exact changes differ from its proposal")
        if {item.observation_id for item in self.source_inputs} != {
            item.observation_id for item in self.proposal_context.source_observations
        }:
            raise ValueError("proposal cycle source inputs differ from its proposal context")
        if {item.observation_id for item in self.source_inputs} != {
            item.observation_id for item in self.assessment_context.source_observations
        }:
            raise ValueError("proposal cycle source inputs differ from its assessment context")
        if self.apply_intent.state != "committed":
            raise ValueError("completed proposal cycle requires a committed apply intent")
        return self


class RepositorySnapshotV2(RepositorySnapshotV3):
    """Current schema-3 snapshot; the internal class name remains for source compatibility."""


class LowLevelPlanV2(LowLevelPlan):
    schema_version: Literal["3.0"]
    snapshot: RepositorySnapshotV2
    operations: list[OperationV2]
    provider_grant_hash: HashRef
    run_resource_grant_hash: HashRef
    policy_binding: PolicyBinding

    @model_validator(mode="after")
    def proposal_authority(self) -> "LowLevelPlanV2":
        _require_ref(self.provider_grant_hash, "provider-grant", "1.0", "provider_grant_hash")
        _require_ref(self.run_resource_grant_hash, "run-resource-grant", "1.0", "run_resource_grant_hash")
        if self.global_policy_hash != self.policy_binding.global_policy_hash:
            raise ValueError("plan global policy hash differs from its policy binding")
        if self.merged_policy_hash != self.policy_binding.effective_policy_hash:
            raise ValueError("plan effective policy hash differs from its policy binding")
        if self.snapshot.policy_binding != self.policy_binding:
            raise ValueError("plan and snapshot policy bindings differ")
        for operation in self.operations:
            if self.policy_binding.policy_path not in operation.path_contract.protected_roots:
                raise ValueError("every operation must protect the fixed project policy path")
        return self


class SemanticRoleContext(StrictModel):
    schema_version: Literal["1.0"]
    context_id: SafeIdentifier
    request_token: SafeIdentifier
    role: Literal["plan_assessor", "verifier"]
    adapter: ProposalAdapter
    assurance_profile: ProposalAssuranceProfile
    provider_grant_hash: HashRef
    run_resource_grant_hash: HashRef
    policy_binding: PolicyBinding
    input_artifact_hashes: list[HashRef]
    prompt_packet_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    created_at: UtcTimestamp

    @model_validator(mode="after")
    def no_tool_role_boundary(self) -> "SemanticRoleContext":
        expected = (
            "framework_tool_enforced_no_tools"
            if self.adapter == "pydantic_ai"
            else "instruction_only_proposal_host"
        )
        if self.assurance_profile != expected:
            raise ValueError("semantic role adapter and no-tool assurance profile contradict")
        _require_ref(self.provider_grant_hash, "provider-grant", "1.0", "provider_grant_hash")
        _require_ref(self.run_resource_grant_hash, "run-resource-grant", "1.0", "run_resource_grant_hash")
        _unique(
            [(item.artifact_type, item.schema_version, item.value) for item in self.input_artifact_hashes],
            "semantic role input artifact hashes",
        )
        return self


class PlanAssessmentRequest(StrictModel):
    schema_version: Literal["1.0"]
    context: SemanticRoleContext
    plan: LowLevelPlanV2
    preflight: DeterministicPreflightV2
    active_policy: ActivePolicyV2
    capabilities: HostCapabilitiesV2
    provider_grant: ProviderGrant
    run_resource_grant: RunResourceGrant
    approvals: list[ApprovalV2]
    prior_assessment_hash: HashRef | None

    @model_validator(mode="after")
    def complete_plan_assessment_packet(self) -> "PlanAssessmentRequest":
        if self.context.role != "plan_assessor":
            raise ValueError("plan assessment request requires the plan_assessor role")
        plan_hash = HashRef(
            artifact_type="low-level-plan", schema_version="3.0",
            value=artifact_hash("low-level-plan", "3.0", self.plan.model_dump(mode="json")),
        )
        policy_hash = HashRef(
            artifact_type="active-policy", schema_version="2.0",
            value=artifact_hash("active-policy", "2.0", self.active_policy.model_dump(mode="json")),
        )
        snapshot_hash = HashRef(
            artifact_type="repository-snapshot", schema_version="3.0",
            value=artifact_hash("repository-snapshot", "3.0", self.plan.snapshot.model_dump(mode="json")),
        )
        provider_hash = HashRef(
            artifact_type="provider-grant", schema_version="1.0",
            value=artifact_hash("provider-grant", "1.0", self.provider_grant.model_dump(mode="json")),
        )
        resource_hash = HashRef(
            artifact_type="run-resource-grant", schema_version="1.0",
            value=artifact_hash("run-resource-grant", "1.0", self.run_resource_grant.model_dump(mode="json")),
        )
        preflight_hash = HashRef(
            artifact_type="deterministic-preflight", schema_version="3.0",
            value=artifact_hash("deterministic-preflight", "3.0", self.preflight.model_dump(mode="json")),
        )
        capability_hash = HashRef(
            artifact_type="host-capabilities", schema_version="3.0",
            value=artifact_hash("host-capabilities", "3.0", self.capabilities.model_dump(mode="json")),
        )
        if (
            self.preflight.plan_hash != plan_hash
            or self.preflight.policy_hash != policy_hash
            or self.preflight.snapshot_hash != snapshot_hash
            or self.preflight.provider_grant_hash != provider_hash
            or self.preflight.run_resource_grant_hash != resource_hash
            or self.plan.provider_grant_hash != provider_hash
            or self.plan.run_resource_grant_hash != resource_hash
            or self.context.provider_grant_hash != provider_hash
            or self.context.run_resource_grant_hash != resource_hash
            or self.context.policy_binding != self.plan.policy_binding
            or self.preflight.policy_binding != self.plan.policy_binding
        ):
            raise ValueError("plan assessment packet authority bindings differ")
        expected_inputs = [
            plan_hash, preflight_hash, policy_hash, capability_hash, provider_hash, resource_hash,
        ]
        if self.context.input_artifact_hashes != expected_inputs:
            raise ValueError("plan assessment context does not bind the complete canonical packet")
        if self.preflight.approvals != self.approvals:
            raise ValueError("plan assessment request approvals differ from deterministic preflight")
        if "plan_assessor" not in self.provider_grant.roles:
            raise ValueError("provider grant does not authorise the plan assessor")
        if self.prior_assessment_hash is not None:
            _require_ref(self.prior_assessment_hash, "assessment", "3.0", "prior_assessment_hash")
        return self


class PlanAssessmentResponse(StrictModel):
    schema_version: Literal["1.0"]
    request_token: SafeIdentifier
    plan_hash: HashRef
    preflight_hash: HashRef
    policy_hash: HashRef
    snapshot_hash: HashRef
    semantic_proposal: SemanticAssessmentProposalV2
    policy_binding: PolicyBinding

    @model_validator(mode="after")
    def typed_bindings(self) -> "PlanAssessmentResponse":
        _require_ref(self.plan_hash, "low-level-plan", "3.0", "plan_hash")
        _require_ref(self.preflight_hash, "deterministic-preflight", "3.0", "preflight_hash")
        _require_ref(self.policy_hash, "active-policy", "2.0", "policy_hash")
        _require_ref(self.snapshot_hash, "repository-snapshot", "3.0", "snapshot_hash")
        if self.policy_binding.effective_policy_hash != self.policy_hash:
            raise ValueError("plan assessment response policy binding differs from its policy hash")
        return self


class VerificationFileState(StrictModel):
    path: str
    state: Literal["present", "absent", "unobserved_policy_denied"]
    content: str | None
    content_hash: str | None = Field(pattern=r"^[0-9a-f]{64}$")
    metadata_hash: str | None = Field(pattern=r"^[0-9a-f]{64}$")
    denied_rule_ids: list[SafeIdentifier] = Field(default_factory=list)

    @model_validator(mode="after")
    def exact_static_state(self) -> "VerificationFileState":
        _absolute_path(self.path, "verification file-state path")
        if self.state in {"absent", "unobserved_policy_denied"}:
            if any(value is not None for value in (self.content, self.content_hash, self.metadata_hash)):
                raise ValueError("absent verification file state cannot contain file data")
            if self.state == "unobserved_policy_denied" and not self.denied_rule_ids:
                raise ValueError("unobserved policy-denied state requires controlling rule IDs")
            if self.state == "absent" and self.denied_rule_ids:
                raise ValueError("an observed absent state cannot claim policy denial")
        else:
            if self.content is None or self.content_hash is None or self.metadata_hash is None:
                raise ValueError("present verification file state requires content and metadata hashes")
            if hashlib.sha256(self.content.encode("utf-8")).hexdigest() != self.content_hash:
                raise ValueError("verification file content differs from its hash")
        return self


class VerificationRoleRequest(StrictModel):
    schema_version: Literal["1.0"]
    context: SemanticRoleContext
    verifier_context_id: SafeIdentifier
    plan: LowLevelPlanV2
    assessment: AssessmentV2
    active_policy: ActivePolicyV2
    capabilities: HostCapabilitiesV2
    provider_grant: ProviderGrant
    run_resource_grant: RunResourceGrant
    post_execution_snapshot: RepositorySnapshotV2
    proposals: list[BoundedPatchProposal]
    patch_assessments: list[PatchAssessment]
    execution_reports: list[ExecutionReportV2]
    file_states: list[VerificationFileState]
    applicable_instructions: dict[str, str]
    expected_success_criteria: list[str]
    expected_verifier_checks: list[str]
    expected_effect_ids: list[SafeIdentifier]

    @model_validator(mode="after")
    def complete_verification_packet(self) -> "VerificationRoleRequest":
        if self.context.role != "verifier":
            raise ValueError("verification request requires the verifier role")
        artifacts: list[tuple[str, str, StrictModel]] = [
            ("low-level-plan", "3.0", self.plan),
            ("assessment", "3.0", self.assessment),
            ("active-policy", "2.0", self.active_policy),
            ("host-capabilities", "3.0", self.capabilities),
            ("provider-grant", "1.0", self.provider_grant),
            ("run-resource-grant", "1.0", self.run_resource_grant),
            ("repository-snapshot", "3.0", self.post_execution_snapshot),
        ]
        artifacts.extend(("bounded-patch-proposal", "2.0", item) for item in self.proposals)
        artifacts.extend(("patch-assessment", "2.0", item) for item in self.patch_assessments)
        artifacts.extend(("execution-report", "3.0", item) for item in self.execution_reports)
        expected_inputs = [
            HashRef(
                artifact_type=kind, schema_version=version,
                value=artifact_hash(kind, version, artifact.model_dump(mode="json")),
            )
            for kind, version, artifact in artifacts
        ]
        if self.context.input_artifact_hashes != expected_inputs:
            raise ValueError("verification context does not bind the complete canonical packet")
        provider_hash = expected_inputs[4]
        resource_hash = expected_inputs[5]
        if (
            self.context.provider_grant_hash != provider_hash
            or self.context.run_resource_grant_hash != resource_hash
            or self.plan.provider_grant_hash != provider_hash
            or self.assessment.provider_grant_hash != provider_hash
            or self.assessment.run_resource_grant_hash != resource_hash
        ):
            raise ValueError("verification authority bindings differ")
        if "verifier" not in self.provider_grant.roles:
            raise ValueError("provider grant does not authorise the verifier")
        expected_paths = set(self.post_execution_snapshot.selected_file_hashes) | set(
            self.post_execution_snapshot.expected_product_changes
        )
        if {item.path for item in self.file_states} != expected_paths:
            raise ValueError("verification file states do not exactly cover selected and expected paths")
        if len(self.file_states) != len(expected_paths):
            raise ValueError("verification file-state paths must be unique")
        by_path = {item.path: item for item in self.file_states}
        for path, content_hash in self.post_execution_snapshot.selected_file_hashes.items():
            if by_path[path].state != "present" or by_path[path].content_hash != content_hash:
                raise ValueError("verification file state differs from the post-execution snapshot")
        if set(self.applicable_instructions) != set(self.post_execution_snapshot.instruction_hashes):
            raise ValueError("verification instructions differ from the post-execution snapshot")
        for path, content in self.applicable_instructions.items():
            if hashlib.sha256(content.encode("utf-8")).hexdigest() != self.post_execution_snapshot.instruction_hashes[path]:
                raise ValueError("verification instruction content differs from its snapshot hash")
        expected_criteria = sorted({value for item in self.plan.operations for value in item.success_criteria})
        expected_checks = sorted({value for item in self.plan.operations for value in item.verifier_checks})
        expected_effects = sorted({effect.effect_id for item in self.plan.operations for effect in item.effects})
        if self.expected_success_criteria != expected_criteria:
            raise ValueError("verification request success criteria are incomplete")
        if self.expected_verifier_checks != expected_checks:
            raise ValueError("verification request checks are incomplete")
        if self.expected_effect_ids != expected_effects:
            raise ValueError("verification request effect inventory is incomplete")
        return self


class VerificationRoleResponse(StrictModel):
    schema_version: Literal["1.0"]
    request_token: SafeIdentifier
    verification_proposal: VerificationProposalV2
