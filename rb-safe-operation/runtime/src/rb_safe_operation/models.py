from __future__ import annotations

from datetime import datetime
from pathlib import PurePosixPath
import re
from typing import Annotated, Literal, Union

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator


def _utc_timestamp(value: str) -> str:
    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise ValueError("timestamp must be a valid whole-second UTC RFC 3339 value ending Z") from exc
    return value


def _safe_identifier(value: str) -> str:
    if value in {".", ".."} or ".." in value:
        raise ValueError("identifier cannot contain traversal components")
    return value


def _absolute_literal(value: str, field: str) -> None:
    path = PurePosixPath(value)
    if not path.is_absolute() or ".." in path.parts or any(token in value for token in ("\0", "$", "*", "?", "[", "]")):
        raise ValueError(f"{field} requires absolute literal paths without traversal, variables, or globs")


def _require_unique(values: list[object], field: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"{field} values must be unique")


UtcTimestamp = Annotated[str, AfterValidator(_utc_timestamp)]
SafeIdentifier = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$"), AfterValidator(_safe_identifier)]
NonNegativeInt = Annotated[int, Field(ge=0)]
PositiveInt = Annotated[int, Field(gt=0)]

INVARIANT_IDS = frozenset({
    "A-001", "A-002", "A-003", "A-004", "A-005", "A-006", "A-007", "A-008",
    "C-001", "C-002", "C-003", "C-004",
    "D-001", "D-002", "D-003", "D-004", "D-005", "D-006", "D-007",
    "E-001", "E-002", "E-003", "E-004",
    "K-001", "K-002", "K-003", "K-004",
    "L-001", "L-002", "L-003", "L-004",
    "O-001", "O-002", "O-003", "O-004", "O-005", "O-006", "O-007", "O-008",
    "P-001", "P-002", "P-003", "P-004",
    "R-001", "R-002", "R-003", "R-004", "R-005",
    "X-001", "X-002",
})


def _known_invariant(value: str) -> str:
    if value not in INVARIANT_IDS:
        raise ValueError(f"unknown controlling invariant ID: {value}")
    return value


InvariantIdentifier = Annotated[str, Field(pattern=r"^[A-Z]-[0-9]{3}$"), AfterValidator(_known_invariant)]
FindingCategory = Literal[
    "ambiguity", "approval_scope", "artifact_identity", "authority_conflict", "delegation",
    "detrimental_effect", "effect_inventory", "environment_widening", "executable_identity",
    "finding_identity", "hidden_scope", "incomplete_operation", "incomplete_verification",
    "instruction_scope", "missing_evidence", "network_widening", "operation_contract",
    "path_escape", "phase_continuity", "plan_fidelity", "policy_limit", "policy_widening",
    "prompt_injection", "recovery_realism", "repairable_local", "snapshot_drift",
    "transitive_execution", "unobservable_risk", "unsupported_adapter", "unsupported_host_capability",
    "unsupported_operation", "unsupported_tool",
]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class HashRef(StrictModel):
    artifact_type: str
    schema_version: str
    algorithm: Literal["sha256"] = "sha256"
    value: str = Field(pattern=r"^[0-9a-f]{64}$")


class EvidenceRef(StrictModel):
    evidence_id: SafeIdentifier
    provenance: Literal["host_observed", "coordinator_observed", "agent_reported"]
    locator: str
    summary: str


class PathContract(StrictModel):
    read_roots: list[str]
    create_roots: list[str]
    modify_roots: list[str]
    delete_roots: list[str]
    protected_roots: list[str]
    working_directories: list[str]

    @model_validator(mode="after")
    def absolute_closed_paths(self) -> "PathContract":
        for field in ("read_roots", "create_roots", "modify_roots", "delete_roots", "protected_roots", "working_directories"):
            _require_unique(getattr(self, field), field)
            for value in getattr(self, field):
                path = PurePosixPath(value)
                if not path.is_absolute() or ".." in path.parts or any(token in value for token in ("\0", "$", "*", "?", "[", "]")):
                    raise ValueError(f"{field} requires absolute literal paths without traversal, variables, or globs")
        if not self.working_directories:
            raise ValueError("at least one working directory is required")
        return self


class EnvironmentEntry(StrictModel):
    name: str
    literal_value: str | None
    value_hash: str | None
    secret_handle: str | None

    @model_validator(mode="after")
    def one_source(self) -> "EnvironmentEntry":
        if sum(value is not None for value in (self.literal_value, self.value_hash, self.secret_handle)) != 1:
            raise ValueError("environment entry requires exactly one value source")
        return self


