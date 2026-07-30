from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import stat
import subprocess
import tempfile
from typing import Any, Callable, Literal

from pydantic import ValidationError

from .canonical import artifact_hash, canonical_bytes, parse_json_strict
from .models import EvidenceRef, Finding, INVARIANT_IDS, SafeIdentifier, StrictModel
from .policy_models import ProjectPolicyProposal
from .proposal_models import (
    AgentPatchProposal,
    PatchSemanticAssessmentProposal,
    PlanAssessmentResponse,
    VerificationRoleResponse,
)


REVIEWED_CODEX_CLI_VERSION = "0.146.0-alpha.3.1"
REVIEWED_CODEX_MODEL = "gpt-5.6-sol"
REVIEWED_CODEX_REASONING_EFFORT = "low"
REVIEWED_CODEX_EXECUTABLE = "/Applications/ChatGPT.app/Contents/Resources/codex"

_ROLE_OUTPUTS = {
    "plan_assessor": PlanAssessmentResponse,
    "proposer": AgentPatchProposal,
    "patch_assessor": PatchSemanticAssessmentProposal,
    "verifier": VerificationRoleResponse,
    "policy_translator": ProjectPolicyProposal,
}


class _CodexVerificationDecision(StrictModel):
    """Semantic verifier output before coordinator-owned identities are attached."""

    schema_version: Literal["1.0"]
    success_criteria_met: list[str]
    verifier_checks_passed: list[str]
    observed_effect_ids: list[SafeIdentifier]
    evidence: list[EvidenceRef]
    criterion_evidence: dict[str, list[SafeIdentifier]]
    check_evidence: dict[str, list[SafeIdentifier]]
    effect_evidence: dict[SafeIdentifier, list[SafeIdentifier]]
    findings: list[Finding]


def _artifact_ref(artifact_type: str, schema_version: str, payload: Any) -> dict[str, str]:
    return {
        "algorithm": "sha256",
        "artifact_type": artifact_type,
        "schema_version": schema_version,
        "value": artifact_hash(artifact_type, schema_version, payload),
    }


def _materialize_verifier_response(
    payload: dict[str, Any],
    decision: _CodexVerificationDecision,
) -> VerificationRoleResponse:
    """Attach deterministic request identities to one semantic verifier decision."""

    semantic = decision.model_dump(mode="json", exclude={"schema_version"})
    return VerificationRoleResponse.model_validate({
        "schema_version": "1.0",
        "request_token": payload["context"]["request_token"],
        "verification_proposal": {
            "schema_version": "3.0",
            "plan_hash": _artifact_ref("low-level-plan", "3.0", payload["plan"]),
            "assessment_hash": _artifact_ref("assessment", "3.0", payload["assessment"]),
            "snapshot_hash": _artifact_ref(
                "repository-snapshot", "3.0", payload["post_execution_snapshot"]
            ),
            "verifier_context_id": payload["verifier_context_id"],
            "proposal_hashes": [
                _artifact_ref("bounded-patch-proposal", "2.0", item)
                for item in payload["proposals"]
            ],
            "patch_assessment_hashes": [
                _artifact_ref("patch-assessment", "2.0", item)
                for item in payload["patch_assessments"]
            ],
            "execution_report_hashes": [
                _artifact_ref("execution-report", "3.0", item)
                for item in payload["execution_reports"]
            ],
            "policy_binding": payload["plan"]["policy_binding"],
            **semantic,
        },
    })
