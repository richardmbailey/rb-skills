from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import platform
import stat
import unicodedata

from .canonical import artifact_hash, canonical_bytes, parse_json_strict
from .models import ActivePolicy, HashRef
from .policy_models import (
    ActivePolicyV2,
    PathCapability,
    PathPolicyDecision,
    PolicyAuthoringIntent,
    PolicyAuthoringRecord,
    PolicyBinding,
    PolicyConfirmation,
    PolicyPreview,
    ProjectPolicyProposal,
    ProjectPolicyV2,
)


POLICY_FILENAME = ".rb-safe-operation-policy.json"
MAX_POLICY_BYTES = 262_144
ABSENT_POLICY_BYTES = canonical_bytes(
    {"schema_version": "1.0", "fixed_filename": POLICY_FILENAME, "state": "absent"}
)


class ProjectPolicyError(RuntimeError):
    pass


class PolicyDenied(ProjectPolicyError):
    def __init__(self, decision: PathPolicyDecision):
        super().__init__(
            f"project policy denied {decision.capability} for {decision.requested_path}; "
            f"rules={decision.matched_rule_ids or ['uncertain-path-identity']}"
        )
        self.decision = decision


def _hash_ref(artifact_type: str, payload: object, schema_version: str) -> HashRef:
    return HashRef(
        artifact_type=artifact_type,
        schema_version=schema_version,
        value=artifact_hash(artifact_type, schema_version, payload),
    )


@dataclass(frozen=True)
class LoadedProjectPolicy:
    project_root: Path
    policy_path: Path
    global_policy: ActivePolicy
    project_policy: ProjectPolicyV2 | None
    effective_policy: ActivePolicyV2
    binding: PolicyBinding
    source_bytes: bytes | None
    case_sensitive: bool


def _inside(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def _read_regular_nofollow(path: Path, *, max_bytes: int = MAX_POLICY_BYTES) -> bytes:
    descriptor = os.open(
        path,
        os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0),
    )
    try:
        observed = os.fstat(descriptor)
        if not stat.S_ISREG(observed.st_mode) or observed.st_nlink != 1:
            raise ProjectPolicyError("the fixed policy path must be one singly linked regular file")
        if observed.st_size > max_bytes:
            raise ProjectPolicyError("the fixed policy file exceeds the byte limit")
        data = b""
        while len(data) <= max_bytes:
            chunk = os.read(descriptor, min(65_536, max_bytes + 1 - len(data)))
            if not chunk:
                break
            data += chunk
        if len(data) > max_bytes:
            raise ProjectPolicyError("the fixed policy file exceeds the byte limit")
        return data
    finally:
        os.close(descriptor)


def _global_hash(global_policy: ActivePolicy):
    return _hash_ref("active-policy", global_policy.model_dump(mode="json"), "1.0")


