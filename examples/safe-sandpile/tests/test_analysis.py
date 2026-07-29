from pathlib import Path
import math
import sys
import unittest


APP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_ROOT))

from sandpile.analysis import (  # noqa: E402
    complementary_cdf,
    fit_power_law,
    frequency_table,
    logarithmic_bins,
    summarize_avalanches,
)


class AvalancheAnalysisTests(unittest.TestCase):
    def test_frequency_and_ccdf_use_positive_avalanches(self) -> None:
        values = [0, 1, 1, 2, 4]
        self.assertEqual(
            frequency_table(values),
            [
                {"size": 1, "count": 2, "frequency": 0.5},
                {"size": 2, "count": 1, "frequency": 0.25},
                {"size": 4, "count": 1, "frequency": 0.25},
            ],
        )
        ccdf = complementary_cdf(values)
        self.assertEqual([row["count_at_least"] for row in ccdf], [4, 2, 1])
        self.assertEqual([row["probability"] for row in ccdf], [1.0, 0.5, 0.25])

    def test_logarithmic_bins_cover_every_positive_value(self) -> None:
        bins = logarithmic_bins([0, 1, 2, 3, 4, 8])
        self.assertEqual([(row["lower"], row["upper"], row["count"]) for row in bins], [(1, 1, 1), (2, 3, 2), (4, 7, 1), (8, 15, 1)])
        self.assertEqual(sum(row["count"] for row in bins), 5)

    def test_power_law_fit_reports_insufficient_tail_explicitly(self) -> None:
        fit = fit_power_law([1, 2, 3], xmin=2, minimum_tail=3)
        self.assertEqual(fit["status"], "insufficient_data")
        self.assertEqual(fit["n"], 2)
        self.assertIsNone(fit["alpha"])

    def test_power_law_fit_uses_documented_approximation(self) -> None:
        values = [2, 3, 4, 5]
        fit = fit_power_law(values, xmin=2, minimum_tail=4)
        expected = 1 + len(values) / sum(math.log(value / 1.5) for value in values)
        self.assertEqual(fit["status"], "estimated")
        self.assertAlmostEqual(fit["alpha"], expected)
        self.assertGreaterEqual(fit["ks_distance"], 0)
        self.assertLessEqual(fit["ks_distance"], 1)

    def test_summary_reports_zeros_and_scientific_caveat(self) -> None:
        summary = summarize_avalanches([0, 0, 3])
        self.assertAlmostEqual(summary["zero_fraction"], 2 / 3)
        self.assertIn("does not", summary["interpretation"])

    def test_invalid_observations_and_parameters_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            frequency_table([1, -1])
        with self.assertRaises(TypeError):
            complementary_cdf([1, 2.5])
        with self.assertRaises(ValueError):
            fit_power_law([1, 2], xmin=0)
        with self.assertRaises(ValueError):
            logarithmic_bins([1], base=1)


if __name__ == "__main__":
    unittest.main()