_DISABLED_CAPABILITIES = (
    "shell_tool",
    "unified_exec",
    "code_mode_host",
    "apps",
    "auth_elicitation",
    "computer_use",
    "browser_use",
    "goals",
    "hooks",
    "image_generation",
    "in_app_browser",
    "memories",
    "multi_agent",
    "personality",
    "plugin_sharing",
    "plugins",
    "remote_plugin",
    "request_permissions_tool",
    "shell_snapshot",
    "skill_mcp_dependency_install",
    "skill_search",
    "tool_call_mcp_elicitation",
    "tool_suggest",
    "workspace_dependencies",
)
_ROLE_CONTRACTS = {
    "proposer": (
        "Copy request_token, operation_id, and attempt_id exactly from the request. "
        "unified_diff must begin with either '--- ' or 'diff --git '. For every created file, "
        "use an exact standard section beginning '--- /dev/null', then '+++ b/<normalized-relative-path>', "
        "then a valid '@@ -0,0 +1,<line-count> @@' hunk whose content lines all begin with '+'. "
        "In unified_diff, every --- and +++ path after a/ or b/ must be a normalized path relative "
        "to the one declared working directory; never put an absolute path in a diff header. "
        "In claimed_created_paths, claimed_modified_paths, and claimed_deleted_paths, use the "
        "corresponding absolute declared target paths. Keep those three lists disjoint. "
        "Copy every request.operation.effects[].effect_id into claimed_effect_ids exactly, "
        "including repository-read effects that do not appear as diff actions. "
        "Set no_other_changes true. Use an empty evidence list unless the request requires evidence; "
        "if evidence is present, every item must use provenance agent_reported and locator "
        "agent-report:<the same evidence_id>."
    ),
    "patch_assessor": (
        "Copy request_token, proposal_hash, and policy_binding exactly. Cover every proposed path "
        "and effect ID. Set semantic_pass true only when findings is empty and there are no "
        "uncontrolled detrimental side effects."
    ),
    "plan_assessor": (
        "Copy request_token, plan, preflight, policy, snapshot, and policy-binding identities exactly. "
        "The nested semantic proposal must cover every required plan evidence item and report every "
        "safety or detrimental-side-effect finding without changing any supplied binding. Set "
        "required_role_assurance_profiles from bounded_agent_task operations only; it is empty for "
        "an exact-only plan. An operation's allowed_read_tools governs proposer interactive reads. "
        "Its read_roots must cover every deliberately selected source file supplied by the coordinator, "
        "as well as any permitted interactive reads. Separated static verification is coordinator-owned: it observes the "
        "snapshot selected_file_hashes and expected_product_changes under the active project policy, "
        "and does not require the new product targets to be proposer read roots. Do not report missing "
        "target-file read authority for a create-only plan whose selected source packet is covered and "
        "whose verifier can observe its declared postimages."
    ),
    "verifier": (
        "Return only the semantic verification decision. The transport attaches the immutable "
        "request, plan, assessment, post-execution snapshot, proposal-cycle, context, and policy "
        "identities deterministically. Evaluate only the supplied static file-state packet and cover "
        "every named criterion, check, and expected effect. Every evidence item must use provenance "
        "agent_reported and locator agent-report:<the same evidence_id>."
    ),
    "policy_translator": (
        "Copy request_token exactly. Use only named project-relative paths, preserve existing "
        "restrictions, report ambiguity explicitly, and set no_protected_content_observed true."
    ),
}


def _resolve_local_ref(root: dict[str, Any], ref: str) -> dict[str, Any]:
    if not ref.startswith("#/"):
        raise ValueError(f"unsupported non-local JSON Schema reference: {ref!r}")
    current: Any = root
    for component in ref[2:].split("/"):
        if not isinstance(current, dict) or component not in current:
            raise ValueError(f"unresolvable JSON Schema reference: {ref!r}")
        current = current[component]
    if not isinstance(current, dict):
        raise ValueError(f"JSON Schema reference does not resolve to an object: {ref!r}")
    return current