class NetworkGrant(StrictModel):
    grant_id: SafeIdentifier
    destinations: list[str]
    ports: list[Annotated[int, Field(ge=1, le=65535)]]
    protocols: list[Literal["http", "https", "tcp"]]
    methods: list[str]
    semantics: list[Literal["read", "write"]]
    request_data_classes: list[str]
    response_data_classes: list[str]
    credential_audiences: list[str]
    redirect_destinations: list[str]
    max_calls: NonNegativeInt
    max_bytes: NonNegativeInt
    max_seconds: NonNegativeInt
    retry_limit: NonNegativeInt
    idempotency_required: bool
    approval_classes: list[str]

    @model_validator(mode="after")
    def unique_dimensions(self) -> "NetworkGrant":
        for field in (
            "destinations", "ports", "protocols", "methods", "semantics", "request_data_classes",
            "response_data_classes", "credential_audiences", "redirect_destinations", "approval_classes",
        ):
            _require_unique(getattr(self, field), f"network grant {self.grant_id} {field}")
        return self


class ResourceLimits(StrictModel):
    max_seconds: PositiveInt
    max_processes: PositiveInt
    max_bytes: NonNegativeInt
    max_calls: NonNegativeInt
    max_cost_decimal: str
    attempt_limit: int | Literal["unbounded"]

    @model_validator(mode="after")
    def canonical_resources(self) -> "ResourceLimits":
        from .canonical import canonical_decimal

        canonical_decimal(self.max_cost_decimal)
        if isinstance(self.attempt_limit, int) and self.attempt_limit < 0:
            raise ValueError("attempt_limit cannot be negative")
        return self


class Effect(StrictModel):
    effect_id: SafeIdentifier
    kind: Literal["direct", "indirect", "verification", "cumulative"]
    effect_class: str
    affected_party: str
    data_classification: Literal["public", "internal", "personal", "sensitive", "secret"]
    security_sensitive: bool
    unmitigated_severity: Literal["none", "low", "medium", "high", "critical"]
    residual_severity: Literal["none", "low", "medium", "high", "critical"]
    likelihood: Literal["rare", "unlikely", "possible", "likely", "almost_certain"]
    exposure: Literal["isolated", "repository", "project_external", "multi_party", "systemic"]
    reversibility: Literal["full", "bounded", "uncertain", "none"]
    detectability: Literal["full", "partial", "weak", "unknown"]
    mitigation: Literal["verified", "proposed", "none"]
    recovery: Literal["tested", "specified", "uncertain", "impossible"]
    cost_impact: Literal["none", "low", "medium", "high"]
    availability_impact: Literal["none", "low", "medium", "high"]
    approval_class: str | None
    targets: list[str]
    observation_sources: list[Literal["host_observed", "coordinator_observed", "agent_reported"]]
    cumulative_interaction: Literal["none", "additive", "amplifying"]
    cumulative_member_effect_ids: list[str]
    evidence_ids: list[SafeIdentifier]

    @model_validator(mode="after")
    def cumulative_shape(self) -> "Effect":
        if self.kind == "cumulative" and not self.cumulative_member_effect_ids:
            raise ValueError("cumulative effects require member effect IDs")
        if self.kind != "cumulative" and self.cumulative_member_effect_ids:
            raise ValueError("only cumulative effects may name member effect IDs")
        if self.kind != "cumulative" and self.cumulative_interaction != "none":
            raise ValueError("non-cumulative effects require cumulative_interaction none")
        if self.kind == "cumulative" and self.cumulative_interaction == "none":
            raise ValueError("cumulative effects require additive or amplifying interaction")
        if self.approval_class is not None and not self.targets:
            raise ValueError("approval-gated effects require exact targets")
        if len(self.targets) != len(set(self.targets)):
            raise ValueError("effect targets must be unique")
        if not self.observation_sources:
            raise ValueError("effects require at least one observation source")
        if not self.evidence_ids or len(self.evidence_ids) != len(set(self.evidence_ids)):
            raise ValueError("effects require unique evidence IDs")
        return self


class Approval(StrictModel):
    approval_id: SafeIdentifier
    plan_hash: HashRef
    operation_hash: HashRef
    policy_hash: HashRef
    snapshot_hash: HashRef
    effect_id: SafeIdentifier
    effect_class: str
    approval_class: str
    target: str
    expires_at: UtcTimestamp | None
    one_use: bool
    consumed: bool
    idempotency_key: str | None
    principal: str | None
    identity_verification: Literal["unavailable"]

    @model_validator(mode="after")
    def bounded_one_use_approval(self) -> "Approval":
        if not self.one_use:
            raise ValueError("approvals must be one-use")
        return self


