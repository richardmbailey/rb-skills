from __future__ import annotations

import json
import os
import re
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .canonical import artifact_hash, canonical_bytes, parse_json_strict
from .models import AuditEvent, EventPayload


class AuditError(RuntimeError):
    pass


SECRET_KEY = re.compile(r"(?:token|secret|password|credential|api[_-]?key)", re.IGNORECASE)


def redact(value: Any, *, trusted_structural: bool = False) -> Any:
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in value.items():
            result[key] = "[REDACTED]" if SECRET_KEY.search(key) else redact(item, trusted_structural=key in {"status", "code", "path", "operation_id", "effect_id"})
        return result
    if isinstance(value, list):
        return [redact(item, trusted_structural=trusted_structural) for item in value]
    if isinstance(value, str) and not trusted_structural:
        return {"omitted": True, "reason": "uncertain_free_text"}
    return value


def build_event(
    run_id: str,
    sequence: int,
    payload: EventPayload,
    provenance: str,
    observation: dict[str, Any],
    previous_hash: str | None,
    event_uuid: str | None = None,
) -> AuditEvent:
    sanitized_payload = payload.model_copy(update={"summary": "[OMITTED: uncertain_free_text]" if payload.summary else ""})
    payload_data = sanitized_payload.model_dump(mode="json")
    payload_hash = artifact_hash("event-payload", "1.0", payload_data)
    body = {
        "schema_version": "1.0",
        "run_id": run_id,
        "sequence": sequence,
        "event_uuid": event_uuid or str(uuid.uuid4()),
        "payload": payload_data,
        "payload_hash": payload_hash,
        "provenance": provenance,
        "observation": {
            "observer_id": provenance,
            "observed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "data": redact(observation),
        },
        "previous_event_record_hash": previous_hash,
        "algorithm": "sha256",
    }
    record_hash = artifact_hash("event-record", "1.0", body)
    return AuditEvent.model_validate({**body, "event_record_hash": record_hash})


class AuditLog:
    def __init__(self, root: str, run_id: str):
        self.root = Path(root).resolve()
        self.run_id = run_id
        self.root.mkdir(parents=True, mode=0o700, exist_ok=True)

    def append(self, payload: EventPayload, provenance: str, observation: dict[str, Any]) -> AuditEvent:
        events = self.validate_chain()
        previous = events[-1].event_record_hash if events else None
        event = build_event(self.run_id, len(events), payload, provenance, observation, previous)
        target = self.root / f"{event.sequence:08d}-{event.event_uuid}.json"
        data = canonical_bytes(event.model_dump(mode="json")) + b"\n"
        descriptor, temp_name = tempfile.mkstemp(prefix=".event-", suffix=".tmp", dir=self.root)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, target)
        finally:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass
        return event

    def validate_chain(self) -> list[AuditEvent]:
        temporary = sorted(self.root.glob(".event-*.tmp"))
        if temporary:
            quarantine = self.root / "quarantine"
            quarantine.mkdir(exist_ok=True)
            for path in temporary:
                os.replace(path, quarantine / path.name)
            raise AuditError("incomplete event files quarantined; human review required")
        files = sorted(self.root.glob("[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]-*.json"))
        events: list[AuditEvent] = []
        uuids: set[str] = set()
        for expected, path in enumerate(files):
            try:
                persisted = path.read_bytes()
                payload = parse_json_strict(persisted)
                event = AuditEvent.model_validate(payload)
            except Exception as exc:
                raise AuditError(f"invalid audit event: {path.name}") from exc
            if persisted != canonical_bytes(event.model_dump(mode="json")) + b"\n":
                raise AuditError(f"non-canonical audit event: {path.name}")
            if event.sequence != expected or event.run_id != self.run_id:
                raise AuditError("audit sequence or run identity conflict")
            if event.event_uuid in uuids:
                raise AuditError("duplicate event UUID")
            uuids.add(event.event_uuid)
            expected_previous = events[-1].event_record_hash if events else None
            if event.previous_event_record_hash != expected_previous:
                raise AuditError("audit chain fork or missing predecessor")
            body = event.model_dump(mode="json")
            observed_hash = body.pop("event_record_hash")
            if artifact_hash("event-record", "1.0", body) != observed_hash:
                raise AuditError("audit event hash mismatch")
            if artifact_hash("event-payload", "1.0", event.payload.model_dump(mode="json")) != event.payload_hash:
                raise AuditError("audit payload hash mismatch")
            events.append(event)
        return events

    def recover(self) -> dict[str, Any]:
        issues: list[str] = []
        temporary = sorted(self.root.glob(".event-*.tmp"))
        if temporary:
            quarantine = self.root / "quarantine"
            quarantine.mkdir(exist_ok=True)
            for path in temporary:
                destination = quarantine / path.name
                os.replace(path, destination)
                issues.append(f"quarantined_partial:{destination.name}")
        try:
            events = self.validate_chain()
            head = events[-1].event_record_hash if events else None
        except AuditError as exc:
            issues.append(f"chain_error:{exc}")
            head = None
        report = {
            "run_id": self.run_id,
            "status": "human_required" if issues else "valid",
            "issues": issues,
            "validated_head": head,
        }
        if issues:
            path = self.root / f"recovery-{uuid.uuid4()}.json"
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(canonical_bytes(report) + b"\n")
                handle.flush()
                os.fsync(handle.fileno())
        return report