def _make_strict_output_schema(
    schema: dict[str, Any],
    *,
    root: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Convert a fresh Pydantic schema to the strict object form Codex accepts."""

    if root is None:
        root = schema
    for definitions_key in ("$defs", "definitions"):
        definitions = schema.get(definitions_key)
        if isinstance(definitions, dict):
            for definition in definitions.values():
                if not isinstance(definition, dict):
                    raise ValueError("JSON Schema definitions must be objects")
                _make_strict_output_schema(definition, root=root)
    if schema.get("type") == "object" and "additionalProperties" not in schema:
        schema["additionalProperties"] = False
    properties = schema.get("properties")
    if isinstance(properties, dict):
        schema["required"] = list(properties)
        for property_name, property_schema in properties.items():
            if not isinstance(property_schema, dict):
                raise ValueError("JSON Schema properties must be objects")
            if property_name == "invariant_id":
                property_schema["enum"] = sorted(INVARIANT_IDS)
            _make_strict_output_schema(property_schema, root=root)
    items = schema.get("items")
    if isinstance(items, dict):
        _make_strict_output_schema(items, root=root)
    for union_key in ("anyOf", "oneOf", "allOf"):
        alternatives = schema.get(union_key)
        if isinstance(alternatives, list):
            for alternative in alternatives:
                if not isinstance(alternative, dict):
                    raise ValueError("JSON Schema alternatives must be objects")
                _make_strict_output_schema(alternative, root=root)
    if schema.get("default", object()) is None:
        schema.pop("default")
    ref = schema.get("$ref")
    if isinstance(ref, str) and len(schema) > 1:
        resolved = _resolve_local_ref(root, ref)
        merged = {**resolved, **schema}
        merged.pop("$ref", None)
        schema.clear()
        schema.update(merged)
        return _make_strict_output_schema(schema, root=root)
    return schema


def _closed_evidence_map(keys: list[str]) -> dict[str, Any]:
    if len(keys) != len(set(keys)):
        raise CodexCliProtocolError("verifier request contains duplicate evidence-map keys")
    return {
        "type": "object",
        "properties": {
            key: {
                "type": "array",
                "items": {
                    "type": "string",
                    "pattern": r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$",
                },
            }
            for key in keys
        },
        "required": list(keys),
        "additionalProperties": False,
    }


def _output_schema_for_role(
    role: str,
    output_type: type[Any],
    payload: dict[str, Any],
) -> dict[str, Any]:
    model_output_type = _CodexVerificationDecision if role == "verifier" else output_type
    schema = _make_strict_output_schema(model_output_type.model_json_schema())
    if role == "plan_assessor":
        operations = payload.get("plan", {}).get("operations")
        if not isinstance(operations, list):
            raise CodexCliProtocolError("plan assessor request lacks its operation list")
        required_profiles = sorted({
            operation["required_assurance_profile"]
            for operation in operations
            if isinstance(operation, dict)
            and operation.get("kind") == "bounded_agent_task"
            and isinstance(operation.get("required_assurance_profile"), str)
        })
        definitions = schema.get("$defs")
        semantic = (
            definitions.get("SemanticAssessmentProposalV2")
            if isinstance(definitions, dict) else None
        )
        semantic_properties = semantic.get("properties") if isinstance(semantic, dict) else None
        if not isinstance(semantic_properties, dict):
            raise CodexCliProtocolError("plan assessor output schema lacks its semantic proposal")
        semantic_properties["required_role_assurance_profiles"] = {
            "type": "array",
            "items": (
                {"type": "string", "enum": required_profiles}
                if required_profiles else {"type": "string"}
            ),
            "minItems": len(required_profiles),
            "maxItems": len(required_profiles),
        }
    if role in {"plan_assessor", "patch_assessor", "verifier"}:
        definitions = schema.get("$defs")
        finding = definitions.get("Finding") if isinstance(definitions, dict) else None
        finding_properties = finding.get("properties") if isinstance(finding, dict) else None
        if not isinstance(finding_properties, dict):
            raise CodexCliProtocolError("semantic output schema lacks its finding definition")
        finding_properties["finding_provenance"] = {
            "type": "string",
            "const": "agent_reported",
        }
    if role in {"proposer", "verifier"}:
        definitions = schema.get("$defs")
        evidence = definitions.get("EvidenceRef") if isinstance(definitions, dict) else None
        evidence_properties = evidence.get("properties") if isinstance(evidence, dict) else None
        if not isinstance(evidence_properties, dict):
            raise CodexCliProtocolError("semantic output schema lacks its evidence definition")
        evidence_properties["provenance"] = {
            "type": "string",
            "const": "agent_reported",
        }
        evidence_properties["locator"] = {
            "type": "string",
            "pattern": r"^agent-report:[A-Za-z0-9][A-Za-z0-9._-]{0,127}$",
        }
    if role != "verifier":
        return schema
    properties = schema.get("properties")
    if not isinstance(properties, dict):
        raise CodexCliProtocolError("verifier output schema lacks its semantic decision fields")
    bindings = {
        "criterion_evidence": payload.get("expected_success_criteria"),
        "check_evidence": payload.get("expected_verifier_checks"),
        "effect_evidence": payload.get("expected_effect_ids"),
    }
    for field, keys in bindings.items():
        if not isinstance(keys, list) or any(not isinstance(key, str) for key in keys):
            raise CodexCliProtocolError("verifier request has malformed expected evidence keys")
        properties[field] = _closed_evidence_map(keys)
    return schema


class CodexCliProtocolError(RuntimeError):
    """The Codex subprocess identity, event stream, or result was not acceptable."""


@dataclass(frozen=True)
class CodexCliUsage:
    requests: int = 0
    tool_calls: int = 0
    input_tokens: int = 0
    cached_input_tokens: int = 0
    output_tokens: int = 0
    reasoning_output_tokens: int = 0


class CodexCliTransport:
    """One tool-disabled, schema-constrained Codex CLI exchange.

    The caller supplies the complete semantic packet. Codex runs ephemerally in a
    fresh temporary directory and cannot authoritatively change runner state.
    """

    def __init__(
        self,
        *,
        cli_path: str,
        model: str,
        expected_cli_version: str,
        max_response_bytes: int,
        runner: Callable[..., subprocess.CompletedProcess[bytes]] = subprocess.run,
    ) -> None:
        source = Path(cli_path)
        if not source.is_absolute() or source.is_symlink():
            raise ValueError("Codex CLI path must name an absolute regular non-symbolic-link executable")
        observed, executable_sha256 = self._executable_identity(source)
        if not stat.S_ISREG(observed.st_mode) or observed.st_mode & 0o111 == 0:
            raise ValueError("Codex CLI path must name an absolute regular non-symbolic-link executable")
        if model != REVIEWED_CODEX_MODEL:
            raise ValueError("Codex CLI model differs from the reviewed Codex-native profile")
        if expected_cli_version != REVIEWED_CODEX_CLI_VERSION:
            raise ValueError("Codex CLI version differs from the reviewed Codex-native profile")
        if max_response_bytes <= 0:
            raise ValueError("Codex CLI response-byte limit must be positive")
        self.cli_path = str(source)
        self.model = model
        self.expected_cli_version = expected_cli_version
        self._executable_identity_value = (
            observed.st_dev, observed.st_ino, observed.st_mode, observed.st_size, executable_sha256
        )
        self.max_response_bytes = max_response_bytes
        self.runner = runner
        self.last_usage = CodexCliUsage()

    @staticmethod
    def _executable_identity(source: Path) -> tuple[os.stat_result, str]:
        descriptor = os.open(source, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        try:
            observed = os.fstat(descriptor)
            digest = hashlib.sha256()
            while True:
                chunk = os.read(descriptor, 1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
        finally:
            os.close(descriptor)
        return observed, digest.hexdigest()

    def _run_identity_probe(self, argv: list[str], timeout_seconds: float) -> tuple[bytes, bytes]:
        try:
            completed = self.runner(
                argv,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=max(1.0, min(timeout_seconds, 10.0)),
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError("Codex CLI identity probe timed out") from exc
        if completed.returncode != 0:
            raise CodexCliProtocolError("Codex CLI identity probe returned non-zero status")
        return completed.stdout, completed.stderr

    def _assert_executable_unchanged(self) -> None:
        try:
            observed, executable_sha256 = self._executable_identity(Path(self.cli_path))
        except OSError as exc:
            raise CodexCliProtocolError("Codex CLI executable identity cannot be revalidated") from exc
        identity = (
            observed.st_dev, observed.st_ino, observed.st_mode, observed.st_size, executable_sha256
        )
        if identity != self._executable_identity_value:
            raise CodexCliProtocolError("Codex CLI executable identity changed after host construction")

    def _validate_identity(self, timeout_seconds: float) -> None:
        self._assert_executable_unchanged()
        version_stdout, version_stderr = self._run_identity_probe(
            [self.cli_path, "--version"], timeout_seconds
        )
        version = (version_stdout + version_stderr).decode("utf-8", errors="replace").strip()
        if version != f"codex-cli {self.expected_cli_version}":
            raise CodexCliProtocolError("Codex CLI version differs from confirmed authority")
        login_stdout, login_stderr = self._run_identity_probe(
            [self.cli_path, "login", "status"], timeout_seconds
        )
        login = login_stdout + login_stderr
        if "Logged in using ChatGPT" not in login.decode("utf-8", errors="replace"):
            raise CodexCliProtocolError("Codex CLI is not authenticated through ChatGPT")

    def validate_identity(self, timeout_seconds: float) -> None:
        """Validate the fixed executable and login before durable call intent exists."""

        if timeout_seconds <= 0:
            raise ValueError("Codex CLI timeout must be positive")
        self._validate_identity(timeout_seconds)

    @staticmethod
    def _parse_request(request: bytes) -> tuple[str, dict[str, Any], type[Any]]:
        try:
            envelope = parse_json_strict(request)
        except Exception as exc:
            raise CodexCliProtocolError("Codex CLI transport received malformed request JSON") from exc
        if (
            not isinstance(envelope, dict)
            or set(envelope) != {"type", "role", "adapter", "payload"}
            or envelope["type"] != "role_request"
            or envelope["adapter"] != "json_line"
            or envelope["role"] not in _ROLE_OUTPUTS
            or not isinstance(envelope["payload"], dict)
        ):
            raise CodexCliProtocolError("Codex CLI transport received an unsupported request envelope")
        role = envelope["role"]
        return role, envelope["payload"], _ROLE_OUTPUTS[role]

    @staticmethod
    def _parse_events(raw: bytes) -> CodexCliUsage:
        state = "awaiting_thread"
        saw_message = False
        usage: dict[str, Any] | None = None
        for line in raw.splitlines():
            if not line:
                continue
            try:
                event = parse_json_strict(line)
            except Exception as exc:
                raise CodexCliProtocolError("Codex CLI emitted malformed JSONL") from exc
            if not isinstance(event, dict) or not isinstance(event.get("type"), str):
                raise CodexCliProtocolError("Codex CLI emitted a malformed event")
            event_type = event["type"]
            if event_type == "thread.started":
                if state != "awaiting_thread" or not isinstance(event.get("thread_id"), str):
                    raise CodexCliProtocolError("Codex CLI emitted an invalid thread lifecycle")
                state = "awaiting_turn"
            elif event_type == "turn.started":
                if state != "awaiting_turn":
                    raise CodexCliProtocolError("Codex CLI emitted an invalid turn lifecycle")
                state = "in_turn"
            elif event_type in {"item.started", "item.completed"}:
                if state != "in_turn":
                    raise CodexCliProtocolError("Codex CLI emitted an item outside the active turn")
                item = event.get("item")
                item_type = item.get("type") if isinstance(item, dict) else None
                if item_type == "reasoning":
                    continue
                if not isinstance(item, dict) or item_type != "agent_message":
                    raise CodexCliProtocolError(
                        f"Codex CLI emitted a tool or unsupported item event: {item_type!r}"
                    )
                if event_type == "item.started":
                    continue
                if saw_message or not isinstance(item.get("text"), str):
                    raise CodexCliProtocolError("Codex CLI emitted an invalid final message event")
                saw_message = True
            elif event_type == "turn.completed":
                if state != "in_turn" or usage is not None or not isinstance(event.get("usage"), dict):
                    raise CodexCliProtocolError("Codex CLI emitted invalid or duplicate usage")
                usage = event["usage"]
                state = "complete"
            else:
                raise CodexCliProtocolError(f"Codex CLI emitted unsupported event type {event_type!r}")
        if state != "complete" or not saw_message or usage is None:
            raise CodexCliProtocolError("Codex CLI event stream is incomplete")
        values = {
            field: usage.get(field, 0)
            for field in (
                "input_tokens", "cached_input_tokens", "output_tokens", "reasoning_output_tokens"
            )
        }
        if any(not isinstance(value, int) or value < 0 for value in values.values()):
            raise CodexCliProtocolError("Codex CLI usage fields are malformed")
        return CodexCliUsage(requests=1, tool_calls=0, **values)

    def exchange(self, request: bytes, timeout_seconds: float) -> bytes:
        if timeout_seconds <= 0:
            raise ValueError("Codex CLI timeout must be positive")
        self.last_usage = CodexCliUsage()
        self._validate_identity(timeout_seconds)
        role, payload, output_type = self._parse_request(request)
        prompt = canonical_bytes({
            "instruction": (
                "Act only as the named bounded semantic role. Use no tools. Do not inspect the "
                "filesystem, environment, network, or prior conversation. Return only JSON matching "
                "the supplied output schema and base every field only on this canonical request."
            ),
            "role_contract": _ROLE_CONTRACTS[role],
            "role": role,
            "request": payload,
        }) + b"\n"

        with tempfile.TemporaryDirectory(prefix="rb-safe-codex-role-") as temporary:
            root = Path(temporary)
            sqlite_root = root / "sqlite"
            log_root = root / "log"
            sqlite_root.mkdir(mode=0o700)
            log_root.mkdir(mode=0o700)
            schema_path = root / "output.schema.json"
            result_path = root / "result.json"
            output_schema = _output_schema_for_role(role, output_type, payload)
            schema_path.write_bytes(canonical_bytes(output_schema) + b"\n")
            argv = [
                self.cli_path,
                "exec",
                "--ephemeral",
                "--ignore-user-config",
                "--ignore-rules",
                "--strict-config",
                "--skip-git-repo-check",
                "-C",
                str(root),
                "--sandbox",
                "read-only",
                "-c",
                f'sqlite_home="{sqlite_root}"',
                "-c",
                f'log_dir="{log_root}"',
            ]
            for capability in _DISABLED_CAPABILITIES:
                argv.extend(["--disable", capability])
            argv.extend([
                "-m",
                self.model,
                "-c",
                f'model_reasoning_effort="{REVIEWED_CODEX_REASONING_EFFORT}"',
                "--output-schema",
                str(schema_path),
                "--json",
                "-o",
                str(result_path),
                "-",
            ])
            try:
                completed = self.runner(
                    argv,
                    input=prompt,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=timeout_seconds,
                    check=False,
                    cwd=str(root),
                )
            except subprocess.TimeoutExpired as exc:
                raise TimeoutError("Codex CLI role call timed out") from exc
            if completed.returncode != 0:
                raise CodexCliProtocolError("Codex CLI role call returned non-zero status")
            self._assert_executable_unchanged()
            if len(completed.stdout) > self.max_response_bytes:
                raise CodexCliProtocolError("Codex CLI event stream exceeds its byte limit")
            if len(completed.stderr) > self.max_response_bytes:
                raise CodexCliProtocolError("Codex CLI error stream exceeds its byte limit")
            usage = self._parse_events(completed.stdout)
            if not result_path.is_file() or result_path.is_symlink():
                raise CodexCliProtocolError("Codex CLI did not create a regular result file")
            raw_result = result_path.read_bytes()
            if len(raw_result) > self.max_response_bytes:
                raise CodexCliProtocolError("Codex CLI result exceeds its byte limit")
            try:
                parsed = parse_json_strict(raw_result)
                model_output_type = (
                    _CodexVerificationDecision if role == "verifier" else output_type
                )
                output = model_output_type.model_validate(parsed)
            except (ValidationError, ValueError, TypeError) as exc:
                raise CodexCliProtocolError("Codex CLI returned a schema-invalid result") from exc
            canonical_result = canonical_bytes(output.model_dump(mode="json"))
            message_events: list[dict[str, Any]] = []
            for line in completed.stdout.splitlines():
                if not line:
                    continue
                event = parse_json_strict(line)
                item = event.get("item") if isinstance(event, dict) else None
                if (
                    event.get("type") == "item.completed"
                    and isinstance(item, dict)
                    and item.get("type") == "agent_message"
                ):
                    message_events.append(event)
            if len(message_events) != 1:
                raise CodexCliProtocolError("Codex CLI did not emit exactly one final message")
            try:
                message_payload = parse_json_strict(message_events[0]["item"]["text"])
            except Exception as exc:
                raise CodexCliProtocolError("Codex CLI final message is not strict JSON") from exc
            if canonical_bytes(message_payload) != canonical_result:
                raise CodexCliProtocolError("Codex CLI result file differs from its final message")
            response_output = (
                _materialize_verifier_response(payload, output)
                if role == "verifier" else output
            )
            self.last_usage = usage
            return canonical_bytes({
                "type": "role_response",
                "role": role,
                "adapter": "json_line",
                "payload": response_output.model_dump(mode="json"),
            }) + b"\n"