class OperationCommon(StrictModel):
    operation_id: SafeIdentifier
    dependencies: list[SafeIdentifier]
    preconditions: list[str]
    success_criteria: list[str]
    verifier_checks: list[str]
    stop_conditions: list[str]
    path_contract: PathContract
    environment: list[EnvironmentEntry]
    network_grants: list[NetworkGrant]
    subprocesses: list[str]
    delegation: list[str]
    approval_classes: list[str]
    effects: list[Effect]
    effect_inventory_complete: Literal[True]
    policy_references: list[str]
    resource_limits: ResourceLimits

    @model_validator(mode="after")
    def unique_operation_collections(self) -> "OperationCommon":
        for field in (
            "dependencies", "preconditions", "success_criteria", "verifier_checks", "stop_conditions",
            "subprocesses", "delegation", "approval_classes", "policy_references",
        ):
            _require_unique(getattr(self, field), f"operation {self.operation_id} {field}")
        _require_unique([item.name for item in self.environment], f"operation {self.operation_id} environment names")
        _require_unique([item.grant_id for item in self.network_grants], f"operation {self.operation_id} network grant IDs")
        return self


class ReadFileAction(OperationCommon):
    kind: Literal["exact_action"]
    adapter: Literal["read_file"]
    path: str
    byte_start: NonNegativeInt
    byte_end: NonNegativeInt
    expected_hash: str | None

    @model_validator(mode="after")
    def ordered_range(self) -> "ReadFileAction":
        _absolute_literal(self.path, "read_file.path")
        if self.byte_end < self.byte_start:
            raise ValueError("byte_end must be at least byte_start")
        return self


class ApplyPatchAction(OperationCommon):
    kind: Literal["exact_action"]
    adapter: Literal["apply_patch"]
    patch: str
    patch_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    preimage_hashes: dict[str, str]
    expected_created_paths: list[str]
    expected_modified_paths: list[str]
    expected_deleted_paths: list[str]

    @model_validator(mode="after")
    def absolute_patch_paths(self) -> "ApplyPatchAction":
        inventories: list[set[str]] = []
        for field in ("expected_created_paths", "expected_modified_paths", "expected_deleted_paths"):
            _require_unique(getattr(self, field), field)
            inventories.append(set(getattr(self, field)))
            for value in getattr(self, field):
                _absolute_literal(value, field)
        if any(inventories[left] & inventories[right] for left, right in ((0, 1), (0, 2), (1, 2))):
            raise ValueError("apply_patch expected action path inventories must be disjoint")
        for value in self.preimage_hashes:
            _absolute_literal(value, "preimage_hashes")
        return self


class ExecArgvAction(OperationCommon):
    kind: Literal["exact_action"]
    adapter: Literal["exec_argv"]
    executable_path: str
    executable_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    argv: list[str]
    input_hashes: dict[str, str]
    child_processes_declared: bool

    @model_validator(mode="after")
    def absolute_exec_paths(self) -> "ExecArgvAction":
        _absolute_literal(self.executable_path, "executable_path")
        for value in self.input_hashes:
            _absolute_literal(value, "input_hashes")
        return self


class CheckAction(OperationCommon):
    kind: Literal["exact_action"]
    adapter: Literal["check"]
    executable_path: str
    executable_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    argv: list[str]
    input_hashes: dict[str, str]
    expected_exit_codes: list[int]
    declared_generated_paths: list[str]
    child_processes_declared: bool

    @model_validator(mode="after")
    def absolute_check_paths(self) -> "CheckAction":
        _require_unique(self.expected_exit_codes, "expected_exit_codes")
        _require_unique(self.declared_generated_paths, "declared_generated_paths")
        _absolute_literal(self.executable_path, "executable_path")
        for value in self.input_hashes:
            _absolute_literal(value, "input_hashes")
        for value in self.declared_generated_paths:
            _absolute_literal(value, "declared_generated_paths")
        return self


