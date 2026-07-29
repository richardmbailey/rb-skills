from __future__ import annotations

import hashlib
import json
import os
import platform
import secrets
import subprocess
import time
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from .canonical import sha256_file
from .models import RepositorySnapshot, RunManifest


class StateError(RuntimeError):
    pass


def _git(root: Path, executable: Path, *args: str, strip_output: bool = True) -> str:
    result = subprocess.run(
        [str(executable), "-c", "core.fsmonitor=false", "-c", "core.untrackedCache=false", "-C", str(root), *args],
        check=False,
        capture_output=True,
        text=True,
        env={
            "PATH": "/usr/bin:/bin", "GIT_OPTIONAL_LOCKS": "0", "LC_ALL": "C",
            "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null",
        },
    )
    if result.returncode != 0:
        raise StateError(f"Git observation failed for {args!r}: {result.stderr.strip()[:200]}")
    return result.stdout.strip() if strip_output else result.stdout


def _index_hash(root: Path, executable: Path) -> str:
    result = subprocess.run(
        [str(executable), "-c", "core.fsmonitor=false", "-c", "core.untrackedCache=false", "-C", str(root), "ls-files", "--stage", "-z"],
        check=False,
        capture_output=True,
        env={
            "PATH": "/usr/bin:/bin", "GIT_OPTIONAL_LOCKS": "0", "LC_ALL": "C",
            "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null",
        },
    )
    if result.returncode != 0:
        raise StateError(f"Git index observation failed: {result.stderr.decode('utf-8', 'replace')[:200]}")
    return hashlib.sha256(result.stdout).hexdigest()


def _status_hashes(root: Path, executable: Path, code: str) -> dict[str, str]:
    output = _git(
        root, executable, "status", "--porcelain=v1", "-z", "--untracked-files=all",
        strip_output=False,
    )
    result: dict[str, str] = {}
    records = output.split("\0")
    index = 0
    while index < len(records):
        record = records[index]
        index += 1
        if not record or len(record) < 4:
            continue
        status, name = record[:2], record[3:]
        rename_from = None
        if "R" in status and index < len(records):
            rename_from = records[index]
            index += 1
        relevant = status[0] != " " if code == "staged" else status[1] != " " if code == "unstaged" else status == "??"
        if relevant:
            path = root / name
            content_hash = sha256_file(path) if path.is_file() else "non-file-or-missing"
            result[name] = f"rename-from:{rename_from}:{content_hash}" if rename_from else content_hash
    return result


def _fixed_git_executable() -> Path:
    for candidate in (Path("/usr/bin/git"), Path("/opt/homebrew/bin/git"), Path("/usr/local/bin/git")):
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate.resolve(strict=True)
    raise StateError("Git worktree found but no fixed, absolute Git executable is available")


def _full_file_inventory(root: Path, control_roots: list[Path]) -> dict[str, str]:
    inventory: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        lexical = Path(os.path.abspath(path))
        if any(_within(lexical, control) for control in control_roots) or _within(lexical, root / ".git"):
            continue
        relative = path.relative_to(root).as_posix()
        stat = path.lstat()
        identity = f"mode={stat.st_mode:o}:uid={stat.st_uid}:gid={stat.st_gid}:dev={stat.st_dev}:ino={stat.st_ino}:nlink={stat.st_nlink}"
        if path.is_symlink():
            resolved = path.resolve(strict=False)
            inventory[relative] = "symlink:" + str(resolved) + ":" + identity
        elif path.is_file():
            inventory[relative] = "file:" + sha256_file(path) + ":" + identity
        elif path.is_dir():
            inventory[relative + "/"] = "directory:" + identity
        else:
            inventory[relative] = "special:" + identity
    return inventory


