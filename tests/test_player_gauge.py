"""게이지 단계가 플레이어에게 주는 영향: 겉모습·속도·달리기 금지·좌우 반전."""

import unittest

from pico2d import SDLK_LEFT, SDLK_LSHIFT, SDLK_RIGHT, SDLK_SPACE

import config
from gauge import Gauge
from player import Idle, Jump, Run, Walk
from tests.support import (
    FRAME,
    STAGE,
    fly_until_landed,
    make_player,
    press,
    release,
    run_for,
    state_of,
)

# 각 단계 한가운데쯤의 값 (경계값은 게이지 쪽 테스트가 다룬다)
CALM, SWEAT, STRAIN, LIMIT = 10.0, 60.0, 85.0, 97.0
SWEAT_WALK = config.WALK_SPEED * config.SWEAT_SPEED_MULT
SWEAT_RUN = config.RUN_SPEED * config.SWEAT_SPEED_MULT


def player_at(value, x=None):
    """게이지가 value인 플레이어와 그리기 장부."""
    player, book = make_player(x=x)
    player.gauge.set_value(value)
    return player, book


class GaugeOwnershipTest(unittest.TestCase):
    def test_a_player_without_a_given_gauge_gets_a_calm_one_at_the_stage_rate(self):
        player, _ = make_player()

        self.assertEqual(player.gauge.value, 0)
        self.assertEqual(player.gauge.rate, config.GAUGE_BASE_RATE[STAGE.number])

    def test_a_given_gauge_is_the_one_the_player_uses(self):
        gauge = Gauge(1.0)

        player, _ = make_player(gauge=gauge)

        self.assertIs(player.gauge, gauge)


class MoodTest(unittest.TestCase):
    def test_sprite_sheet_follows_the_gauge_stage(self):
        cases = ((CALM, "calm"), (SWEAT, "sweat"), (STRAIN, "strain"), (LIMIT, "limit"))
        for value, mood in cases:
            with self.subTest(mood=mood):
                player, book = player_at(value)

                player.draw()

                self.assertEqual(book.draws[-1].name, f"player_{mood}_idle")

    def test_a_full_gauge_keeps_the_limit_sheet(self):
        player, book = player_at(config.GAUGE_MAX)

        player.draw()

        self.assertEqual(book.draws[-1].name, "player_limit_idle")

    def test_the_sheet_goes_back_when_the_gauge_drops(self):
        player, book = player_at(SWEAT)
        player.gauge.set_value(CALM)

        player.draw()

        self.assertEqual(book.draws[-1].name, "player_calm_idle")

    def test_every_pose_uses_the_current_mood(self):
        player, book = player_at(STRAIN)
        press(player, SDLK_SPACE)
        run_for(player, 0.2)

        player.draw()

        self.assertEqual(book.draws[-1].name, "player_strain_jump")


class SpeedTest(unittest.TestCase):
    def test_multiplier_is_one_while_calm(self):
        player, _ = player_at(CALM, x=300)

        self.assertEqual(player.speed_multiplier(), 1.0)

    def test_multiplier_is_the_sweat_value_from_the_sweat_stage_up(self):
        for value in (SWEAT, STRAIN, LIMIT):
            with self.subTest(value=value):
                player, _ = player_at(value, x=300)

                self.assertEqual(player.speed_multiplier(), config.SWEAT_SPEED_MULT)

    def test_multiplier_stacks_with_the_stairs(self):
        player, _ = player_at(SWEAT, x=4300)

        expected = config.STAIRS_SPEED_MULT * config.SWEAT_SPEED_MULT
        self.assertAlmostEqual(player.speed_multiplier(), expected)

    def test_walking_while_sweating_is_slower_by_the_sweat_multiplier(self):
        player, _ = player_at(SWEAT)

        press(player, SDLK_RIGHT)
        run_for(player, 1.0)

        self.assertAlmostEqual(player.x, STAGE.player_start_x + SWEAT_WALK, 2)

    def test_running_while_sweating_is_slower_by_the_same_multiplier(self):
        player, _ = player_at(SWEAT)

        press(player, SDLK_RIGHT)
        press(player, SDLK_LSHIFT)
        run_for(player, 1.0)

        self.assertAlmostEqual(player.x, STAGE.player_start_x + SWEAT_RUN, 2)
        self.assertIs(state_of(player), Run)

    def test_the_slowdown_starts_the_moment_the_stage_does(self):
        player, _ = make_player()
        press(player, SDLK_RIGHT)
        run_for(player, 0.5)
        calm_x = player.x

        player.gauge.set_value(SWEAT)
        run_for(player, 0.5)

        self.assertAlmostEqual(player.x - calm_x, SWEAT_WALK * 0.5, 2)