class BoundedAgentTask(OperationCommon):
    kind: Literal["bounded_agent_task"]
    goal: str
    non_goals: list[str]
    evidence_ids: list[str]
    allowed_tools: list[str]
    allowed_executables: dict[str, list[list[str]]]
    allowed_executable_hashes: dict[str, str]
    allowed_executable_input_hashes: dict[str, str]
    forbidden_actions: list[str]
    permitted_adaptations: list[Literal[
        "choose_file_within_root", "choose_approved_test_form", "revise_local_code", "diagnose_failure"
    ]]
    diagnostic_checkpoint_rules: list[str]
    completion_evidence: list[SafeIdentifier]
    escalation_conditions: list[str]

    @model_validator(mode="after")
    def executable_contracts_are_exact(self) -> "BoundedAgentTask":
        for field in (
            "non_goals", "evidence_ids", "allowed_tools", "forbidden_actions", "permitted_adaptations",
            "diagnostic_checkpoint_rules", "completion_evidence", "escalation_conditions",
        ):
            _require_unique(getattr(self, field), f"bounded task {self.operation_id} {field}")
        if set(self.allowed_executable_hashes) != set(self.allowed_executables):
            raise ValueError("bounded executable paths and hashes must have identical keys")
        for executable, forms in self.allowed_executables.items():
            _absolute_literal(executable, "allowed_executables")
            if not re.fullmatch(r"[0-9a-f]{64}", self.allowed_executable_hashes[executable]):
                raise ValueError("bounded executable hashes must be lowercase SHA-256")
            for argv in forms:
                if not argv or argv[0] != executable:
                    raise ValueError("bounded executable argument forms must begin with the exact executable path")
        for path in self.allowed_executable_input_hashes:
            _absolute_literal(path, "allowed_executable_input_hashes")
        return self


ExactAction = Annotated[
    Union[ReadFileAction, ApplyPatchAction, ExecArgvAction, CheckAction],
    Field(discriminator="adapter"),
]
Operation = Union[ExactAction, BoundedAgentTask]


class SourcePhase(StrictModel):
    plan_path: str
    phase_id: SafeIdentifier
    heading: str
    selected_text_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    selected_text: str

    @model_validator(mode="after")
    def absolute_plan_path(self) -> "SourcePhase":
        if not PurePosixPath(self.plan_path).is_absolute():
            raise ValueError("plan_path must be absolute")
        return self


class RepositorySnapshot(StrictModel):
    project_root: str
    platform: str
    case_sensitive: bool
    unicode_normalization: Literal["NFC"]
    device_identity: str
    observation_mode: Literal["git_and_filesystem", "full_filesystem"]
    git_executable_path: str | None
    git_executable_hash: str | None
    git_head: str | None
    git_branch: str | None
    index_hash: str | None
    staged_paths: dict[str, str]
    unstaged_paths: dict[str, str]
    untracked_paths: dict[str, str]
    full_file_inventory: dict[str, str]
    selected_file_hashes: dict[str, str]
    instruction_hashes: dict[str, str]
    resolved_links: dict[str, str]
    expected_product_changes: list[str]
    control_plane_roots: list[str]

    @model_validator(mode="after")
    def absolute_snapshot_root(self) -> "RepositorySnapshot":
        _absolute_literal(self.project_root, "project_root")
        canonical_control = str(PurePosixPath(self.project_root) / ".rb-safe-operation")
        if self.control_plane_roots != [canonical_control]:
            raise ValueError(f"first-release control_plane_roots must equal [{canonical_control!r}]")
        for value in self.expected_product_changes:
            _absolute_literal(value, "expected_product_changes")
            if value == canonical_control or value.startswith(canonical_control + "/"):
                raise ValueError("expected product changes cannot include protected control-plane state")
        if self.observation_mode == "git_and_filesystem":
            if self.git_executable_path is None or self.git_executable_hash is None:
                raise ValueError("Git observation requires a bound executable path and hash")
            _absolute_literal(self.git_executable_path, "git_executable_path")
        elif self.git_executable_path is not None or self.git_executable_hash is not None:
            raise ValueError("non-Git observation cannot claim a Git executable identity")
        return self


class HostCapabilities(StrictModel):
    profile: Literal["semi_formal", "strict_isolation"]
    role_read_only: Literal["host_enforced", "instruction_only", "unknown"]
    product_state_observation: Literal["host_observed", "coordinator_observed", "agent_reported", "unknown"]
    complete_child_trace: bool
    atomic_path_enforcement: bool
    atomic_lease_create: bool
    bounded_resource_enforcement: Literal["host_enforced", "instruction_only", "unknown"]
    fresh_context_enforcement: Literal["host_enforced", "instruction_only", "unknown"]


