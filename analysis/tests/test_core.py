import unittest

import numpy as np

from analysis.ca import simulate, step
from analysis.features import extract_features
from analysis.rules import format_rule, parse_rule


class RuleTests(unittest.TestCase):
    def test_round_trips(self):
        for rule in ("B3/S23", "B36/S23", "B/S", "B012345678/S012345678"):
            self.assertEqual(format_rule(parse_rule(rule)), rule)

    def test_rejects_invalid_rule(self):
        with self.assertRaises(ValueError):
            parse_rule("23/3")


class ConwayTests(unittest.TestCase):
    def test_block_is_stable(self):
        grid = np.zeros((8, 8), dtype=np.uint8)
        grid[3:5, 3:5] = 1
        np.testing.assert_array_equal(step(grid, "B3/S23"), grid)

    def test_blinker_has_period_two(self):
        grid = np.zeros((9, 9), dtype=np.uint8)
        grid[4, 3:6] = 1
        np.testing.assert_array_equal(step(step(grid, "B3/S23"), "B3/S23"), grid)

    def test_glider_translates_after_four_steps(self):
        grid = np.zeros((12, 12), dtype=np.uint8)
        grid[2:5, 2:5] = np.array([[0, 1, 0], [0, 0, 1], [1, 1, 1]], dtype=np.uint8)
        evolved = simulate("B3/S23", steps=4, seed=0, initial_grid=grid)[-1]
        expected = np.roll(np.roll(grid, 1, axis=0), 1, axis=1)
        np.testing.assert_array_equal(evolved, expected)

    def test_boundary_setting_changes_edge_behavior(self):
        grid = np.zeros((5, 5), dtype=np.uint8)
        grid[0, 0] = grid[0, 4] = grid[4, 0] = 1
        self.assertEqual(step(grid, "B3/S23", boundary="toroidal")[4, 4], 1)
        self.assertEqual(step(grid, "B3/S23", boundary="dead")[4, 4], 0)


class FeatureTests(unittest.TestCase):
    def test_dead_board_features(self):
        trajectory = np.zeros((6, 8, 8), dtype=np.uint8)
        features = extract_features(trajectory)
        self.assertEqual(features["mean_density"], 0.0)
        self.assertEqual(features["activity"], 0.0)
        self.assertEqual(features["entropy"], 0.0)

    def test_still_life_has_no_activity_and_full_lifespan(self):
        grid = np.zeros((8, 8), dtype=np.uint8)
        grid[3:5, 3:5] = 1
        features = extract_features(simulate("B3/S23", steps=8, initial_grid=grid))
        self.assertEqual(features["activity"], 0.0)
        self.assertEqual(features["normalized_lifespan"], 1.0)

    def test_blinker_recurs(self):
        grid = np.zeros((9, 9), dtype=np.uint8)
        grid[4, 3:6] = 1
        features = extract_features(simulate("B3/S23", steps=6, initial_grid=grid))
        self.assertEqual(features["recurrence"], 1.0)


if __name__ == "__main__":
    unittest.main()