def capture_snapshot(
    project_root: str,
    selected_paths: list[str],
    instruction_paths: list[str],
    expected_product_changes: list[str],
    control_plane_roots: list[str] | None = None,
) -> RepositorySnapshot:
    root = Path(project_root).resolve(strict=True)
    canonical_controls = [Path(value).resolve(strict=False) for value in (control_plane_roots or [str(root / ".rb-safe-operation")])]
    selected: dict[str, str] = {}
    links: dict[str, str] = {}
    for supplied in selected_paths:
        path = Path(supplied)
        if not path.is_absolute():
            path = root / path
        resolved = path.resolve(strict=False)
        try:
            resolved.relative_to(root)
        except ValueError as exc:
            raise StateError(f"selected path outside project: {supplied}") from exc
        if path.exists() and path.is_file():
            selected[str(resolved)] = sha256_file(path)
        if path.is_symlink():
            links[str(path)] = str(resolved)
    instructions: dict[str, str] = {}
    for supplied in instruction_paths:
        path = Path(supplied)
        if not path.is_absolute():
            path = root / path
        if path.is_file():
            instructions[str(path.resolve())] = sha256_file(path)
    device = root.stat().st_dev
    expected_changes: list[str] = []
    for supplied in expected_product_changes:
        path = Path(supplied)
        if not path.is_absolute():
            path = root / path
        resolved = path.resolve(strict=False)
        try:
            resolved.relative_to(root)
        except ValueError as exc:
            raise StateError(f"expected product change outside project: {supplied}") from exc
        expected_changes.append(str(resolved))
    is_git = (root / ".git").exists()
    git_executable = _fixed_git_executable() if is_git else None
    git_head = _git(root, git_executable, "rev-parse", "HEAD") if git_executable else None
    git_branch = _git(root, git_executable, "branch", "--show-current") if git_executable else None
    index_hash = _index_hash(root, git_executable) if git_executable else None
    return RepositorySnapshot(
        project_root=str(root),
        platform=platform.system().lower(),
        case_sensitive=_case_sensitive(root),
        unicode_normalization="NFC",
        device_identity=str(device),
        observation_mode="git_and_filesystem" if git_executable else "full_filesystem",
        git_executable_path=str(git_executable) if git_executable else None,
        git_executable_hash=sha256_file(git_executable) if git_executable else None,
        git_head=git_head,
        git_branch=git_branch,
        index_hash=index_hash,
        staged_paths=_status_hashes(root, git_executable, "staged") if git_executable else {},
        unstaged_paths=_status_hashes(root, git_executable, "unstaged") if git_executable else {},
        untracked_paths=_status_hashes(root, git_executable, "untracked") if git_executable else {},
        full_file_inventory=_full_file_inventory(root, canonical_controls),
        selected_file_hashes=selected,
        instruction_hashes=instructions,
        resolved_links=links,
        expected_product_changes=expected_changes,
        control_plane_roots=[str(value) for value in canonical_controls],
    )