def _to_active_v2(global_policy: ActivePolicy, project_policy: ProjectPolicyV2 | None) -> ActivePolicyV2:
    data = global_policy.model_dump(mode="json")
    limits = data.pop("limits")
    data["schema_version"] = "2.0"
    data["limits"] = limits
    data["path_rules"] = [] if project_policy is None else [
        item.model_dump(mode="json") for item in project_policy.path_rules
    ]
    active = ActivePolicyV2.model_validate(data)
    if project_policy is None:
        return active
    payload = active.model_dump(mode="json")
    for field, additions in {
        "denied_operations": project_policy.deny_operations,
        "denied_adapters": project_policy.deny_adapters,
        "denied_effect_classes": project_policy.deny_effect_classes,
        "denied_command_forms": project_policy.deny_command_forms,
        "required_approvals": project_policy.require_approvals,
        "required_evidence_sources": project_policy.require_evidence_sources,
        "required_verification": project_policy.require_verification,
    }.items():
        payload[field] = sorted(set(payload[field]) | set(additions))
    for field, requested in {
        "allowed_executable_hashes": project_policy.intersect_executable_hashes,
        "allowed_environment_names": project_policy.intersect_environment_names,
    }.items():
        if requested is not None:
            payload[field] = sorted(set(payload[field]) & set(requested))
    if project_policy.intersect_path_roots is not None:
        kept: list[str] = []
        for baseline in payload["allowed_path_roots"]:
            base = Path(baseline).resolve(strict=False)
            for requested in project_policy.intersect_path_roots:
                candidate = Path(requested).resolve(strict=False)
                if _inside(candidate, base):
                    kept.append(str(candidate))
                elif _inside(base, candidate):
                    kept.append(str(base))
        payload["allowed_path_roots"] = sorted(set(kept))
    if project_policy.intersect_network_grants is not None:
        requested = {
            item.grant_id: item.model_dump(mode="json")
            for item in project_policy.intersect_network_grants
        }
        list_fields = (
            "destinations", "ports", "protocols", "methods", "semantics",
            "request_data_classes", "response_data_classes", "credential_audiences",
            "redirect_destinations",
        )
        numeric_fields = ("max_calls", "max_bytes", "max_seconds", "retry_limit")
        narrowed: list[dict[str, object]] = []
        for baseline in payload["network_grants"]:
            candidate = requested.get(baseline["grant_id"])
            if candidate is None:
                continue
            grant = dict(baseline)
            for field in list_fields:
                grant[field] = sorted(set(baseline[field]) & set(candidate[field]))
            for field in numeric_fields:
                grant[field] = min(int(baseline[field]), int(candidate[field]))
            grant["idempotency_required"] = bool(
                baseline["idempotency_required"] or candidate["idempotency_required"]
            )
            grant["approval_classes"] = sorted(
                set(baseline["approval_classes"]) | set(candidate["approval_classes"])
            )
            narrowed.append(grant)
        payload["network_grants"] = narrowed
    for field, value in project_policy.lower_maximums.items():
        baseline = payload["limits"][field]
        if field == "max_cost_decimal":
            from decimal import Decimal
            if Decimal(str(value)) > Decimal(str(baseline)):
                raise ProjectPolicyError(f"project policy attempts to widen {field}")
        elif int(value) > int(baseline):
            raise ProjectPolicyError(f"project policy attempts to widen {field}")
        payload["limits"][field] = value
    enforcement_order = {"instruction_only": 0, "host_enforced": 1}
    observation_order = {"agent_reported": 0, "coordinator_observed": 1, "host_observed": 2}
    for field, value in project_policy.require_minimum_enforcement.items():
        existing = payload["required_enforcement"].get(field, "instruction_only")
        payload["required_enforcement"][field] = max(
            (existing, value), key=lambda item: enforcement_order[item]
        )
    for field, value in project_policy.require_minimum_observation.items():
        existing = payload["required_observation"].get(field, "agent_reported")
        payload["required_observation"][field] = max(
            (existing, value), key=lambda item: observation_order[item]
        )
    return ActivePolicyV2.model_validate(payload)


def load_project_policy(project_root: str | Path, global_policy: ActivePolicy) -> LoadedProjectPolicy:
    root = Path(project_root).resolve(strict=True)
    if not root.is_dir() or root.is_symlink():
        raise ProjectPolicyError("project root must be a real directory")
    policy_path = root / POLICY_FILENAME
    source: bytes | None
    policy: ProjectPolicyV2 | None
    if policy_path.is_symlink():
        raise ProjectPolicyError("the fixed policy path cannot be a symlink")
    try:
        source = _read_regular_nofollow(policy_path)
    except FileNotFoundError:
        source = None
    if source is None:
        policy = None
        source_hash = hashlib.sha256(ABSENT_POLICY_BYTES).hexdigest()
        presence = "absent"
    else:
        try:
            payload = parse_json_strict(source)
            policy = ProjectPolicyV2.model_validate(payload)
        except Exception as exc:
            raise ProjectPolicyError("the fixed policy file is not canonical ProjectPolicy schema 2.0") from exc
        if source != canonical_bytes(policy.model_dump(mode="json")) + b"\n":
            raise ProjectPolicyError("the fixed policy file must contain canonical JSON followed by one newline")
        source_hash = hashlib.sha256(source).hexdigest()
        presence = "present"
    effective = _to_active_v2(global_policy, policy)
    effective_hash = _hash_ref("active-policy", effective.model_dump(mode="json"), "2.0")
    binding = PolicyBinding(
        schema_version="1.0",
        project_root=str(root),
        policy_path=str(policy_path),
        presence=presence,
        global_policy_hash=_global_hash(global_policy),
        source_policy_sha256=source_hash,
        effective_policy_hash=effective_hash,
    )
    case_sensitive = platform.system().lower() not in {"darwin", "windows"}
    for child in root.iterdir():
        swapped = child.name.swapcase()
        if swapped != child.name:
            case_sensitive = not (root / swapped).exists()
            break
    return LoadedProjectPolicy(root, policy_path, global_policy, policy, effective, binding, source, case_sensitive)