class StrainTest(unittest.TestCase):
    """긴장 단계(80~): 달릴 수 없고, 걸음이 뒤뚱거린다."""

    def test_shift_does_not_make_a_strained_player_run(self):
        player, _ = player_at(STRAIN)

        press(player, SDLK_RIGHT)
        press(player, SDLK_LSHIFT)
        run_for(player, 1.0)

        self.assertIs(state_of(player), Walk)
        self.assertAlmostEqual(player.x, STAGE.player_start_x + SWEAT_WALK, 2)

    def test_a_running_player_drops_to_a_walk_when_the_strain_stage_begins(self):
        player, _ = make_player()
        press(player, SDLK_RIGHT)
        press(player, SDLK_LSHIFT)
        self.assertIs(state_of(player), Run)

        player.gauge.set_value(STRAIN)
        run_for(player, 0.1)

        self.assertIs(state_of(player), Walk)

    def test_the_player_runs_again_when_the_gauge_falls_below_the_strain_stage(self):
        player, _ = player_at(STRAIN)
        press(player, SDLK_RIGHT)
        press(player, SDLK_LSHIFT)
        run_for(player, 0.2)
        self.assertIs(state_of(player), Walk)

        player.gauge.set_value(SWEAT)
        run_for(player, 0.1)

        self.assertIs(state_of(player), Run)

    def test_a_stage_change_does_not_move_a_standing_player(self):
        player, _ = make_player()

        for value in (SWEAT, STRAIN, LIMIT, CALM):
            player.gauge.set_value(value)
            run_for(player, 0.2)

        self.assertEqual(player.x, STAGE.player_start_x)
        self.assertIs(state_of(player), Idle)

    def test_a_stage_change_does_not_cut_a_jump_short(self):
        player, _ = make_player()
        press(player, SDLK_SPACE)
        run_for(player, 0.2)

        player.gauge.set_value(STRAIN)
        run_for(player, 0.1)

        self.assertIs(state_of(player), Jump)

    def test_walking_shows_the_waddle_sheet_only_from_the_strain_stage(self):
        cases = (
            (CALM, "player_calm_walk"),
            (SWEAT, "player_sweat_walk"),
            (STRAIN, "player_strain_waddle"),
            (LIMIT, "player_limit_waddle"),
        )
        for value, sheet in cases:
            with self.subTest(sheet=sheet):
                player, book = player_at(value)
                press(player, SDLK_RIGHT)

                player.draw()

                self.assertEqual(book.draws[-1].name, sheet)

    def test_the_waddle_animation_runs_at_the_sheet_fps(self):
        player, book = player_at(STRAIN)
        press(player, SDLK_RIGHT)
        run_for(player, 0.55)  # 뒤뚱 시트는 6fps -> 3.3번째 칸

        player.draw()

        self.assertEqual(book.draws[-1].frame, 3)

    def test_a_strained_jump_with_shift_held_flies_at_walk_speed(self):
        player, _ = player_at(STRAIN)
        press(player, SDLK_RIGHT)
        press(player, SDLK_LSHIFT)
        press(player, SDLK_SPACE)

        airborne_frames = fly_until_landed(player)

        flown = SWEAT_WALK * airborne_frames * FRAME
        self.assertAlmostEqual(player.x, STAGE.player_start_x + flown, 2)
        self.assertIs(state_of(player), Walk)

    def test_strain_that_begins_in_mid_air_slows_the_flight_down(self):
        player, _ = make_player()
        press(player, SDLK_RIGHT)
        press(player, SDLK_LSHIFT)
        press(player, SDLK_SPACE)
        run_for(player, 0.2)
        player.gauge.set_value(STRAIN)
        before = player.x

        player.step(FRAME)

        self.assertAlmostEqual(player.x - before, SWEAT_WALK * FRAME, 4)


