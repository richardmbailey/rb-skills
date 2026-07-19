from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class FakeCapabilityViolation(RuntimeError):
    pass


@dataclass
class Ledger:
    entries: list[dict[str, Any]] = field(default_factory=list)

    def record(self, capability: str, action: str, **details: Any) -> None:
        self.entries.append({"capability": capability, "action": action, **details})

    def assert_no(self, capability: str, action: str | None = None) -> None:
        matches = [item for item in self.entries if item["capability"] == capability and (action is None or item["action"] == action)]
        if matches:
            raise AssertionError(f"unexpected fake calls: {matches}")


@dataclass
class FakeFilesystem:
    ledger: Ledger
    files: dict[str, bytes] = field(default_factory=dict)
    links: dict[str, str] = field(default_factory=dict)
    protected: set[str] = field(default_factory=set)

    def read(self, path: str) -> bytes:
        self.ledger.record("filesystem", "read", path=path)
        if path in self.links:
            path = self.links[path]
        if path not in self.files:
            raise FileNotFoundError(path)
        return self.files[path]

    def write(self, path: str, data: bytes) -> None:
        if path in self.protected:
            raise FakeCapabilityViolation(f"protected fake path: {path}")
        self.ledger.record("filesystem", "write", path=path, size=len(data))
        self.files[path] = data


@dataclass
class FakeSubprocess:
    ledger: Ledger
    allowed: set[tuple[str, ...]]
    results: dict[tuple[str, ...], tuple[int, str, str]] = field(default_factory=dict)

    def run(self, argv: list[str], env: dict[str, str], cwd: str) -> tuple[int, str, str]:
        key = tuple(argv)
        if key not in self.allowed:
            raise FakeCapabilityViolation(f"undeclared argv: {argv}")
        if any(name.upper().endswith(("TOKEN", "SECRET", "PASSWORD", "API_KEY")) for name in env):
            raise FakeCapabilityViolation("ambient secret reached fake subprocess")
        self.ledger.record("subprocess", "run", argv=argv, env_names=sorted(env), cwd=cwd)
        return self.results.get(key, (0, "", ""))


@dataclass
class FakeNetwork:
    ledger: Ledger
    allowed: set[tuple[str, int, str, str]]

    def request(self, host: str, port: int, protocol: str, method: str, write: bool = False) -> dict[str, Any]:
        key = (host, port, protocol, method)
        if key not in self.allowed:
            raise FakeCapabilityViolation(f"undeclared network request: {key}")
        self.ledger.record("network", "write" if write else "read", host=host, port=port, protocol=protocol, method=method)
        return {"status": 200, "bytes": 0}


@dataclass
class FakeApprovalStore:
    ledger: Ledger
    approvals: dict[str, dict[str, Any]]

    def consume(self, approval_id: str, artifact_hash: str) -> None:
        item = self.approvals.get(approval_id)
        if not item or item.get("artifact_hash") != artifact_hash or item.get("consumed"):
            raise FakeCapabilityViolation("approval missing, stale, broad, or reused")
        item["consumed"] = True
        self.ledger.record("approval", "consume", approval_id=approval_id, artifact_hash=artifact_hash)


@dataclass
class FakeSecretStore:
    ledger: Ledger
    handles: dict[str, str]

    def resolve(self, handle: str, audience: str) -> str:
        if handle not in self.handles:
            raise FakeCapabilityViolation("unknown secret handle")
        self.ledger.record("secret", "resolve", handle=handle, audience=audience)
        return self.handles[handle]


@dataclass
class FakeClockResourceHost:
    ledger: Ledger
    now: int = 0
    remaining_steps: int = 100

    def consume(self, label: str) -> None:
        if self.remaining_steps <= 0:
            self.ledger.record("resource", "pause", label=label)
            raise FakeCapabilityViolation("resource budget exhausted")
        self.remaining_steps -= 1
        self.now += 1
        self.ledger.record("resource", "consume", label=label, now=self.now)


@dataclass
class FakeAgentHost:
    ledger: Ledger
    responses: list[dict[str, Any]]
    fresh_contexts: bool = True

    def invoke(self, role: str, packet: dict[str, Any]) -> dict[str, Any]:
        self.ledger.record("agent", "invoke", role=role, fresh=self.fresh_contexts, packet_keys=sorted(packet))
        if not self.responses:
            raise FakeCapabilityViolation("no fake agent response")
        return self.responses.pop(0)


@dataclass
class FakeExternalService:
    ledger: Ledger
    seen_keys: set[str] = field(default_factory=set)

    def write(self, target: str, idempotency_key: str | None) -> None:
        if not idempotency_key or idempotency_key in self.seen_keys:
            raise FakeCapabilityViolation("fresh idempotency key required")
        self.seen_keys.add(idempotency_key)
        self.ledger.record("external_service", "write", target=target, idempotency_key=idempotency_key)