def capture_policy_snapshot(
    loaded_policy,
    selected_paths: list[str],
    instruction_paths: list[str],
    expected_product_changes: list[str],
    control_plane_roots: list[str] | None = None,
    metadata_loader=None,
):
    """Capture repository state without opening denied content or descending denied subtrees."""

    from .patches import capture_file_metadata, metadata_fingerprint_hash
    from .policy_models import RepositorySnapshotV3
    from .project_policy import evaluate_path, require_path, revalidate_decision

    root = loaded_policy.project_root
    load_metadata = metadata_loader or capture_file_metadata
    canonical_controls = [
        Path(value).resolve(strict=False)
        for value in (control_plane_roots or [str(root / ".rb-safe-operation")])
    ]
    denied_rule_ids = sorted(
        {rule.rule_id for rule in loaded_policy.effective_policy.path_rules if "read" in rule.deny}
    )
    unobserved_subtrees = sorted(
        {
            rule.rule_id
            for rule in loaded_policy.effective_policy.path_rules
            if "read" in rule.deny and rule.scope == "subtree"
        }
    )

    def policy_inventory() -> dict[str, str]:
        inventory: dict[str, str] = {}

        def descend(directory: Path, relative: Path) -> None:
            if directory != root:
                directory_decision = require_path(loaded_policy, directory, "read")
                revalidate_decision(loaded_policy, directory_decision)
            with os.scandir(directory) as entries:
                ordered = sorted(entries, key=lambda item: unicodedata.normalize("NFC", item.name))
            for entry in ordered:
                child_relative = relative / entry.name
                child = root / child_relative
                lexical = Path(os.path.abspath(child))
                if any(_within(lexical, control) for control in canonical_controls) or _within(
                    lexical, root / ".git"
                ):
                    continue
                decision = evaluate_path(loaded_policy, child, "read")
                key = child_relative.as_posix()
                if not decision.allowed:
                    matched_subtree = any(
                        rule.rule_id in decision.matched_rule_ids and rule.scope == "subtree"
                        for rule in loaded_policy.effective_policy.path_rules
                    )
                    inventory[key] = (
                        "unobserved-policy-denied:rules="
                        + ",".join(decision.matched_rule_ids)
                    )
                    if matched_subtree:
                        continue
                    # Exact denied paths expose only the path already named by the rule.
                    continue
                revalidate_decision(loaded_policy, decision)
                observed = entry.stat(follow_symlinks=False)
                identity = (
                    f"mode={observed.st_mode:o}:uid={observed.st_uid}:gid={observed.st_gid}:"
                    f"dev={observed.st_dev}:ino={observed.st_ino}:nlink={observed.st_nlink}"
                )
                if entry.is_symlink():
                    inventory[key] = "symlink:" + os.readlink(child) + ":" + identity
                elif entry.is_file(follow_symlinks=False):
                    inventory[key] = "file:" + sha256_file(child) + ":" + identity
                elif entry.is_dir(follow_symlinks=False):
                    inventory[key + "/"] = "directory:" + identity
                    descend(child, child_relative)
                else:
                    inventory[key] = "special:" + identity

        descend(root, Path("."))
        return inventory

    selected: dict[str, str] = {}
    selected_metadata: dict[str, str] = {}
    instructions: dict[str, str] = {}
    links: dict[str, str] = {}
    for supplied in selected_paths:
        path = Path(supplied) if Path(supplied).is_absolute() else root / supplied
        decision = evaluate_path(loaded_policy, path, "read")
        if not decision.allowed:
            continue
        decision = require_path(loaded_policy, path, "read")
        revalidate_decision(loaded_policy, decision)
        if path.is_symlink():
            raise StateError("selected paths cannot cross a symlink under project policy")
        if path.is_file():
            resolved = path.resolve(strict=True)
            selected[str(resolved)] = sha256_file(path)
            selected_metadata[str(resolved)] = metadata_fingerprint_hash(load_metadata(path))
    for supplied in instruction_paths:
        path = Path(supplied) if Path(supplied).is_absolute() else root / supplied
        decision = evaluate_path(loaded_policy, path, "read")
        if decision.allowed:
            revalidate_decision(loaded_policy, decision)
        if decision.allowed and path.is_file() and not path.is_symlink():
            instructions[str(path.resolve(strict=True))] = sha256_file(path)
    expected: list[str] = []
    for supplied in expected_product_changes:
        path = Path(supplied) if Path(supplied).is_absolute() else root / supplied
        lexical = Path(os.path.abspath(path))
        if not _within(lexical.resolve(strict=False), root):
            raise StateError(f"expected product change outside project: {supplied}")
        expected.append(str(lexical.resolve(strict=False)))
    inventory = policy_inventory()
    return RepositorySnapshotV3(
        project_root=str(root),
        platform=platform.system().lower(),
        case_sensitive=_case_sensitive(root),
        unicode_normalization="NFC",
        device_identity=str(root.stat().st_dev),
        observation_mode="policy_pruned_filesystem",
        git_executable_path=None,
        git_executable_hash=None,
        git_head=None,
        git_branch=None,
        index_hash=None,
        staged_paths={},
        unstaged_paths={},
        untracked_paths={},
        full_file_inventory=inventory,
        selected_file_hashes=selected,
        instruction_hashes=instructions,
        resolved_links=links,
        expected_product_changes=expected,
        control_plane_roots=[str(value) for value in canonical_controls],
        policy_binding=loaded_policy.binding,
        denied_rule_ids=denied_rule_ids,
        unobserved_subtree_rule_ids=unobserved_subtrees,
        selected_file_metadata_hashes=selected_metadata,
        proposal_context_observation_hashes={},
    )


