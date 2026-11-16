import dataclasses
import unittest

import stage_data


class Stage2DataTest(unittest.TestCase):
    def test_layout_matches_the_design_document(self):
        stage = stage_data.STAGE_2
        self.assertEqual(stage.number, 2)
        self.assertEqual(stage.length, 9000)
        self.assertEqual(stage.goal_x, 8800)
        self.assertEqual(stage.player_start_x, 150)
        self.assertEqual(stage.stairs_zone, (4200, 5400))

    def test_player_starts_before_the_goal_and_the_goal_is_inside_the_level(self):
        stage = stage_data.STAGE_2
        self.assertLess(stage.player_start_x, stage.goal_x)
        self.assertLess(stage.goal_x, stage.length)

    def test_stage_data_is_immutable(self):
        with self.assertRaises(dataclasses.FrozenInstanceError):
            stage_data.STAGE_2.length = 1

    def test_in_stairs_is_true_only_inside_the_zone(self):
        stage = stage_data.STAGE_2
        self.assertFalse(stage.in_stairs(4199))
        self.assertTrue(stage.in_stairs(4200))
        self.assertTrue(stage.in_stairs(5399))
        self.assertFalse(stage.in_stairs(5400))

    def test_a_stage_without_stairs_never_reports_stairs(self):
        flat = dataclasses.replace(stage_data.STAGE_2, stairs_zone=None)
        self.assertFalse(flat.in_stairs(4500))


class GetStageTest(unittest.TestCase):
    def test_returns_the_registered_stage(self):
        self.assertIs(stage_data.get_stage(2), stage_data.STAGE_2)

    def test_unknown_stage_number_raises_a_readable_error(self):
        with self.assertRaises(KeyError) as ctx:
            stage_data.get_stage(1)
        self.assertIn("1", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
