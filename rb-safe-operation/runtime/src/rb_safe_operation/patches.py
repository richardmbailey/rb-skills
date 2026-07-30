from __future__ import annotations

import ctypes
from dataclasses import dataclass
import errno
import hashlib
import os
from pathlib import Path
import posixpath
import re
import shutil
import stat
import sys
import tempfile
from typing import Callable, Literal

from .canonical import artifact_hash
from .proposal_models import FileMetadataFingerprint


class PatchContractError(ValueError):
    """The supplied patch cannot be represented by the exact text-patch contract."""


class PatchFormatError(PatchContractError):
    """The proposal uses malformed unified-diff syntax but requests no wider action."""


class MetadataContractError(PatchContractError):
    """Target metadata cannot be inspected or represented without hidden effects."""


@dataclass(frozen=True)
class PreparedTextTarget:
    path: Path
    relative_path: str
    action: Literal["create", "modify", "delete"]
    preimage: bytes | None
    postimage: bytes | None
    preimage_hash: str | None
    postimage_hash: str | None


@dataclass(frozen=True)
class PreparedTextPatch:
    patch: str
    patch_hash: str
    working_directory: Path
    targets: tuple[PreparedTextTarget, ...]

    @property
    def created_paths(self) -> tuple[str, ...]:
        return tuple(str(item.path) for item in self.targets if item.action == "create")

    @property
    def modified_paths(self) -> tuple[str, ...]:
        return tuple(str(item.path) for item in self.targets if item.action == "modify")

    @property
    def deleted_paths(self) -> tuple[str, ...]:
        return tuple(str(item.path) for item in self.targets if item.action == "delete")


def metadata_fingerprint_hash(value: FileMetadataFingerprint) -> str:
    return artifact_hash("file-metadata-fingerprint", "1.0", value.model_dump(mode="json"))


def inspect_patch_paths(patch: str) -> tuple[set[str], set[str], set[str]]:
    """Validate supported patch metadata and return normalized target paths by action."""
    forbidden_metadata = (
        "GIT binary patch", "Binary files ", "old mode ", "new mode ", "new file mode ",
        "deleted file mode ", "similarity index ", "dissimilarity index ", "rename from ",
        "rename to ", "copy from ", "copy to ", "diff --cc ", "diff --combined ",
    )
    if any(line.startswith(forbidden_metadata) for line in patch.splitlines()):
        raise PatchContractError("patch contains unmodelled binary, mode, link, rename, copy, or combined-diff metadata")
    old_paths = re.findall(r"^--- (?:a/)?(.+)$", patch, flags=re.MULTILINE)
    new_paths = re.findall(r"^\+\+\+ (?:b/)?(.+)$", patch, flags=re.MULTILINE)
    if len(old_paths) != len(new_paths) or not old_paths:
        raise PatchFormatError("patch must be a standard unified diff")
    created: set[str] = set()
    modified: set[str] = set()
    deleted: set[str] = set()
    seen_targets: dict[str, str] = {}
    for old, new in zip(old_paths, new_paths):
        if old == "/dev/null":
            action, target = "create", new
        elif new == "/dev/null":
            action, target = "delete", old
        elif old == new:
            action, target = "modify", new
        else:
            raise PatchContractError("renames are unsupported in apply_patch exact actions")
        target = posixpath.normpath(target)
        if target in {"", ".", ".."} or target.startswith("../") or target.startswith("/"):
            raise PatchContractError("patch paths must be normalized project-relative paths")
        prior_action = seen_targets.get(target)
        if prior_action is not None:
            raise PatchContractError(
                f"patch target appears more than once or across actions: {target} ({prior_action}, {action})"
            )
        seen_targets[target] = action
        {"create": created, "modify": modified, "delete": deleted}[action].add(target)
    return created, modified, deleted


