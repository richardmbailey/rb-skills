#!/usr/bin/env python3
"""Explicitly provision the dedicated runtime. This script never runs implicitly."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


RUNTIME_VERSION = "0.1.0"
SCHEMA_VERSION = "1.0"
CLI_MODULE = "rb_safe_operation.cli"


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
        if (
            path.is_file()
            and "__pycache__" not in path.parts
            and not path.name.endswith(".pyc")
            and path.name != "_source_identity.json"
        ):
            rows.append({"path": path.relative_to(package_root).as_posix(), "sha256": file_hash(path)})
    body = json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(b"rb-safe-operation\0installed-package-tree\0" + b"1.0\0" + body).hexdigest()


def environment_tree_hash(venv_root: Path) -> str:
    rows: list[dict[str, object]] = []
    for path in sorted(venv_root.rglob("*")):
        stat = path.lstat()
        row: dict[str, object] = {
            "path": path.relative_to(venv_root).as_posix(),
            "mode": stat.st_mode,
        }
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


def locate_installed_package(environment_root: Path) -> Path:
    candidates = sorted((environment_root / "venv" / "lib").glob("python*/site-packages/rb_safe_operation"))
    if len(candidates) != 1 or not candidates[0].is_dir():
        raise RuntimeError(f"installed package path is missing or ambiguous: {candidates}")
    return candidates[0].resolve(strict=True)


def runtime_info(interpreter: Path) -> dict[str, object]:
    result = subprocess.run(
        [str(interpreter), "-I", "-B", "-m", CLI_MODULE, "runtime-info"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"installed runtime-info failed: {result.stderr.strip()[:300]}")
    try:
        parsed = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("installed runtime-info returned invalid JSON") from exc
    if not isinstance(parsed, dict):
        raise RuntimeError("installed runtime-info must return an object")
    return parsed


def validate_installed_runtime(
    interpreter: Path,
    *,
    expected_source_hash: str,
    expected_lock_hash: str,
    expected_source_package_hash: str,
) -> dict[str, object]:
    if not interpreter.is_file():
        raise RuntimeError(f"installed interpreter is missing: {interpreter}")
    environment_root = interpreter.parents[2]
    package_root = locate_installed_package(environment_root)
    observed_package_hash = package_tree_hash(package_root)
    if observed_package_hash != expected_source_package_hash:
        raise RuntimeError("installed package tree differs from the reviewed source package tree")
    parsed = runtime_info(interpreter)
    expected = {
        "runtime_version": RUNTIME_VERSION,
        "schema_version": SCHEMA_VERSION,
        "runtime_source_hash": expected_source_hash,
        "runtime_lock_hash": expected_lock_hash,
    }
    mismatches = {
        field: {"expected": value, "observed": parsed.get(field)}
        for field, value in expected.items()
        if parsed.get(field) != value
    }
    installed_hash = parsed.get("installed_package_hash")
    recorded_hash = parsed.get("recorded_installed_package_hash")
    if not isinstance(installed_hash, str) or installed_hash != recorded_hash:
        mismatches["installed_package_hash"] = {
            "expected": recorded_hash,
            "observed": installed_hash,
        }
    if installed_hash != expected_source_package_hash:
        mismatches["source_package_hash"] = {
            "expected": expected_source_package_hash,
            "observed": installed_hash,
        }
    if mismatches:
        raise RuntimeError(f"installed runtime identity mismatch: {json.dumps(mismatches, sort_keys=True)}")
    return parsed


def copy_runtime_source(runtime: Path, destination: Path) -> None:
    shutil.copytree(
        runtime,
        destination,
        ignore=shutil.ignore_patterns("build", "*.egg-info", "__pycache__", "*.pyc", ".pytest_cache", "_source_identity.json"),
    )


def write_manifest(control: Path, manifest: dict[str, object]) -> None:
    descriptor, temporary_name = tempfile.mkstemp(prefix=".current-", suffix=".json.tmp", dir=control)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, control / "current.json")
    finally:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--control-root", required=True)
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--runtime-root", default=str(Path(__file__).resolve().parents[1] / "runtime"))
    parser.add_argument("--wheelhouse", required=True)
    args = parser.parse_args()
    runtime = Path(args.runtime_root).resolve()
    verified_launcher = Path(__file__).resolve().with_name("run_runtime.py")
    control = Path(args.control_root).resolve()
    wheelhouse = Path(args.wheelhouse).resolve()
    try:
        bootstrap_interpreter = Path(args.python).expanduser().resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        print(f"unsupported_python_version: cannot resolve bootstrap interpreter {args.python}: {exc}", file=sys.stderr)
        return 2
    if not bootstrap_interpreter.is_file():
        print(f"unsupported_python_version: bootstrap interpreter is not a file: {bootstrap_interpreter}", file=sys.stderr)
        return 2
    required = [runtime / "pyproject.toml", runtime / "requirements.lock", runtime / "build-requirements.lock", runtime / "src", verified_launcher]
    if not all(path.exists() for path in required):
        print(f"missing_runtime_skill: incomplete runtime source at {runtime}", file=sys.stderr)
        return 2
    if not wheelhouse.is_dir():
        print(f"copy_install_dependency_missing: wheelhouse does not exist: {wheelhouse}", file=sys.stderr)
        return 2
    python_version = subprocess.run(
        [str(bootstrap_interpreter), "-I", "-S", "-B", "-c", "import json,sys; print(json.dumps(list(sys.version_info[:3])))"],
        check=False,
        capture_output=True,
        text=True,
    )
    if python_version.returncode != 0 or tuple(json.loads(python_version.stdout)) < (3, 9, 0):
        observed = python_version.stdout.strip() or python_version.stderr.strip()
        print(f"unsupported_python_version: expected >=3.9, observed {observed}", file=sys.stderr)
        return 2
    lock_hash = combined_lock_hash(runtime)
    source_hash = tree_hash(runtime)
    source_package_hash = package_tree_hash(runtime / "src" / "rb_safe_operation")
    setup_key = hashlib.sha256(f"{RUNTIME_VERSION}:{lock_hash}".encode("ascii")).hexdigest()
    control.mkdir(parents=True, mode=0o700, exist_ok=True)
    lock = control / f"setup-{setup_key}.lock"
    try:
        descriptor = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        print("setup_lock_conflict: another explicit setup owns this runtime", file=sys.stderr)
        return 2
    os.close(descriptor)
    temporary = Path(tempfile.mkdtemp(prefix="rb-safe-operation-setup-", dir=control))
    target = control / "environments" / f"{RUNTIME_VERSION}-{source_hash}-{lock_hash}"
    stage = "environment_creation"
    try:
        if target.exists():
            prior_manifest_path = control / "current.json"
            try:
                prior_manifest = json.loads(prior_manifest_path.read_text(encoding="utf-8"))
            except Exception as exc:
                raise RuntimeError("existing environment has no readable setup manifest") from exc
            observed_environment_hash = environment_tree_hash(target / "venv")
            if (
                prior_manifest.get("interpreter_path") != str(target / "venv" / "bin" / "python")
                or prior_manifest.get("installed_environment_hash") != observed_environment_hash
            ):
                raise RuntimeError("existing environment tree differs from its setup manifest")
            parsed = validate_installed_runtime(
                target / "venv" / "bin" / "python",
                expected_source_hash=source_hash,
                expected_lock_hash=lock_hash,
                expected_source_package_hash=source_package_hash,
            )
            installed_package_hash = str(parsed["installed_package_hash"])
            installed_python = target / "venv" / "bin" / "python"
            installed_environment_hash = observed_environment_hash
        else:
            source_copy = temporary / "source"
            copy_runtime_source(runtime, source_copy)
            if tree_hash(source_copy) != source_hash:
                raise RuntimeError("temporary runtime source identity mismatch")
            environment = temporary / "venv"
            subprocess.run([str(bootstrap_interpreter), "-I", "-B", "-m", "venv", str(environment)], check=True)
            python = environment / "bin" / "python"
            pip = environment / "bin" / "pip"
            stage = "dependency_install"
            subprocess.run([str(pip), "install", "--no-index", "--find-links", str(wheelhouse), "--require-hashes", "-r", str(runtime / "build-requirements.lock")], check=True)
            subprocess.run([str(pip), "install", "--no-index", "--find-links", str(wheelhouse), "--require-hashes", "-r", str(runtime / "requirements.lock")], check=True)
            stage = "package_install"
            subprocess.run([str(pip), "install", "--no-deps", "--no-build-isolation", str(source_copy)], check=True)
            package_dir = locate_installed_package(temporary)
            installed_package_hash = package_tree_hash(package_dir)
            if installed_package_hash != source_package_hash:
                raise RuntimeError("built package tree differs from the reviewed source package tree")
            (package_dir / "_source_identity.json").write_text(
                json.dumps(
                    {
                        "runtime_source_hash": source_hash,
                        "runtime_lock_hash": lock_hash,
                        "installed_package_hash": installed_package_hash,
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                )
                + "\n",
                encoding="utf-8",
            )
            validate_installed_runtime(
                python,
                expected_source_hash=source_hash,
                expected_lock_hash=lock_hash,
                expected_source_package_hash=source_package_hash,
            )
            shutil.rmtree(source_copy)
            target.parent.mkdir(parents=True, exist_ok=True)
            os.replace(temporary, target)
            installed_python = target / "venv" / "bin" / "python"
            installed_environment_hash = environment_tree_hash(target / "venv")
        installed_package_path = locate_installed_package(target)
        resolved_interpreter = installed_python.resolve(strict=True)
        manifest = {
            "schema_version": SCHEMA_VERSION,
            "runtime_version": RUNTIME_VERSION,
            "interpreter_path": str(installed_python),
            "cli_module": CLI_MODULE,
            "lock_hash": lock_hash,
            "installed_source_hash": source_hash,
            "installed_package_hash": installed_package_hash,
            "expected_source_package_hash": source_package_hash,
            "installed_package_path": str(installed_package_path),
            "installed_environment_hash": installed_environment_hash,
            "interpreter_resolved_path": str(resolved_interpreter),
            "interpreter_hash": file_hash(resolved_interpreter),
            "runtime_source_path": str(runtime),
            "verified_launcher_path": str(verified_launcher),
            "verified_launcher_hash": file_hash(verified_launcher),
            "launcher_bootstrap_interpreter_path": str(bootstrap_interpreter),
            "launcher_bootstrap_interpreter_hash": file_hash(bootstrap_interpreter),
        }
        write_manifest(control, manifest)
        print(json.dumps(manifest, sort_keys=True))
        return 0
    except Exception as exc:
        diagnostic = "copy_install_dependency_missing" if stage == "dependency_install" else "runtime_setup_failed"
        print(f"{diagnostic}: stage={stage}: {exc}", file=sys.stderr)
        return 2
    finally:
        try:
            shutil.rmtree(temporary)
        except FileNotFoundError:
            pass
        try:
            lock.unlink()
        except FileNotFoundError:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
