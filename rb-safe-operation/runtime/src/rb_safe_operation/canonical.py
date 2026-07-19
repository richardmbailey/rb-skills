from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path
from typing import Any


_DECIMAL = re.compile(r"^(?:0|[1-9][0-9]*)(?:\.[0-9]*[1-9])?$")


class CanonicalizationError(ValueError):
    pass


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    normalized: set[str] = set()
    for key, value in pairs:
        if key in result:
            raise CanonicalizationError(f"duplicate key: {key}")
        norm = unicodedata.normalize("NFC", key)
        if norm in normalized:
            raise CanonicalizationError(f"keys collide after NFC normalization: {key}")
        normalized.add(norm)
        result[key] = value
    return result


def parse_json_strict(data: bytes | str) -> Any:
    if isinstance(data, bytes):
        if data.startswith(b"\xef\xbb\xbf"):
            raise CanonicalizationError("UTF-8 BOM is forbidden")
        try:
            text = data.decode("utf-8", "strict")
        except UnicodeDecodeError as exc:
            raise CanonicalizationError("input is not strict UTF-8") from exc
    else:
        text = data
    if any(0xD800 <= ord(char) <= 0xDFFF for char in text):
        raise CanonicalizationError("unpaired surrogate is forbidden")
    try:
        return json.loads(
            text,
            object_pairs_hook=_pairs,
            parse_float=lambda value: (_ for _ in ()).throw(CanonicalizationError(f"float forbidden: {value}")),
            parse_constant=lambda value: (_ for _ in ()).throw(CanonicalizationError(f"constant forbidden: {value}")),
        )
    except json.JSONDecodeError as exc:
        raise CanonicalizationError(str(exc)) from exc


def normalize(value: Any) -> Any:
    if isinstance(value, str):
        if any(0xD800 <= ord(char) <= 0xDFFF for char in value):
            raise CanonicalizationError("unpaired surrogate is forbidden")
        return unicodedata.normalize("NFC", value.replace("\r\n", "\n").replace("\r", "\n"))
    if value is None or isinstance(value, (bool, int)):
        return value
    if isinstance(value, float):
        raise CanonicalizationError("floating-point values are forbidden")
    if isinstance(value, list):
        return [normalize(item) for item in value]
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in value.items():
            norm_key = normalize(key)
            if norm_key in result:
                raise CanonicalizationError(f"keys collide after normalization: {key}")
            result[norm_key] = normalize(item)
        return result
    if hasattr(value, "model_dump"):
        return normalize(value.model_dump(mode="json"))
    raise CanonicalizationError(f"unsupported canonical type: {type(value).__name__}")


def canonical_bytes(value: Any) -> bytes:
    normalized = normalize(value)
    return json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def artifact_hash(artifact_type: str, schema_version: str, payload: Any) -> str:
    for token in (artifact_type, schema_version):
        if not token.isascii() or "\0" in token:
            raise CanonicalizationError("artifact type and schema version must be ASCII without NUL")
    data = b"rb-safe-operation\0" + artifact_type.encode("ascii") + b"\0" + schema_version.encode("ascii") + b"\0" + canonical_bytes(payload)
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_tree_hash(runtime_root: Path) -> str:
    entries: list[dict[str, str]] = []
    candidates = [runtime_root / "pyproject.toml", *sorted((runtime_root / "src").rglob("*"))]
    for path in candidates:
        generated = (
            "__pycache__" in path.parts
            or any(part.endswith(".egg-info") for part in path.parts)
            or path.name.endswith(".pyc")
            or path.name == "_source_identity.json"
        )
        if path.is_file() and not generated:
            entries.append({"path": path.relative_to(runtime_root).as_posix(), "sha256": sha256_file(path)})
    return artifact_hash("runtime-source-tree", "1.0", entries)


def canonical_decimal(value: str) -> str:
    if not _DECIMAL.fullmatch(value):
        raise CanonicalizationError("decimal must be unsigned, non-exponent, and have no insignificant zeros")
    return value
