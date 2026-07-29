from __future__ import annotations

import re
import unicodedata
from typing import Literal

from pydantic import Field, model_validator

from .models import HashRef, NetworkPolicyGrant, PolicyLimits, RepositorySnapshot, SafeIdentifier, StrictModel, UtcTimestamp


PathCapability = Literal["read", "create", "modify", "delete"]
PolicyPresence = Literal["absent", "present"]


def _unique(values: list[object], label: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"{label} values must be unique")


def canonical_relative_policy_path(value: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 1024 or "\0" in value:
        raise ValueError("policy paths must contain 1 to 1024 non-NUL characters")
    if value != unicodedata.normalize("NFC", value):
        raise ValueError("policy paths must use NFC Unicode normalization")
    if value.startswith("/") or value.startswith("\\") or "\\" in value:
        raise ValueError("policy paths must be project-relative POSIX paths")
    parts = value.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise ValueError("policy paths cannot contain empty, dot, or parent components")
    if len(parts) > 64:
        raise ValueError("policy paths cannot exceed 64 components")
    canonical = "/".join(parts)
    if canonical in {".rb-safe-operation-policy.json", ".rb-safe-operation"} or canonical.startswith(
        ".rb-safe-operation/"
    ):
        raise ValueError("the policy file and safe-operation control state have fixed protection")
    return canonical


class PathRule(StrictModel):
    rule_id: SafeIdentifier
    path: str
    scope: Literal["exact", "subtree"]
    deny: list[PathCapability] = Field(min_length=1, max_length=4)
    reason: str = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def canonical_rule(self) -> "PathRule":
        if self.path != canonical_relative_policy_path(self.path):
            raise ValueError("policy path is not canonical")
        _unique(self.deny, "denied capability")
        if self.deny != sorted(self.deny):
            raise ValueError("denied capabilities must be in canonical alphabetical order")
        return self


class ProjectPolicyV2(StrictModel):
    schema_version: Literal["2.0"]
    policy_version: str = Field(min_length=1, max_length=128)
    path_rules: list[PathRule] = Field(max_length=256)
    deny_operations: list[str]
    deny_adapters: list[str]
    deny_effect_classes: list[str]
    deny_command_forms: list[str]
    intersect_path_roots: list[str] | None
    intersect_executable_hashes: list[str] | None
    intersect_network_grants: list[NetworkPolicyGrant] | None
    intersect_environment_names: list[str] | None
    lower_maximums: dict[str, int | str]
    require_approvals: list[str]
    require_minimum_enforcement: dict[str, Literal["instruction_only", "host_enforced"]]
    require_minimum_observation: dict[
        str, Literal["agent_reported", "coordinator_observed", "host_observed"]
    ]
    require_evidence_sources: list[str]
    require_verification: list[str]

    @model_validator(mode="after")
    def closed_policy(self) -> "ProjectPolicyV2":
        for field in (
            "deny_operations",
            "deny_adapters",
            "deny_effect_classes",
            "deny_command_forms",
            "require_approvals",
            "require_evidence_sources",
            "require_verification",
        ):
            _unique(getattr(self, field), f"project policy {field}")
        for field in ("intersect_path_roots", "intersect_executable_hashes", "intersect_environment_names"):
            values = getattr(self, field)
            if values is not None:
                _unique(values, f"project policy {field}")
        if self.intersect_network_grants is not None:
            _unique([item.grant_id for item in self.intersect_network_grants], "network grant IDs")
        allowed = {"max_seconds", "max_processes", "max_bytes", "max_calls", "max_cost_decimal"}
        if set(self.lower_maximums) - allowed:
            raise ValueError("project policy contains unknown maximum fields")
        ids = [item.rule_id for item in self.path_rules]
        _unique(ids, "path rule IDs")
        semantic = [(item.path, item.scope, tuple(item.deny)) for item in self.path_rules]
        _unique(semantic, "semantic path rules")
        casefolded = [item.path.casefold() for item in self.path_rules]
        if len(casefolded) != len(set(casefolded)):
            raise ValueError("path rules contain a case-insensitive alias collision")
        return self


class ActivePolicyV2(StrictModel):
    schema_version: Literal["2.0"]
    policy_version: str
    allowed_operation_kinds: list[str]
    allowed_adapters: list[str]
    allowed_tools: list[str]
    allowed_effect_classes: list[str]
    allowed_path_roots: list[str]
    allowed_executable_hashes: list[str]
    allowed_environment_names: list[str]
    network_grants: list[NetworkPolicyGrant]
    limits: PolicyLimits
    required_approvals: list[str]
    required_enforcement: dict[str, Literal["instruction_only", "host_enforced"]]
    required_observation: dict[
        str, Literal["agent_reported", "coordinator_observed", "host_observed"]
    ]
    required_evidence_sources: list[str]
    required_verification: list[str]
    denied_operations: list[str]
    denied_adapters: list[str]
    denied_effect_classes: list[str]
    denied_command_forms: list[str]
    path_rules: list[PathRule]

    @model_validator(mode="after")
    def canonical_collections(self) -> "ActivePolicyV2":
        for field in (
            "allowed_operation_kinds", "allowed_adapters", "allowed_tools", "allowed_effect_classes",
            "allowed_path_roots", "allowed_executable_hashes", "allowed_environment_names",
            "required_approvals", "required_evidence_sources", "required_verification",
            "denied_operations", "denied_adapters", "denied_effect_classes", "denied_command_forms",
        ):
            _unique(getattr(self, field), f"active policy {field}")
        _unique([item.rule_id for item in self.path_rules], "active path rule IDs")
        return self


class PolicyBinding(StrictModel):
    schema_version: Literal["1.0"]
    project_root: str
    policy_path: str
    presence: PolicyPresence
    global_policy_hash: HashRef
    source_policy_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    effective_policy_hash: HashRef

    @model_validator(mode="after")
    def correct_hash_types(self) -> "PolicyBinding":
        if self.global_policy_hash.artifact_type != "active-policy" or self.global_policy_hash.schema_version != "1.0":
            raise ValueError("global policy hash must bind active-policy schema 1.0")
        if self.effective_policy_hash.artifact_type != "active-policy" or self.effective_policy_hash.schema_version != "2.0":
            raise ValueError("effective policy hash must bind active-policy schema 2.0")
        if not self.project_root.startswith("/") or not self.policy_path.startswith("/"):
            raise ValueError("policy binding paths must be absolute")
        return self


class PathPolicyDecision(StrictModel):
    schema_version: Literal["1.0"]
    capability: PathCapability
    requested_path: str
    allowed: bool
    matched_rule_ids: list[SafeIdentifier]
    component_identity_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    uncertainty: str | None

    @model_validator(mode="after")
    def decision_consistency(self) -> "PathPolicyDecision":
        _unique(self.matched_rule_ids, "matched path rule IDs")
        denied_or_uncertain = bool(self.matched_rule_ids) or self.uncertainty is not None
        if self.allowed == denied_or_uncertain:
            raise ValueError("allowed path decisions cannot contain a denial or uncertainty")
        return self


class ProjectPolicyProposal(StrictModel):
    schema_version: Literal["1.0"]
    request_token: SafeIdentifier
    proposed_policy: ProjectPolicyV2
    ambiguity_questions: list[str] = Field(max_length=8)
    interpretation_summary: str = Field(min_length=1, max_length=2000)
    no_protected_content_observed: Literal[True]


class PolicyTranslationRequest(StrictModel):
    schema_version: Literal["1.0"]
    request_token: SafeIdentifier
    adapter: Literal["json_line", "pydantic_ai"]
    assurance_profile: Literal["instruction_only_authoring", "framework_tool_enforced_authoring"]
    provider_grant_hash: HashRef
    run_resource_grant_hash: HashRef
    project_root_identity_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_policy_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    policy_binding: PolicyBinding
    current_policy: ProjectPolicyV2 | None
    bounded_user_request: str = Field(min_length=1, max_length=8000)
    named_project_relative_paths: list[str] = Field(max_length=64)
    created_at: UtcTimestamp

    @model_validator(mode="after")
    def bounded_translation_packet(self) -> "PolicyTranslationRequest":
        if self.provider_grant_hash.artifact_type != "provider-grant" or self.provider_grant_hash.schema_version != "1.0":
            raise ValueError("translation request requires a provider grant hash")
        if self.run_resource_grant_hash.artifact_type != "run-resource-grant" or self.run_resource_grant_hash.schema_version != "1.0":
            raise ValueError("translation request requires a run resource grant hash")
        for value in self.named_project_relative_paths:
            canonical_relative_policy_path(value)
        _unique(self.named_project_relative_paths, "named translation paths")
        expected = (
            "framework_tool_enforced_authoring"
            if self.adapter == "pydantic_ai" else "instruction_only_authoring"
        )
        if self.assurance_profile != expected:
            raise ValueError("translation adapter and assurance profile contradict")
        if self.policy_binding.source_policy_sha256 != self.source_policy_sha256:
            raise ValueError("translation request source identity differs from its policy binding")
        return self


class PolicyPreview(StrictModel):
    schema_version: Literal["1.0"]
    project_root: str
    proposal_hash: HashRef
    expected_source_policy_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    proposed_source_policy_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    proposed_effective_policy_hash: HashRef
    change_classification: Literal["create", "tightening", "reason_only", "relaxation", "mixed"]
    added_rule_ids: list[SafeIdentifier]
    retained_rule_ids: list[SafeIdentifier]
    removed_rule_ids: list[SafeIdentifier]
    plain_language_lines: list[str]
    prospective_only_disclosure: str
    assurance_profile: Literal["instruction_only_authoring", "framework_tool_enforced_authoring"]
    confirmation_token: str = Field(pattern=r"^[0-9a-f]{64}$")
    confirmation_statement: str

    @model_validator(mode="after")
    def exact_confirmation_statement(self) -> "PolicyPreview":
        qualifier = (
            " RELAXATION"
            if self.change_classification in {"relaxation", "mixed"}
            else ""
        )
        expected = f"CONFIRM SAFE OPERATION POLICY{qualifier} {self.confirmation_token}"
        if self.confirmation_statement != expected:
            raise ValueError("policy preview confirmation statement differs from its classification and token")
        return self


class PolicyConfirmation(StrictModel):
    schema_version: Literal["1.0"]
    proposal_hash: HashRef
    preview_hash: HashRef
    confirmation_token: str = Field(pattern=r"^[0-9a-f]{64}$")
    statement_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    relaxation_explicitly_confirmed: bool
    confirmed_at: UtcTimestamp
    confirmation_assurance: Literal["instruction_only"]


class PolicyAuthoringRecord(StrictModel):
    schema_version: Literal["1.0"]
    authoring_id: SafeIdentifier
    project_root: str
    proposal_hash: HashRef
    preview_hash: HashRef
    confirmation_hash: HashRef
    old_source_policy_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    new_source_policy_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    old_effective_policy_hash: HashRef
    new_effective_policy_hash: HashRef
    change_classification: Literal["create", "tightening", "reason_only", "relaxation", "mixed"]
    added_rule_ids: list[SafeIdentifier]
    removed_rule_ids: list[SafeIdentifier]
    outcome: Literal["committed", "rejected", "indeterminate"]
    committed_at: UtcTimestamp | None


class PolicyAuthoringIntent(StrictModel):
    schema_version: Literal["1.0"]
    authoring_id: SafeIdentifier
    project_root: str
    proposal_hash: HashRef
    preview_hash: HashRef
    confirmation_hash: HashRef
    expected_source_policy_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    proposed_source_policy_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    change_classification: Literal["create", "tightening", "reason_only", "relaxation", "mixed"]
    created_at: UtcTimestamp


class RepositorySnapshotV3(RepositorySnapshot):
    schema_version: Literal["3.0"] = "3.0"
    observation_mode: Literal["git_and_filesystem", "full_filesystem", "policy_pruned_filesystem"]
    policy_binding: PolicyBinding
    denied_rule_ids: list[SafeIdentifier]
    unobserved_subtree_rule_ids: list[SafeIdentifier]
    selected_file_metadata_hashes: dict[str, str]
    proposal_context_observation_hashes: dict[SafeIdentifier, str]

    @model_validator(mode="after")
    def policy_snapshot_consistency(self) -> "RepositorySnapshotV3":
        if self.policy_binding.project_root != self.project_root:
            raise ValueError("snapshot and policy binding project roots differ")
        _unique(self.denied_rule_ids, "snapshot denied rule IDs")
        _unique(self.unobserved_subtree_rule_ids, "snapshot unobserved subtree rule IDs")
        if not set(self.unobserved_subtree_rule_ids).issubset(self.denied_rule_ids):
            raise ValueError("unobserved subtree rules must be denied rules")
        if self.observation_mode == "policy_pruned_filesystem" and any(
            value is not None
            for value in (
                self.git_executable_path,
                self.git_executable_hash,
                self.git_head,
                self.git_branch,
                self.index_hash,
            )
        ):
            raise ValueError("policy-pruned snapshots cannot claim broad Git observations")
        return self
