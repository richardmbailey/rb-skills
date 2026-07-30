from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import secrets
from typing import Callable

from .canonical import artifact_hash, canonical_bytes
from .models import EvidenceRef, Finding, HashRef
from .policy_models import ActivePolicyV2
from .project_policy import LoadedProjectPolicy, evaluate_path, require_path, revalidate_decision
from .patches import (
    PatchFormatError,
    PreparedTextPatch,
    capture_file_metadata,
    metadata_fingerprint_hash,
    prepare_text_patch,
)
from .paths import resolve_contained
from .proposal_models import (
    AgentPatchProposal,
    AssessmentV2,
    BoundedAgentTaskV2,
    BoundedPatchProposal,
    ExactProposedChange,
    ExactTextInput,
    LowLevelPlanV2,
    PatchAssessment,
    PatchAssessmentRequest,
    PatchProposalPreflight,
    PatchSemanticAssessmentProposal,
    ProposalContext,
    ProposalRequest,
    ProviderGrant,
    ReadToolResult,
    RepositorySnapshotV2,
    RunResourceGrant,
    SourceObservation,
)
from .role_hosts import ProposalRoleHost


class ProposalCycleError(RuntimeError):
    pass


class ProposalSafetyRejected(ProposalCycleError):
    def __init__(self, message: str, findings: list[Finding] | None = None):
        super().__init__(message)
        self.findings = findings or []


class RetryableProposalFormatError(PatchFormatError):
    def __init__(
        self,
        message: str,
        *,
        context: ProposalContext,
        proposal: AgentPatchProposal,
    ) -> None:
        super().__init__(message)
        self.context = context
        self.proposal = proposal


def _ref(artifact_type: str, version: str, payload: object) -> HashRef:
    return HashRef(
        artifact_type=artifact_type,
        schema_version=version,
        value=artifact_hash(artifact_type, version, payload),
    )


def _utc_now(clock: Callable[[], datetime]) -> str:
    value = clock().astimezone(timezone.utc).replace(microsecond=0)
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def _blocking_finding(
    code: str,
    category: str,
    explanation: str,
    operation_id: str,
    effect_ids: list[str],
) -> Finding:
    return Finding(
        finding_id=f"finding-{hashlib.sha256((code + explanation).encode()).hexdigest()[:32]}",
        invariant_id="O-001",
        operation_ids=[operation_id],
        effect_ids=effect_ids,
        category=category,
        severity="high",
        evidence_ids=[],
        evidence_provenance=[],
        finding_provenance="coordinator_observed",
        explanation=explanation,
        remediation_or_human_decision="compile and assess a new run or leave the constrained route",
        blocking=True,
    )


def _path_is_covered(path: str, targets: list[str]) -> bool:
    candidate = Path(path)
    for target in targets:
        root = Path(target)
        if candidate == root or root in candidate.parents:
            return True
    return False


@dataclass(frozen=True)
class ProposalCycleArtifacts:
    proposal_context: ProposalContext
    agent_proposal: AgentPatchProposal
    prepared_patch: PreparedTextPatch
    bounded_proposal: BoundedPatchProposal
    preflight: PatchProposalPreflight
    assessment_context: ProposalContext
    semantic_proposal: PatchSemanticAssessmentProposal
    patch_assessment: PatchAssessment
    metadata: dict[str, object]
    exact_changes: list[ExactProposedChange]
    source_inputs: list[ExactTextInput]


