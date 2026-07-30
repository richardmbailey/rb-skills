from pathlib import Path
import sys
import unittest


TEST_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(TEST_ROOT))

from run_scientific_benchmark import compact_summary, run_case  # noqa: E402


class ScientificBenchmarkTests(unittest.TestCase):
    def test_compact_summary_omits_unbounded_raw_tables(self) -> None:
        summary = compact_summary(
            {
                "recorded_additions": 4,
                "frequency": [{"size": 1, "count": 2}],
                "ccdf": [{"size": 1, "count_at_least": 2}],
                "logarithmic_bins": [{"lower": 1, "upper": 1, "count": 2}],
                "power_law_fit": {"status": "insufficient_data"},
            }
        )

        self.assertNotIn("frequency", summary)
        self.assertNotIn("ccdf", summary)
        self.assertIn("logarithmic_bins", summary)
        self.assertIn("power_law_fit", summary)

    def test_run_case_preserves_scientific_evidence_in_compact_form(self) -> None:
        result = run_case(size=6, seed=7, burn_in=20, samples=40, xmin=2)

        self.assertEqual(result["mass"]["residual"], 0)
        self.assertEqual(result["summary"]["recorded_additions"], 40)
        self.assertNotIn("frequency", result["summary"])
        self.assertNotIn("ccdf", result["summary"])
        self.assertIn("logarithmic_bins", result["summary"])


if __name__ == "__main__":
    unittest.main()