def _component_identity(root: Path, relative: Path) -> tuple[str, str | None]:
    facts: list[str] = []
    current = root
    for component in relative.parts:
        current = current / component
        try:
            observed = current.lstat()
        except FileNotFoundError:
            facts.append(f"{component}:missing")
            continue
        facts.append(
            f"{component}:mode={observed.st_mode}:dev={observed.st_dev}:ino={observed.st_ino}:nlink={observed.st_nlink}"
        )
        if stat.S_ISLNK(observed.st_mode):
            return hashlib.sha256("|".join(facts).encode()).hexdigest(), "symlink component"
        if stat.S_ISREG(observed.st_mode) and observed.st_nlink != 1:
            return hashlib.sha256("|".join(facts).encode()).hexdigest(), "hard-linked file identity"
        if observed.st_dev != root.stat().st_dev:
            return hashlib.sha256("|".join(facts).encode()).hexdigest(), "device or mount boundary"
    return hashlib.sha256("|".join(facts).encode()).hexdigest(), None


def evaluate_path(
    loaded: LoadedProjectPolicy,
    path: str | Path,
    capability: PathCapability,
) -> PathPolicyDecision:
    supplied = Path(path)
    if ".." in supplied.parts:
        raise ProjectPolicyError("requested path contains parent traversal")
    lexical = supplied if supplied.is_absolute() else loaded.project_root / supplied
    lexical = Path(os.path.abspath(lexical))
    if not _inside(lexical, loaded.project_root):
        raise ProjectPolicyError("requested path is outside the authoritative project root")
    relative = lexical.relative_to(loaded.project_root)
    relative_text = "" if relative == Path(".") else relative.as_posix()
    normalized = unicodedata.normalize("NFC", relative_text)
    if normalized != relative_text:
        uncertainty = "non-canonical Unicode path"
        identity_hash = hashlib.sha256(normalized.encode()).hexdigest()
        matches: list[str] = []
    else:
        identity_hash, uncertainty = _component_identity(loaded.project_root, relative)
        matches = []
        if capability in {"modify", "delete"} and relative_text == "":
            matches.extend(["system-policy-file", "system-control-plane"])
        if relative_text == POLICY_FILENAME and capability in {"create", "modify", "delete"}:
            matches.append("system-policy-file")
        if (
            relative_text == ".rb-safe-operation"
            or relative_text.startswith(".rb-safe-operation/")
        ):
            matches.append("system-control-plane")
        comparable_relative = relative_text if loaded.case_sensitive else relative_text.casefold()
        for rule in loaded.effective_policy.path_rules:
            governed = Path(rule.path)
            comparable_governed = rule.path if loaded.case_sensitive else rule.path.casefold()
            applies = comparable_relative == comparable_governed or (
                rule.scope == "subtree"
                and (
                    comparable_relative == comparable_governed
                    or comparable_relative.startswith(comparable_governed + "/")
                )
            )
            ancestor_prefix = comparable_relative.rstrip("/")
            ancestor_effect = capability in {"modify", "delete"} and (
                ancestor_prefix == "" or comparable_governed.startswith(ancestor_prefix + "/")
            )
            if (applies or ancestor_effect) and capability in rule.deny:
                matches.append(rule.rule_id)
    return PathPolicyDecision(
        schema_version="1.0",
        capability=capability,
        requested_path=str(lexical),
        allowed=not matches and uncertainty is None,
        matched_rule_ids=sorted(matches),
        component_identity_hash=identity_hash,
        uncertainty=uncertainty,
    )