def prepare_text_patch(patch: str, working_directory: Path, preimages: dict[str, bytes]) -> PreparedTextPatch:
    """Materialise a supported patch from coordinator-captured bytes without product I/O."""

    if "\0" in patch:
        raise PatchFormatError("patch contains a NUL byte")
    created, modified, deleted = inspect_patch_paths(patch)
    cwd = working_directory.resolve(strict=True)
    if not cwd.is_dir():
        raise PatchContractError("patch working directory is not a directory")
    expected_preimage_paths = {
        str((cwd / relative).resolve(strict=False)) for relative in modified | deleted
    }
    if set(preimages) != expected_preimage_paths:
        raise PatchContractError("captured preimage set differs from modified and deleted targets")

    lines = patch.splitlines(keepends=True)
    prepared: list[PreparedTextTarget] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.startswith("diff --git ") or line.startswith("index ") or not line.strip():
            index += 1
            continue
        if not line.startswith("--- ") or index + 1 >= len(lines) or not lines[index + 1].startswith("+++ "):
            raise PatchFormatError("patch contains unsupported metadata or malformed file headers")
        old_name = line[4:].strip()
        new_name = lines[index + 1][4:].strip()
        old_relative = None if old_name == "/dev/null" else re.sub(r"^a/", "", old_name)
        new_relative = None if new_name == "/dev/null" else re.sub(r"^b/", "", new_name)
        relative = new_relative or old_relative
        if relative is None:
            raise PatchContractError("patch file header cannot use /dev/null on both sides")
        normalized = posixpath.normpath(relative)
        if normalized != relative or normalized in {"", ".", ".."} or normalized.startswith("../") or normalized.startswith("/"):
            raise PatchContractError("patch paths must be normalized project-relative paths")
        path = (cwd / normalized).resolve(strict=False)
        try:
            path.relative_to(cwd)
        except ValueError as exc:
            raise PatchContractError("patch target escapes its working directory") from exc
        action: Literal["create", "modify", "delete"] = (
            "create" if old_relative is None else "delete" if new_relative is None else "modify"
        )
        preimage = None if action == "create" else preimages.get(str(path))
        if action != "create" and preimage is None:
            raise PatchContractError(f"captured preimage is missing for {path}")
        try:
            original_lines = [] if preimage is None else preimage.decode("utf-8").splitlines(keepends=True)
        except UnicodeDecodeError as exc:
            raise PatchContractError(f"exact patch supports UTF-8 text only: {path}") from exc

        output: list[str] = []
        source_index = 0
        index += 2
        saw_hunk = False
        while index < len(lines) and not lines[index].startswith(("diff --git ", "--- ")):
            header = lines[index]
            if header.startswith("index ") or not header.strip():
                index += 1
                continue
            match = re.match(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", header)
            if not match:
                raise PatchFormatError("patch contains unsupported metadata or malformed hunk header")
            saw_hunk = True
            old_start = int(match.group(1))
            old_count = int(match.group(2) or "1")
            new_count = int(match.group(4) or "1")
            hunk_source = 0 if old_start == 0 else old_start - 1
            if hunk_source < source_index or hunk_source > len(original_lines):
                raise PatchFormatError("patch hunk source range is invalid or overlaps")
            output.extend(original_lines[source_index:hunk_source])
            source_index = hunk_source
            index += 1
            observed_old = 0
            observed_new = 0
            while index < len(lines) and not lines[index].startswith(("@@ ", "diff --git ", "--- ")):
                item = lines[index]
                if item.startswith("\\ No newline at end of file"):
                    if not output:
                        raise PatchFormatError("no-newline marker has no preceding patch line")
                    output[-1] = output[-1].rstrip("\r\n")
                    index += 1
                    continue
                if not item or item[0] not in {" ", "+", "-"}:
                    raise PatchFormatError("patch hunk contains an unsupported line")
                content = item[1:]
                if item[0] in {" ", "-"}:
                    if source_index >= len(original_lines) or original_lines[source_index] != content:
                        raise PatchContractError("patch preimage text differs from the captured file")
                    source_index += 1
                    observed_old += 1
                if item[0] in {" ", "+"}:
                    output.append(content)
                    observed_new += 1
                index += 1
            if observed_old != old_count or observed_new != new_count:
                raise PatchFormatError("patch hunk line counts differ from its header")
        if not saw_hunk:
            raise PatchFormatError("patch file has no hunks")
        output.extend(original_lines[source_index:])
        candidate = "".join(output).encode("utf-8")
        if action == "delete" and candidate:
            raise PatchContractError("delete patch did not remove the complete file")
        postimage = None if action == "delete" else candidate
        prepared.append(
            PreparedTextTarget(
                path=path,
                relative_path=normalized,
                action=action,
                preimage=preimage,
                postimage=postimage,
                preimage_hash=None if preimage is None else hashlib.sha256(preimage).hexdigest(),
                postimage_hash=None if postimage is None else hashlib.sha256(postimage).hexdigest(),
            )
        )
    if not prepared:
        raise PatchFormatError("patch contains no files")
    return PreparedTextPatch(
        patch=patch,
        patch_hash=hashlib.sha256(patch.encode("utf-8")).hexdigest(),
        working_directory=cwd,
        targets=tuple(prepared),
    )


def validate_live_preimages(prepared: PreparedTextPatch) -> None:
    """Fail if any product target changed after pure preparation."""

    for target in prepared.targets:
        if target.action == "create":
            if target.path.exists() or target.path.is_symlink():
                raise PatchContractError(f"patch create target appeared before commit: {target.path}")
            continue
        try:
            live = target.path.read_bytes()
        except OSError as exc:
            raise PatchContractError(f"patch source changed before commit: {target.path}") from exc
        if hashlib.sha256(live).hexdigest() != target.preimage_hash:
            raise PatchContractError(f"patch preimage changed before commit: {target.path}")


def _read_macos_acl(path: Path) -> bytes:
    if sys.platform != "darwin":
        raise MetadataContractError("ACL inspection is unavailable on this host")
    library = ctypes.CDLL("/usr/lib/libSystem.B.dylib", use_errno=True)
    library.acl_get_file.argtypes = [ctypes.c_char_p, ctypes.c_int]
    library.acl_get_file.restype = ctypes.c_void_p
    library.acl_to_text.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ssize_t)]
    library.acl_to_text.restype = ctypes.c_void_p
    library.acl_free.argtypes = [ctypes.c_void_p]
    acl = library.acl_get_file(os.fsencode(path), 0x00000100)
    if not acl:
        observed_errno = ctypes.get_errno()
        if observed_errno == errno.ENOENT:
            return b""
        raise MetadataContractError(f"ACL inspection failed for {path}: errno {observed_errno}")
    try:
        length = ctypes.c_ssize_t()
        text_pointer = library.acl_to_text(acl, ctypes.byref(length))
        if not text_pointer:
            raise MetadataContractError(f"ACL text conversion failed for {path}")
        try:
            return ctypes.string_at(text_pointer, length.value)
        finally:
            library.acl_free(text_pointer)
    finally:
        library.acl_free(acl)


