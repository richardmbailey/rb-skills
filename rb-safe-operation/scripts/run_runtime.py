#!/usr/bin/env python3
"""Invoke the explicit manifest-pinned runtime without installing anything."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path


RUNTIME_VERSION = "0.1.0"
SCHEMA_VERSION = "1.0"
CLI_MODULE = "rb_safe_operation.cli"


def canonical_control_root() -> Path:
    """Return the one normal control-plane location."""

    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    return codex_home.expanduser().resolve() / "rb-safe-operation"


def validate_bootstrap_flags() -> bool:
    return bool(sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode)


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tree_hash(root: Path) -> str:
    rows = []
    candidates = [root / "pyproject.toml", *sorted((root / "src" / "rb_safe_operation").rglob("*"))]
    for path in candidates:
        if (
            path.is_file()
            and "__pycache__" not in path.parts
            and not path.name.endswith(".pyc")
            and path.name != "_source_identity.json"
        ):
            rows.append({"path": path.relative_to(root).as_posix(), "sha256": file_hash(path)})
    body = json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(b"rb-safe-operation\0runtime-source-tree\0" + b"1.0\0" + body).hexdigest()


def combined_lock_hash(runtime: Path) -> str:
    rows = [
        {"path": name, "sha256": file_hash(runtime / name)}
        for name in ("build-requirements.lock", "requirements.lock")
    ]
    body = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode("ascii")
    return hashlib.sha256(b"rb-safe-operation\0runtime-lock-set\0" + b"1.0\0" + body).hexdigest()


def package_tree_hash(package_root: Path) -> str:
    rows = []
    for path in sorted(package_root.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts and not path.name.endswith(".pyc") and path.name != "_source_identity.json":
            rows.append({"path": path.relative_to(package_root).as_posix(), "sha256": file_hash(path)})
    body = json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(b"rb-safe-operation\0installed-package-tree\0" + b"1.0\0" + body).hexdigest()


def environment_tree_hash(venv_root: Path) -> str:
    rows: list[dict[str, object]] = []
    for path in sorted(venv_root.rglob("*")):
        stat = path.lstat()
        row: dict[str, object] = {"path": path.relative_to(venv_root).as_posix(), "mode": stat.st_mode}
        if path.is_symlink():
            row.update({"kind": "symlink", "target": os.readlink(path)})
        elif path.is_file():
            row.update({"kind": "file", "sha256": file_hash(path)})
        elif path.is_dir():
            row["kind"] = "directory"
        else:
            row["kind"] = "other"
        rows.append(row)
    body = json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(b"rb-safe-operation\0installed-environment-tree\0" + b"1.0\0" + body).hexdigest()


def main() -> int:
    if not validate_bootstrap_flags():
        print(
            "unsafe_runtime_bootstrap: invoke the absolute trusted Python interpreter "
            "with -I -S -B and the absolute verified launcher path",
            file=sys.stderr,
        )
        return 2
    if not Path(sys.argv[0]).is_absolute():
        print("unsafe_runtime_bootstrap: verified launcher path must be absolute", file=sys.stderr)
        return 2
    remaining = sys.argv[1:]
    control = canonical_control_root()
    manifest_path = control / "current.json"
    if not manifest_path.is_file():
        print(f"missing_runtime_manifest: expected {manifest_path}; run setup_runtime.py explicitly", file=sys.stderr)
        return 2
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"missing_runtime_environment: invalid manifest {manifest_path}: {exc}", file=sys.stderr)
        return 2
    if not isinstance(manifest, dict):
        print(f"missing_runtime_environment: manifest must be an object: {manifest_path}", file=sys.stderr)
        return 2
    if manifest.get("schema_version") != SCHEMA_VERSION:
        print(f"runtime_schema_version_mismatch: expected {SCHEMA_VERSION}, observed {manifest.get('schema_version')}", file=sys.stderr)
        return 2
    if manifest.get("runtime_version") != RUNTIME_VERSION:
        print(f"runtime_schema_version_mismatch: expected runtime {RUNTIME_VERSION}, observed {manifest.get('runtime_version')}", file=sys.stderr)
        return 2
    if manifest.get("cli_module") != CLI_MODULE:
        print(f"runtime_schema_version_mismatch: expected CLI module {CLI_MODULE}, observed {manifest.get('cli_module')}", file=sys.stderr)
        return 2
    try:
        bootstrap = Path(sys.executable).resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        print(f"unsafe_runtime_bootstrap: cannot resolve current interpreter: {exc}", file=sys.stderr)
        return 2
    if (
        manifest.get("launcher_bootstrap_interpreter_path") != str(bootstrap)
        or manifest.get("launcher_bootstrap_interpreter_hash") != file_hash(bootstrap)
    ):
        print(
            "unsafe_runtime_bootstrap: current interpreter identity differs from the explicit setup manifest",
            file=sys.stderr,
        )
        return 2
    launcher = Path(__file__).resolve()
    if manifest.get("verified_launcher_path") != str(launcher) or manifest.get("verified_launcher_hash") != file_hash(launcher):
        print("runtime_source_hash_mismatch: verified launcher identity differs from the manifest; rerun explicit setup", file=sys.stderr)
        return 2
    expected_source = Path(__file__).resolve().parents[1] / "runtime"
    required_source = [
        expected_source / "pyproject.toml",
        expected_source / "requirements.lock",
        expected_source / "build-requirements.lock",
        expected_source / "src" / "rb_safe_operation",
    ]
    if not all(path.exists() for path in required_source):
        print(f"missing_runtime_skill: expected runtime source {expected_source}", file=sys.stderr)
        return 2
    runtime_source_path = manifest.get("runtime_source_path")
    if not isinstance(runtime_source_path, str) or not Path(runtime_source_path).is_absolute():
        print("runtime_source_hash_mismatch: manifest runtime_source_path must be absolute; rerun explicit setup", file=sys.stderr)
        return 2
    if Path(runtime_source_path).resolve() != expected_source.resolve():
        print("runtime_source_hash_mismatch: manifest belongs to a different installed source; rerun explicit setup", file=sys.stderr)
        return 2
    observed_source_hash = tree_hash(expected_source)
    if manifest.get("installed_source_hash") != observed_source_hash:
        print(f"runtime_source_hash_mismatch: expected {manifest.get('installed_source_hash')}, observed {observed_source_hash}; rerun explicit setup", file=sys.stderr)
        return 2
    observed_lock_hash = combined_lock_hash(expected_source)
    if manifest.get("lock_hash") != observed_lock_hash:
        print(f"runtime_source_hash_mismatch: expected lock {manifest.get('lock_hash')}, observed {observed_lock_hash}; rerun explicit setup", file=sys.stderr)
        return 2
    interpreter_value = manifest.get("interpreter_path")
    if not isinstance(interpreter_value, str):
        print("missing_runtime_environment: manifest interpreter_path must be an absolute string", file=sys.stderr)
        return 2
    interpreter = Path(interpreter_value)
    if not interpreter.is_absolute() or not interpreter.is_file():
        print(f"missing_runtime_environment: expected absolute interpreter {interpreter}; run setup_runtime.py explicitly", file=sys.stderr)
        return 2
    resolved_interpreter = interpreter.resolve(strict=True)
    if manifest.get("interpreter_resolved_path") != str(resolved_interpreter) or manifest.get("interpreter_hash") != file_hash(resolved_interpreter):
        print("runtime_source_hash_mismatch: interpreter bytes differ from the explicit setup manifest", file=sys.stderr)
        return 2
    venv_root = interpreter.parents[1]
    observed_environment_hash = environment_tree_hash(venv_root)
    if manifest.get("installed_environment_hash") != observed_environment_hash:
        print("runtime_source_hash_mismatch: installed environment or dependency bytes differ from the setup manifest", file=sys.stderr)
        return 2
    package_value = manifest.get("installed_package_path")
    if not isinstance(package_value, str) or not Path(package_value).is_absolute():
        print("missing_runtime_environment: installed_package_path must be absolute", file=sys.stderr)
        return 2
    package_root = Path(package_value).resolve(strict=True)
    try:
        package_root.relative_to(interpreter.parents[1])
    except ValueError:
        print("runtime_source_hash_mismatch: installed package is outside the manifest environment", file=sys.stderr)
        return 2
    observed_package_hash = package_tree_hash(package_root)
    expected_source_package_hash = package_tree_hash(expected_source / "src" / "rb_safe_operation")
    if (
        manifest.get("installed_package_hash") != observed_package_hash
        or manifest.get("expected_source_package_hash") != expected_source_package_hash
        or observed_package_hash != expected_source_package_hash
    ):
        print("runtime_source_hash_mismatch: installed package bytes differ from the reviewed source package tree", file=sys.stderr)
        return 2
    preflight = subprocess.run(
        [str(interpreter), "-I", "-B", "-c", "import json,sys; import pydantic; print(json.dumps({'python':list(sys.version_info[:3]),'pydantic':pydantic.__version__}))"],
        check=False,
        capture_output=True,
        text=True,
    )
    if preflight.returncode != 0:
        print("missing_pydantic: manifest interpreter cannot import Pydantic; run setup_runtime.py explicitly", file=sys.stderr)
        return 2
    try:
        versions = json.loads(preflight.stdout)
        python_version = tuple(versions["python"])
        pydantic_parts = tuple(int(item) for item in versions["pydantic"].split(".")[:2])
    except Exception as exc:
        print(f"missing_runtime_environment: invalid version preflight output: {exc}", file=sys.stderr)
        return 2
    if python_version < (3, 9, 0):
        print(f"unsupported_python_version: expected >=3.9, observed {versions['python']}", file=sys.stderr)
        return 2
    pydantic_major, pydantic_minor = pydantic_parts
    if (pydantic_major, pydantic_minor) < (2, 12) or pydantic_major >= 3:
        print(f"unsupported_pydantic_version: expected >=2.12,<3, observed {versions['pydantic']}", file=sys.stderr)
        return 2
    identity_result = subprocess.run(
        [str(interpreter), "-I", "-B", "-m", CLI_MODULE, "runtime-info"],
        check=False,
        capture_output=True,
        text=True,
    )
    if identity_result.returncode != 0:
        print(f"runtime_source_hash_mismatch: installed runtime-info failed: {identity_result.stderr.strip()[:300]}", file=sys.stderr)
        return 2
    try:
        identity = json.loads(identity_result.stdout)
    except Exception as exc:
        print(f"runtime_source_hash_mismatch: installed runtime-info returned invalid JSON: {exc}", file=sys.stderr)
        return 2
    expected_identity = {
        "runtime_version": RUNTIME_VERSION,
        "schema_version": SCHEMA_VERSION,
        "runtime_source_hash": observed_source_hash,
        "runtime_lock_hash": observed_lock_hash,
        "installed_package_hash": manifest.get("installed_package_hash"),
        "recorded_installed_package_hash": manifest.get("installed_package_hash"),
    }
    identity_mismatches = {
        field: {"expected": expected, "observed": identity.get(field) if isinstance(identity, dict) else None}
        for field, expected in expected_identity.items()
        if not isinstance(identity, dict) or identity.get(field) != expected
    }
    if identity_mismatches:
        print(f"runtime_source_hash_mismatch: installed runtime identity mismatch: {json.dumps(identity_mismatches, sort_keys=True)}", file=sys.stderr)
        return 2
    result = subprocess.run([str(interpreter), "-I", "-B", "-m", CLI_MODULE, *remaining], check=False)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