def require_path(
    loaded: LoadedProjectPolicy,
    path: str | Path,
    capability: PathCapability,
) -> PathPolicyDecision:
    decision = evaluate_path(loaded, path, capability)
    if not decision.allowed:
        raise PolicyDenied(decision)
    return decision


def revalidate_decision(loaded: LoadedProjectPolicy, decision: PathPolicyDecision) -> None:
    current = evaluate_path(loaded, decision.requested_path, decision.capability)
    if current != decision:
        raise ProjectPolicyError("path identity or policy decision changed before use")


def _compare_permitted_sets(old: list[object], new: list[object]) -> tuple[bool, bool]:
    """Return whether authority tightened and/or relaxed for an allow-list."""
    old_set, new_set = set(old), set(new)
    return bool(old_set - new_set), bool(new_set - old_set)


def _compare_required_sets(old: list[object], new: list[object]) -> tuple[bool, bool]:
    """Return whether constraints tightened and/or relaxed for a deny/require list."""
    old_set, new_set = set(old), set(new)
    return bool(new_set - old_set), bool(old_set - new_set)


def _path_coverage_is_contained(
    path: str,
    scope: str,
    capability: PathCapability,
    covering_rules: list[object],
) -> bool:
    for rule in covering_rules:
        if capability not in rule.deny:
            continue
        if rule.scope == "subtree" and (
            path == rule.path or path.startswith(rule.path + "/")
        ):
            return True
        if scope == "exact" and rule.scope == "exact" and path == rule.path:
            return True
    return False


def _path_change_directions(old: ActivePolicyV2, new: ActivePolicyV2) -> tuple[bool, bool]:
    old_items = [
        (rule.path, rule.scope, capability)
        for rule in old.path_rules
        for capability in rule.deny
    ]
    new_items = [
        (rule.path, rule.scope, capability)
        for rule in new.path_rules
        for capability in rule.deny
    ]
    tightened = any(
        not _path_coverage_is_contained(path, scope, capability, old.path_rules)
        for path, scope, capability in new_items
    )
    relaxed = any(
        not _path_coverage_is_contained(path, scope, capability, new.path_rules)
        for path, scope, capability in old_items
    )
    return tightened, relaxed