class ProposalCycleService:
    """Prepare and assess one proposal without mutating product files or workflow state."""

    def __init__(
        self,
        *,
        plan: LowLevelPlanV2,
        assessment: AssessmentV2,
        active_policy: ActivePolicyV2,
        loaded_project_policy: LoadedProjectPolicy,
        provider_grant: ProviderGrant,
        resource_grant: RunResourceGrant,
        role_host: ProposalRoleHost,
        base_snapshot: RepositorySnapshotV2 | None = None,
        root_resource_grant_hash: HashRef | None = None,
        authorized_resource_grants: list[RunResourceGrant] | None = None,
        metadata_loader=capture_file_metadata,
        clock: Callable[[], datetime] | None = None,
    ):
        self.plan = LowLevelPlanV2.model_validate(plan.model_dump(mode="json"))
        self.assessment = AssessmentV2.model_validate(assessment.model_dump(mode="json"))
        self.active_policy = ActivePolicyV2.model_validate(active_policy.model_dump(mode="json"))
        self.loaded_project_policy = loaded_project_policy
        self.policy_binding = self.plan.policy_binding
        if loaded_project_policy.binding != self.policy_binding:
            raise ProposalCycleError("current project policy identity differs from the plan")
        self.provider_grant = ProviderGrant.model_validate(provider_grant.model_dump(mode="json"))
        self.resource_grant = RunResourceGrant.model_validate(resource_grant.model_dump(mode="json"))
        self.role_host = role_host
        self.base_snapshot = (
            self.plan.snapshot if base_snapshot is None
            else RepositorySnapshotV2.model_validate(base_snapshot.model_dump(mode="json"))
        )
        self.metadata_loader = metadata_loader
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.plan_hash = _ref("low-level-plan", "3.0", self.plan.model_dump(mode="json"))
        self.assessment_hash = _ref("assessment", "3.0", self.assessment.model_dump(mode="json"))
        self.policy_hash = _ref("active-policy", "2.0", self.active_policy.model_dump(mode="json"))
        self.plan_snapshot_hash = _ref("repository-snapshot", "3.0", self.plan.snapshot.model_dump(mode="json"))
        self.snapshot_hash = _ref("repository-snapshot", "3.0", self.base_snapshot.model_dump(mode="json"))
        self.provider_hash = _ref("provider-grant", "1.0", self.provider_grant.model_dump(mode="json"))
        self.resource_hash = _ref("run-resource-grant", "1.0", self.resource_grant.model_dump(mode="json"))
        self.root_resource_grant_hash = root_resource_grant_hash or self.resource_hash
        resource_chain = [
            RunResourceGrant.model_validate(item.model_dump(mode="json"))
            for item in (authorized_resource_grants or [self.resource_grant])
        ]
        if not resource_chain or resource_chain[-1] != self.resource_grant:
            raise ProposalCycleError("active resource grant is not the end of the authorised replenishment chain")
        if _ref(
            "run-resource-grant", "1.0", resource_chain[0].model_dump(mode="json")
        ) != self.root_resource_grant_hash:
            raise ProposalCycleError("resource replenishment chain does not begin at the assessed root grant")
        for previous, current in zip(resource_chain, resource_chain[1:]):
            if (
                current.replenishes_grant_id != previous.grant_id
                or current.issued_at < previous.issued_at
            ):
                raise ProposalCycleError("resource replenishment chain has an invalid predecessor binding")
        if len({item.grant_id for item in resource_chain}) != len(resource_chain):
            raise ProposalCycleError("resource replenishment chain repeats a grant identity")
        self.authorized_resource_grants = resource_chain
        if self.assessment.plan_hash != self.plan_hash or self.assessment.policy_hash != self.policy_hash:
            raise ProposalCycleError("plan assessment identity differs from the proposal authority")
        if self.assessment.snapshot_hash != self.plan_snapshot_hash or not self.assessment.safe:
            raise ProposalCycleError("proposal authority requires the exact approved base snapshot")
        if self.plan.provider_grant_hash != self.provider_hash or self.assessment.provider_grant_hash != self.provider_hash:
            raise ProposalCycleError("provider grant identity differs from the plan assessment")
        if (
            self.plan.run_resource_grant_hash != self.root_resource_grant_hash
            or self.assessment.run_resource_grant_hash != self.root_resource_grant_hash
        ):
            raise ProposalCycleError("run resource grant identity differs from the plan assessment")
        now = self.clock().astimezone(timezone.utc)
        provider_expiry = datetime.strptime(self.provider_grant.expires_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        resource_expiry = datetime.strptime(self.resource_grant.expires_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        if now >= provider_expiry or now >= resource_expiry:
            raise ProposalCycleError("provider or run resource grant expired before proposal construction")
        if not {"patch_proposal", "patch_assessment"}.issubset(self.provider_grant.response_data_classes):
            raise ProposalCycleError("provider grant omits required proposal response data classes")

    def _operation(self, operation_id: str) -> BoundedAgentTaskV2:
        matches = [item for item in self.plan.operations if item.operation_id == operation_id]
        if len(matches) != 1 or not isinstance(matches[0], BoundedAgentTaskV2):
            raise ProposalCycleError("proposal cycle requires one exact bounded operation identity")
        operation = matches[0]
        if operation.provider_grant_id != self.provider_grant.grant_id:
            raise ProposalCycleError("operation provider grant ID differs from the supplied grant")
        if operation.run_resource_grant_id == self.authorized_resource_grants[0].grant_id:
            pass
        else:
            raise ProposalCycleError("operation resource grant ID differs from the authorised grant chain")
        if operation.required_adapter != self.provider_grant.adapter:
            raise ProposalCycleError("operation adapter differs from the provider grant")
        if operation.required_assurance_profile not in self.assessment.required_role_assurance_profiles:
            raise ProposalCycleError("operation assurance profile was not required by the assessment")
        classification_order = ["public", "internal", "personal", "sensitive", "secret"]
        if classification_order.index(self.provider_grant.maximum_data_classification) < classification_order.index(
            operation.source_data_classification
        ):
            raise ProposalCycleError("provider grant does not permit the declared source-data classification")
        required_data_class = f"{operation.source_data_classification}_source"
        if required_data_class not in self.provider_grant.request_data_classes:
            raise ProposalCycleError(f"provider grant omits transmitted data class {required_data_class}")
        return operation

    def _read_context(self, operation: BoundedAgentTaskV2):
        instructions: dict[str, str] = {}
        for path, expected in sorted(self.base_snapshot.instruction_hashes.items()):
            decision = require_path(self.loaded_project_policy, path, "read")
            revalidate_decision(self.loaded_project_policy, decision)
            content = Path(path).read_text(encoding="utf-8")
            if hashlib.sha256(content.encode("utf-8")).hexdigest() != expected:
                raise ProposalCycleError(f"instruction changed before proposal: {path}")
            instructions[path] = content

        inputs: list[ExactTextInput] = []
        observations: list[SourceObservation] = []
        metadata: dict[str, object] = {}
        for index, (path, expected) in enumerate(sorted(self.base_snapshot.selected_file_hashes.items()), start=1):
            decision = require_path(self.loaded_project_policy, path, "read")
            revalidate_decision(self.loaded_project_policy, decision)
            resolved = resolve_contained(path, operation.path_contract.read_roots, operation.path_contract.protected_roots)
            raw = Path(resolved.resolved).read_bytes()
            if hashlib.sha256(raw).hexdigest() != expected:
                raise ProposalCycleError(f"source input changed before proposal: {path}")
            try:
                content = raw.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise ProposalCycleError(f"proposal source is not UTF-8 text: {path}") from exc
            fingerprint = self.metadata_loader(Path(path))
            fingerprint_hash = metadata_fingerprint_hash(fingerprint)
            snapshot_metadata = self.base_snapshot.selected_file_metadata_hashes.get(path)
            if snapshot_metadata != fingerprint_hash:
                raise ProposalCycleError(f"source metadata differs from the assessed snapshot: {path}")
            metadata[path] = fingerprint
            observation_id = f"source-{index}"
            observation = SourceObservation(
                observation_id=observation_id,
                path=path,
                byte_start=0,
                byte_end=len(raw),
                content_hash=expected,
                metadata_hash=fingerprint_hash,
                data_classification=operation.source_data_classification,
                policy_decision=decision,
            )
            observations.append(observation)
            inputs.append(ExactTextInput(
                input_id=f"input-{index}",
                observation_id=observation_id,
                path=path,
                byte_start=0,
                byte_end=len(raw),
                content=content,
                content_hash=expected,
                metadata_hash=fingerprint_hash,
                data_classification=operation.source_data_classification,
            ))
        return instructions, inputs, observations, metadata

    def _mediated_reader(
        self,
        operation: BoundedAgentTaskV2,
        request_token: str,
    ) -> Callable[[str, int, int | None], ReadToolResult]:
        calls = 0
        total_bytes = 0

        def read_file(path: str, byte_start: int = 0, byte_end: int | None = None) -> ReadToolResult:
            nonlocal calls, total_bytes
            if calls >= self.resource_grant.max_read_tool_calls:
                raise ProposalCycleError("bounded read-tool call grant is exhausted")
            resolved = resolve_contained(
                path, operation.path_contract.read_roots,
                operation.path_contract.protected_roots,
            )
            target = Path(resolved.resolved)
            decision = require_path(self.loaded_project_policy, target, "read")
            revalidate_decision(self.loaded_project_policy, decision)
            if target.is_symlink() or not target.is_file():
                raise ProposalCycleError("bounded read tool requires an ordinary regular file")
            raw = target.read_bytes()
            if byte_end is None:
                byte_end = len(raw)
            if byte_start < 0 or byte_end < byte_start or byte_end > len(raw):
                raise ProposalCycleError("bounded read tool byte range is outside the file")
            selected = raw[byte_start:byte_end]
            if total_bytes + len(selected) > self.resource_grant.max_read_tool_bytes:
                raise ProposalCycleError("bounded read-tool byte grant is exhausted")
            try:
                content = selected.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise ProposalCycleError("bounded read tool supports UTF-8 text only") from exc
            fingerprint_hash = metadata_fingerprint_hash(self.metadata_loader(target))
            calls += 1
            total_bytes += len(selected)
            identity = hashlib.sha256(
                canonical_bytes({
                    "path": str(target), "byte_start": byte_start, "byte_end": byte_end,
                    "content_hash": hashlib.sha256(selected).hexdigest(),
                })
            ).hexdigest()[:24]
            return ReadToolResult(
                schema_version="2.0", request_token=request_token,
                observation_id=f"tool-read-{identity}", path=str(target),
                byte_start=byte_start, byte_end=byte_end, content=content,
                content_hash=hashlib.sha256(selected).hexdigest(),
                metadata_hash=fingerprint_hash,
                data_classification=operation.source_data_classification,
                policy_decision=decision,
            )

        return read_file

    def _context(
        self,
        operation: BoundedAgentTaskV2,
        *,
        role: str,
        attempt_id: str,
        instructions: dict[str, str],
        observations: list[SourceObservation],
        prompt_payload: object,
        repair_attempt_hash: HashRef | None,
    ) -> ProposalContext:
        token = f"request-{secrets.token_hex(16)}"
        return ProposalContext(
            schema_version="2.0",
            context_id=f"context-{secrets.token_hex(16)}",
            request_token=token,
            operation_id=operation.operation_id,
            attempt_id=attempt_id,
            role=role,
            adapter=operation.required_adapter,
            assurance_profile=(
                operation.required_assurance_profile
                if role == "proposer" or operation.required_adapter == "json_line"
                else "framework_tool_enforced_no_tools"
            ),
            plan_hash=self.plan_hash,
            plan_assessment_hash=self.assessment_hash,
            operation_hash=_ref("operation", "2.0", operation.model_dump(mode="json")),
            active_policy_hash=self.policy_hash,
            policy_binding=self.policy_binding,
            base_snapshot_hash=self.snapshot_hash,
            provider_grant_hash=self.provider_hash,
            run_resource_grant_hash=self.resource_hash,
            repair_attempt_hash=repair_attempt_hash,
            input_artifact_hashes=[self.plan_hash, self.assessment_hash, self.policy_hash],
            instruction_hashes={
                path: hashlib.sha256(content.encode("utf-8")).hexdigest()
                for path, content in sorted(instructions.items())
            },
            source_observations=observations,
            prompt_packet_hash=hashlib.sha256(canonical_bytes(prompt_payload)).hexdigest(),
            toolset_hash=artifact_hash(
                "proposal-toolset",
                "1.0",
                {"read_tools": operation.allowed_read_tools, "write_tools": []},
            ),
            created_at=_utc_now(self.clock),
        )

    def _preflight(
        self,
        operation: BoundedAgentTaskV2,
        agent: AgentPatchProposal,
        prepared: PreparedTextPatch,
        proposal: BoundedPatchProposal,
    ) -> PatchProposalPreflight:
        findings: list[Finding] = []
        actual = {
            "create": set(prepared.created_paths),
            "modify": set(prepared.modified_paths),
            "delete": set(prepared.deleted_paths),
        }
        claims = {
            "create": set(agent.claimed_created_paths),
            "modify": set(agent.claimed_modified_paths),
            "delete": set(agent.claimed_deleted_paths),
        }
        effect_ids = [item.effect_id for item in operation.effects]
        if actual != claims:
            findings.append(_blocking_finding(
                "proposal_inventory_mismatch", "operation_contract",
                "model path claims differ from the parsed diff", operation.operation_id, effect_ids
            ))
        if set(agent.claimed_effect_ids) != set(effect_ids):
            findings.append(_blocking_finding(
                "proposal_effect_mismatch", "effect_inventory",
                "model effect claims differ from the assessed effect envelope", operation.operation_id, effect_ids
            ))
        roots = {
            "create": operation.path_contract.create_roots,
            "modify": operation.path_contract.modify_roots,
            "delete": operation.path_contract.delete_roots,
        }
        for action, paths in actual.items():
            if paths and action not in operation.allowed_patch_actions:
                findings.append(_blocking_finding(
                    "proposal_action_forbidden", "operation_contract",
                    f"{action} is outside the assessed patch actions", operation.operation_id, effect_ids
                ))
            for path in paths:
                decision = evaluate_path(self.loaded_project_policy, path, action)
                if not decision.allowed:
                    findings.append(_blocking_finding(
                        "project_policy_denied",
                        "policy_limit",
                        f"project policy denied {action} for {path}; rules={decision.matched_rule_ids}",
                        operation.operation_id,
                        effect_ids,
                    ))
                try:
                    resolve_contained(path, roots[action], operation.path_contract.protected_roots, mutation=True)
                except Exception:
                    findings.append(_blocking_finding(
                        "proposal_path_forbidden", "path_escape",
                        f"{path} is outside the assessed {action} roots", operation.operation_id, effect_ids
                    ))
                if not any(_path_is_covered(path, effect.targets) for effect in operation.effects):
                    findings.append(_blocking_finding(
                        "proposal_effect_path_uncovered", "effect_inventory",
                        f"{path} is not covered by a declared effect target", operation.operation_id, effect_ids
                    ))
        proposal_hash = _ref("bounded-patch-proposal", "2.0", proposal.model_dump(mode="json"))
        return PatchProposalPreflight(
            schema_version="2.0",
            preflight_id=f"proposal-preflight-{proposal_hash.value[:24]}",
            proposal_hash=proposal_hash,
            plan_hash=self.plan_hash,
            policy_hash=self.policy_hash,
            snapshot_hash=self.snapshot_hash,
            deterministic_pass=not findings,
            semantic_assessment_required=not findings,
            findings=findings,
            policy_binding=self.policy_binding,
        )

    def _validate_agent_claim_envelope(
        self,
        operation: BoundedAgentTaskV2,
        agent: AgentPatchProposal,
    ) -> None:
        """Reject claimed authority expansion before reading any claimed target."""

        effect_ids = {item.effect_id for item in operation.effects}
        if set(agent.claimed_effect_ids) != effect_ids:
            raise ProposalSafetyRejected(
                "proposal effect claims differ from the assessed effect envelope",
                [_blocking_finding(
                    "proposal_effect_mismatch",
                    "effect_inventory",
                    "model effect claims differ from the assessed effect envelope",
                    operation.operation_id,
                    sorted(effect_ids),
                )],
            )
        roots = {
            "create": operation.path_contract.create_roots,
            "modify": operation.path_contract.modify_roots,
            "delete": operation.path_contract.delete_roots,
        }
        claims = {
            "create": set(agent.claimed_created_paths),
            "modify": set(agent.claimed_modified_paths),
            "delete": set(agent.claimed_deleted_paths),
        }
        for action, paths in claims.items():
            if paths and action not in operation.allowed_patch_actions:
                raise ProposalSafetyRejected(
                    f"claimed {action} action is outside the assessed patch actions",
                    [_blocking_finding(
                        "proposal_action_forbidden",
                        "operation_contract",
                        f"claimed {action} is outside the assessed patch actions",
                        operation.operation_id,
                        sorted(effect_ids),
                    )],
                )
            for path in paths:
                decision = evaluate_path(self.loaded_project_policy, path, action)
                if not decision.allowed:
                    raise ProposalSafetyRejected(
                        f"project policy denied claimed {action} path"
                    )
                try:
                    resolve_contained(
                        path,
                        roots[action],
                        operation.path_contract.protected_roots,
                        mutation=True,
                    )
                except Exception as exc:
                    raise ProposalSafetyRejected(
                        f"claimed {action} path is outside the assessed roots"
                    ) from exc
                if not any(
                    _path_is_covered(path, effect.targets)
                    for effect in operation.effects
                ):
                    raise ProposalSafetyRejected(
                        f"claimed {action} path is not covered by an assessed effect"
                    )

    def _propose_and_prepare(
        self,
        operation: BoundedAgentTaskV2,
        *,
        attempt_id: str,
        repair_attempt_hash: HashRef | None,
        retry_context: dict[str, object] | None,
        state_guard: Callable[[str], None] | None,
        artifact_checkpoint: Callable[[str, object], None] | None,
    ):
        instructions, inputs, observations, source_metadata = self._read_context(operation)
        evidence = [item for item in self.plan.evidence if item.evidence_id in operation.evidence_ids]
        proposer_payload = {
            "operation": operation.model_dump(mode="json"),
            "evidence": [item.model_dump(mode="json") for item in evidence],
            "instructions": instructions,
            "sources": [item.model_dump(mode="json") for item in inputs],
            "attempt_id": attempt_id,
        }
        if retry_context is not None:
            proposer_payload["automatic_retry"] = retry_context
        proposer_context = self._context(
            operation,
            role="proposer",
            attempt_id=attempt_id,
            instructions=instructions,
            observations=observations,
            prompt_payload=proposer_payload,
            repair_attempt_hash=repair_attempt_hash,
        )
        request = ProposalRequest(
            schema_version="2.0",
            context=proposer_context,
            operation=operation,
            plan_evidence=evidence,
            applicable_instructions=instructions,
            source_inputs=inputs,
        )
        if artifact_checkpoint:
            artifact_checkpoint("proposer_requested", request)
        if state_guard:
            state_guard("before_proposer")
        if operation.allowed_read_tools:
            reader = self._mediated_reader(operation, proposer_context.request_token)
            agent_result = self.role_host.propose_patch(request, read_file=reader)
        else:
            agent_result = self.role_host.propose_patch(request)
        agent = AgentPatchProposal.model_validate(agent_result.model_dump(mode="json"))
        if state_guard:
            state_guard("after_proposer")
        if artifact_checkpoint:
            artifact_checkpoint(
                "proposer_response_received",
                (proposer_context, agent, inputs),
            )
        if agent.operation_id != operation.operation_id or agent.attempt_id != attempt_id:
            raise ProposalSafetyRejected("proposal operation or attempt identity differs")
        self._validate_agent_claim_envelope(operation, agent)
        drain_reads = getattr(self.role_host, "drain_read_results", None)
        read_results = [] if drain_reads is None else drain_reads(proposer_context.request_token)
        if read_results and not operation.allowed_read_tools:
            raise ProposalSafetyRejected("proposal host reported ungranted runtime-mediated reads")
        for result in read_results:
            result = ReadToolResult.model_validate(result)
            target = Path(result.path)
            raw = target.read_bytes()
            observed = raw[result.byte_start:result.byte_end]
            if hashlib.sha256(observed).hexdigest() != result.content_hash:
                raise ProposalSafetyRejected("runtime-mediated source changed before proposal validation")
            fingerprint = self.metadata_loader(target)
            if metadata_fingerprint_hash(fingerprint) != result.metadata_hash:
                raise ProposalSafetyRejected("runtime-mediated source metadata changed before proposal validation")
            source_metadata[result.path] = fingerprint
            observations.append(SourceObservation(
                observation_id=result.observation_id, path=result.path,
                byte_start=result.byte_start, byte_end=result.byte_end,
                content_hash=result.content_hash, metadata_hash=result.metadata_hash,
                data_classification=result.data_classification,
                policy_decision=result.policy_decision,
            ))
            inputs.append(ExactTextInput(
                input_id=f"input-{result.observation_id}", observation_id=result.observation_id,
                path=result.path, byte_start=result.byte_start, byte_end=result.byte_end,
                content=result.content, content_hash=result.content_hash,
                metadata_hash=result.metadata_hash,
                data_classification=result.data_classification,
            ))
        if read_results:
            read_hashes = [
                _ref("read-tool-result", "2.0", item.model_dump(mode="json"))
                for item in read_results
            ]
            proposer_context = proposer_context.model_copy(update={
                "source_observations": observations,
                "input_artifact_hashes": proposer_context.input_artifact_hashes + read_hashes,
                "prompt_packet_hash": hashlib.sha256(canonical_bytes({
                    "initial_packet": proposer_payload,
                    "read_result_hashes": [item.model_dump(mode="json") for item in read_hashes],
                })).hexdigest(),
            })

        patch_bytes = len(agent.unified_diff.encode("utf-8"))
        if patch_bytes > min(operation.resource_limits.max_bytes, self.resource_grant.max_patch_bytes):
            raise ProposalSafetyRejected("proposed patch exceeds the assessed patch-byte limit")

        absolute_preimages: dict[str, bytes] = {}
        for path in set(agent.claimed_modified_paths) | set(agent.claimed_deleted_paths):
            decision = require_path(self.loaded_project_policy, path, "read")
            revalidate_decision(self.loaded_project_policy, decision)
            raw = Path(path).read_bytes()
            matching = next((
                item for item in inputs
                if item.path == path
                and item.byte_start == 0
                and item.byte_end == len(raw)
                and item.content.encode("utf-8") == raw
            ), None)
            if matching is None:
                raise ProposalSafetyRejected(
                    "proposal target lacks a complete exact coordinator-captured preimage"
                )
            absolute_preimages[path] = raw
        try:
            prepared = prepare_text_patch(
                agent.unified_diff,
                Path(operation.path_contract.working_directories[0]),
                absolute_preimages,
            )
        except PatchFormatError as exc:
            raise RetryableProposalFormatError(
                str(exc), context=proposer_context, proposal=agent
            ) from exc
        target_metadata = {
            path: source_metadata[path]
            for path in set(prepared.modified_paths) | set(prepared.deleted_paths)
            if path in source_metadata
        }
        if set(target_metadata) != set(prepared.modified_paths) | set(prepared.deleted_paths):
            raise ProposalSafetyRejected("prepared proposal target metadata is incomplete")
        return (
            instructions,
            inputs,
            observations,
            proposer_context,
            agent,
            prepared,
            target_metadata,
        )

    def run(
        self,
        operation_id: str,
        *,
        attempt_id: str = "attempt-initial",
        repair_attempt_hash: HashRef | None = None,
        state_guard: Callable[[str], None] | None = None,
        artifact_checkpoint: Callable[[str, object], None] | None = None,
        automatic_retry_count: int = 0,
        retry_context: dict[str, object] | None = None,
    ) -> ProposalCycleArtifacts:
        operation = self._operation(operation_id)
        while True:
            try:
                (
                    instructions,
                    inputs,
                    observations,
                    proposer_context,
                    agent,
                    prepared,
                    target_metadata,
                ) = self._propose_and_prepare(
                    operation,
                    attempt_id=attempt_id,
                    repair_attempt_hash=repair_attempt_hash,
                    retry_context=retry_context,
                    state_guard=state_guard,
                    artifact_checkpoint=artifact_checkpoint,
                )
                break
            except RetryableProposalFormatError as exc:
                next_retry_index = automatic_retry_count + 1
                limit = self.resource_grant.automatic_retry_attempt_limit
                authorised = (
                    "proposal_format_error" in self.resource_grant.automatic_retry_classes
                    and (limit == "unbounded" or next_retry_index <= limit)
                )
                if not authorised:
                    raise
                if artifact_checkpoint is None:
                    raise ProposalCycleError(
                        "automatic retry requires a durable coordinator checkpoint"
                    ) from exc
                if state_guard:
                    state_guard("before_automatic_retry")
                artifact_checkpoint(
                    "automatic_retry_scheduled",
                    (exc.context, exc.proposal, next_retry_index, "proposal_format_error"),
                )
                automatic_retry_count = next_retry_index
                retry_context = {
                    "retry_index": automatic_retry_count,
                    "failure_class": "proposal_format_error",
                    "failed_request_token": exc.context.request_token,
                    "correction": (
                        "Return a syntactically complete standard unified diff. Keep the same "
                        "operation, paths, actions, effects, and safety envelope."
                    ),
                }
        proposal = BoundedPatchProposal(
            schema_version="2.0",
            proposal_id=f"proposal-{hashlib.sha256(agent.unified_diff.encode()).hexdigest()[:24]}",
            context_hash=_ref("proposal-context", "2.0", proposer_context.model_dump(mode="json")),
            agent_proposal_hash=_ref("agent-patch-proposal", "1.0", agent.model_dump(mode="json")),
            plan_hash=self.plan_hash,
            plan_assessment_hash=self.assessment_hash,
            operation_hash=_ref("operation", "2.0", operation.model_dump(mode="json")),
            active_policy_hash=self.policy_hash,
            policy_binding=self.policy_binding,
            base_snapshot_hash=self.snapshot_hash,
            repair_attempt_hash=repair_attempt_hash,
            patch_hash=prepared.patch_hash,
            created_paths=list(prepared.created_paths),
            modified_paths=list(prepared.modified_paths),
            deleted_paths=list(prepared.deleted_paths),
            preimage_hashes={str(item.path): item.preimage_hash for item in prepared.targets if item.preimage_hash},
            postimage_hashes={str(item.path): item.postimage_hash for item in prepared.targets if item.postimage_hash},
            metadata_hashes={path: metadata_fingerprint_hash(value) for path, value in target_metadata.items()},
            expected_effect_ids=sorted(effect_ids := [item.effect_id for item in operation.effects]),
            proposer_role="proposer",
            assurance_profile=operation.required_assurance_profile,
            evidence=agent.evidence,
        )
        exact_changes = [ExactProposedChange(
            path=str(item.path),
            action=item.action,
            preimage=None if item.preimage is None else item.preimage.decode("utf-8"),
            postimage=None if item.postimage is None else item.postimage.decode("utf-8"),
            preimage_hash=item.preimage_hash,
            postimage_hash=item.postimage_hash,
            metadata_hash=None if item.action == "create" else proposal.metadata_hashes[str(item.path)],
        ) for item in prepared.targets]
        if artifact_checkpoint:
            artifact_checkpoint(
                "proposal_received",
                (proposer_context, agent, prepared, proposal, target_metadata, exact_changes, inputs),
            )
        preflight = self._preflight(operation, agent, prepared, proposal)
        if artifact_checkpoint:
            artifact_checkpoint("preflight_complete", (prepared, proposal, preflight, target_metadata))
        if not preflight.deterministic_pass:
            raise ProposalSafetyRejected("proposal failed deterministic preflight", preflight.findings)

        assessor_payload = {
            "operation": operation.model_dump(mode="json"),
            "proposal": proposal.model_dump(mode="json"),
            "preflight": preflight.model_dump(mode="json"),
            "changes": [item.model_dump(mode="json") for item in exact_changes],
            "sources": [item.model_dump(mode="json") for item in inputs],
            "instructions": instructions,
        }
        assessment_context = self._context(
            operation,
            role="patch_assessor",
            attempt_id=attempt_id,
            instructions=instructions,
            observations=observations,
            prompt_payload=assessor_payload,
            repair_attempt_hash=repair_attempt_hash,
        )
        assessment_request = PatchAssessmentRequest(
            schema_version="2.0",
            context=assessment_context,
            operation=operation,
            proposal=proposal,
            preflight=preflight,
            exact_changes=exact_changes,
            source_inputs=inputs,
            applicable_instructions=instructions,
        )
        if artifact_checkpoint:
            artifact_checkpoint(
                "assessment_requested",
                (assessment_context, exact_changes, assessment_request),
            )
        if state_guard:
            state_guard("before_assessor")
        semantic = PatchSemanticAssessmentProposal.model_validate(
            self.role_host.assess_patch(assessment_request).model_dump(mode="json")
        )
        if state_guard:
            state_guard("after_assessor")
        proposal_hash = preflight.proposal_hash
        if semantic.proposal_hash != proposal_hash or semantic.policy_binding != self.policy_binding:
            raise ProposalSafetyRejected("semantic assessment names another proposal")
        expected_paths = set(proposal.created_paths + proposal.modified_paths + proposal.deleted_paths)
        complete = set(semantic.covered_paths) == expected_paths and set(semantic.covered_effect_ids) == set(effect_ids)
        findings = list(preflight.findings) + list(semantic.findings)
        semantic_pass = semantic.semantic_pass and complete
        assessment = PatchAssessment(
            schema_version="2.0",
            assessment_id=f"patch-assessment-{proposal_hash.value[:24]}",
            proposal_hash=proposal_hash,
            preflight_hash=_ref("patch-proposal-preflight", "2.0", preflight.model_dump(mode="json")),
            semantic_proposal_hash=_ref(
                "patch-semantic-assessment-proposal", "2.0", semantic.model_dump(mode="json")
            ),
            complete_context=complete,
            deterministic_pass=preflight.deterministic_pass,
            semantic_pass=semantic_pass,
            safe=preflight.deterministic_pass and semantic_pass and not any(item.blocking for item in findings),
            status=(
                "approved"
                if preflight.deterministic_pass and semantic_pass and not any(item.blocking for item in findings)
                else "rejected"
            ),
            findings=findings,
            policy_binding=self.policy_binding,
        )
        if artifact_checkpoint:
            artifact_checkpoint("assessment_complete", (semantic, assessment))
        if not assessment.safe:
            raise ProposalSafetyRejected("proposal failed semantic patch assessment", findings)
        return ProposalCycleArtifacts(
            proposal_context=proposer_context,
            agent_proposal=agent,
            prepared_patch=prepared,
            bounded_proposal=proposal,
            preflight=preflight,
            assessment_context=assessment_context,
            semantic_proposal=semantic,
            patch_assessment=assessment,
            metadata=target_metadata,
            exact_changes=exact_changes,
            source_inputs=inputs,
        )

    def assess_existing(
        self,
        operation_id: str,
        *,
        context: ProposalContext,
        proposal: BoundedPatchProposal,
        preflight: PatchProposalPreflight,
        exact_changes: list[ExactProposedChange],
        source_inputs: list[ExactTextInput],
        state_guard: Callable[[str], None] | None = None,
        artifact_checkpoint: Callable[[str, object], None] | None = None,
    ) -> tuple[PatchSemanticAssessmentProposal, PatchAssessment]:
        """Resume only the assessor call for an already persisted canonical proposal."""

        operation = self._operation(operation_id)
        instructions, _, _, _ = self._read_context(operation)
        inputs = [ExactTextInput.model_validate(item) for item in source_inputs]
        for item in inputs:
            decision = require_path(self.loaded_project_policy, item.path, "read")
            revalidate_decision(self.loaded_project_policy, decision)
            raw = Path(item.path).read_bytes()
            observed = raw[item.byte_start:item.byte_end]
            if hashlib.sha256(observed).hexdigest() != item.content_hash:
                raise ProposalCycleError(f"resumed proposal source input changed: {item.path}")
            if metadata_fingerprint_hash(self.metadata_loader(Path(item.path))) != item.metadata_hash:
                raise ProposalCycleError(f"resumed proposal source metadata changed: {item.path}")
        expected_context = ProposalContext.model_validate(context.model_dump(mode="json"))
        if expected_context.role != "patch_assessor":
            raise ProposalCycleError("resumed assessment context has the wrong role")
        expected_bindings = {
            "plan_hash": self.plan_hash,
            "plan_assessment_hash": self.assessment_hash,
            "operation_hash": _ref("operation", "2.0", operation.model_dump(mode="json")),
            "active_policy_hash": self.policy_hash,
            "base_snapshot_hash": self.snapshot_hash,
            "provider_grant_hash": self.provider_hash,
            "run_resource_grant_hash": self.resource_hash,
        }
        for field, value in expected_bindings.items():
            if getattr(expected_context, field) != value:
                raise ProposalCycleError(f"resumed assessment context {field} differs from current authority")
        expected_prompt_payload = {
            "operation": operation.model_dump(mode="json"),
            "proposal": proposal.model_dump(mode="json"),
            "preflight": preflight.model_dump(mode="json"),
            "changes": [item.model_dump(mode="json") for item in exact_changes],
            "sources": [item.model_dump(mode="json") for item in inputs],
            "instructions": instructions,
        }
        if expected_context.prompt_packet_hash != hashlib.sha256(
            canonical_bytes(expected_prompt_payload)
        ).hexdigest():
            raise ProposalCycleError("resumed assessment context differs from the exact assessment packet")
        request = PatchAssessmentRequest(
            schema_version="2.0", context=expected_context, operation=operation,
            proposal=proposal, preflight=preflight, exact_changes=exact_changes,
            source_inputs=inputs,
            applicable_instructions=instructions,
        )
        if state_guard:
            state_guard("before_assessor")
        semantic = PatchSemanticAssessmentProposal.model_validate(
            self.role_host.assess_patch(request).model_dump(mode="json")
        )
        if state_guard:
            state_guard("after_assessor")
        if (
            semantic.proposal_hash != preflight.proposal_hash
            or semantic.policy_binding != self.policy_binding
        ):
            raise ProposalSafetyRejected("resumed semantic assessment names another proposal")
        expected_paths = set(proposal.created_paths + proposal.modified_paths + proposal.deleted_paths)
        complete = (
            set(semantic.covered_paths) == expected_paths
            and set(semantic.covered_effect_ids) == set(proposal.expected_effect_ids)
        )
        findings = list(preflight.findings) + list(semantic.findings)
        semantic_pass = semantic.semantic_pass and complete
        assessment = PatchAssessment(
            schema_version="2.0",
            assessment_id=f"patch-assessment-{preflight.proposal_hash.value[:24]}",
            proposal_hash=preflight.proposal_hash,
            preflight_hash=_ref("patch-proposal-preflight", "2.0", preflight.model_dump(mode="json")),
            semantic_proposal_hash=_ref(
                "patch-semantic-assessment-proposal", "2.0", semantic.model_dump(mode="json")
            ),
            complete_context=complete, deterministic_pass=preflight.deterministic_pass,
            semantic_pass=semantic_pass,
            safe=preflight.deterministic_pass and semantic_pass and not any(item.blocking for item in findings),
            status=(
                "approved" if preflight.deterministic_pass and semantic_pass
                and not any(item.blocking for item in findings) else "rejected"
            ),
            findings=findings,
            policy_binding=self.policy_binding,
        )
        if artifact_checkpoint:
            artifact_checkpoint("assessment_complete", (semantic, assessment))
        if not assessment.safe:
            raise ProposalSafetyRejected("proposal failed resumed semantic patch assessment", findings)
        return semantic, assessment