def snapshot_materially_equal(before: RepositorySnapshot, after: RepositorySnapshot, declared_changed_paths: set[str] | None = None) -> tuple[bool, list[str]]:
    declared = {str(Path(os.path.abspath(value))) for value in (declared_changed_paths or set())}
    control_roots = [Path(os.path.abspath(value)) for value in before.control_plane_roots]
    project_root = Path(before.project_root)
    declared_parent_inventory_keys: set[str] = set()
    for path_value in declared:
        try:
            relative_parent = Path(path_value).parent.relative_to(project_root)
        except ValueError:
            continue
        if relative_parent != Path("."):
            declared_parent_inventory_keys.add(relative_parent.as_posix().rstrip("/") + "/")

    def ignored(path_value: str) -> bool:
        candidate = Path(path_value)
        if not candidate.is_absolute():
            candidate = Path(before.project_root) / candidate
        candidate = Path(os.path.abspath(candidate))
        if str(candidate) in declared:
            return True
        return any(_within(candidate, root) for root in control_roots)

    def filtered(mapping: dict[str, str]) -> dict[str, str]:
        return {key: value for key, value in mapping.items() if not ignored(key)}

    def directory_identity_without_nlink(value: str) -> str | None:
        if not value.startswith("directory:"):
            return None
        prefix, marker, nlink = value.rpartition(":nlink=")
        if marker != ":nlink=" or not nlink.isdigit():
            return None
        return prefix

    def full_inventory_equal() -> bool:
        before_inventory = filtered(before.full_file_inventory)
        after_inventory = filtered(after.full_file_inventory)
        if set(before_inventory) != set(after_inventory):
            return False
        for key, before_value in before_inventory.items():
            after_value = after_inventory[key]
            if before_value == after_value:
                continue
            before_directory = directory_identity_without_nlink(before_value)
            after_directory = directory_identity_without_nlink(after_value)
            if (
                key in declared_parent_inventory_keys
                and before_directory is not None
                and before_directory == after_directory
            ):
                continue
            return False
        return True

    differences: list[str] = []
    stable_fields = (
        "project_root", "platform", "case_sensitive", "unicode_normalization", "device_identity",
        "observation_mode", "git_executable_path", "git_executable_hash", "git_head", "git_branch",
        "index_hash", "instruction_hashes", "resolved_links",
    )
    for field in stable_fields:
        if getattr(before, field) != getattr(after, field):
            differences.append(field)
    all_selected = set(before.selected_file_hashes) | set(after.selected_file_hashes)
    for path in all_selected:
        if not ignored(path) and before.selected_file_hashes.get(path) != after.selected_file_hashes.get(path):
            differences.append(f"selected_file:{path}")
    for field in ("staged_paths", "unstaged_paths", "untracked_paths"):
        if filtered(getattr(before, field)) != filtered(getattr(after, field)):
            differences.append(field)
    if not full_inventory_equal():
        differences.append("full_file_inventory")
    return not differences, differences