def _effective_change_directions(old: ActivePolicyV2, new: ActivePolicyV2) -> tuple[bool, bool]:
    """Classify the complete effective authority change, not only path-rule changes."""
    tightened = False
    relaxed = False

    for field in (
        "allowed_operation_kinds", "allowed_adapters", "allowed_tools",
        "allowed_effect_classes", "allowed_path_roots", "allowed_executable_hashes",
        "allowed_environment_names",
    ):
        narrower, wider = _compare_permitted_sets(getattr(old, field), getattr(new, field))
        tightened |= narrower
        relaxed |= wider

    for field in (
        "required_approvals", "required_evidence_sources", "required_verification",
        "denied_operations", "denied_adapters", "denied_effect_classes",
        "denied_command_forms",
    ):
        stronger, weaker = _compare_required_sets(getattr(old, field), getattr(new, field))
        tightened |= stronger
        relaxed |= weaker

    path_tightened, path_relaxed = _path_change_directions(old, new)
    tightened |= path_tightened
    relaxed |= path_relaxed

    from decimal import Decimal
    for field in ("max_seconds", "max_processes", "max_bytes", "max_calls", "max_cost_decimal"):
        old_value = Decimal(str(getattr(old.limits, field)))
        new_value = Decimal(str(getattr(new.limits, field)))
        tightened |= new_value < old_value
        relaxed |= new_value > old_value

    enforcement_order = {"instruction_only": 0, "host_enforced": 1}
    observation_order = {"agent_reported": 0, "coordinator_observed": 1, "host_observed": 2}
    for field in set(old.required_enforcement) | set(new.required_enforcement):
        old_value = enforcement_order[old.required_enforcement.get(field, "instruction_only")]
        new_value = enforcement_order[new.required_enforcement.get(field, "instruction_only")]
        tightened |= new_value > old_value
        relaxed |= new_value < old_value
    for field in set(old.required_observation) | set(new.required_observation):
        old_value = observation_order[old.required_observation.get(field, "agent_reported")]
        new_value = observation_order[new.required_observation.get(field, "agent_reported")]
        tightened |= new_value > old_value
        relaxed |= new_value < old_value

    old_network = {item.grant_id: item for item in old.network_grants}
    new_network = {item.grant_id: item for item in new.network_grants}
    tightened |= bool(set(old_network) - set(new_network))
    relaxed |= bool(set(new_network) - set(old_network))
    list_fields = (
        "destinations", "ports", "protocols", "methods", "semantics",
        "request_data_classes", "response_data_classes", "credential_audiences",
        "redirect_destinations",
    )
    for grant_id in set(old_network) & set(new_network):
        old_grant, new_grant = old_network[grant_id], new_network[grant_id]
        for field in list_fields:
            narrower, wider = _compare_permitted_sets(
                getattr(old_grant, field), getattr(new_grant, field)
            )
            tightened |= narrower
            relaxed |= wider
        for field in ("max_calls", "max_bytes", "max_seconds", "retry_limit"):
            old_value, new_value = getattr(old_grant, field), getattr(new_grant, field)
            tightened |= new_value < old_value
            relaxed |= new_value > old_value
        tightened |= new_grant.idempotency_required and not old_grant.idempotency_required
        relaxed |= old_grant.idempotency_required and not new_grant.idempotency_required
        stronger, weaker = _compare_required_sets(
            old_grant.approval_classes, new_grant.approval_classes
        )
        tightened |= stronger
        relaxed |= weaker

    return tightened, relaxed


def build_policy_preview(
    loaded: LoadedProjectPolicy,
    proposal: ProjectPolicyProposal,
    assurance_profile: str,
) -> PolicyPreview:
    if proposal.ambiguity_questions:
        raise ProjectPolicyError("policy proposal contains unresolved ambiguity")
    proposed_effective = _to_active_v2(loaded.global_policy, proposal.proposed_policy)
    tightened, relaxed = _effective_change_directions(loaded.effective_policy, proposed_effective)
    if loaded.project_policy is None:
        classification = "create"
    elif tightened and relaxed:
        classification = "mixed"
    elif relaxed:
        classification = "relaxation"
    elif tightened:
        classification = "tightening"
    else:
        classification = "reason_only"
    old_ids = {item.rule_id for item in (loaded.project_policy.path_rules if loaded.project_policy else [])}
    new_ids = {item.rule_id for item in proposal.proposed_policy.path_rules}
    source = canonical_bytes(proposal.proposed_policy.model_dump(mode="json")) + b"\n"
    proposal_hash = _hash_ref("project-policy-proposal", proposal.model_dump(mode="json"), "1.0")
    effective_hash = _hash_ref("active-policy", proposed_effective.model_dump(mode="json"), "2.0")
    lines = []
    for rule in proposal.proposed_policy.path_rules:
        capabilities = ", ".join(rule.deny)
        lines.append(
            f"Rule {rule.rule_id} denies {capabilities} for {rule.path} ({rule.scope}). {rule.reason}"
        )
    lines.append("User-facing write means create, modify, and delete.")
    lines.append(f"The complete effective authority change is classified as {classification}.")
    token_payload = {
        "project_root": str(loaded.project_root),
        "proposal_hash": proposal_hash.model_dump(mode="json"),
        "expected_source": loaded.binding.source_policy_sha256,
        "new_source": hashlib.sha256(source).hexdigest(),
        "effective": effective_hash.model_dump(mode="json"),
        "classification": classification,
    }
    token = hashlib.sha256(canonical_bytes(token_payload)).hexdigest()
    return PolicyPreview(
        schema_version="1.0",
        project_root=str(loaded.project_root),
        proposal_hash=proposal_hash,
        expected_source_policy_sha256=loaded.binding.source_policy_sha256,
        proposed_source_policy_sha256=hashlib.sha256(source).hexdigest(),
        proposed_effective_policy_hash=effective_hash,
        change_classification=classification,
        added_rule_ids=sorted(new_ids - old_ids),
        retained_rule_ids=sorted(new_ids & old_ids),
        removed_rule_ids=sorted(old_ids - new_ids),
        plain_language_lines=lines,
        prospective_only_disclosure=(
            "These restrictions apply prospectively to governed safe-operation activity. They cannot remove "
            "content from an earlier conversation, provider log, Git history, copy, backup, or process memory."
        ),
        assurance_profile=assurance_profile,
        confirmation_token=token,
        confirmation_statement=(
            f"CONFIRM SAFE OPERATION POLICY"
            f"{' RELAXATION' if classification in {'relaxation', 'mixed'} else ''} {token}"
        ),
    )