_DEFAULT_ACL_READER = object()
_DEFAULT_XATTR_READER = object()


def _read_macos_xattrs(path: Path) -> dict[str, bytes]:
    if sys.platform != "darwin":
        raise MetadataContractError("extended attribute inspection is unavailable on this host")
    library = ctypes.CDLL("/usr/lib/libSystem.B.dylib", use_errno=True)
    library.listxattr.argtypes = [ctypes.c_char_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int]
    library.listxattr.restype = ctypes.c_ssize_t
    library.getxattr.argtypes = [
        ctypes.c_char_p,
        ctypes.c_char_p,
        ctypes.c_void_p,
        ctypes.c_size_t,
        ctypes.c_uint32,
        ctypes.c_int,
    ]
    library.getxattr.restype = ctypes.c_ssize_t
    encoded_path = os.fsencode(path)
    options = 0x0001  # XATTR_NOFOLLOW
    name_size = library.listxattr(encoded_path, None, 0, options)
    if name_size < 0:
        raise MetadataContractError(f"extended attribute listing failed for {path}: errno {ctypes.get_errno()}")
    if name_size == 0:
        return {}
    name_buffer = ctypes.create_string_buffer(name_size)
    observed_name_size = library.listxattr(encoded_path, name_buffer, name_size, options)
    if observed_name_size != name_size:
        raise MetadataContractError(f"extended attribute names changed during inspection: {path}")
    names = sorted(name for name in name_buffer.raw[:name_size].split(b"\0") if name)
    result: dict[str, bytes] = {}
    for encoded_name in names:
        value_size = library.getxattr(encoded_path, encoded_name, None, 0, 0, options)
        if value_size < 0:
            raise MetadataContractError(
                f"extended attribute size inspection failed for {path}: errno {ctypes.get_errno()}"
            )
        value_buffer = ctypes.create_string_buffer(value_size) if value_size else None
        observed_value_size = library.getxattr(
            encoded_path,
            encoded_name,
            value_buffer,
            value_size,
            0,
            options,
        )
        if observed_value_size != value_size:
            raise MetadataContractError(f"extended attribute changed during inspection: {path}")
        try:
            name = os.fsdecode(encoded_name)
        except UnicodeDecodeError as exc:
            raise MetadataContractError(f"extended attribute name is not representable: {path}") from exc
        result[name] = b"" if value_buffer is None else value_buffer.raw[:value_size]
    return result