class LowLevelPlan(StrictModel):
    schema_version: Literal["1.0"]
    plan_id: SafeIdentifier
    run_id: SafeIdentifier
    source_phase: SourcePhase
    snapshot: RepositorySnapshot
    global_policy_hash: HashRef
    merged_policy_hash: HashRef
    operations: list[Operation]
    evidence: list[EvidenceRef]
    later_phase_ids: list[SafeIdentifier]
    current_artifact_locations: list[str]
    exact_next_action: str
    semantic_guidance: list[str]

    @model_validator(mode="after")
    def validate_graph(self) -> "LowLevelPlan":
        _require_unique(self.later_phase_ids, "later_phase_ids")
        _require_unique(self.current_artifact_locations, "current_artifact_locations")
        for value in self.current_artifact_locations:
            _absolute_literal(value, "current_artifact_locations")
        canonical_control = self.snapshot.control_plane_roots[0]
        for operation in self.operations:
            if canonical_control not in operation.path_contract.protected_roots:
                raise ValueError(f"operation {operation.operation_id} must protect the canonical control-plane root")
        ids = [op.operation_id for op in self.operations]
        if len(ids) != len(set(ids)):
            raise ValueError("operation IDs must be unique")
        evidence_ids = [item.evidence_id for item in self.evidence]
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("plan evidence IDs must be unique")
        snapshot_bound_locators = set(self.snapshot.selected_file_hashes) | set(self.snapshot.instruction_hashes)
        for item in self.evidence:
            if item.provenance == "host_observed":
                raise ValueError("first-release plan evidence cannot claim host_observed provenance")
            if item.provenance == "coordinator_observed" and item.locator not in snapshot_bound_locators:
                raise ValueError("coordinator-observed plan evidence must name a snapshot-bound locator")
            if item.provenance == "agent_reported" and item.locator != f"agent-report:{item.evidence_id}":
                raise ValueError("agent-reported plan evidence requires its structural agent-report locator")
        seen: set[str] = set()
        for op in self.operations:
            if not set(op.dependencies).issubset(seen):
                raise ValueError(f"operation {op.operation_id} has forward or unknown dependency")
            if not op.policy_references or len(op.policy_references) != len(set(op.policy_references)):
                raise ValueError(f"operation {op.operation_id} requires unique controlling policy references")
            unknown_policy_references = set(op.policy_references) - INVARIANT_IDS
            if unknown_policy_references:
                raise ValueError(f"operation {op.operation_id} cites unknown policy references")
            if op.kind == "bounded_agent_task" and not set(op.evidence_ids).issubset(evidence_ids):
                raise ValueError(f"bounded task {op.operation_id} cites unknown plan evidence IDs")
            seen.add(op.operation_id)
        effects = [effect for operation in self.operations for effect in operation.effects]
        effect_ids = [effect.effect_id for effect in effects]
        if len(effect_ids) != len(set(effect_ids)):
            raise ValueError("effect IDs must be unique across the plan")
        evidence_by_id = {item.evidence_id: item for item in self.evidence}
        for effect in effects:
            if not set(effect.evidence_ids).issubset(evidence_by_id):
                raise ValueError(f"effect {effect.effect_id} cites unknown evidence IDs")
            observed_provenance = {evidence_by_id[item].provenance for item in effect.evidence_ids}
            if set(effect.observation_sources) != observed_provenance:
                raise ValueError(f"effect {effect.effect_id} observation sources differ from bound evidence provenance")
            if observed_provenance == {"agent_reported"} and effect.detectability in {"full", "partial"}:
                raise ValueError(f"effect {effect.effect_id} overstates detectability from agent-only evidence")
        severity = {name: index for index, name in enumerate(("none", "low", "medium", "high", "critical"))}
        by_id = {effect.effect_id: effect for effect in effects}
        for effect in effects:
            if effect.kind != "cumulative":
                continue
            if len(effect.cumulative_member_effect_ids) != len(set(effect.cumulative_member_effect_ids)):
                raise ValueError(f"cumulative effect {effect.effect_id} has duplicate members")
            if effect.effect_id in effect.cumulative_member_effect_ids:
                raise ValueError(f"cumulative effect {effect.effect_id} cannot include itself")
            if not set(effect.cumulative_member_effect_ids).issubset(by_id):
                raise ValueError(f"cumulative effect {effect.effect_id} has unknown members")
            maximum = max(severity[by_id[item].residual_severity] for item in effect.cumulative_member_effect_ids)
            required = min(maximum + (1 if effect.cumulative_interaction == "amplifying" else 0), 4)
            if severity[effect.residual_severity] < required:
                raise ValueError(f"cumulative effect {effect.effect_id} understates combined residual severity")

        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(effect_id: str) -> None:
            if effect_id in visiting:
                raise ValueError("cumulative effect graph contains a cycle")
            if effect_id in visited or by_id[effect_id].kind != "cumulative":
                return
            visiting.add(effect_id)
            for member_id in by_id[effect_id].cumulative_member_effect_ids:
                visit(member_id)
            visiting.remove(effect_id)
            visited.add(effect_id)

        for effect in effects:
            visit(effect.effect_id)
        return self


