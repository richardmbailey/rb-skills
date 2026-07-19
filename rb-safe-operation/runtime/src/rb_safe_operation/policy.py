from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
import hashlib
from importlib.resources import files
from pathlib import Path
from typing import Iterable

from .canonical import canonical_decimal, parse_json_strict
from .models import (
    ActivePolicy,
    Assessment,
    Effect,
    Finding,
    HostCapabilities,
    LowLevelPlan,
    MergeProofEntry,
    MergeResult,
    NetworkPolicyGrant,
    ProjectPolicy,
)


ENFORCEMENT_ORDER = {"instruction_only": 0, "host_enforced": 1}
OBSERVATION_ORDER = {"agent_reported": 0, "coordinator_observed": 1, "host_observed": 2}
SEVERITY_ORDER = ["none", "low", "medium", "high", "critical"]


def default_global_policy(project_root: str) -> ActivePolicy:
    template = parse_json_strict(files("rb_safe_operation").joinpath("data/global-policy-1.0.json").read_bytes())
    template["allowed_path_roots"] = [str(Path(project_root).resolve()) if value == "${PROJECT_ROOT}" else value for value in template["allowed_path_roots"]]
    return ActivePolicy.model_validate(template)


def active_policy_widening_errors(global_policy: ActivePolicy, active_policy: ActivePolicy) -> list[str]:
    """Return every way a caller-supplied active policy is wider than the immutable baseline."""
    errors: list[str] = []
    allowed_sets = (
        "allowed_operation_kinds", "allowed_adapters", "allowed_tools", "allowed_effect_classes",
        "allowed_executable_hashes", "allowed_environment_names",
    )
    for field in allowed_sets:
        if not set(getattr(active_policy, field)).issubset(set(getattr(global_policy, field))):
            errors.append(field)
    for root in active_policy.allowed_path_roots:
        if not any(_is_within(Path(root).resolve(), Path(base).resolve()) for base in global_policy.allowed_path_roots):
            errors.append("allowed_path_roots")
            break
    baseline_network = {item.grant_id: item for item in global_policy.network_grants}
    for grant in active_policy.network_grants:
        baseline = baseline_network.get(grant.grant_id)
        if baseline is None or not _network_grant_is_subset(grant, baseline):
            errors.append(f"network_grants.{grant.grant_id}")
    for field in ("max_seconds", "max_processes", "max_bytes", "max_calls"):
        if getattr(active_policy.limits, field) > getattr(global_policy.limits, field):
            errors.append(f"limits.{field}")
    if Decimal(active_policy.limits.max_cost_decimal) > Decimal(global_policy.limits.max_cost_decimal):
        errors.append("limits.max_cost_decimal")
    required_sets = ("required_approvals", "required_evidence_sources", "required_verification")
    for field in required_sets:
        if not set(getattr(global_policy, field)).issubset(set(getattr(active_policy, field))):
            errors.append(field)
    denied_sets = ("denied_operations", "denied_adapters", "denied_effect_classes", "denied_command_forms")
    for field in denied_sets:
        if not set(getattr(global_policy, field)).issubset(set(getattr(active_policy, field))):
            errors.append(field)
    for field, baseline in global_policy.required_enforcement.items():
        observed = active_policy.required_enforcement.get(field)
        if observed is None or ENFORCEMENT_ORDER[observed] < ENFORCEMENT_ORDER[baseline]:
            errors.append(f"required_enforcement.{field}")
    for field, baseline in global_policy.required_observation.items():
        observed = active_policy.required_observation.get(field)
        if observed is None or OBSERVATION_ORDER[observed] < OBSERVATION_ORDER[baseline]:
            errors.append(f"required_observation.{field}")
    return sorted(set(errors))


def _unique(*values: Iterable[str]) -> list[str]:
    return sorted(set().union(*[set(value) for value in values]))


