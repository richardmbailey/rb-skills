from __future__ import annotations

import posixpath
import re


class PatchContractError(ValueError):
    """The supplied patch cannot be represented by the exact text-patch contract."""


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
        raise PatchContractError("patch must be a standard unified diff")
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
