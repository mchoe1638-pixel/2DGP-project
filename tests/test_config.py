import os
import tempfile
import unittest

import config


def _make_asset_tree(root):
    manifest_dir = os.path.join(root, "resource", "image")
    os.makedirs(manifest_dir)
    with open(os.path.join(manifest_dir, "manifest.json"), "w", encoding="utf-8") as f:
        f.write("{}")


class FindAssetRootTest(unittest.TestCase):
    def test_returns_base_dir_when_resource_folder_sits_next_to_the_code(self):
        with tempfile.TemporaryDirectory() as base:
            _make_asset_tree(base)
            self.assertEqual(config.find_asset_root(base), base)

    def test_falls_back_to_bladder_run_resource_subfolder(self):
        with tempfile.TemporaryDirectory() as base:
            nested = os.path.join(base, "bladder_run_resource")
            _make_asset_tree(nested)
            self.assertEqual(config.find_asset_root(base), nested)

    def test_raises_readable_error_when_resources_are_missing(self):
        with tempfile.TemporaryDirectory() as base:
            with self.assertRaises(FileNotFoundError) as ctx:
                config.find_asset_root(base)
            self.assertIn("resource", str(ctx.exception))

    def test_real_project_resources_are_found(self):
        self.assertTrue(os.path.isfile(config.MANIFEST_PATH))


class BalanceInvariantTest(unittest.TestCase):
    def test_jump_peak_clears_walking_height_npcs_but_not_the_crowd(self):
        peak = config.JUMP_V0**2 / (2 * config.GRAVITY)
        self.assertGreater(peak, config.NPC_BB_HEIGHT)
        self.assertLess(peak, config.CROWD_BB_HEIGHT)

    def test_jump_peak_is_about_190_pixels(self):
        peak = config.JUMP_V0**2 / (2 * config.GRAVITY)
        self.assertAlmostEqual(peak, 190, delta=5)

    def test_gauge_stage_thresholds_are_strictly_ascending_and_end_at_100(self):
        thresholds = config.STAGE_THRESHOLDS
        self.assertEqual(list(thresholds), sorted(set(thresholds)))
        self.assertEqual(thresholds[-1], 100)

    def test_run_is_faster_than_walk(self):
        self.assertGreater(config.RUN_SPEED, config.WALK_SPEED)

    def test_stairs_slow_the_player_down_without_stopping_them(self):
        self.assertGreater(config.STAIRS_SPEED_MULT, 0)
        self.assertLess(config.STAIRS_SPEED_MULT, 1)

    def test_sweat_slows_the_player_down_without_stopping_them(self):
        self.assertGreater(config.SWEAT_SPEED_MULT, 0)
        self.assertLess(config.SWEAT_SPEED_MULT, 1)

    def test_running_fills_the_gauge_faster_than_walking(self):
        self.assertGreater(config.RUN_GAUGE_MULT, 1)

    def test_growl_interval_is_a_positive_ascending_range(self):
        low, high = config.GROWL_INTERVAL
        self.assertGreater(low, 0)
        self.assertLess(low, high)

    def test_stage_two_base_rate_exists(self):
        self.assertIn(2, config.GAUGE_BASE_RATE)

    def test_screen_is_1280_by_720(self):
        self.assertEqual((config.SCREEN_W, config.SCREEN_H), (1280, 720))

    def test_frame_time_is_clamped_to_a_sane_maximum(self):
        self.assertLessEqual(config.MAX_FRAME_TIME, 0.1)


if __name__ == "__main__":
    unittest.main()