def capture_file_metadata(
    path: Path,
    *,
    acl_reader: Callable[[Path], bytes] | None | object = _DEFAULT_ACL_READER,
    xattr_reader: Callable[[Path], dict[str, bytes]] | None | object = _DEFAULT_XATTR_READER,
) -> FileMetadataFingerprint:
    """Capture the fail-closed metadata contract for one existing regular file."""

    if acl_reader is None:
        raise MetadataContractError("ACL inspection is unavailable for this target")
    if xattr_reader is None:
        raise MetadataContractError("extended attributes cannot be inspected for this target")
    reader = _read_macos_acl if acl_reader is _DEFAULT_ACL_READER else acl_reader
    xattr_loader = _read_macos_xattrs if xattr_reader is _DEFAULT_XATTR_READER else xattr_reader
    try:
        observed = path.lstat()
    except OSError as exc:
        raise MetadataContractError(f"target metadata is unavailable: {path}") from exc
    if not stat.S_ISREG(observed.st_mode):
        raise MetadataContractError(f"target is not a regular file: {path}")
    if observed.st_nlink != 1:
        raise MetadataContractError(f"hard-linked targets are unsupported: {path}")
    assert callable(xattr_loader)
    try:
        raw_xattrs = xattr_loader(path)
    except MetadataContractError:
        raise
    except Exception as exc:
        raise MetadataContractError(f"extended attributes cannot be inspected for {path}") from exc
    xattrs = {name: hashlib.sha256(value).hexdigest() for name, value in sorted(raw_xattrs.items())}
    assert callable(reader)
    try:
        acl_bytes = reader(path)
    except MetadataContractError:
        raise
    except Exception as exc:
        raise MetadataContractError(f"ACL inspection failed for {path}") from exc
    try:
        content = path.read_bytes()
    except OSError as exc:
        raise MetadataContractError(f"target content cannot be captured: {path}") from exc
    return FileMetadataFingerprint(
        file_type="regular",
        device=observed.st_dev,
        inode=observed.st_ino,
        link_count=1,
        mode=stat.S_IMODE(observed.st_mode),
        uid=observed.st_uid,
        gid=observed.st_gid,
        flags=getattr(observed, "st_flags", None),
        acl_hash=hashlib.sha256(acl_bytes).hexdigest(),
        extended_attribute_hashes=xattrs,
        content_hash=hashlib.sha256(content).hexdigest(),
        size=len(content),
    )


def _same_preserved_metadata(
    expected: FileMetadataFingerprint,
    observed: FileMetadataFingerprint,
) -> bool:
    """Compare every preserved property while allowing replacement to change inode and content."""

    return (
        observed.file_type == expected.file_type
        and observed.device == expected.device
        and observed.link_count == expected.link_count
        and observed.mode == expected.mode
        and observed.uid == expected.uid
        and observed.gid == expected.gid
        and observed.flags == expected.flags
        and observed.acl_hash == expected.acl_hash
        and observed.extended_attribute_hashes == expected.extended_attribute_hashes
    )


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


CREATED_PARENT_DIRECTORY_MODE = 0o755