def _intersect_roots(baseline: list[str], requested: list[str]) -> tuple[list[str], list[str]]:
    kept: set[str] = set()
    discarded: set[str] = set()
    for base_value in baseline:
        base = Path(base_value).resolve()
        for project_value in requested:
            project = Path(project_value).resolve()
            try:
                project.relative_to(base)
                kept.add(str(project))
                continue
            except ValueError:
                pass
            try:
                base.relative_to(project)
                kept.add(str(base))
            except ValueError:
                discarded.add(str(project))
    compact: list[str] = []
    for candidate in sorted(kept, key=lambda value: (len(Path(value).parts), value)):
        if not any(_is_within(Path(candidate), Path(parent)) for parent in compact):
            compact.append(candidate)
    return compact, sorted(discarded)


def _is_within(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def _network_key(grant: NetworkPolicyGrant) -> str:
    return grant.grant_id


def _intersect_network(baseline: list[NetworkPolicyGrant], requested: list[NetworkPolicyGrant]) -> tuple[list[NetworkPolicyGrant], list[str]]:
    baseline_by_id = {_network_key(item): item for item in baseline}
    result: list[NetworkPolicyGrant] = []
    discarded: list[str] = []
    for project in requested:
        base = baseline_by_id.get(project.grant_id)
        if base is None:
            discarded.append(project.grant_id)
            continue
        payload = base.model_dump()
        for field in ("destinations", "ports", "protocols", "methods", "semantics", "request_data_classes", "response_data_classes", "credential_audiences", "redirect_destinations"):
            payload[field] = sorted(set(getattr(base, field)) & set(getattr(project, field)))
        for field in ("max_calls", "max_bytes", "max_seconds", "retry_limit"):
            payload[field] = min(getattr(base, field), getattr(project, field))
        payload["idempotency_required"] = base.idempotency_required or project.idempotency_required
        payload["approval_classes"] = _unique(base.approval_classes, project.approval_classes)
        required = ("destinations", "ports", "protocols", "methods", "semantics")
        if any(not payload[field] for field in required):
            discarded.append(project.grant_id)
            continue
        result.append(NetworkPolicyGrant.model_validate(payload))
    return result, sorted(discarded)


def merge_policy(global_policy: ActivePolicy, project_policy: ProjectPolicy | None) -> MergeResult:
    if project_policy is None:
        return MergeResult(active_policy=global_policy, proof=[])
    result = deepcopy(global_policy)
    proof: list[MergeProofEntry] = []

    unions = {
        "denied_operations": project_policy.deny_operations,
        "denied_adapters": project_policy.deny_adapters,
        "denied_effect_classes": project_policy.deny_effect_classes,
        "denied_command_forms": project_policy.deny_command_forms,
        "required_approvals": project_policy.require_approvals,
        "required_evidence_sources": project_policy.require_evidence_sources,
        "required_verification": project_policy.require_verification,
    }
    for field, added in unions.items():
        before = list(getattr(result, field))
        after = _unique(before, added)
        setattr(result, field, after)
        proof.append(MergeProofEntry(field=field, baseline=before, project_operation=added, result=after, discarded=None))

    intersections = {
        "allowed_executable_hashes": project_policy.intersect_executable_hashes,
        "allowed_environment_names": project_policy.intersect_environment_names,
    }
    for field, requested in intersections.items():
        if requested is not None:
            before = list(getattr(result, field))
            after = sorted(set(before) & set(requested))
            setattr(result, field, after)
            proof.append(MergeProofEntry(field=field, baseline=before, project_operation=requested, result=after, discarded=sorted(set(requested) - set(before))))

    if project_policy.intersect_path_roots is not None:
        before = list(result.allowed_path_roots)
        after, discarded = _intersect_roots(before, project_policy.intersect_path_roots)
        result.allowed_path_roots = after
        proof.append(MergeProofEntry(field="allowed_path_roots", baseline=before, project_operation=project_policy.intersect_path_roots, result=after, discarded=discarded))

    if project_policy.intersect_network_grants is not None:
        before = [item.model_dump(mode="json") for item in result.network_grants]
        after_items, discarded = _intersect_network(result.network_grants, project_policy.intersect_network_grants)
        result.network_grants = after_items
        proof.append(MergeProofEntry(field="network_grants", baseline=before, project_operation=[item.model_dump(mode="json") for item in project_policy.intersect_network_grants], result=[item.model_dump(mode="json") for item in after_items], discarded=discarded))

    for field, requested in project_policy.lower_maximums.items():
        before = getattr(result.limits, field)
        if field == "max_cost_decimal":
            canonical_decimal(str(requested))
            if Decimal(str(requested)) > Decimal(str(before)):
                raise ValueError(f"P-003 widening attempted for {field}")
        elif int(requested) > int(before):
            raise ValueError(f"P-003 widening attempted for {field}")
        setattr(result.limits, field, requested)
        proof.append(MergeProofEntry(field=f"limits.{field}", baseline=before, project_operation=requested, result=requested, discarded=None))

    for field, requested in project_policy.require_minimum_enforcement.items():
        before = result.required_enforcement.get(field, "instruction_only")
        after = max((before, requested), key=lambda value: ENFORCEMENT_ORDER[value])
        result.required_enforcement[field] = after
        proof.append(MergeProofEntry(field=f"required_enforcement.{field}", baseline=before, project_operation=requested, result=after, discarded=None))
    for field, requested in project_policy.require_minimum_observation.items():
        before = result.required_observation.get(field, "agent_reported")
        after = max((before, requested), key=lambda value: OBSERVATION_ORDER[value])
        result.required_observation[field] = after
        proof.append(MergeProofEntry(field=f"required_observation.{field}", baseline=before, project_operation=requested, result=after, discarded=None))

    canonical_decimal(result.limits.max_cost_decimal)
    return MergeResult(active_policy=ActivePolicy.model_validate(result.model_dump()), proof=proof)


def effect_allowed(effect: Effect, policy: ActivePolicy, approved_effect_ids: set[str]) -> tuple[bool, str]:
    if effect.effect_class in policy.denied_effect_classes or effect.effect_class not in policy.allowed_effect_classes:
        return False, "effect class is prohibited or unsupported"
    unmitigated = SEVERITY_ORDER.index(effect.unmitigated_severity)
    residual = SEVERITY_ORDER.index(effect.residual_severity)
    if residual < unmitigated:
        can_reduce = (
            unmitigated - residual <= 1
            and effect.mitigation == "verified"
            and effect.recovery in {"tested", "specified"}
            and effect.reversibility in {"full", "bounded"}
            and effect.detectability in {"full", "partial"}
        )
        if not can_reduce:
            return False, "residual severity reduction lacks required controls"
    block = (
        residual >= SEVERITY_ORDER.index("high")
        or effect.exposure == "systemic"
        or effect.reversibility == "none"
        or (effect.detectability == "unknown" and _material(effect, residual))
        or not effect.evidence_ids
    )
    if block:
        return False, "effect matches a blocking E-002 condition"
    review = (
        residual >= SEVERITY_ORDER.index("medium")
        or effect.likelihood in {"likely", "almost_certain"}
        or effect.exposure in {"project_external", "multi_party"}
        or effect.data_classification in {"personal", "sensitive", "secret"}
        or effect.reversibility == "uncertain"
        or effect.detectability == "weak"
        or effect.cost_impact in {"medium", "high"}
        or effect.availability_impact in {"medium", "high"}
    )
    if review and effect.effect_id not in approved_effect_ids:
        return False, "effect requires exact current approval"
    if review:
        allowed = (
            residual <= SEVERITY_ORDER.index("medium")
            and effect.exposure in {"isolated", "repository", "project_external", "multi_party"}
            and effect.reversibility in {"full", "bounded"}
            and effect.detectability in {"full", "partial"}
            and effect.recovery in {"tested", "specified"}
        )
        return allowed, "approved review-class effect" if allowed else "approved effect still exceeds E-002 allowance"
    low = (
        residual <= SEVERITY_ORDER.index("low")
        and effect.exposure in {"isolated", "repository"}
        and effect.reversibility in {"full", "bounded"}
        and effect.detectability in {"full", "partial"}
        and effect.recovery in {"tested", "specified"}
    )
    return low, "low bounded observed effect" if low else "no E-002 row proves allowance"


def _material(effect: Effect, residual: int) -> bool:
    return (
        residual >= SEVERITY_ORDER.index("medium")
        or effect.likelihood in {"likely", "almost_certain"}
        or effect.exposure in {"project_external", "multi_party", "systemic"}
        or effect.data_classification in {"personal", "sensitive", "secret"}
        or effect.cost_impact in {"medium", "high"}
        or effect.availability_impact in {"medium", "high"}
        or effect.reversibility in {"uncertain", "none"}
    )


def capability_findings(capabilities: HostCapabilities, policy: ActivePolicy) -> list[Finding]:
    findings: list[Finding] = []
    if capabilities.profile == "strict_isolation":
        missing = []
        if capabilities.role_read_only != "host_enforced":
            missing.append("host-enforced role restrictions")
        if capabilities.product_state_observation != "host_observed":
            missing.append("host-observed product state")
        if not capabilities.complete_child_trace:
            missing.append("complete child-process trace")
        if not capabilities.atomic_path_enforcement:
            missing.append("atomic path enforcement")
        if not capabilities.atomic_lease_create:
            missing.append("atomic lease creation")
        if capabilities.bounded_resource_enforcement != "host_enforced":
            missing.append("host-enforced bounded resources")
        if capabilities.fresh_context_enforcement != "host_enforced":
            missing.append("host-enforced fresh role contexts")
        if missing:
            findings.append(_finding("capability-strict", "A-007", "unsupported_host_capability", f"strict isolation is unavailable: {', '.join(missing)}"))
    for control, required in policy.required_enforcement.items():
        observed_by_control = {
            "assessor_read_only": capabilities.role_read_only,
            "verifier_read_only": capabilities.role_read_only,
            "path_containment": "host_enforced" if capabilities.atomic_path_enforcement else "instruction_only",
            "lease_create": "host_enforced" if capabilities.atomic_lease_create else "instruction_only",
            "child_process_trace": "host_enforced" if capabilities.complete_child_trace else "instruction_only",
            "bounded_resources": capabilities.bounded_resource_enforcement,
            "fresh_context": capabilities.fresh_context_enforcement,
        }
        observed = observed_by_control.get(control)
        if observed is None:
            findings.append(_finding(f"capability-{control}", "A-008", "unsupported_host_capability", f"unknown required enforcement control: {control}"))
            continue
        if ENFORCEMENT_ORDER[observed] < ENFORCEMENT_ORDER[required]:
            findings.append(_finding(f"capability-{control}", "A-008", "unsupported_host_capability", f"{control} requires {required}, observed {observed}"))
    for control, required in policy.required_observation.items():
        observed_by_control = {
            "product_state": capabilities.product_state_observation,
            "child_trace": "host_observed" if capabilities.complete_child_trace else "agent_reported",
            "path_enforcement": "host_observed" if capabilities.atomic_path_enforcement else "agent_reported",
            "lease_create": "host_observed" if capabilities.atomic_lease_create else "agent_reported",
        }
        observed = observed_by_control.get(control)
        if observed is None or observed == "unknown":
            findings.append(_finding(f"observation-{control}", "A-008", "unsupported_host_capability", f"required observation control is unknown or unavailable: {control}"))
            continue
        if OBSERVATION_ORDER[observed] < OBSERVATION_ORDER[required]:
            findings.append(_finding(f"observation-{control}", "A-008", "unsupported_host_capability", f"{control} requires {required}, observed {observed}"))
    return findings


def deterministic_assessment_findings(
    plan: LowLevelPlan,
    policy: ActivePolicy,
    capabilities: HostCapabilities,
    covered_evidence_ids: set[str],
    approved_effect_ids: set[str],
) -> list[Finding]:
    findings = capability_findings(capabilities, policy)
    evidence_ids = {item.evidence_id for item in plan.evidence}
    evidence_sources = {
        "snapshot": bool(plan.snapshot.selected_file_hashes or plan.snapshot.instruction_hashes),
        "operation_contract": bool(plan.operations),
        "effect_inventory": bool(plan.operations) and all(op.effect_inventory_complete for op in plan.operations),
        "verifier_checks": bool(plan.operations) and all(op.verifier_checks for op in plan.operations),
    }
    for source in policy.required_evidence_sources:
        if not evidence_sources.get(source, False):
            findings.append(_finding(f"required-evidence-{source}", "E-003", "missing_evidence", f"required evidence source is unavailable or unsupported: {source}"))
    verification_features = {
        "success_criteria": bool(plan.operations) and all(op.success_criteria for op in plan.operations),
        "product_diff": bool(plan.operations) and all("product_diff" in op.verifier_checks for op in plan.operations),
        "undeclared_effects": bool(plan.operations) and all("undeclared_effects" in op.verifier_checks for op in plan.operations),
    }
    for requirement in policy.required_verification:
        if not verification_features.get(requirement, False):
            findings.append(_finding(f"required-verification-{requirement}", "E-003", "incomplete_verification", f"required verification gate is unavailable or unsupported: {requirement}"))
    for op in plan.operations:
        if op.kind not in policy.allowed_operation_kinds or op.operation_id in policy.denied_operations:
            findings.append(_finding(f"operation-{op.operation_id}", "O-001", "unsupported_operation", "operation is denied or unsupported", [op.operation_id]))
        if op.kind == "exact_action" and (op.adapter not in policy.allowed_adapters or op.adapter in policy.denied_adapters):
            findings.append(_finding(f"adapter-{op.operation_id}", "O-002", "unsupported_adapter", "adapter is denied or unsupported", [op.operation_id]))
        if op.kind == "bounded_agent_task" and not set(op.allowed_tools).issubset(set(policy.allowed_tools)):
            findings.append(_finding(f"tools-{op.operation_id}", "O-001", "unsupported_tool", "bounded task requests a tool outside active policy", [op.operation_id]))
        if op.kind == "bounded_agent_task" and ({"exec_argv", "check"} & set(op.allowed_tools)):
            findings.append(_finding(f"bounded-command-{op.operation_id}", "O-003", "transitive_execution", "first-release bounded tasks cannot execute repository code because no capability sandbox is available", [op.operation_id]))
        if op.kind == "bounded_agent_task":
            if op.allowed_executables or op.allowed_executable_hashes or op.allowed_executable_input_hashes:
                findings.append(_finding(f"bounded-check-contract-{op.operation_id}", "O-003", "transitive_execution", "first-release bounded executable contracts must be empty because identity binding does not constrain executable side effects", [op.operation_id]))
        if op.subprocesses:
            findings.append(_finding(f"subprocesses-{op.operation_id}", "O-003", "transitive_execution", "first-release operations cannot declare untyped subprocess contracts", [op.operation_id]))
        if op.delegation:
            findings.append(_finding(f"delegation-{op.operation_id}", "O-003", "delegation", "first-release operations cannot declare untyped delegation contracts", [op.operation_id]))
        if op.kind == "exact_action" and op.adapter in {"exec_argv", "check"} and op.child_processes_declared:
            findings.append(_finding(f"child-processes-{op.operation_id}", "O-003", "transitive_execution", "first-release exact commands cannot declare child processes without a typed child contract", [op.operation_id]))
        if op.kind == "exact_action" and op.adapter == "check" and op.declared_generated_paths:
            findings.append(_finding(f"generated-paths-{op.operation_id}", "E-001", "effect_inventory", "first-release check outputs cannot distinguish create from modify preimages, so declared_generated_paths must be empty", [op.operation_id]))
        if op.kind == "exact_action" and op.adapter in {"exec_argv", "check"}:
            findings.append(_finding(f"command-capability-{op.operation_id}", "O-003", "transitive_execution", "first-release command adapters are schema-reserved but disabled because executable identity does not provide a capability sandbox", [op.operation_id]))
        for field in ("read_roots", "create_roots", "modify_roots", "delete_roots", "working_directories"):
            outside = [
                root for root in getattr(op.path_contract, field)
                if not any(_is_within(Path(root).resolve(), Path(allowed).resolve()) for allowed in policy.allowed_path_roots)
            ]
            if outside:
                findings.append(_finding(f"path-{op.operation_id}-{field}", "X-001", "path_escape", f"{field} contains roots outside active policy", [op.operation_id]))
        if op.kind == "exact_action" and op.adapter in {"exec_argv", "check"}:
            from .planning import classify_command
            classifications = classify_command(op.executable_path, op.argv, op.child_processes_declared)
            blocked_forms = sorted(set(classifications) & set(policy.denied_command_forms))
            if blocked_forms:
                findings.append(_finding(f"command-{op.operation_id}", "O-003", "transitive_execution", f"command uses denied forms: {blocked_forms}", [op.operation_id]))
            if op.executable_hash not in policy.allowed_executable_hashes:
                findings.append(_finding(f"executable-{op.operation_id}", "O-003", "executable_identity", "executable hash is absent from the active allowlist", [op.operation_id]))
        findings.extend(_operation_contract_findings(op))
        environment_names = {entry.name for entry in op.environment}
        if not environment_names.issubset(set(policy.allowed_environment_names)):
            findings.append(_finding(f"environment-{op.operation_id}", "O-004", "environment_widening", "operation requests environment names outside active policy", [op.operation_id]))
        policy_network = {grant.grant_id: grant for grant in policy.network_grants}
        for grant in op.network_grants:
            baseline = policy_network.get(grant.grant_id)
            if baseline is None or not _network_grant_is_subset(grant, baseline):
                findings.append(_finding(f"network-{op.operation_id}-{grant.grant_id}", "O-005", "network_widening", "operation network grant is absent from or wider than active policy", [op.operation_id]))
        if op.resource_limits.max_seconds > policy.limits.max_seconds or op.resource_limits.max_processes > policy.limits.max_processes or op.resource_limits.max_bytes > policy.limits.max_bytes or op.resource_limits.max_calls > policy.limits.max_calls:
            findings.append(_finding(f"limits-{op.operation_id}", "P-002", "policy_limit", "operation resource ceiling exceeds active policy", [op.operation_id]))
        if op.resource_limits.max_calls == 0 or (isinstance(op.resource_limits.attempt_limit, int) and op.resource_limits.attempt_limit == 0):
            findings.append(_finding(f"limits-zero-{op.operation_id}", "P-002", "policy_limit", "an executable operation requires at least one permitted call and attempt", [op.operation_id]))
        if Decimal(op.resource_limits.max_cost_decimal) > Decimal(policy.limits.max_cost_decimal):
            findings.append(_finding(f"cost-{op.operation_id}", "P-002", "policy_limit", "operation cost ceiling exceeds active policy", [op.operation_id]))
        for effect in op.effects:
            allowed, reason = effect_allowed(effect, policy, approved_effect_ids)
            if not allowed:
                findings.append(_finding(f"effect-{effect.effect_id}", "E-002", "detrimental_effect", reason, [op.operation_id], [effect.effect_id]))
            for evidence_id in effect.evidence_ids:
                if evidence_id not in evidence_ids or evidence_id not in covered_evidence_ids:
                    findings.append(_finding(f"evidence-{op.operation_id}-{effect.effect_id}-{evidence_id}", "E-003", "missing_evidence", f"required evidence is absent or uncovered: {evidence_id}", [op.operation_id], [effect.effect_id]))
        if not op.verifier_checks or not op.success_criteria or not op.stop_conditions:
            findings.append(_finding(f"completeness-{op.operation_id}", "O-001", "incomplete_operation", "operation lacks success, verification, or stop conditions", [op.operation_id]))
    return findings


def _contained_in_any(path: str, roots: list[str]) -> bool:
    candidate = Path(path).resolve(strict=False)
    return any(_is_within(candidate, Path(root).resolve(strict=False)) for root in roots)


def _operation_contract_findings(op) -> list[Finding]:
    """Bind concrete operation fields and declared effects to the assessed path envelope."""
    findings: list[Finding] = []
    required_effect_targets: dict[str, set[str]] = {}

    def require_path(path: str, roots: list[str], label: str) -> None:
        if not _contained_in_any(path, roots):
            path_key = hashlib.sha256(path.encode("utf-8")).hexdigest()[:16]
            findings.append(_finding(f"concrete-path-{op.operation_id}-{label}-{path_key}", "X-001", "path_escape", f"concrete {label} path is outside its declared roots", [op.operation_id]))

    def require_effect(effect_class: str, targets: Iterable[str]) -> None:
        required_effect_targets.setdefault(effect_class, set()).update(targets)

    if op.kind == "exact_action" and op.adapter == "read_file":
        require_path(op.path, op.path_contract.read_roots, "read")
        require_effect("repository_read", [op.path])
    elif op.kind == "exact_action" and op.adapter == "apply_patch":
        expected_preimages = set(op.expected_modified_paths) | set(op.expected_deleted_paths)
        if set(op.preimage_hashes) != expected_preimages:
            findings.append(_finding(f"patch-preimages-{op.operation_id}", "O-002", "operation_contract", "patch preimages must exactly cover modified and deleted paths", [op.operation_id]))
        for path in op.expected_created_paths:
            require_path(path, op.path_contract.create_roots, "create")
        for path in op.expected_modified_paths:
            require_path(path, op.path_contract.modify_roots, "modify")
        for path in op.expected_deleted_paths:
            require_path(path, op.path_contract.delete_roots, "delete")
        require_effect("repository_create", op.expected_created_paths)
        require_effect("repository_modify", op.expected_modified_paths)
        require_effect("repository_delete", op.expected_deleted_paths)
    elif op.kind == "exact_action" and op.adapter in {"exec_argv", "check"}:
        for path in op.input_hashes:
            require_path(path, op.path_contract.read_roots, "command-input")
        require_effect("repository_read", op.input_hashes)
        require_effect("local_process", [op.executable_path])
        if op.adapter == "check":
            for path in op.declared_generated_paths:
                require_path(path, op.path_contract.create_roots + op.path_contract.modify_roots, "generated")
    elif op.kind == "bounded_agent_task":
        require_effect("repository_read", op.path_contract.read_roots)
        require_effect("repository_create", op.path_contract.create_roots)
        require_effect("repository_modify", op.path_contract.modify_roots)
        require_effect("repository_delete", op.path_contract.delete_roots)

    declared: dict[str, set[str]] = {}
    for effect in op.effects:
        declared.setdefault(effect.effect_class, set()).update(effect.targets)
    for effect_class, targets in required_effect_targets.items():
        missing = targets - declared.get(effect_class, set())
        if missing:
            findings.append(_finding(f"effect-target-{op.operation_id}-{effect_class}", "E-001", "effect_inventory", f"{effect_class} effects do not cover concrete targets: {sorted(missing)}", [op.operation_id]))
    return findings


def _network_grant_is_subset(candidate, baseline) -> bool:
    set_fields = (
        "destinations", "ports", "protocols", "methods", "semantics", "request_data_classes",
        "response_data_classes", "credential_audiences", "redirect_destinations",
    )
    if any(not set(getattr(candidate, field)).issubset(set(getattr(baseline, field))) for field in set_fields):
        return False
    if any(getattr(candidate, field) > getattr(baseline, field) for field in ("max_calls", "max_bytes", "max_seconds", "retry_limit")):
        return False
    if baseline.idempotency_required and not candidate.idempotency_required:
        return False
    return set(baseline.approval_classes).issubset(set(candidate.approval_classes))


def _finding(
    finding_id: str,
    invariant: str,
    category: str,
    explanation: str,
    operation_ids: list[str] | None = None,
    effect_ids: list[str] | None = None,
) -> Finding:
    if len(finding_id) > 128 or not finding_id or any(char not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._-" for char in finding_id) or ".." in finding_id:
        finding_id = "finding-" + hashlib.sha256(finding_id.encode("utf-8")).hexdigest()[:32]
    return Finding(
        finding_id=finding_id,
        invariant_id=invariant,
        operation_ids=operation_ids or [],
        effect_ids=effect_ids or [],
        category=category,
        severity="high",
        evidence_ids=[],
        evidence_provenance=[],
        finding_provenance="coordinator_observed",
        explanation=explanation,
        remediation_or_human_decision="revise and reassess, or leave the constrained pipeline",
        blocking=True,
    )