class PolicyLimits(StrictModel):
    max_seconds: PositiveInt
    max_processes: PositiveInt
    max_bytes: NonNegativeInt
    max_calls: NonNegativeInt
    max_cost_decimal: str

    @model_validator(mode="after")
    def canonical_cost(self) -> "PolicyLimits":
        from .canonical import canonical_decimal

        canonical_decimal(self.max_cost_decimal)
        return self


class NetworkPolicyGrant(NetworkGrant):
    pass


class ActivePolicy(StrictModel):
    schema_version: Literal["1.0"]
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
    required_observation: dict[str, Literal["agent_reported", "coordinator_observed", "host_observed"]]
    required_evidence_sources: list[str]
    required_verification: list[str]
    denied_operations: list[str]
    denied_adapters: list[str]
    denied_effect_classes: list[str]
    denied_command_forms: list[str]

    @model_validator(mode="after")
    def unique_policy_collections(self) -> "ActivePolicy":
        for field in (
            "allowed_operation_kinds", "allowed_adapters", "allowed_tools", "allowed_effect_classes",
            "allowed_path_roots", "allowed_executable_hashes", "allowed_environment_names", "required_approvals",
            "required_evidence_sources", "required_verification", "denied_operations", "denied_adapters",
            "denied_effect_classes", "denied_command_forms",
        ):
            _require_unique(getattr(self, field), f"active policy {field}")
        _require_unique([item.grant_id for item in self.network_grants], "active policy network grant IDs")
        return self


class ProjectPolicy(StrictModel):
    schema_version: Literal["1.0"]
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
    require_minimum_observation: dict[str, Literal["agent_reported", "coordinator_observed", "host_observed"]]
    require_evidence_sources: list[str]
    require_verification: list[str]

    @model_validator(mode="after")
    def closed_lower_maximums(self) -> "ProjectPolicy":
        for field in (
            "deny_operations", "deny_adapters", "deny_effect_classes", "deny_command_forms",
            "require_approvals", "require_evidence_sources", "require_verification",
        ):
            _require_unique(getattr(self, field), f"project policy {field}")
        for field in ("intersect_path_roots", "intersect_executable_hashes", "intersect_environment_names"):
            values = getattr(self, field)
            if values is not None:
                _require_unique(values, f"project policy {field}")
        if self.intersect_network_grants is not None:
            _require_unique([item.grant_id for item in self.intersect_network_grants], "project policy network grant IDs")
        allowed = {"max_seconds", "max_processes", "max_bytes", "max_calls", "max_cost_decimal"}
        unknown = set(self.lower_maximums) - allowed
        if unknown:
            raise ValueError(f"unknown maximum fields: {sorted(unknown)}")
        for field, value in self.lower_maximums.items():
            if field == "max_cost_decimal" and not isinstance(value, str):
                raise ValueError("max_cost_decimal requires a canonical decimal string")
            if field != "max_cost_decimal" and (not isinstance(value, int) or isinstance(value, bool)):
                raise ValueError(f"{field} requires an integer")
        return self


class MergeProofEntry(StrictModel):
    field: str
    baseline: object
    project_operation: object
    result: object
    discarded: object | None


class MergeResult(StrictModel):
    active_policy: ActivePolicy
    proof: list[MergeProofEntry]


class Finding(StrictModel):
    finding_id: SafeIdentifier
    invariant_id: InvariantIdentifier
    operation_ids: list[SafeIdentifier]
    effect_ids: list[SafeIdentifier]
    category: FindingCategory
    severity: Literal["low", "medium", "high", "critical"]
    evidence_ids: list[str]
    evidence_provenance: list[Literal["host_observed", "coordinator_observed", "agent_reported"]]
    finding_provenance: Literal["coordinator_observed", "agent_reported"]
    explanation: str
    remediation_or_human_decision: str
    blocking: bool

    @model_validator(mode="after")
    def severity_requires_blocking(self) -> "Finding":
        if self.severity in {"high", "critical"} and not self.blocking:
            raise ValueError("high and critical findings must be blocking")
        if len(self.evidence_ids) != len(set(self.evidence_ids)):
            raise ValueError("finding evidence IDs must be unique")
        if bool(self.evidence_ids) != bool(self.evidence_provenance):
            raise ValueError("finding evidence IDs and provenance must both be present or both be absent")
        return self


