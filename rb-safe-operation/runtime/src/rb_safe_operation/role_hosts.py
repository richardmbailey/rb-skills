from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import select
import time
from typing import Any, BinaryIO, Callable, Protocol, TypeVar

from pydantic import ValidationError
from pydantic_ai import Agent, Tool
from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.models import Model
from pydantic_ai.usage import UsageLimits

from .canonical import artifact_hash, canonical_bytes, canonical_decimal, parse_json_strict
from .models import HashRef, StrictModel
from .policy_models import PolicyTranslationRequest, ProjectPolicyProposal
from .proposal_models import (
    AgentPatchProposal,
    PatchAssessmentRequest,
    PatchSemanticAssessmentProposal,
    PlanAssessmentRequest,
    PlanAssessmentResponse,
    ProposalRequest,
    ProviderGrant,
    ReadToolResult,
    RoleCallRecord,
    RunResourceGrant,
    VerificationRoleRequest,
    VerificationRoleResponse,
)


class ProposalRoleHost(Protocol):
    """Provider-neutral, proposal-only semantic role boundary."""

    def propose_patch(
        self,
        request: ProposalRequest,
        read_file: Callable[[str, int, int | None], ReadToolResult] | None = None,
    ) -> AgentPatchProposal: ...

    def assess_patch(self, request: PatchAssessmentRequest) -> PatchSemanticAssessmentProposal: ...

    def assess_plan(self, request: PlanAssessmentRequest) -> PlanAssessmentResponse: ...

    def verify(self, request: VerificationRoleRequest) -> VerificationRoleResponse: ...

    def translate_policy(self, request: PolicyTranslationRequest) -> ProjectPolicyProposal: ...

    def adopt_call_record(self, record: RoleCallRecord) -> None: ...


def _hash_ref(artifact_type: str, payload: Any, schema_version: str) -> HashRef:
    return HashRef(
        artifact_type=artifact_type,
        schema_version=schema_version,
        value=artifact_hash(artifact_type, schema_version, payload),
    )


class RoleHostError(RuntimeError):
    pass


class RoleHostProtocolError(RoleHostError):
    pass


class RoleHostTimeout(RoleHostError):
    pass


class RoleHostResourceExhausted(RoleHostError):
    pass


def _remaining_elapsed_timeout(
    *,
    configured_timeout_seconds: float,
    aggregate_elapsed_milliseconds: int,
    aggregate_limit_seconds: int,
) -> float:
    """Return the timeout that cannot exceed the remaining aggregate grant."""

    remaining_milliseconds = aggregate_limit_seconds * 1000 - aggregate_elapsed_milliseconds
    if remaining_milliseconds <= 0:
        raise RoleHostResourceExhausted("aggregate elapsed-time grant is exhausted")
    return min(configured_timeout_seconds, remaining_milliseconds / 1000)


def _failure_outcome(error: Exception) -> str:
    if isinstance(error, RoleHostTimeout):
        return "timeout"
    if isinstance(error, RoleHostResourceExhausted):
        return "resource_exhausted"
    if isinstance(error, RoleHostProtocolError):
        return "protocol_error"
    return "role_error"


def _adopt_prior_call_record(
    host: Any,
    record: RoleCallRecord,
    *,
    adapter: str,
    provider: str,
    endpoint: str,
    model: str,
    model_revision: str | None,
    host_revision: str | None,
) -> None:
    adopted = RoleCallRecord.model_validate(record.model_dump(mode="json"))
    provider_hash = _hash_ref(
        "provider-grant", host.provider_grant.model_dump(mode="json"), "1.0"
    )
    identity = {
        "adapter": (adapter, adopted.adapter),
        "provider": (provider, adopted.provider),
        "endpoint": (endpoint, adopted.endpoint),
        "model": (model, adopted.model),
        "model_revision": (model_revision, adopted.model_revision),
        "host_revision": (host_revision, adopted.host_revision),
        "provider_grant_hash": (provider_hash, adopted.provider_grant_hash),
    }
    if any(expected != observed for expected, observed in identity.values()):
        raise RoleHostProtocolError("adopted role-call record has a different provider identity")
    if adopted.role not in host._attempt_counts or adopted.role not in host.provider_grant.roles:
        raise RoleHostProtocolError("adopted role-call record names an ungranted role")
    existing = next((item for item in host.call_records if item.call_id == adopted.call_id), None)
    if existing is not None:
        if existing != adopted:
            raise RoleHostProtocolError("adopted role-call record conflicts with an existing call ID")
        return

    candidate_records = [*host.call_records, adopted]
    logical_counts = dict(host._attempt_counts)
    logical_counts[adopted.role] += 1
    semantic_calls = sum(value for role, value in logical_counts.items() if role != "proposer")
    if logical_counts["proposer"] > host.run_resource_grant.max_proposer_calls:
        raise RoleHostResourceExhausted("adopted proposer calls exceed the aggregate grant")
    if semantic_calls > host.run_resource_grant.max_assessor_calls:
        raise RoleHostResourceExhausted("adopted semantic-role calls exceed the aggregate grant")
    if sum(item.requests for item in candidate_records) > min(
        host.provider_grant.max_calls, host.run_resource_grant.max_model_requests
    ):
        raise RoleHostResourceExhausted("adopted model requests exceed the aggregate grant")
    totals = {
        "request bytes": sum(item.request_bytes for item in candidate_records),
        "response bytes": sum(item.response_bytes for item in candidate_records),
        "input tokens": sum(item.input_tokens for item in candidate_records),
        "output tokens": sum(item.output_tokens for item in candidate_records),
        "elapsed time": sum(item.elapsed_milliseconds for item in candidate_records),
    }
    limits = {
        "request bytes": host.run_resource_grant.max_request_bytes,
        "response bytes": host.run_resource_grant.max_response_bytes,
        "input tokens": host.run_resource_grant.max_input_tokens,
        "output tokens": host.run_resource_grant.max_output_tokens,
        "elapsed time": host.run_resource_grant.max_elapsed_seconds * 1000,
    }
    exceeded = [name for name in totals if totals[name] > limits[name]]
    if exceeded:
        raise RoleHostResourceExhausted(f"adopted role-call usage exceeds aggregate limits: {exceeded}")
    known_costs = [Decimal(item.cost_decimal) for item in candidate_records if item.cost_decimal is not None]
    if sum(known_costs, Decimal("0")) > min(
        Decimal(host.provider_grant.max_cost_decimal),
        Decimal(host.run_resource_grant.max_cost_decimal),
    ):
        raise RoleHostResourceExhausted("adopted role-call cost exceeds the aggregate grant")

    host.call_records.append(adopted)
    host._attempt_counts = logical_counts
    host._aggregate_request_bytes = totals["request bytes"]
    host._aggregate_response_bytes = totals["response bytes"]
    host._aggregate_elapsed_milliseconds = totals["elapsed time"]


