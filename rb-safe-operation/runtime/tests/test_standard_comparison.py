from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "benchmark_standard_static_edit.py"
SPEC = importlib.util.spec_from_file_location("benchmark_standard_static_edit", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load matched standard comparison driver")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class StandardComparisonTests(unittest.TestCase):
    def test_direct_edit_comparison_is_content_exact_and_path_redacted(self) -> None:
        result = MODULE.run_comparison()
        self.assertTrue(result["verified"])
        self.assertEqual(
            result["expected_target_sha256"],
            "0263829989b6fd954f72baaf2fc64bc2e2f01d692d4de72986ea808f6e99813f",
        )
        self.assertGreaterEqual(result["elapsed_nanoseconds"], 0)
        self.assertNotIn("project_root", result)
        self.assertIn("excludes model deliberation", result["scope"])


if __name__ == "__main__":
    unittest.main()