class Assessment(StrictModel):
    schema_version: Literal["1.0"]
    assessment_id: SafeIdentifier
    plan_hash: HashRef
    policy_hash: HashRef
    snapshot_hash: HashRef
    deterministic_pass: bool
    semantic_pass: bool
    safe: bool
    status: Literal["rejected", "approved"]
    profile: Literal["semi_formal", "strict_isolation"]
    findings: list[Finding]
    covered_evidence_ids: list[str]
    missing_evidence_ids: list[str]
    approvals: list[Approval]
    enforcement_disclosures: list[str]
    prior_assessment_hash: HashRef | None

    @model_validator(mode="after")
    def verdict_consistency(self) -> "Assessment":
        finding_ids = [finding.finding_id for finding in self.findings]
        if len(finding_ids) != len(set(finding_ids)):
            raise ValueError("assessment finding IDs must be unique")
        approval_ids = [approval.approval_id for approval in self.approvals]
        if len(approval_ids) != len(set(approval_ids)):
            raise ValueError("assessment approval IDs must be unique")
        expected = self.deterministic_pass and self.semantic_pass and not self.missing_evidence_ids and not any(
            finding.blocking for finding in self.findings
        )
        if self.safe != expected or (self.safe and self.status != "approved") or (not self.safe and self.status != "rejected"):
            raise ValueError("safe Boolean, status, gates, and findings contradict")
        return self


class DeterministicPreflight(StrictModel):
    schema_version: Literal["1.0"]
    preflight_id: SafeIdentifier
    plan_hash: HashRef
    policy_hash: HashRef
    snapshot_hash: HashRef
    deterministic_pass: bool
    semantic_assessment_required: bool
    findings: list[Finding]
    approvals: list[Approval]
    enforcement_disclosures: list[str]
    required_semantic_evidence_ids: list[str]

    @model_validator(mode="after")
    def preflight_consistency(self) -> "DeterministicPreflight":
        finding_ids = [finding.finding_id for finding in self.findings]
        if len(finding_ids) != len(set(finding_ids)):
            raise ValueError("preflight finding IDs must be unique")
        expected = not any(finding.blocking for finding in self.findings)
        if self.deterministic_pass != expected or self.semantic_assessment_required != expected:
            raise ValueError("deterministic preflight Boolean and semantic routing contradict findings")
        return self


class SemanticAssessmentProposal(StrictModel):
    schema_version: Literal["1.0"]
    semantic_pass: bool
    findings: list[Finding]
    covered_evidence_ids: list[str]
    enforcement_disclosures: list[str]

    @model_validator(mode="after")
    def unique_finding_ids(self) -> "SemanticAssessmentProposal":
        finding_ids = [finding.finding_id for finding in self.findings]
        if len(finding_ids) != len(set(finding_ids)):
            raise ValueError("semantic finding IDs must be unique")
        return self


class AssessmentBundle(StrictModel):
    schema_version: Literal["1.0"]
    assessment: Assessment
    semantic_proposal: SemanticAssessmentProposal


class ExecutionReport(StrictModel):
    schema_version: Literal["1.0"]
    operation_id: SafeIdentifier
    success: bool
    evidence: list[EvidenceRef]
    expected_effect_ids_observed: list[str]
    unexpected_effects: list[str]
    next_strategy: str | None


LifecycleState = Literal[
    "drafting", "validating", "rejected", "approved", "executing", "verifying", "repairing",
    "paused_resource", "human_required", "verified", "failed", "abandoned"
]


class RunManifest(StrictModel):
    schema_version: Literal["1.0"]
    run_id: SafeIdentifier
    state: LifecycleState
    suspended_from: Literal["drafting", "validating", "approved", "executing", "verifying", "repairing"] | None
    plan_hash: HashRef | None
    assessment_hash: HashRef | None
    policy_hash: HashRef | None
    snapshot_hash: HashRef | None
    event_head_hash: str | None

    @model_validator(mode="after")
    def suspension_shape(self) -> "RunManifest":
        requires_origin = self.state in {"paused_resource", "human_required"}
        if requires_origin != (self.suspended_from is not None):
            raise ValueError("paused and human-required states retain an origin; other states forbid it")
        return self