def policy_confirmation_statement(preview: PolicyPreview) -> str:
    return preview.confirmation_statement


def apply_confirmed_policy(
    loaded: LoadedProjectPolicy,
    proposal: ProjectPolicyProposal,
    preview: PolicyPreview,
    confirmation: PolicyConfirmation,
    *,
    control_root: str | Path,
) -> PolicyAuthoringRecord:
    from .state import acquire_lease, release_lease

    recomputed_preview = build_policy_preview(loaded, proposal, preview.assurance_profile)
    if recomputed_preview != preview:
        raise ProjectPolicyError("policy preview differs from the deterministic current preview")
    proposal_hash = _hash_ref("project-policy-proposal", proposal.model_dump(mode="json"), "1.0")
    preview_hash = _hash_ref("policy-preview", preview.model_dump(mode="json"), "1.0")
    if confirmation.proposal_hash != proposal_hash or confirmation.preview_hash != preview_hash:
        raise ProjectPolicyError("confirmation is not bound to this proposal and preview")
    if confirmation.confirmation_token != preview.confirmation_token:
        raise ProjectPolicyError("confirmation token does not match the preview")
    relaxation = preview.change_classification in {"relaxation", "mixed"}
    if confirmation.relaxation_explicitly_confirmed != relaxation:
        raise ProjectPolicyError("relaxation requires enhanced explicit confirmation")
    expected_statement_hash = hashlib.sha256(
        policy_confirmation_statement(preview).encode("utf-8")
    ).hexdigest()
    if confirmation.statement_sha256 != expected_statement_hash:
        raise ProjectPolicyError("confirmation statement does not match the exact preview statement")
    fresh = load_project_policy(loaded.project_root, loaded.global_policy)
    if fresh.binding.source_policy_sha256 != preview.expected_source_policy_sha256:
        raise ProjectPolicyError("the policy changed after preview; regenerate the proposal")
    source = canonical_bytes(proposal.proposed_policy.model_dump(mode="json")) + b"\n"
    if hashlib.sha256(source).hexdigest() != preview.proposed_source_policy_sha256:
        raise ProjectPolicyError("the proposal bytes differ from the preview")
    expected_control = loaded.project_root / ".rb-safe-operation"
    if Path(control_root).resolve(strict=False) != expected_control:
        raise ProjectPolicyError("policy authoring must use the canonical shared control root")
    authoring_id = f"policy-authoring-{proposal_hash.value[:24]}"
    authoring_root = expected_control / "artifacts" / "policy-authoring" / authoring_id
    for directory in (expected_control, expected_control / "artifacts", expected_control / "artifacts" / "policy-authoring"):
        if directory.is_symlink():
            raise ProjectPolicyError("policy authoring control path cannot contain a symlink")
        directory.mkdir(mode=0o700, exist_ok=True)
    lease = acquire_lease(
        str(loaded.project_root),
        f"policy-authoring-{proposal_hash.value[:20]}",
        str(loaded.project_root.stat().st_dev),
        None,
    )
    try:
        authoring_root.mkdir(mode=0o700, exist_ok=False)
    except Exception:
        release_lease(lease)
        raise

    def create_only_record(name: str, payload: object) -> None:
        target = authoring_root / name
        descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
        try:
            os.write(descriptor, canonical_bytes(payload) + b"\n")
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        directory_descriptor = os.open(authoring_root, os.O_RDONLY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)

    confirmation_hash = _hash_ref("policy-confirmation", confirmation.model_dump(mode="json"), "1.0")
    intent = PolicyAuthoringIntent(
        schema_version="1.0",
        authoring_id=authoring_id,
        project_root=str(loaded.project_root),
        proposal_hash=proposal_hash,
        preview_hash=preview_hash,
        confirmation_hash=confirmation_hash,
        expected_source_policy_sha256=preview.expected_source_policy_sha256,
        proposed_source_policy_sha256=preview.proposed_source_policy_sha256,
        change_classification=preview.change_classification,
        created_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )
    try:
        create_only_record("intent.json", intent.model_dump(mode="json"))
    except Exception:
        release_lease(lease)
        raise
    temporary = loaded.policy_path.with_name(f".{POLICY_FILENAME}.{proposal_hash.value[:16]}.tmp")
    replaced = False
    try:
        # Compare again under the shared project mutation lease.
        if loaded.policy_path.exists():
            current_hash = hashlib.sha256(_read_regular_nofollow(loaded.policy_path)).hexdigest()
        else:
            current_hash = hashlib.sha256(ABSENT_POLICY_BYTES).hexdigest()
        if current_hash != preview.expected_source_policy_sha256:
            raise ProjectPolicyError("the policy changed while acquiring the authoring lease")
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
        try:
            os.write(descriptor, source)
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        os.replace(temporary, loaded.policy_path)
        replaced = True
        directory = os.open(loaded.project_root, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        committed = _read_regular_nofollow(loaded.policy_path)
        if committed != source:
            raise ProjectPolicyError("committed policy bytes differ from the confirmed proposal")
        committed_loaded = load_project_policy(loaded.project_root, loaded.global_policy)
        record = PolicyAuthoringRecord(
            schema_version="1.0",
            authoring_id=authoring_id,
            project_root=str(loaded.project_root),
            proposal_hash=proposal_hash,
            preview_hash=preview_hash,
            confirmation_hash=confirmation_hash,
            old_source_policy_sha256=preview.expected_source_policy_sha256,
            new_source_policy_sha256=committed_loaded.binding.source_policy_sha256,
            old_effective_policy_hash=loaded.binding.effective_policy_hash,
            new_effective_policy_hash=committed_loaded.binding.effective_policy_hash,
            change_classification=preview.change_classification,
            added_rule_ids=preview.added_rule_ids,
            removed_rule_ids=preview.removed_rule_ids,
            outcome="committed",
            committed_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        )
        create_only_record("committed.json", record.model_dump(mode="json"))
        return record
    except Exception:
        if replaced:
            try:
                indeterminate = PolicyAuthoringRecord(
                    schema_version="1.0",
                    authoring_id=authoring_id,
                    project_root=str(loaded.project_root),
                    proposal_hash=proposal_hash,
                    preview_hash=preview_hash,
                    confirmation_hash=confirmation_hash,
                    old_source_policy_sha256=preview.expected_source_policy_sha256,
                    new_source_policy_sha256=preview.proposed_source_policy_sha256,
                    old_effective_policy_hash=loaded.binding.effective_policy_hash,
                    new_effective_policy_hash=preview.proposed_effective_policy_hash,
                    change_classification=preview.change_classification,
                    added_rule_ids=preview.added_rule_ids,
                    removed_rule_ids=preview.removed_rule_ids,
                    outcome="indeterminate",
                    committed_at=None,
                )
                create_only_record("indeterminate.json", indeterminate.model_dump(mode="json"))
            except Exception:
                pass
            raise ProjectPolicyError(
                "policy replacement occurred but the authoring transaction did not finish; human inspection is required"
            )
        raise
    finally:
        try:
            if temporary.exists():
                temporary.unlink()
        finally:
            release_lease(lease)