class JsonLineTransport(Protocol):
    def exchange(self, request: bytes, timeout_seconds: float) -> bytes: ...


class StreamJsonLineTransport:
    """One bounded JSON-line exchange over explicit binary streams."""

    def __init__(self, input_stream: BinaryIO, output_stream: BinaryIO, *, max_response_bytes: int):
        self.input_stream = input_stream
        self.output_stream = output_stream
        self.max_response_bytes = max_response_bytes

    def exchange(self, request: bytes, timeout_seconds: float) -> bytes:
        self.output_stream.write(request)
        self.output_stream.flush()
        try:
            descriptor = self.input_stream.fileno()
        except (AttributeError, OSError) as exc:
            raise RoleHostProtocolError("JSON-line input stream has no selectable file descriptor") from exc
        ready, _, _ = select.select([descriptor], [], [], timeout_seconds)
        if not ready:
            raise RoleHostTimeout("JSON-line role response timed out")
        line = self.input_stream.readline(self.max_response_bytes + 1)
        if len(line) > self.max_response_bytes:
            raise RoleHostProtocolError("JSON-line role response exceeds its byte limit")
        return line


class JsonLineProposalRoleHost:
    """Instruction-only compatibility adapter that carries proposal schemas only."""

    def __init__(
        self,
        transport: JsonLineTransport,
        *,
        timeout_seconds: float,
        provider_grant: ProviderGrant,
        run_resource_grant: RunResourceGrant,
        cost_observer: Callable[[bytes, bytes, int], str] | None = None,
        now: Any | None = None,
    ):
        if timeout_seconds <= 0:
            raise ValueError("JSON-line timeout must be positive")
        if provider_grant.adapter != "json_line":
            raise ValueError("JSON-line host requires an explicit json_line provider grant")
        if provider_grant.cost_accounting == "unavailable":
            raise ValueError("JSON-line provider grant requires available cost accounting")
        if provider_grant.cost_accounting == "observed" and cost_observer is None:
            raise ValueError("observed JSON-line cost accounting requires an explicit observer")
        self.transport = transport
        self.timeout_seconds = min(timeout_seconds, provider_grant.max_seconds, run_resource_grant.max_elapsed_seconds)
        self.provider_grant = provider_grant
        self.run_resource_grant = run_resource_grant
        self.cost_observer = cost_observer
        self._now = now or (lambda: datetime.now(timezone.utc))
        self.call_records: list[RoleCallRecord] = []
        self._attempt_counts = {
            "plan_assessor": 0, "proposer": 0, "patch_assessor": 0, "verifier": 0,
            "policy_translator": 0,
        }
        self._aggregate_request_bytes = 0
        self._aggregate_response_bytes = 0
        self._aggregate_elapsed_milliseconds = 0
        self._last_attempt_elapsed_milliseconds = 0

    def adopt_call_record(self, record: RoleCallRecord) -> None:
        _adopt_prior_call_record(
            self,
            record,
            adapter="json_line",
            provider=self.provider_grant.provider,
            endpoint=self.provider_grant.endpoint,
            model=self.provider_grant.model,
            model_revision=self.provider_grant.model_revision,
            host_revision=self.provider_grant.host_revision,
        )

    def _record_failed_attempt(self, role: str, request: StrictModel, error: Exception) -> None:
        envelope = {
            "type": "role_request", "role": role, "adapter": "json_line",
            "payload": request.model_dump(mode="json"),
        }
        request_bytes = canonical_bytes(envelope) + b"\n"
        request_hash = hashlib.sha256(request_bytes).hexdigest()
        self.call_records.append(RoleCallRecord(
            schema_version="2.0", call_id=f"call-{request_hash[:20]}-failed-{len(self.call_records) + 1}",
            role=role, adapter="json_line", assurance_profile="instruction_only_proposal_host",
            provider_grant_hash=_hash_ref("provider-grant", self.provider_grant.model_dump(mode="json"), "1.0"),
            policy_binding=(request.context.policy_binding if hasattr(request, "context") else request.policy_binding),
            request_hash=request_hash, response_hash=None, outcome=_failure_outcome(error),
            usage_complete=False, provider=self.provider_grant.provider,
            endpoint=self.provider_grant.endpoint, model=self.provider_grant.model,
            model_revision=self.provider_grant.model_revision,
            host_revision=self.provider_grant.host_revision, requests=1, tool_calls=0,
            input_tokens=0, output_tokens=0, request_bytes=len(request_bytes), response_bytes=0,
            elapsed_milliseconds=self._last_attempt_elapsed_milliseconds, cost_decimal=None,
            cost_provenance="unavailable_after_failure",
        ))

    def _validate_grants(self, role: str, request_bytes: bytes) -> None:
        if any(not item.usage_complete for item in self.call_records):
            raise RoleHostResourceExhausted(
                "a prior failed JSON-line call has incomplete usage; a replacement grant and new host are required"
            )
        now = self._now()
        if isinstance(now, str):
            now = datetime.strptime(now, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        provider_expiry = datetime.strptime(self.provider_grant.expires_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        resource_expiry = datetime.strptime(self.run_resource_grant.expires_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        if now >= provider_expiry or now >= resource_expiry:
            raise RoleHostResourceExhausted("JSON-line provider or resource grant is expired")
        if role not in self.provider_grant.roles:
            raise RoleHostProtocolError(f"provider grant does not permit JSON-line role {role}")
        if len(request_bytes) > min(self.provider_grant.max_request_bytes, self.run_resource_grant.max_request_bytes):
            raise RoleHostResourceExhausted("JSON-line request exceeds the granted byte limit")
        used = self._attempt_counts[role]
        used_semantic = sum(
            count for name, count in self._attempt_counts.items() if name != "proposer"
        )
        limit = self.run_resource_grant.max_proposer_calls if role == "proposer" else self.run_resource_grant.max_assessor_calls
        if (
            used >= limit
            or (role != "proposer" and used_semantic >= self.run_resource_grant.max_assessor_calls)
            or sum(self._attempt_counts.values()) >= self.provider_grant.max_calls
            or sum(self._attempt_counts.values()) >= self.run_resource_grant.max_model_requests
        ):
            raise RoleHostResourceExhausted("JSON-line role-call grant is exhausted")
        if self._aggregate_request_bytes + len(request_bytes) > self.run_resource_grant.max_request_bytes:
            raise RoleHostResourceExhausted("aggregate JSON-line request-byte grant is exhausted")
        if self._aggregate_elapsed_milliseconds >= self.run_resource_grant.max_elapsed_seconds * 1000:
            raise RoleHostResourceExhausted("aggregate JSON-line elapsed-time grant is exhausted")

    def _exchange(self, role: str, request: StrictModel, output_type):
        envelope = {
            "type": "role_request",
            "role": role,
            "adapter": "json_line",
            "payload": request.model_dump(mode="json"),
        }
        request_bytes = canonical_bytes(envelope) + b"\n"
        self._validate_grants(role, request_bytes)
        self._attempt_counts[role] += 1
        self._aggregate_request_bytes += len(request_bytes)
        started = time.monotonic()
        try:
            try:
                response_bytes = self.transport.exchange(
                    request_bytes,
                    _remaining_elapsed_timeout(
                        configured_timeout_seconds=self.timeout_seconds,
                        aggregate_elapsed_milliseconds=self._aggregate_elapsed_milliseconds,
                        aggregate_limit_seconds=self.run_resource_grant.max_elapsed_seconds,
                    ),
                )
            finally:
                elapsed_ms = max(0, int((time.monotonic() - started) * 1000))
                self._last_attempt_elapsed_milliseconds = elapsed_ms
                self._aggregate_elapsed_milliseconds += elapsed_ms
        except TimeoutError as exc:
            raise RoleHostTimeout(f"{role} JSON-line response timed out") from exc
        if not response_bytes:
            raise RoleHostProtocolError(f"{role} response stream ended before a response")
        try:
            response = parse_json_strict(response_bytes)
        except Exception as exc:
            raise RoleHostProtocolError(f"{role} returned malformed JSON") from exc
        if not isinstance(response, dict) or set(response) != {"type", "role", "adapter", "payload"}:
            raise RoleHostProtocolError(f"{role} response envelope is malformed")
        if response["type"] != "role_response" or response["role"] != role or response["adapter"] != "json_line":
            raise RoleHostProtocolError(f"{role} response identity differs from the request")
        try:
            output = output_type.model_validate(response["payload"])
        except ValidationError as exc:
            raise RoleHostProtocolError(f"{role} returned a schema-invalid payload") from exc
        request_token = request.context.request_token if hasattr(request, "context") else request.request_token
        if output.request_token != request_token:
            raise RoleHostProtocolError(f"{role} response request token differs from the request")
        response_canonical = canonical_bytes(response)
        if self._aggregate_response_bytes + len(response_canonical) > self.run_resource_grant.max_response_bytes:
            raise RoleHostResourceExhausted("JSON-line response exceeds the run resource byte limit")
        self._aggregate_response_bytes += len(response_canonical)
        observed_usage = getattr(self.transport, "last_usage", None)
        observed_requests = getattr(observed_usage, "requests", 1)
        observed_tool_calls = getattr(observed_usage, "tool_calls", 0)
        observed_input_tokens = getattr(observed_usage, "input_tokens", 0)
        observed_output_tokens = getattr(observed_usage, "output_tokens", 0)
        if any(
            not isinstance(value, int) or value < 0
            for value in (
                observed_requests, observed_tool_calls,
                observed_input_tokens, observed_output_tokens,
            )
        ):
            raise RoleHostProtocolError("JSON-line transport returned malformed usage accounting")
        if observed_requests != 1 or observed_tool_calls != 0:
            raise RoleHostProtocolError("JSON-line transport used an unsupported request or tool count")
        if sum(item.input_tokens for item in self.call_records) + observed_input_tokens > min(
            self.provider_grant.max_input_tokens, self.run_resource_grant.max_input_tokens
        ):
            raise RoleHostResourceExhausted("aggregate JSON-line input-token grant is exhausted")
        if sum(item.output_tokens for item in self.call_records) + observed_output_tokens > min(
            self.provider_grant.max_output_tokens, self.run_resource_grant.max_output_tokens
        ):
            raise RoleHostResourceExhausted("aggregate JSON-line output-token grant is exhausted")
        request_hash = hashlib.sha256(request_bytes).hexdigest()
        response_hash = hashlib.sha256(response_canonical).hexdigest()
        cost_decimal = (
            "0" if self.provider_grant.cost_accounting == "declared_zero"
            else canonical_decimal(self.cost_observer(request_bytes, response_canonical, elapsed_ms))
        )
        known_costs = [Decimal(item.cost_decimal) for item in self.call_records if item.cost_decimal is not None]
        if any(item.cost_decimal is None for item in self.call_records):
            raise RoleHostResourceExhausted("prior failed JSON-line call has unknown cost")
        total_cost = sum(known_costs, Decimal("0")) + Decimal(cost_decimal)
        if total_cost > min(Decimal(self.provider_grant.max_cost_decimal), Decimal(self.run_resource_grant.max_cost_decimal)):
            raise RoleHostResourceExhausted("aggregate JSON-line cost grant is exhausted")
        self.call_records.append(RoleCallRecord(
            schema_version="2.0", call_id=f"call-{request_hash[:24]}", role=role,
            adapter="json_line", assurance_profile="instruction_only_proposal_host",
            provider_grant_hash=_hash_ref(
                "provider-grant", self.provider_grant.model_dump(mode="json"), "1.0"
            ),
            policy_binding=(request.context.policy_binding if hasattr(request, "context") else request.policy_binding),
            request_hash=request_hash, response_hash=response_hash,
            outcome="success", usage_complete=True,
            provider=self.provider_grant.provider, endpoint=self.provider_grant.endpoint,
            model=self.provider_grant.model, model_revision=self.provider_grant.model_revision,
            host_revision=self.provider_grant.host_revision,
            requests=observed_requests, tool_calls=observed_tool_calls,
            input_tokens=observed_input_tokens, output_tokens=observed_output_tokens,
            request_bytes=len(request_bytes), response_bytes=len(response_canonical),
            elapsed_milliseconds=elapsed_ms,
            cost_decimal=cost_decimal,
            cost_provenance=(
                "provider_declared_zero"
                if self.provider_grant.cost_accounting == "declared_zero" else "adapter_observed"
            ),
        ))
        return output

    def propose_patch(
        self,
        request: ProposalRequest,
        read_file: Callable[[str, int, int | None], ReadToolResult] | None = None,
    ) -> AgentPatchProposal:
        if request.context.adapter != "json_line" or request.operation.required_adapter != "json_line":
            raise RoleHostProtocolError("JSON-line proposer received a request for another adapter")
        if read_file is not None or request.operation.allowed_read_tools:
            raise RoleHostProtocolError(
                "JSON-line compatibility hosts do not support interactive read tools; supply an exact source bundle"
            )
        before = self._attempt_counts["proposer"]
        try:
            return self._exchange("proposer", request, AgentPatchProposal)
        except Exception as exc:
            if self._attempt_counts["proposer"] > before:
                self._record_failed_attempt("proposer", request, exc)
            raise

    def assess_patch(self, request: PatchAssessmentRequest) -> PatchSemanticAssessmentProposal:
        if request.context.adapter != "json_line" or request.operation.required_adapter != "json_line":
            raise RoleHostProtocolError("JSON-line assessor received a request for another adapter")
        before = self._attempt_counts["patch_assessor"]
        try:
            return self._exchange("patch_assessor", request, PatchSemanticAssessmentProposal)
        except Exception as exc:
            if self._attempt_counts["patch_assessor"] > before:
                self._record_failed_attempt("patch_assessor", request, exc)
            raise

    def assess_plan(self, request: PlanAssessmentRequest) -> PlanAssessmentResponse:
        if request.context.adapter != "json_line":
            raise RoleHostProtocolError("JSON-line plan assessor received a request for another adapter")
        before = self._attempt_counts["plan_assessor"]
        try:
            return self._exchange("plan_assessor", request, PlanAssessmentResponse)
        except Exception as exc:
            if self._attempt_counts["plan_assessor"] > before:
                self._record_failed_attempt("plan_assessor", request, exc)
            raise

    def verify(self, request: VerificationRoleRequest) -> VerificationRoleResponse:
        if request.context.adapter != "json_line":
            raise RoleHostProtocolError("JSON-line verifier received a request for another adapter")
        before = self._attempt_counts["verifier"]
        try:
            return self._exchange("verifier", request, VerificationRoleResponse)
        except Exception as exc:
            if self._attempt_counts["verifier"] > before:
                self._record_failed_attempt("verifier", request, exc)
            raise

    def translate_policy(self, request: PolicyTranslationRequest) -> ProjectPolicyProposal:
        if request.adapter != "json_line" or request.assurance_profile != "instruction_only_authoring":
            raise RoleHostProtocolError("JSON-line policy translator requires its explicit instruction-only profile")
        before = self._attempt_counts["policy_translator"]
        try:
            return self._exchange("policy_translator", request, ProjectPolicyProposal)
        except Exception as exc:
            if self._attempt_counts["policy_translator"] > before:
                self._record_failed_attempt("policy_translator", request, exc)
            raise


OutputT = TypeVar(
    "OutputT", AgentPatchProposal, PatchSemanticAssessmentProposal,
    PlanAssessmentResponse, VerificationRoleResponse, ProjectPolicyProposal,
)


class PydanticAIProposalRoleHost:
    """PydanticAI adapter with typed output and no allocated function or native tools."""

    def __init__(
        self,
        *,
        model: Model,
        provider_grant: ProviderGrant,
        run_resource_grant: RunResourceGrant,
        observed_provider: str,
        observed_endpoint: str,
        observed_credential_audience: str,
        observed_model_revision: str | None,
        cost_observer: Callable[[Any], str] | None = None,
        now: Any | None = None,
    ):
        if provider_grant.adapter != "pydantic_ai":
            raise ValueError("PydanticAI host requires a pydantic_ai provider grant")
        if provider_grant.cost_accounting == "unavailable":
            raise ValueError("PydanticAI provider grant requires available cost accounting")
        if provider_grant.cost_accounting == "observed" and cost_observer is None:
            raise ValueError("observed PydanticAI cost accounting requires an explicit observer")
        if provider_grant.structured_output_mode != "tool":
            raise ValueError("PydanticAI proposal roles require tool-mode structured output")
        if provider_grant.redirect_endpoints:
            raise ValueError("first-release PydanticAI transport does not permit redirect endpoints")
        observed_model = model.model_name
        mismatches = {
            "provider": (provider_grant.provider, observed_provider),
            "endpoint": (provider_grant.endpoint, observed_endpoint),
            "model": (provider_grant.model, observed_model),
            "credential_audience": (provider_grant.credential_audience, observed_credential_audience),
            "model_revision": (provider_grant.model_revision, observed_model_revision),
        }
        differences = {field: values for field, values in mismatches.items() if values[0] != values[1]}
        if differences:
            raise ValueError(f"PydanticAI observed provider identity differs from the grant: {sorted(differences)}")
        self.model = model
        self.provider_grant = provider_grant
        self.run_resource_grant = run_resource_grant
        self.observed_provider = observed_provider
        self.observed_endpoint = observed_endpoint
        self.observed_credential_audience = observed_credential_audience
        self.observed_model_revision = observed_model_revision
        self.cost_observer = cost_observer
        self._now = now or (lambda: datetime.now(timezone.utc))
        self.call_records: list[RoleCallRecord] = []
        self._attempt_counts = {
            "plan_assessor": 0, "proposer": 0, "patch_assessor": 0, "verifier": 0,
            "policy_translator": 0,
        }
        self._aggregate_request_bytes = 0
        self._aggregate_response_bytes = 0
        self._aggregate_elapsed_milliseconds = 0
        self._last_attempt_elapsed_milliseconds = 0
        self._read_results: dict[str, list[ReadToolResult]] = {}

    def adopt_call_record(self, record: RoleCallRecord) -> None:
        _adopt_prior_call_record(
            self,
            record,
            adapter="pydantic_ai",
            provider=self.observed_provider,
            endpoint=self.observed_endpoint,
            model=self.model.model_name,
            model_revision=self.observed_model_revision,
            host_revision=self.provider_grant.host_revision,
        )

    def _record_failed_attempt(self, role: str, request: StrictModel, error: Exception) -> None:
        request_bytes = canonical_bytes(request.model_dump(mode="json"))
        request_hash = hashlib.sha256(request_bytes).hexdigest()
        self.call_records.append(RoleCallRecord(
            schema_version="2.0", call_id=f"call-{request_hash[:20]}-failed-{len(self.call_records) + 1}",
            role=role, adapter="pydantic_ai", assurance_profile=(
                "framework_tool_enforced_proposer" if role == "proposer" else "framework_tool_enforced_no_tools"
            ),
            provider_grant_hash=_hash_ref("provider-grant", self.provider_grant.model_dump(mode="json"), "1.0"),
            policy_binding=(request.context.policy_binding if hasattr(request, "context") else request.policy_binding),
            request_hash=request_hash, response_hash=None, outcome=_failure_outcome(error),
            usage_complete=False, provider=self.observed_provider, endpoint=self.observed_endpoint,
            model=self.model.model_name, model_revision=self.provider_grant.model_revision,
            host_revision=self.provider_grant.host_revision,
            requests=0, tool_calls=0, input_tokens=0, output_tokens=0,
            request_bytes=len(request_bytes), response_bytes=0,
            elapsed_milliseconds=self._last_attempt_elapsed_milliseconds,
            cost_decimal=None, cost_provenance="unavailable_after_failure",
        ))

    def _current_time(self) -> datetime:
        value = self._now()
        if isinstance(value, str):
            return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        if not isinstance(value, datetime):
            raise RoleHostProtocolError("provider clock returned an unsupported value")
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)

    def _validate_grants(self, role: str, request_bytes: bytes) -> None:
        if any(not item.usage_complete for item in self.call_records):
            raise RoleHostResourceExhausted(
                "a prior failed provider call has incomplete usage; a replacement grant and new host are required"
            )
        now = self._current_time()
        provider_expiry = datetime.strptime(self.provider_grant.expires_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        resource_expiry = datetime.strptime(self.run_resource_grant.expires_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        if now >= provider_expiry or now >= resource_expiry:
            raise RoleHostResourceExhausted("provider or run resource grant is expired")
        if role not in self.provider_grant.roles:
            raise RoleHostProtocolError(f"provider grant does not permit role {role}")
        if len(request_bytes) > min(self.provider_grant.max_request_bytes, self.run_resource_grant.max_request_bytes):
            raise RoleHostResourceExhausted("role request exceeds the granted byte limit")
        proposer_calls = self._attempt_counts["proposer"]
        assessor_calls = sum(
            count for name, count in self._attempt_counts.items() if name != "proposer"
        )
        if role == "proposer" and proposer_calls >= self.run_resource_grant.max_proposer_calls:
            raise RoleHostResourceExhausted("proposer call grant is exhausted")
        if role != "proposer" and assessor_calls >= self.run_resource_grant.max_assessor_calls:
            raise RoleHostResourceExhausted("semantic-role call grant is exhausted")
        used_requests = sum(item.requests for item in self.call_records)
        if used_requests >= min(self.provider_grant.max_calls, self.run_resource_grant.max_model_requests):
            raise RoleHostResourceExhausted("provider model-request grant is exhausted")
        if self._aggregate_request_bytes + len(request_bytes) > self.run_resource_grant.max_request_bytes:
            raise RoleHostResourceExhausted("aggregate PydanticAI request-byte grant is exhausted")
        if self._aggregate_elapsed_milliseconds >= self.run_resource_grant.max_elapsed_seconds * 1000:
            raise RoleHostResourceExhausted("aggregate PydanticAI elapsed-time grant is exhausted")

    async def _run_agent(
        self,
        agent: Agent[Any, OutputT],
        prompt: str,
        *,
        tool_calls_limit: int,
        request_limit: int,
        timeout_seconds: float,
    ):
        try:
            return await asyncio.wait_for(
                agent.run(
                    prompt,
                    usage_limits=UsageLimits(
                        request_limit=request_limit,
                        tool_calls_limit=tool_calls_limit,
                        input_tokens_limit=min(
                            self.provider_grant.max_input_tokens, self.run_resource_grant.max_input_tokens
                        ),
                        output_tokens_limit=min(
                            self.provider_grant.max_output_tokens, self.run_resource_grant.max_output_tokens
                        ),
                    ),
                ),
                timeout=timeout_seconds,
            )
        except (TimeoutError, asyncio.TimeoutError) as exc:
            raise RoleHostTimeout("PydanticAI role call timed out and was cancelled") from exc
        except UsageLimitExceeded as exc:
            raise RoleHostResourceExhausted("PydanticAI usage limit was exhausted") from exc

    def _invoke(
        self,
        role: str,
        request: StrictModel,
        output_type: type[OutputT],
        read_file: Callable[[str, int, int | None], ReadToolResult] | None = None,
    ) -> OutputT:
        request_adapter = request.context.adapter if hasattr(request, "context") else request.adapter
        if request_adapter != "pydantic_ai":
            raise RoleHostProtocolError("PydanticAI host received a request for another adapter")
        operation = getattr(request, "operation", None)
        if operation is not None and operation.required_adapter != "pydantic_ai":
            raise RoleHostProtocolError("PydanticAI host received an operation for another adapter")
        request_payload = request.model_dump(mode="json")
        request_bytes = canonical_bytes(request_payload)
        self._validate_grants(role, request_bytes)
        self._attempt_counts[role] += 1
        self._aggregate_request_bytes += len(request_bytes)
        if role == "proposer" and read_file is not None:
            instructions = (
                "Return only the strict typed patch proposal. You may use only the allocated read_file "
                "tool and cannot apply changes."
            )
        elif role == "proposer":
            instructions = "Return only the strict typed patch proposal. You have no tools and cannot apply changes."
        elif role == "patch_assessor":
            instructions = "Assess the exact proposed patch and return only the strict typed assessment. You have no tools."
        elif role == "plan_assessor":
            instructions = "Assess the complete plan packet and return only the strict typed plan assessment response. You have no tools."
        elif role == "policy_translator":
            instructions = (
                "Translate only the bounded user restriction into the strict typed policy proposal. "
                "Use only named paths, preserve current restrictions, report ambiguity, and observe no protected content. "
                "You have no tools and no persistence authority."
            )
        else:
            instructions = "Verify only the complete supplied static file-state packet and return the strict typed verifier response. You have no tools."
        tools: tuple[Any, ...] = ()
        if role == "proposer" and read_file is not None:
            if "read_file" not in request.operation.allowed_read_tools:
                raise RoleHostProtocolError("runtime attempted to allocate an unapproved read tool")

            def bounded_read_file(path: str, byte_start: int = 0, byte_end: int | None = None) -> dict[str, Any]:
                """Read an approved UTF-8 byte range through the coordinator."""

                result = ReadToolResult.model_validate(read_file(path, byte_start, byte_end))
                if result.request_token != request.context.request_token:
                    raise RoleHostProtocolError("mediated read result has the wrong request token")
                self._read_results.setdefault(request.context.request_token, []).append(result)
                return result.model_dump(mode="json")

            tools = (Tool(bounded_read_file, name="read_file"),)
        elif read_file is not None:
            raise RoleHostProtocolError("only the proposer may receive the bounded read tool")

        agent: Agent[Any, OutputT] = Agent(
            self.model,
            output_type=output_type,
            instructions=instructions,
            tools=tools,
            toolsets=(),
            capabilities=(),
            retries=0,
            model_settings={
                "temperature": float(Decimal(self.provider_grant.temperature_decimal)),
                "seed": self.provider_grant.seed,
                "parallel_tool_calls": False,
                "openai_store": False,
                "openai_native_tools": (),
            },
        )
        prompt = canonical_bytes({"role": role, "request": request_payload}).decode("utf-8")
        started = time.monotonic()
        try:
            try:
                asyncio.get_running_loop()
            except RuntimeError:
                result = asyncio.run(self._run_agent(
                    agent, prompt,
                    tool_calls_limit=(
                        self.run_resource_grant.max_read_tool_calls
                        if role == "proposer" and read_file is not None else 0
                    ),
                    request_limit=max(
                        1,
                        min(self.provider_grant.max_calls, self.run_resource_grant.max_model_requests)
                        - sum(item.requests for item in self.call_records),
                    ),
                    timeout_seconds=_remaining_elapsed_timeout(
                        configured_timeout_seconds=min(
                            self.provider_grant.max_seconds,
                            self.run_resource_grant.max_elapsed_seconds,
                        ),
                        aggregate_elapsed_milliseconds=self._aggregate_elapsed_milliseconds,
                        aggregate_limit_seconds=self.run_resource_grant.max_elapsed_seconds,
                    ),
                ))
            else:
                raise RoleHostProtocolError("synchronous PydanticAI role host cannot run inside an active event loop")
        finally:
            elapsed_attempt = max(0, int((time.monotonic() - started) * 1000))
            self._last_attempt_elapsed_milliseconds = elapsed_attempt
            self._aggregate_elapsed_milliseconds += elapsed_attempt
        output = output_type.model_validate(result.output.model_dump(mode="json"))
        request_token = request.context.request_token if hasattr(request, "context") else request.request_token
        if output.request_token != request_token:
            raise RoleHostProtocolError(f"{role} response request token differs from the request")
        response_bytes = canonical_bytes(output.model_dump(mode="json"))
        if self._aggregate_response_bytes + len(response_bytes) > self.run_resource_grant.max_response_bytes:
            raise RoleHostResourceExhausted("role response exceeds the granted byte limit")
        self._aggregate_response_bytes += len(response_bytes)
        elapsed_ms = max(0, int((time.monotonic() - started) * 1000))
        usage = result.usage
        total_requests = sum(item.requests for item in self.call_records) + usage.requests
        if total_requests > min(self.provider_grant.max_calls, self.run_resource_grant.max_model_requests):
            raise RoleHostResourceExhausted("aggregate provider model-request grant is exhausted")
        total_input = sum(item.input_tokens for item in self.call_records) + usage.input_tokens
        total_output = sum(item.output_tokens for item in self.call_records) + usage.output_tokens
        total_elapsed = self._aggregate_elapsed_milliseconds
        if total_input > self.run_resource_grant.max_input_tokens:
            raise RoleHostResourceExhausted("aggregate input-token grant is exhausted")
        if total_output > self.run_resource_grant.max_output_tokens:
            raise RoleHostResourceExhausted("aggregate output-token grant is exhausted")
        if total_elapsed > self.run_resource_grant.max_elapsed_seconds * 1000:
            raise RoleHostResourceExhausted("aggregate elapsed-time grant is exhausted")
        cost_decimal = (
            "0" if self.provider_grant.cost_accounting == "declared_zero"
            else canonical_decimal(self.cost_observer(usage))
        )
        known_costs = [Decimal(item.cost_decimal) for item in self.call_records if item.cost_decimal is not None]
        if any(item.cost_decimal is None for item in self.call_records):
            raise RoleHostResourceExhausted("prior failed provider call has unknown cost")
        total_cost = sum(known_costs, Decimal("0")) + Decimal(cost_decimal)
        if total_cost > min(Decimal(self.provider_grant.max_cost_decimal), Decimal(self.run_resource_grant.max_cost_decimal)):
            raise RoleHostResourceExhausted("aggregate provider cost grant is exhausted")
        request_hash = hashlib.sha256(request_bytes).hexdigest()
        response_hash = hashlib.sha256(response_bytes).hexdigest()
        record = RoleCallRecord(
            schema_version="2.0",
            call_id=f"call-{request_hash[:24]}",
            role=role,
            adapter="pydantic_ai",
            assurance_profile=(
                "framework_tool_enforced_proposer" if role == "proposer" else "framework_tool_enforced_no_tools"
            ),
            provider_grant_hash=_hash_ref(
                "provider-grant", self.provider_grant.model_dump(mode="json"), "1.0"
            ),
            policy_binding=(request.context.policy_binding if hasattr(request, "context") else request.policy_binding),
            request_hash=request_hash,
            response_hash=response_hash,
            outcome="success",
            usage_complete=True,
            provider=self.observed_provider,
            endpoint=self.observed_endpoint,
            model=self.model.model_name,
            model_revision=self.provider_grant.model_revision,
            host_revision=self.provider_grant.host_revision,
            requests=usage.requests,
            tool_calls=usage.tool_calls,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            request_bytes=len(request_bytes),
            response_bytes=len(response_bytes),
            elapsed_milliseconds=elapsed_ms,
            cost_decimal=cost_decimal,
            cost_provenance=(
                "provider_declared_zero"
                if self.provider_grant.cost_accounting == "declared_zero" else "adapter_observed"
            ),
        )
        self.call_records.append(record)
        return output

    def propose_patch(
        self,
        request: ProposalRequest,
        read_file: Callable[[str, int, int | None], ReadToolResult] | None = None,
    ) -> AgentPatchProposal:
        before = self._attempt_counts["proposer"]
        try:
            return self._invoke("proposer", request, AgentPatchProposal, read_file=read_file)
        except Exception as exc:
            if self._attempt_counts["proposer"] > before:
                self._record_failed_attempt("proposer", request, exc)
            raise

    def assess_patch(self, request: PatchAssessmentRequest) -> PatchSemanticAssessmentProposal:
        before = self._attempt_counts["patch_assessor"]
        try:
            return self._invoke("patch_assessor", request, PatchSemanticAssessmentProposal)
        except Exception as exc:
            if self._attempt_counts["patch_assessor"] > before:
                self._record_failed_attempt("patch_assessor", request, exc)
            raise

    def assess_plan(self, request: PlanAssessmentRequest) -> PlanAssessmentResponse:
        before = self._attempt_counts["plan_assessor"]
        try:
            return self._invoke("plan_assessor", request, PlanAssessmentResponse)
        except Exception as exc:
            if self._attempt_counts["plan_assessor"] > before:
                self._record_failed_attempt("plan_assessor", request, exc)
            raise

    def verify(self, request: VerificationRoleRequest) -> VerificationRoleResponse:
        before = self._attempt_counts["verifier"]
        try:
            return self._invoke("verifier", request, VerificationRoleResponse)
        except Exception as exc:
            if self._attempt_counts["verifier"] > before:
                self._record_failed_attempt("verifier", request, exc)
            raise

    def translate_policy(self, request: PolicyTranslationRequest) -> ProjectPolicyProposal:
        if request.adapter != "pydantic_ai" or request.assurance_profile != "framework_tool_enforced_authoring":
            raise RoleHostProtocolError("PydanticAI policy translator requires its framework no-tool profile")
        before = self._attempt_counts["policy_translator"]
        try:
            return self._invoke("policy_translator", request, ProjectPolicyProposal)
        except Exception as exc:
            if self._attempt_counts["policy_translator"] > before:
                self._record_failed_attempt("policy_translator", request, exc)
            raise

    def drain_read_results(self, request_token: str) -> list[ReadToolResult]:
        """Return and clear the typed reads produced by one completed proposer call."""

        return self._read_results.pop(request_token, [])