class EventPayload(StrictModel):
    event_type: str
    lifecycle_from: LifecycleState | None
    lifecycle_to: LifecycleState | None
    operation_id: SafeIdentifier | None
    summary: str
    evidence_ids: list[str]


class ObservationEnvelope(StrictModel):
    observer_id: str
    observed_at: UtcTimestamp
    data: dict[str, object]


class AuditEvent(StrictModel):
    schema_version: Literal["1.0"]
    run_id: SafeIdentifier
    sequence: int
    event_uuid: str
    payload: EventPayload
    payload_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    provenance: Literal["host_observed", "coordinator_observed", "agent_reported"]
    observation: ObservationEnvelope
    previous_event_record_hash: str | None
    algorithm: Literal["sha256"]
    event_record_hash: str = Field(pattern=r"^[0-9a-f]{64}$")


class VerificationReport(StrictModel):
    schema_version: Literal["1.0"]
    verification_id: SafeIdentifier
    plan_hash: HashRef
    assessment_hash: HashRef
    snapshot_hash: HashRef
    independent_context: bool
    independence_assurance: Literal["instruction_only", "host_enforced"]
    coordinator_evidence_ids: list[SafeIdentifier]
    verifier_evidence_ids: list[SafeIdentifier]
    success_criteria_met: list[str]
    verifier_checks_passed: list[str]
    findings: list[Finding]
    verified: bool
    provenance: Literal["agent_reported", "coordinator_observed", "host_observed"]

    @model_validator(mode="after")
    def verified_consistency(self) -> "VerificationReport":
        finding_ids = [finding.finding_id for finding in self.findings]
        if len(finding_ids) != len(set(finding_ids)):
            raise ValueError("verification report finding IDs must be unique")
        if self.independent_context and self.independence_assurance != "host_enforced":
            raise ValueError("definitive independent_context requires host enforcement")
        if self.verified and (any(item.blocking for item in self.findings) or not self.coordinator_evidence_ids or not self.verifier_evidence_ids):
            raise ValueError("verified requires both evidence sources and no blocking finding")
        return self


class VerificationProposal(StrictModel):
    schema_version: Literal["1.0"]
    plan_hash: HashRef
    assessment_hash: HashRef
    snapshot_hash: HashRef
    verifier_context_id: SafeIdentifier
    success_criteria_met: list[str]
    verifier_checks_passed: list[str]
    observed_effect_ids: list[str]
    evidence: list[EvidenceRef]
    criterion_evidence: dict[str, list[SafeIdentifier]]
    check_evidence: dict[str, list[SafeIdentifier]]
    effect_evidence: dict[SafeIdentifier, list[SafeIdentifier]]
    findings: list[Finding]

    @model_validator(mode="after")
    def unique_finding_ids(self) -> "VerificationProposal":
        finding_ids = [finding.finding_id for finding in self.findings]
        if len(finding_ids) != len(set(finding_ids)):
            raise ValueError("verification proposal finding IDs must be unique")
        return self


class RepairAttempt(StrictModel):
    schema_version: Literal["1.0"]
    attempt_id: SafeIdentifier
    finding_id: SafeIdentifier
    hypothesis: str
    observed_result: str
    reconsidered_assumption: str
    materially_different_next_strategy: str
    strategy_code: Literal[
        "diagnose_with_fresh_evidence",
        "reinspect_and_revise_local_code",
        "recompute_from_preconditions",
        "narrow_targeted_correction",
    ] = "diagnose_with_fresh_evidence"
    high_risk_replay: bool
    fresh_idempotency_proof: str | None
    approval_id: str | None

    @model_validator(mode="after")
    def high_risk_gate(self) -> "RepairAttempt":
        if self.high_risk_replay and (not self.fresh_idempotency_proof or not self.approval_id):
            raise ValueError("high-risk replay requires fresh idempotency proof and approval")
        return self


class HumanIntervention(StrictModel):
    schema_version: Literal["1.0"]
    decision_type: Literal["revise_and_reassess", "leave_constrained_pipeline", "approve_declared_gate", "abandon", "resume_after_pause"]
    plan_hash: HashRef
    assessment_hash: HashRef
    policy_hash: HashRef
    snapshot_hash: HashRef
    operation_id: SafeIdentifier | None
    effect_id: SafeIdentifier | None
    timestamp: UtcTimestamp
    rationale: str
    resulting_version_or_outcome: str
    approval_expiry: UtcTimestamp | None
    idempotency_key: str | None
    principal: str | None
    identity_verification: Literal["unavailable"]