class LimitTest(unittest.TestCase):
    """한계 단계(95~): 좌우가 뒤바뀐다."""

    def test_right_key_walks_left_and_faces_left(self):
        player, _ = player_at(LIMIT, x=1000)

        press(player, SDLK_RIGHT)
        run_for(player, 1.0)

        self.assertAlmostEqual(player.x, 1000 - SWEAT_WALK, 2)
        self.assertEqual(player.facing, -1)

    def test_left_key_walks_right_and_faces_right(self):
        player, _ = player_at(LIMIT, x=1000)

        press(player, SDLK_LEFT)
        run_for(player, 1.0)

        self.assertAlmostEqual(player.x, 1000 + SWEAT_WALK, 2)
        self.assertEqual(player.facing, 1)

    def test_controls_are_still_normal_one_step_below_the_limit(self):
        below_limit = config.STAGE_THRESHOLDS[2] - 0.1
        player, _ = player_at(below_limit, x=1000)

        press(player, SDLK_RIGHT)
        run_for(player, 0.5)

        self.assertGreater(player.x, 1000)

    def test_a_key_already_held_reverses_the_moment_the_limit_begins(self):
        player, _ = player_at(STRAIN, x=1000)
        press(player, SDLK_RIGHT)
        run_for(player, 0.5)
        turning_point = player.x
        self.assertGreater(turning_point, 1000)

        player.gauge.set_value(LIMIT)
        run_for(player, 0.5)

        self.assertLess(player.x, turning_point)

    def test_controls_go_back_to_normal_when_the_gauge_falls_below_the_limit(self):
        player, _ = player_at(LIMIT, x=1000)
        player.gauge.set_value(STRAIN)

        press(player, SDLK_RIGHT)
        run_for(player, 0.5)

        self.assertGreater(player.x, 1000)

    def test_both_arrows_still_cancel_out(self):
        player, _ = player_at(LIMIT, x=1000)

        press(player, SDLK_LEFT)
        press(player, SDLK_RIGHT)
        run_for(player, 0.5)

        self.assertEqual(player.x, 1000)
        self.assertIs(state_of(player), Idle)

    def test_air_control_is_reversed_too(self):
        player, _ = player_at(LIMIT, x=1000)
        press(player, SDLK_SPACE)

        press(player, SDLK_LEFT)
        run_for(player, 0.2)

        self.assertGreater(player.x, 1000)
        release(player, SDLK_LEFT)


class IsRunningTest(unittest.TestCase):
    """게이지가 더 빨리 차는 "달리는 중"의 기준: 달리는 속도로 움직이고 있는가."""

    def test_standing_and_walking_are_not_running(self):
        player, _ = make_player()
        self.assertFalse(player.is_running())

        press(player, SDLK_RIGHT)
        self.assertFalse(player.is_running())

    def test_shift_alone_is_not_running(self):
        player, _ = make_player()

        press(player, SDLK_LSHIFT)

        self.assertFalse(player.is_running())

    def test_direction_with_shift_is_running(self):
        player, _ = make_player()

        press(player, SDLK_RIGHT)
        press(player, SDLK_LSHIFT)

        self.assertTrue(player.is_running())

    def test_jumping_at_run_speed_still_counts_as_running(self):
        player, _ = make_player()
        press(player, SDLK_RIGHT)
        press(player, SDLK_LSHIFT)

        press(player, SDLK_SPACE)

        self.assertIs(state_of(player), Jump)
        self.assertTrue(player.is_running())

    def test_jumping_at_walk_speed_does_not(self):
        player, _ = make_player()
        press(player, SDLK_RIGHT)

        press(player, SDLK_SPACE)

        self.assertFalse(player.is_running())

    def test_a_strained_player_never_runs(self):
        player, _ = player_at(STRAIN)

        press(player, SDLK_RIGHT)
        press(player, SDLK_LSHIFT)

        self.assertFalse(player.is_running())


if __name__ == "__main__":
    unittest.main()