def _sanitise_created_extended_attributes(path: Path) -> dict[str, str]:
    """Remove unapproved xattrs and return the accepted created-path set."""

    if sys.platform == "darwin":
        observed = _read_macos_xattrs(path)
        parent = _read_macos_xattrs(path.parent)
        provenance_name = "com.apple.provenance"
        accepted_raw: dict[str, bytes] = {}
        if provenance_name in observed:
            if parent.get(provenance_name) != observed[provenance_name]:
                raise MetadataContractError(
                    f"created path has unexpected platform provenance metadata: {path}"
                )
            accepted_raw[provenance_name] = observed[provenance_name]
        names = sorted(set(observed) - set(accepted_raw))
        if names:
            library = ctypes.CDLL("/usr/lib/libSystem.B.dylib", use_errno=True)
            library.removexattr.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]
            library.removexattr.restype = ctypes.c_int
            for name in names:
                if library.removexattr(os.fsencode(path), os.fsencode(name), 0x0001) != 0:
                    raise MetadataContractError(
                        f"inherited extended attribute cannot be removed from {path}: {name}"
                    )
        remaining = _read_macos_xattrs(path)
    else:
        accepted_raw = {}
        try:
            names = os.listxattr(path, follow_symlinks=False)
            for name in names:
                os.removexattr(path, name, follow_symlinks=False)
            remaining = {
                name: b"" for name in os.listxattr(path, follow_symlinks=False)
            }
        except (AttributeError, OSError) as exc:
            raise MetadataContractError(
                f"created-path extended attributes cannot be sanitised for {path}"
            ) from exc
    if remaining != accepted_raw:
        raise MetadataContractError(f"created path retains undeclared extended attributes: {path}")
    return {
        name: hashlib.sha256(value).hexdigest()
        for name, value in sorted(accepted_raw.items())
    }


def _ensure_create_parent_directories(
    prepared: PreparedTextPatch,
    targets: tuple[PreparedTextTarget, ...],
    created: list[Path],
    policy_check: Callable[[Path, Literal["read", "create", "modify", "delete"]], None] | None,
) -> None:
    """Create only missing parents for declared create targets.

    Each component is inspected without following a final symlink. Newly
    created components use one fixed non-writable-by-group-or-other mode and
    are fsynced through their parent before product-file staging begins.
    """

    working_directory = prepared.working_directory
    for target in targets:
        if target.action != "create":
            continue
        try:
            relative_parent = target.path.parent.relative_to(working_directory)
        except ValueError as exc:
            raise PatchContractError("patch create parent escapes its working directory") from exc
        current = working_directory
        for component in relative_parent.parts:
            candidate = current / component
            try:
                observed = candidate.lstat()
            except FileNotFoundError:
                if policy_check is not None:
                    policy_check(candidate, "create")
                try:
                    os.mkdir(candidate, CREATED_PARENT_DIRECTORY_MODE)
                except FileExistsError:
                    pass
                else:
                    created.append(candidate)
                    os.chmod(candidate, CREATED_PARENT_DIRECTORY_MODE)
                    _sanitise_created_extended_attributes(candidate)
                    _fsync_directory(current)
                try:
                    observed = candidate.lstat()
                except FileNotFoundError as exc:
                    raise PatchContractError(
                        f"patch create parent disappeared during preparation: {candidate}"
                    ) from exc
            if stat.S_ISLNK(observed.st_mode):
                raise PatchContractError(f"patch create parent is a symlink: {candidate}")
            if not stat.S_ISDIR(observed.st_mode):
                raise PatchContractError(f"patch create parent is not a directory: {candidate}")
            current = candidate


def _remove_empty_created_directories(paths: list[Path]) -> None:
    """Best-effort rollback for parent directories that contain no commit."""

    for path in reversed(paths):
        try:
            observed = path.lstat()
            if stat.S_ISLNK(observed.st_mode) or not stat.S_ISDIR(observed.st_mode):
                continue
            path.rmdir()
            _fsync_directory(path.parent)
        except (FileNotFoundError, OSError):
            continue


