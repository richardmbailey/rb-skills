from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from rb_safe_operation.canonical import canonical_bytes
from rb_safe_operation.schemas import check_drift


class SchemaDriftTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.expected = self.root / "expected"
        self.generated = self.root / "generated"
        self.expected.mkdir()
        self.generated.mkdir()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    @staticmethod
    def _envelope(source_hash: str, *, schema_type: str = "string") -> dict[str, object]:
        schema = {"title": "Example", "type": schema_type}
        return {
            "generator_version": "0.1.0",
            "model_schema_version": "1.0",
            "runtime_source_hash": source_hash,
            "schema_payload_hash": f"payload-{schema_type}",
            "schema": schema,
        }

    @staticmethod
    def _write(path: Path, payload: dict[str, object]) -> None:
        path.write_bytes(canonical_bytes(payload) + b"\n")

    def test_runtime_source_provenance_change_is_not_schema_drift(self) -> None:
        name = "example-1.0.schema.json"
        self._write(self.expected / name, self._envelope("old-source"))
        self._write(self.generated / name, self._envelope("new-source"))
        self.assertEqual(check_drift(self.expected, self.generated), [])

    def test_schema_payload_change_is_drift(self) -> None:
        name = "example-1.0.schema.json"
        self._write(self.expected / name, self._envelope("same-source", schema_type="string"))
        self._write(self.generated / name, self._envelope("same-source", schema_type="integer"))
        self.assertEqual(check_drift(self.expected, self.generated), [name])

    def test_missing_or_malformed_schema_is_drift(self) -> None:
        missing = "missing-1.0.schema.json"
        malformed = "malformed-1.0.schema.json"
        self._write(self.expected / missing, self._envelope("source"))
        (self.expected / malformed).write_text("not-json\n", encoding="utf-8")
        (self.generated / malformed).write_text("different\n", encoding="utf-8")
        self.assertEqual(
            check_drift(self.expected, self.generated),
            [malformed, missing],
        )


if __name__ == "__main__":
    unittest.main()