def _within(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def _case_sensitive(root: Path) -> bool:
    for child in root.iterdir():
        swapped = child.name.swapcase()
        if swapped != child.name:
            return not (root / swapped).exists()
    return platform.system().lower() not in {"darwin", "windows"}


def project_key(root: str, device_identity: str) -> str:
    normalized = unicodedata.normalize("NFC", str(Path(root).resolve())).encode("utf-8")
    return hashlib.sha256(b"rb-safe-operation\0project-root\0" + normalized + b"\0" + device_identity.encode("ascii")).hexdigest()


@dataclass
class Lease:
    path: Path
    ownership_token: str
    payload_hash: str


def heartbeat_lease(lease: Lease) -> None:
    try:
        data = lease.path.read_bytes()
    except FileNotFoundError as exc:
        raise StateError("lease disappeared before heartbeat") from exc
    payload = json.loads(data)
    if payload.get("ownership_token") != lease.ownership_token or hashlib.sha256(data).hexdigest() != lease.payload_hash:
        raise StateError("lease ownership or content changed")
    payload["heartbeat_epoch"] = int(time.time())
    updated = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    temporary = lease.path.with_suffix(".lease.tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(updated)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, lease.path)
    lease.payload_hash = hashlib.sha256(updated).hexdigest()


def acquire_lease(project_root: str, run_id: str, device_identity: str, prior_event_hash: str | None) -> Lease:
    root = Path(project_root).resolve(strict=True)
    control = root / ".rb-safe-operation"
    control.mkdir(mode=0o700, exist_ok=True)
    path = control / "execution.lease"
    token = secrets.token_hex(32)
    payload = {
        "project_key": project_key(str(root), device_identity),
        "run_id": run_id,
        "ownership_token": token,
        "pid": os.getpid(),
        "created_epoch": int(time.time()),
        "heartbeat_epoch": int(time.time()),
        "prior_event_hash": prior_event_hash,
    }
    data = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise StateError("live or indeterminate execution lease exists") from exc
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    return Lease(path=path, ownership_token=token, payload_hash=hashlib.sha256(data).hexdigest())


def release_lease(lease: Lease) -> None:
    try:
        data = lease.path.read_bytes()
    except FileNotFoundError as exc:
        raise StateError("lease disappeared before release") from exc
    payload = json.loads(data)
    if payload.get("ownership_token") != lease.ownership_token or hashlib.sha256(data).hexdigest() != lease.payload_hash:
        raise StateError("lease ownership or content changed")
    lease.path.unlink()


ACTIVE = {
    "drafting", "validating", "approved", "executing", "proposing", "validating_proposal",
    "assessing_proposal", "proposal_approved", "applying_proposal", "verifying", "repairing",
}
RESUMABLE = {"paused_resource"}
TERMINAL = {"rejected", "human_required", "verified", "failed", "abandoned"}
TRANSITIONS = {
    "drafting": {"validating", "paused_resource", "human_required", "abandoned"},
    "validating": {"rejected", "approved", "paused_resource", "human_required", "failed", "abandoned"},
    "approved": {"executing", "paused_resource", "human_required", "failed", "abandoned"},
    "executing": {"proposing", "verifying", "repairing", "paused_resource", "human_required", "failed", "abandoned"},
    "proposing": {"validating_proposal", "paused_resource", "human_required", "failed", "abandoned"},
    "validating_proposal": {"assessing_proposal", "paused_resource", "human_required", "failed", "abandoned"},
    "assessing_proposal": {"proposal_approved", "paused_resource", "human_required", "failed", "abandoned"},
    "proposal_approved": {"applying_proposal", "paused_resource", "human_required", "failed", "abandoned"},
    "applying_proposal": {"executing", "verifying", "human_required", "failed", "abandoned"},
    "repairing": {"executing", "paused_resource", "human_required", "failed", "abandoned"},
    "verifying": {"verified", "repairing", "paused_resource", "human_required", "failed", "abandoned"},
    "paused_resource": {"drafting", "validating", "approved", "executing", "proposing", "validating_proposal", "assessing_proposal", "proposal_approved", "verifying", "repairing", "abandoned"},
    "human_required": set(),
}


def transition(manifest: RunManifest, target: str, evidence_ids: list[str], resumed_state: str | None = None):
    current_pause_escalation = (
        manifest.schema_version == "3.0"
        and manifest.state == "paused_resource"
        and target == "human_required"
    )
    if target not in TRANSITIONS.get(manifest.state, set()) and not current_pause_escalation:
        raise StateError(f"illegal lifecycle transition: {manifest.state} -> {target}")
    if not evidence_ids:
        raise StateError("lifecycle transition requires evidence")
    prior = manifest.state
    payload = manifest.model_dump()
    payload["state"] = target
    if target == "human_required" and manifest.schema_version == "1.0":
        payload["suspended_from"] = manifest.suspended_from or prior
    elif target == "human_required":
        payload["suspended_from"] = None
    elif target in RESUMABLE:
        payload["suspended_from"] = manifest.suspended_from or prior
    elif prior in RESUMABLE:
        if resumed_state != manifest.suspended_from or target != manifest.suspended_from:
            raise StateError("resume must return to exact suspended_from state")
        payload["suspended_from"] = None
    else:
        payload["suspended_from"] = None
    return type(manifest).model_validate(payload)


def escalate_resume_drift(manifest: RunManifest, evidence_ids: list[str]) -> RunManifest:
    """Escalate a resource pause after resume preflight finds drift, without nesting suspension."""
    if manifest.state != "paused_resource" or manifest.suspended_from is None:
        raise StateError("resume-drift escalation requires a paused_resource manifest")
    if not evidence_ids:
        raise StateError("resume-drift escalation requires evidence")
    payload = manifest.model_dump()
    payload["state"] = "human_required"
    payload["suspended_from"] = None if manifest.schema_version == "3.0" else manifest.suspended_from
    return type(manifest).model_validate(payload)


def validate_resume_identity(manifest: RunManifest, *, plan_hash, assessment_hash, policy_hash, snapshot_hash, event_head_hash: str | None) -> None:
    observed = {
        "plan_hash": plan_hash, "assessment_hash": assessment_hash, "policy_hash": policy_hash,
        "snapshot_hash": snapshot_hash, "event_head_hash": event_head_hash,
    }
    mismatches = [field for field, value in observed.items() if getattr(manifest, field) != value]
    if mismatches:
        raise StateError(f"resume identity mismatch: {mismatches}")
