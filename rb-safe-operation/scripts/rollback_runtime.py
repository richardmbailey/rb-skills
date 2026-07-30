#!/usr/bin/env python3
"""Select a retained, fully revalidated safe-operation runtime manifest."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import re
import sys


_SETUP_PATH = Path(__file__).resolve().with_name("setup_runtime.py")
if _SETUP_PATH.is_symlink() or not _SETUP_PATH.is_file():
    raise RuntimeError("trusted setup helper is missing or symbolic")
_SETUP_SPEC = importlib.util.spec_from_file_location(
    "_rb_safe_operation_setup_runtime", _SETUP_PATH
)
if _SETUP_SPEC is None or _SETUP_SPEC.loader is None:
    raise RuntimeError("trusted setup helper cannot be loaded")
_SETUP = importlib.util.module_from_spec(_SETUP_SPEC)
_SETUP_SPEC.loader.exec_module(_SETUP)

CLI_MODULE = _SETUP.CLI_MODULE
RUNTIME_VERSION = _SETUP.RUNTIME_VERSION
SCHEMA_VERSION = _SETUP.SCHEMA_VERSION
combined_lock_hash = _SETUP.combined_lock_hash
environment_tree_hash = _SETUP.environment_tree_hash
file_hash = _SETUP.file_hash
locate_installed_package = _SETUP.locate_installed_package
manifest_identity = _SETUP.manifest_identity
tree_hash = _SETUP.tree_hash
validate_installed_runtime = _SETUP.validate_installed_runtime
write_manifest = _SETUP.write_manifest


def _required_string(manifest: dict[str, object], field: str) -> str:
    value = manifest.get(field)
    if not isinstance(value, str) or not value:
        raise RuntimeError(f"rollback manifest has an invalid {field}")
    return value


def validate_rollback_manifest(
    manifest: dict[str, object],
    *,
    expected_manifest_hash: str,
) -> None:
    """Prove the retained source, launcher, interpreter, environment, and package identities."""

    if manifest.get("manifest_hash") != expected_manifest_hash:
        raise RuntimeError("rollback manifest identity differs from the requested hash")
    if manifest_identity(manifest) != expected_manifest_hash:
        raise RuntimeError("rollback manifest content differs from its identity")
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise RuntimeError("rollback manifest has an unsupported schema version")
    if manifest.get("runtime_version") != RUNTIME_VERSION:
        raise RuntimeError("rollback manifest has an unsupported runtime version")
    if manifest.get("cli_module") != CLI_MODULE:
        raise RuntimeError("rollback manifest has an unsupported CLI module")

    runtime_source = Path(_required_string(manifest, "runtime_source_path"))
    launcher = Path(_required_string(manifest, "verified_launcher_path"))
    interpreter = Path(_required_string(manifest, "interpreter_path"))
    bootstrap = Path(_required_string(manifest, "launcher_bootstrap_interpreter_path"))
    for label, path in (
        ("runtime source", runtime_source),
        ("verified launcher", launcher),
        ("bootstrap interpreter", bootstrap),
    ):
        if not path.is_absolute() or path.is_symlink():
            raise RuntimeError(f"rollback {label} path is not an absolute non-symbolic path")
    if not interpreter.is_absolute():
        raise RuntimeError("rollback interpreter path is not absolute")

    runtime_source = runtime_source.resolve(strict=True)
    launcher = launcher.resolve(strict=True)
    interpreter = interpreter.resolve(strict=True)
    bootstrap = bootstrap.resolve(strict=True)
    if not runtime_source.is_dir():
        raise RuntimeError("rollback runtime source is not a directory")
    expected_launcher = runtime_source.parent / "scripts" / "run_runtime.py"
    if launcher != expected_launcher.resolve(strict=True):
        raise RuntimeError("rollback launcher does not belong to the retained runtime source")
    if tree_hash(runtime_source) != _required_string(manifest, "installed_source_hash"):
        raise RuntimeError("rollback runtime source differs from the retained manifest")
    if combined_lock_hash(runtime_source) != _required_string(manifest, "lock_hash"):
        raise RuntimeError("rollback dependency locks differ from the retained manifest")
    if file_hash(launcher) != _required_string(manifest, "verified_launcher_hash"):
        raise RuntimeError("rollback launcher bytes differ from the retained manifest")

    active_bootstrap = Path(sys.executable).resolve(strict=True)
    if active_bootstrap != bootstrap or file_hash(bootstrap) != _required_string(
        manifest, "launcher_bootstrap_interpreter_hash"
    ):
        raise RuntimeError("rollback must use the retained bootstrap interpreter")
    if file_hash(interpreter) != _required_string(manifest, "interpreter_hash"):
        raise RuntimeError("rollback interpreter bytes differ from the retained manifest")
    if str(interpreter) != _required_string(manifest, "interpreter_resolved_path"):
        raise RuntimeError("rollback interpreter resolution differs from the retained manifest")

    environment_root = Path(_required_string(manifest, "interpreter_path")).parents[1]
    if environment_tree_hash(environment_root) != _required_string(
        manifest, "installed_environment_hash"
    ):
        raise RuntimeError("rollback installed environment differs from the retained manifest")
    package_path = locate_installed_package(environment_root.parent)
    if str(package_path) != _required_string(manifest, "installed_package_path"):
        raise RuntimeError("rollback package path differs from the retained manifest")
    validate_installed_runtime(
        Path(_required_string(manifest, "interpreter_path")),
        expected_source_hash=_required_string(manifest, "installed_source_hash"),
        expected_lock_hash=_required_string(manifest, "lock_hash"),
        expected_source_package_hash=_required_string(
            manifest, "expected_source_package_hash"
        ),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--control-root", required=True)
    parser.add_argument("--manifest-hash", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{64}", args.manifest_hash):
        print("runtime_rollback_failed: manifest hash must be 64 lowercase hexadecimal characters", file=sys.stderr)
        return 2
    control_value = Path(args.control_root).expanduser()
    if not control_value.is_absolute():
        print("runtime_rollback_failed: control root must be absolute", file=sys.stderr)
        return 2
    try:
        control = control_value.resolve(strict=True)
        if control.is_symlink() or not control.is_dir():
            raise RuntimeError("control root is not a non-symbolic directory")
        archive = control / "manifests" / f"{args.manifest_hash}.json"
        if archive.is_symlink() or not archive.is_file():
            raise RuntimeError("requested retained manifest is missing or unsafe")
        raw = archive.read_bytes()
        manifest = json.loads(raw)
        if not isinstance(manifest, dict):
            raise RuntimeError("retained manifest is not an object")
        canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"
        if raw != canonical:
            raise RuntimeError("retained manifest is not canonical")
        validate_rollback_manifest(
            manifest,
            expected_manifest_hash=args.manifest_hash,
        )
        write_manifest(control, manifest)
    except Exception as exc:
        print(f"runtime_rollback_failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(manifest, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