def commit_prepared_text_patch(
    prepared: PreparedTextPatch,
    metadata: dict[str, FileMetadataFingerprint],
    *,
    created_file_mode: int,
    checkpoint: Callable[[PreparedTextTarget], None] | None = None,
    metadata_loader: Callable[[Path], FileMetadataFingerprint] = capture_file_metadata,
    policy_check: Callable[[Path, Literal["read", "create", "modify", "delete"]], None] | None = None,
    start_index: int = 0,
) -> tuple[str, ...]:
    """Commit an already prepared patch without interpreting model output.

    Targets are committed in the order present in the canonical diff. Each
    modification is staged in the target directory, checked for metadata
    preservation, fsynced, and atomically replaced. Multi-target operation is
    deliberately sequential; callers must journal the committed prefix.
    """

    if not 0 <= created_file_mode <= 0o7777:
        raise PatchContractError("created file mode is outside the supported permission range")
    if not 0 <= start_index <= len(prepared.targets):
        raise PatchContractError("commit start index is outside the prepared target sequence")
    expected_existing = {
        str(item.path) for item in prepared.targets[start_index:] if item.action in {"modify", "delete"}
    }
    if set(metadata) != expected_existing:
        raise PatchContractError("metadata inventory differs from modified and deleted targets")
    remaining = prepared.targets[start_index:]
    created_directories: list[Path] = []
    try:
        _ensure_create_parent_directories(
            prepared, remaining, created_directories, policy_check
        )
        for target in remaining:
            if target.action == "create":
                if policy_check is not None:
                    policy_check(target.path, "create")
                if target.path.exists() or target.path.is_symlink():
                    raise PatchContractError(f"patch create target appeared before commit: {target.path}")
            else:
                if policy_check is not None:
                    policy_check(target.path, "read")
                try:
                    live = target.path.read_bytes()
                except OSError as exc:
                    raise PatchContractError(f"patch source changed before commit: {target.path}") from exc
                if hashlib.sha256(live).hexdigest() != target.preimage_hash:
                    raise PatchContractError(f"patch preimage changed before commit: {target.path}")
        for target in remaining:
            if target.action != "create":
                observed = metadata_loader(target.path)
                if observed != metadata[str(target.path)]:
                    raise MetadataContractError(f"target metadata changed before commit: {target.path}")

        committed: list[str] = []
        for target in remaining:
            if policy_check is not None:
                policy_check(target.path, target.action)
            parent = target.path.parent
            if target.action == "delete":
                target.path.unlink()
                _fsync_directory(parent)
            else:
                descriptor, temporary_name = tempfile.mkstemp(prefix=".rb-safe-stage-", suffix=".tmp", dir=parent)
                temporary = Path(temporary_name)
                try:
                    assert target.postimage is not None
                    with os.fdopen(descriptor, "wb") as handle:
                        handle.write(target.postimage)
                        handle.flush()
                        os.fsync(handle.fileno())
                    if target.action == "modify":
                        shutil.copystat(target.path, temporary, follow_symlinks=False)
                        expected = metadata[str(target.path)]
                        try:
                            os.chown(temporary, expected.uid, expected.gid, follow_symlinks=False)
                        except PermissionError as exc:
                            raise MetadataContractError(
                                f"target ownership cannot be preserved for {target.path}"
                            ) from exc
                        observed_stage = metadata_loader(temporary)
                        if not _same_preserved_metadata(expected, observed_stage):
                            raise MetadataContractError(
                                f"staged replacement cannot preserve target metadata: {target.path}"
                            )
                    else:
                        os.chmod(temporary, created_file_mode, follow_symlinks=False)
                        accepted_xattrs = _sanitise_created_extended_attributes(temporary)
                        observed_stage = metadata_loader(temporary)
                        if (
                            observed_stage.mode != created_file_mode
                            or observed_stage.link_count != 1
                            or observed_stage.acl_hash != hashlib.sha256(b"").hexdigest()
                            or (
                                observed_stage.extended_attribute_hashes
                                and observed_stage.extended_attribute_hashes != accepted_xattrs
                            )
                        ):
                            raise MetadataContractError(
                                f"created target would inherit undeclared metadata: {target.path}"
                            )
                    if hashlib.sha256(temporary.read_bytes()).hexdigest() != target.postimage_hash:
                        raise PatchContractError(f"staged postimage hash differs for {target.path}")
                    os.replace(temporary, target.path)
                    _fsync_directory(parent)
                finally:
                    try:
                        temporary.unlink()
                    except FileNotFoundError:
                        pass
            committed.append(str(target.path))
            if checkpoint is not None:
                checkpoint(target)
        return tuple(committed)
    except Exception:
        _remove_empty_created_directories(created_directories)
        raise
