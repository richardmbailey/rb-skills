from __future__ import annotations

import ctypes
import os
import sys
import tempfile
import unittest
import hashlib
from pathlib import Path
from unittest.mock import patch

from rb_safe_operation.patches import (
    MetadataContractError,
    PatchContractError,
    _read_macos_xattrs,
    capture_file_metadata,
    commit_prepared_text_patch,
    prepare_text_patch,
    validate_live_preimages,
)
from rb_safe_operation.proposal_models import FileMetadataFingerprint


class PurePatchPreparationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        self.target = self.root / "input.txt"
        self.target.write_bytes(b"a\n")
        self.patch = "--- a/input.txt\n+++ b/input.txt\n@@ -1 +1 @@\n-a\n+b\n"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_preparation_materialises_postimage_without_reading_or_writing_target(self):
        before = self.target.read_bytes()
        with patch.object(Path, "read_bytes", side_effect=AssertionError("preparation read live product state")):
            prepared = prepare_text_patch(self.patch, self.root, {str(self.target): before})
        self.assertEqual(self.target.read_bytes(), b"a\n")
        self.assertEqual(len(prepared.targets), 1)
        self.assertEqual(prepared.targets[0].action, "modify")
        self.assertEqual(prepared.targets[0].preimage, b"a\n")
        self.assertEqual(prepared.targets[0].postimage, b"b\n")

    def test_preparation_rejects_missing_or_wrong_captured_preimage(self):
        with self.assertRaisesRegex(PatchContractError, "captured preimage"):
            prepare_text_patch(self.patch, self.root, {})
        with self.assertRaisesRegex(PatchContractError, "preimage text"):
            prepare_text_patch(self.patch, self.root, {str(self.target): b"different\n"})

    def test_live_preimage_validation_detects_stale_content(self):
        prepared = prepare_text_patch(self.patch, self.root, {str(self.target): b"a\n"})
        self.target.write_bytes(b"concurrent\n")
        with self.assertRaisesRegex(PatchContractError, "changed before commit"):
            validate_live_preimages(prepared)

    def test_malformed_or_duplicate_target_diff_is_rejected(self):
        with self.assertRaises(PatchContractError):
            prepare_text_patch("not a diff", self.root, {})
        duplicate = self.patch + self.patch
        with self.assertRaisesRegex(PatchContractError, "more than once"):
            prepare_text_patch(duplicate, self.root, {str(self.target): b"a\n"})

    def test_hard_link_metadata_is_rejected(self):
        alias = self.root / "alias.txt"
        os.link(self.target, alias)
        with self.assertRaisesRegex(MetadataContractError, "hard-linked"):
            capture_file_metadata(self.target, acl_reader=lambda _: b"", xattr_reader=lambda _: {})

    def test_unavailable_acl_or_xattr_inspection_is_rejected(self):
        with self.assertRaisesRegex(MetadataContractError, "ACL inspection"):
            capture_file_metadata(self.target, acl_reader=None, xattr_reader=lambda _: {})
        with self.assertRaisesRegex(MetadataContractError, "extended attributes"):
            capture_file_metadata(self.target, acl_reader=lambda _: b"", xattr_reader=None)

    def test_default_metadata_inspector_matches_the_supported_host_profile(self):
        if sys.platform != "darwin":
            with self.assertRaisesRegex(MetadataContractError, "unavailable on this host"):
                capture_file_metadata(self.target)
            return
        metadata = capture_file_metadata(self.target)
        self.assertEqual(metadata.file_type, "regular")
        self.assertEqual(metadata.link_count, 1)
        self.assertEqual(metadata.content_hash, __import__("hashlib").sha256(b"a\n").hexdigest())

    def _portable_metadata(self, path: Path) -> FileMetadataFingerprint:
        return capture_file_metadata(path, acl_reader=lambda _: b"", xattr_reader=lambda _: {})

    def test_commit_preserves_modified_file_metadata_and_records_target(self):
        os.chmod(self.target, 0o640)
        before = self.target.read_bytes()
        prepared = prepare_text_patch(self.patch, self.root, {str(self.target): before})
        metadata = self._portable_metadata(self.target)
        committed = []
        result = commit_prepared_text_patch(
            prepared,
            {str(self.target): metadata},
            created_file_mode=0o600,
            checkpoint=lambda item: committed.append(str(item.path)),
            metadata_loader=self._portable_metadata,
        )
        self.assertEqual(result, (str(self.target),))
        self.assertEqual(committed, [str(self.target)])
        self.assertEqual(self.target.read_bytes(), b"b\n")
        self.assertEqual(self.target.stat().st_mode & 0o7777, 0o640)

    def test_commit_supports_create_and_delete_with_explicit_create_mode(self):
        created = self.root / "new.txt"
        patch_text = (
            "--- /dev/null\n+++ b/new.txt\n@@ -0,0 +1 @@\n+new\n"
            "--- a/input.txt\n+++ /dev/null\n@@ -1 +0,0 @@\n-a\n"
        )
        prepared = prepare_text_patch(patch_text, self.root, {str(self.target): b"a\n"})
        commit_prepared_text_patch(
            prepared,
            {str(self.target): self._portable_metadata(self.target)},
            created_file_mode=0o640,
            metadata_loader=self._portable_metadata,
        )
        self.assertFalse(self.target.exists())
        self.assertEqual(created.read_bytes(), b"new\n")
        self.assertEqual(created.stat().st_mode & 0o7777, 0o640)

    def test_commit_creates_missing_parent_directories_with_fixed_safe_mode(self):
        created = self.root / "examples" / "nested" / "new.txt"
        patch_text = (
            "--- /dev/null\n"
            "+++ b/examples/nested/new.txt\n"
            "@@ -0,0 +1 @@\n"
            "+new\n"
        )
        prepared = prepare_text_patch(patch_text, self.root, {})

        result = commit_prepared_text_patch(
            prepared,
            {},
            created_file_mode=0o640,
            metadata_loader=self._portable_metadata,
        )

        self.assertEqual(result, (str(created),))
        self.assertEqual(created.read_bytes(), b"new\n")
        self.assertEqual(created.stat().st_mode & 0o7777, 0o640)
        self.assertEqual((self.root / "examples").stat().st_mode & 0o7777, 0o755)
        self.assertEqual((self.root / "examples" / "nested").stat().st_mode & 0o7777, 0o755)

    def test_policy_callback_runs_before_implicit_parent_creation(self):
        created = self.root / "private" / "nested" / "new.txt"
        patch_text = (
            "--- /dev/null\n"
            "+++ b/private/nested/new.txt\n"
            "@@ -0,0 +1 @@\n"
            "+new\n"
        )
        prepared = prepare_text_patch(patch_text, self.root, {})
        observed = []

        def policy_check(path: Path, capability: str) -> None:
            observed.append((path, capability))
            if path == self.root / "private" and capability == "create":
                raise PermissionError("project policy denied implicit parent creation")

        with self.assertRaisesRegex(PermissionError, "implicit parent creation"):
            commit_prepared_text_patch(
                prepared, {}, created_file_mode=0o640,
                metadata_loader=self._portable_metadata,
                policy_check=policy_check,
            )
        self.assertEqual(observed[0], (self.root / "private", "create"))
        self.assertFalse((self.root / "private").exists())
        self.assertFalse(created.exists())

    def test_commit_rejects_parent_replaced_by_symlink_after_preparation(self):
        created = self.root / "nested" / "new.txt"
        outside = self.root.parent / f"{self.root.name}-outside"
        outside.mkdir()
        self.addCleanup(outside.rmdir)
        patch_text = (
            "--- /dev/null\n"
            "+++ b/nested/new.txt\n"
            "@@ -0,0 +1 @@\n"
            "+new\n"
        )
        prepared = prepare_text_patch(patch_text, self.root, {})
        (self.root / "nested").symlink_to(outside, target_is_directory=True)

        with self.assertRaisesRegex(PatchContractError, "parent.*symlink"):
            commit_prepared_text_patch(
                prepared,
                {},
                created_file_mode=0o640,
                metadata_loader=self._portable_metadata,
            )

        self.assertFalse((outside / "new.txt").exists())
        self.assertFalse(created.exists())

    def test_parent_preparation_failure_rolls_back_new_empty_directories(self):
        blocked_parent = self.root / "blocked"
        blocked_parent.write_text("not a directory\n", encoding="utf-8")
        patch_text = (
            "--- /dev/null\n"
            "+++ b/new/tree/first.txt\n"
            "@@ -0,0 +1 @@\n"
            "+first\n"
            "--- /dev/null\n"
            "+++ b/blocked/second.txt\n"
            "@@ -0,0 +1 @@\n"
            "+second\n"
        )
        prepared = prepare_text_patch(patch_text, self.root, {})

        with self.assertRaisesRegex(PatchContractError, "parent.*not a directory"):
            commit_prepared_text_patch(
                prepared,
                {},
                created_file_mode=0o640,
                metadata_loader=self._portable_metadata,
            )

        self.assertFalse((self.root / "new").exists())
        self.assertEqual(blocked_parent.read_text(encoding="utf-8"), "not a directory\n")

    def test_created_target_strips_inherited_extended_attributes(self):
        created = self.root / "new.txt"
        patch_text = (
            "--- /dev/null\n"
            "+++ b/new.txt\n"
            "@@ -0,0 +1 @@\n"
            "+new\n"
        )
        prepared = prepare_text_patch(patch_text, self.root, {})
        attribute = "com.rb-safe-operation.test" if sys.platform == "darwin" else "user.rb_safe_operation_test"
        original_mkstemp = tempfile.mkstemp

        def inherited_xattr(*args, **kwargs):
            descriptor, path = original_mkstemp(*args, **kwargs)
            try:
                if hasattr(os, "setxattr"):
                    os.setxattr(path, attribute, b"inherited", follow_symlinks=False)
                elif sys.platform == "darwin":
                    library = ctypes.CDLL("/usr/lib/libSystem.B.dylib", use_errno=True)
                    library.setxattr.argtypes = [
                        ctypes.c_char_p,
                        ctypes.c_char_p,
                        ctypes.c_void_p,
                        ctypes.c_size_t,
                        ctypes.c_uint32,
                        ctypes.c_int,
                    ]
                    library.setxattr.restype = ctypes.c_int
                    value = ctypes.create_string_buffer(b"inherited")
                    result = library.setxattr(
                        os.fsencode(path),
                        os.fsencode(attribute),
                        value,
                        len(b"inherited"),
                        0,
                        0x0001,
                    )
                    if result != 0:
                        raise OSError(ctypes.get_errno(), "setxattr failed")
                else:
                    self.skipTest("test platform has no extended-attribute setter")
            except OSError:
                os.close(descriptor)
                Path(path).unlink()
                self.skipTest("test filesystem does not support removable extended attributes")
            return descriptor, path

        with patch("rb_safe_operation.patches.tempfile.mkstemp", side_effect=inherited_xattr):
            commit_prepared_text_patch(
                prepared,
                {},
                created_file_mode=0o640,
                metadata_loader=self._portable_metadata,
            )

        if hasattr(os, "listxattr"):
            observed_xattrs = os.listxattr(created, follow_symlinks=False)
        else:
            observed_xattrs = list(_read_macos_xattrs(created))
        self.assertNotIn(attribute, observed_xattrs)
        self.assertTrue(set(observed_xattrs).issubset({"com.apple.provenance"}))

    def test_commit_rejects_metadata_drift_before_writing(self):
        prepared = prepare_text_patch(self.patch, self.root, {str(self.target): b"a\n"})
        metadata = self._portable_metadata(self.target)
        os.chmod(self.target, 0o600)
        with self.assertRaisesRegex(MetadataContractError, "metadata changed"):
            commit_prepared_text_patch(
                prepared,
                {str(self.target): metadata},
                created_file_mode=0o600,
                metadata_loader=self._portable_metadata,
            )
        self.assertEqual(self.target.read_bytes(), b"a\n")

    def test_commit_continues_a_known_committed_prefix_without_reapplying_it(self):
        second = self.root / "second.txt"
        second.write_bytes(b"x\n")
        patch_text = (
            "--- a/input.txt\n+++ b/input.txt\n@@ -1 +1 @@\n-a\n+b\n"
            "--- a/second.txt\n+++ b/second.txt\n@@ -1 +1 @@\n-x\n+y\n"
        )
        prepared = prepare_text_patch(
            patch_text, self.root, {str(self.target): b"a\n", str(second): b"x\n"}
        )
        self.target.write_bytes(b"b\n")
        commit_prepared_text_patch(
            prepared,
            {str(second): self._portable_metadata(second)},
            created_file_mode=0o600,
            metadata_loader=self._portable_metadata,
            start_index=1,
        )
        self.assertEqual(self.target.read_bytes(), b"b\n")
        self.assertEqual(second.read_bytes(), b"y\n")


if __name__ == "__main__":
    unittest.main()
