from __future__ import annotations

import os
import unicodedata
from dataclasses import dataclass
from pathlib import Path, PurePosixPath


class PathViolation(ValueError):
    pass


@dataclass(frozen=True)
class ResolvedPath:
    supplied: str
    resolved: str
    nearest_existing_ancestor: str
    device: int
    inode: int | None
    links: int | None


def resolve_contained(path: str, allowed_roots: list[str], protected_roots: list[str], mutation: bool = False) -> ResolvedPath:
    if not path or "\0" in path or any(token in path for token in ("$", "*", "?", "[", "]")):
        raise PathViolation("path contains an empty, NUL, variable, or glob form")
    normalized = unicodedata.normalize("NFC", path.replace(os.sep, "/"))
    pure = PurePosixPath(normalized)
    if not pure.is_absolute() or ".." in pure.parts:
        raise PathViolation("path must be absolute and cannot contain lexical traversal")
    candidate = Path(str(pure))
    ancestor = candidate
    suffix: list[str] = []
    while not ancestor.exists():
        if ancestor.parent == ancestor:
            raise PathViolation("no existing ancestor")
        suffix.append(ancestor.name)
        ancestor = ancestor.parent
    ancestor_real = ancestor.resolve(strict=True)
    resolved = ancestor_real.joinpath(*reversed(suffix))
    roots = [Path(root).resolve(strict=True) for root in allowed_roots]
    if not any(_within(resolved, root) for root in roots):
        raise PathViolation("resolved path escapes allowed roots")
    protected = [Path(root).resolve(strict=False) for root in protected_roots]
    if mutation and any(_within(resolved, root) or _within(root, resolved) for root in protected):
        raise PathViolation("mutation intersects a protected root")
    stat = ancestor_real.stat()
    if candidate.exists():
        actual = candidate.resolve(strict=True)
        stat = actual.stat()
        resolved = actual
        if mutation and stat.st_nlink > 1:
            raise PathViolation("mutation of multiply linked file denied")
        if not (candidate.is_file() or candidate.is_dir()):
            raise PathViolation("special device paths are denied")
    return ResolvedPath(path, str(resolved), str(ancestor_real), stat.st_dev, stat.st_ino if candidate.exists() else None, stat.st_nlink if candidate.exists() else None)


def revalidate_path(prior: ResolvedPath, allowed_roots: list[str], protected_roots: list[str], mutation: bool = False) -> ResolvedPath:
    current = resolve_contained(prior.supplied, allowed_roots, protected_roots, mutation=mutation)
    if (prior.resolved, prior.device, prior.inode) != (current.resolved, current.device, current.inode):
        raise PathViolation("path identity changed after assessment")
    return current


def _within(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False
