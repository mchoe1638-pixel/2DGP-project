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

    def test_a_fall_stops_the_player_briefly_and_raises_the_gauge(self):
        self.assertGreater(config.FALL_STOP_TIME, 0)
        self.assertGreater(config.FALL_GAUGE_ADD, 0)

    def test_the_flyer_slows_the_player_without_stopping_them(self):
        self.assertGreater(config.FLYER_SPEED_MULT, 0)
        self.assertLess(config.FLYER_SPEED_MULT, 1)
        self.assertGreater(config.FLYER_SLOW_TIME, 0)

    def test_the_boss_warns_early_enough_to_react_after_the_exclaim_ends(self):
        # "!"가 사라진 뒤 가장 빠르게 달려도(상사도 걸어 온다) 부딪히기까지 반응할 시간이 남아야 한다.
        left = config.BOSS_WARN_DISTANCE - config.RUN_SPEED * config.BOSS_EXCLAIM_TIME
        closing_speed = config.RUN_SPEED + config.BOSS_WALK_SPEED

        self.assertGreaterEqual(left / closing_speed, 0.5)

    def test_the_boss_line_is_the_one_from_the_design_document(self):
        self.assertEqual(config.BOSS_SPEECH_TEXT, "김대리~ 잠깐만!")

    def test_a_crowd_push_throws_the_player_clear_of_the_widest_crowd(self):
        widest_half = 1.5 * config.CROWD_MEMBER_SPACING + config.NPC_BB_HALF_W
        reach = widest_half + config.PLAYER_BB_HALF_W

        self.assertGreater(config.CROWD_PUSH_DISTANCE, reach)

    def test_crowd_gap_is_a_part_of_each_cycle_and_the_ease_fits_inside_it(self):
        self.assertGreater(config.CROWD_GAP_OPEN_TIME, 0)
        self.assertLess(config.CROWD_GAP_OPEN_TIME, config.CROWD_GAP_PERIOD)
        self.assertLessEqual(2 * config.CROWD_GAP_EASE, config.CROWD_GAP_OPEN_TIME)

    def test_crowd_members_stand_shoulder_to_shoulder(self):
        self.assertEqual(config.CROWD_MEMBER_SPACING, 2 * config.NPC_BB_HALF_W)

    def test_a_running_player_can_cross_the_gap_even_on_the_stairs(self):
        widest_half = 1.5 * config.CROWD_MEMBER_SPACING + config.NPC_BB_HALF_W
        travel = 2 * (widest_half + config.PLAYER_BB_HALF_W)
        stairs_run_speed = config.RUN_SPEED * config.STAIRS_SPEED_MULT

        self.assertLess(travel / stairs_run_speed, config.CROWD_GAP_OPEN_TIME)

    def test_npcs_walk_off_slowly_and_fade_out(self):
        self.assertGreater(config.NPC_EXIT_SPEED, 0)
        self.assertGreater(config.NPC_FADE_TIME, 0)

    def test_effect_frames_advance_at_a_visible_pace(self):
        self.assertGreater(config.FX_FRAME_PERIOD, 0)
        self.assertLess(config.FX_FRAME_PERIOD, config.BOSS_EXCLAIM_TIME / 2)


if __name__ == "__main__":
    unittest.main()
