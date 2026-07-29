from pathlib import Path
import sys
import unittest


APP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_ROOT))

from sandpile.model import SandpileModel  # noqa: E402


class SandpileModelTests(unittest.TestCase):
    def test_centre_site_topples_to_four_neighbours(self) -> None:
        model = SandpileModel(size=3, seed=1, drop_mode="center")
        for _ in range(3):
            event = model.add_grain(row=1, column=1)
            self.assertEqual(event.size, 0)
        event = model.add_grain(row=1, column=1)
        self.assertEqual((event.size, event.area, event.duration, event.lost), (1, 1, 1, 0))
        self.assertEqual(model.grid, [[0, 1, 0], [1, 0, 1], [0, 1, 0]])
        self.assertEqual(model.mass_balance_residual, 0)

    def test_corner_toppling_loses_two_grains(self) -> None:
        model = SandpileModel(size=3)
        for _ in range(4):
            event = model.add_grain(row=0, column=0)
        self.assertEqual((event.size, event.lost), (1, 2))
        self.assertEqual(model.total_lost, 2)
        self.assertEqual(model.retained_mass, 2)
        self.assertEqual(model.mass_balance_residual, 0)

    def test_mass_is_conserved_and_lattice_is_stable_after_long_run(self) -> None:
        model = SandpileModel(size=12, seed=39)
        model.add_grains(4_000)
        self.assertEqual(model.mass_balance_residual, 0)
        self.assertTrue(all(0 <= height < 4 for row in model.grid for height in row))
        self.assertGreater(model.total_lost, 0)

    def test_seeded_runs_are_identical(self) -> None:
        first = SandpileModel(size=10, seed=17)
        second = SandpileModel(size=10, seed=17)
        first.add_grains(750)
        second.add_grains(750)
        self.assertEqual(first.grid, second.grid)
        self.assertEqual(first.avalanches, second.avalanches)
        self.assertEqual(first.total_lost, second.total_lost)

    def test_centre_drop_mode_uses_one_fixed_central_source(self) -> None:
        model = SandpileModel(size=8, seed=17, drop_mode="center")

        events = model.add_grains(12)

        self.assertEqual({(event.row, event.column) for event in events}, {(4, 4)})
        self.assertEqual(model.mass_balance_residual, 0)

    def test_central_noise_is_seeded_bounded_and_centre_weighted(self) -> None:
        first = SandpileModel(
            size=21,
            seed=17,
            drop_mode="center",
            central_noise_radius=3,
        )
        second = SandpileModel(
            size=21,
            seed=17,
            drop_mode="center",
            central_noise_radius=3,
        )

        first_events = first.add_grains(500)
        second_events = second.add_grains(500)
        first_positions = [(event.row, event.column) for event in first_events]
        centre = first.size // 2

        self.assertEqual(
            first_positions,
            [(event.row, event.column) for event in second_events],
        )
        self.assertGreater(len(set(first_positions)), 1)
        self.assertTrue(
            all(
                (row - centre) ** 2 + (column - centre) ** 2 <= 3 ** 2
                for row, column in first_positions
            )
        )
        self.assertLess(
            sum((row - centre) ** 2 + (column - centre) ** 2 for row, column in first_positions)
            / len(first_positions),
            4.5,
        )
        self.assertEqual(first.mass_balance_residual, 0)

    def test_source_configuration_changes_without_resetting_state(self) -> None:
        model = SandpileModel(size=9, seed=5, drop_mode="random")
        model.add_grains(20)
        before = (model.total_added, model.retained_mass, model.total_lost)

        model.set_source(drop_mode="center", central_noise_radius=2)

        self.assertEqual(before, (model.total_added, model.retained_mass, model.total_lost))
        self.assertEqual(model.snapshot()["central_noise_radius"], 2)

    def test_physical_slope_model_builds_a_tall_stable_reproducible_pile(self) -> None:
        configuration = {
            "size": 21,
            "seed": 29,
            "drop_mode": "center",
            "central_noise_radius": 1,
            "model_type": "slope",
            "angle_of_repose_degrees": 40.0,
        }
        first = SandpileModel(**configuration)
        second = SandpileModel(**configuration)

        first.add_grains(2_000)
        second.add_grains(2_000)

        self.assertGreater(first.maximum_height_layers, 3)
        self.assertLessEqual(first.maximum_slope_degrees, 40.0 + 1e-9)
        self.assertEqual(first.grid, second.grid)
        self.assertEqual(first.avalanches, second.avalanches)
        self.assertEqual(first.mass_balance_residual, 0)
        self.assertTrue(all(height >= 0 for row in first.grid for height in row))

    def test_higher_repose_angle_supports_a_steeper_taller_pile(self) -> None:
        common = {
            "size": 17,
            "seed": 31,
            "drop_mode": "center",
            "central_noise_radius": 0,
            "model_type": "slope",
        }
        shallow = SandpileModel(**common, angle_of_repose_degrees=30.0)
        steep = SandpileModel(**common, angle_of_repose_degrees=45.0)

        shallow.add_grains(1_500)
        steep.add_grains(1_500)

        self.assertGreater(steep.maximum_height_layers, shallow.maximum_height_layers)
        self.assertLessEqual(shallow.maximum_slope_degrees, 30.0 + 1e-9)
        self.assertLessEqual(steep.maximum_slope_degrees, 45.0 + 1e-9)

    def test_physical_height_avoids_binary_floating_point_residue(self) -> None:
        model = SandpileModel(size=3, model_type="slope")
        model.grid[1][1] = 68

        self.assertEqual(model.maximum_height_cells, 6.8)

    def test_physical_slope_model_loses_mass_at_open_edges(self) -> None:
        model = SandpileModel(
            size=9,
            seed=37,
            drop_mode="center",
            model_type="slope",
            angle_of_repose_degrees=40.0,
        )

        model.add_grains(4_000)

        self.assertGreater(model.total_lost, 0)
        self.assertEqual(model.mass_balance_residual, 0)
        self.assertLessEqual(model.maximum_slope_degrees, 40.0 + 1e-9)

    def test_clearing_history_preserves_physical_state(self) -> None:
        model = SandpileModel(size=8, seed=3)
        model.add_grains(100)
        before = (model.total_added, model.retained_mass, model.total_lost, [row[:] for row in model.grid])
        model.clear_avalanche_history()
        self.assertEqual(model.avalanches, [])
        self.assertEqual(before, (model.total_added, model.retained_mass, model.total_lost, model.grid))

    def test_invalid_configuration_and_locations_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            SandpileModel(size=2)
        with self.assertRaises(ValueError):
            SandpileModel(drop_mode="edge")
        with self.assertRaises(ValueError):
            SandpileModel(drop_mode="center", central_noise_radius=-1)
        with self.assertRaises(TypeError):
            SandpileModel(drop_mode="center", central_noise_radius=1.5)
        with self.assertRaises(ValueError):
            SandpileModel(model_type="continuum")
        with self.assertRaises(ValueError):
            SandpileModel(model_type="slope", angle_of_repose_degrees=9.9)
        with self.assertRaises(ValueError):
            SandpileModel(model_type="slope", angle_of_repose_degrees=60.1)
        with self.assertRaises(TypeError):
            SandpileModel(model_type="slope", angle_of_repose_degrees=True)
        model = SandpileModel(size=3)
        with self.assertRaises(ValueError):
            model.add_grain(row=1)
        with self.assertRaises(ValueError):
            model.add_grain(row=-1, column=0)
        with self.assertRaises(ValueError):
            model.add_grains(0)
        with self.assertRaises(ValueError):
            model.set_drop_mode("edge")
        with self.assertRaises(ValueError):
            model.set_source(drop_mode="center", central_noise_radius=33)


if __name__ == "__main__":
    unittest.main()
