"""플레이어가 장애물에 걸렸을 때: 기절(멈춤), 넘어짐, 전단지 감속, 인파에 밀려남."""

import unittest

from pico2d import SDLK_LEFT, SDLK_LSHIFT, SDLK_RIGHT, SDLK_SPACE

import config
import game_world
from player import Idle, Run, Stunned, Walk
from tests.support import (
    FRAME,
    STAGE,
    make_player,
    press,
    release,
    run_for,
    state_of,
)

START_X = 1000.0  # 계단 구간(4200~5400) 밖이고 스테이지 양 끝에서도 멀다


class PlayerTestCase(unittest.TestCase):
    """넘어짐이 별 이펙트를 월드에 올리므로, 시험마다 월드를 비워 둔다."""

    def setUp(self):
        game_world.clear()
        self.addCleanup(game_world.clear)
        self.player, self.book = make_player(x=START_X)

    def draw_name(self):
        """지금 플레이어를 그려 어떤 시트가 쓰였는지 돌려준다."""
        self.player.draw()
        return self.book.draws[-1].name


class StunTest(PlayerTestCase):
    def test_a_stun_takes_effect_at_once(self):
        self.player.stun(1.0)

        self.assertIs(state_of(self.player), Stunned)

    def test_every_state_can_be_stunned(self):
        held_keys = {
            "idle": [],
            "walk": [SDLK_RIGHT],
            "run": [SDLK_RIGHT, SDLK_LSHIFT],
            "jump": [SDLK_SPACE],
        }
        for name, keys in held_keys.items():
            with self.subTest(state=name):
                player, _ = make_player(x=START_X)
                for key in keys:
                    press(player, key)
                run_for(player, 0.1)

                player.stun(1.0)

                self.assertIs(state_of(player), Stunned)

    def test_a_stunned_player_stays_put_even_with_the_keys_held(self):
        press(self.player, SDLK_RIGHT)
        run_for(self.player, 0.2)
        self.player.stun(1.0)
        stopped_at = self.player.x

        run_for(self.player, 0.5)

        self.assertEqual(self.player.x, stopped_at)

    def test_the_player_stands_up_when_the_stun_is_over(self):
        self.player.stun(1.0)

        run_for(self.player, 0.9)
        still_stunned = state_of(self.player)
        run_for(self.player, 0.2)

        self.assertIs(still_stunned, Stunned)
        self.assertIs(state_of(self.player), Idle)

    def test_a_key_held_through_the_stun_makes_the_player_walk_when_it_ends(self):
        press(self.player, SDLK_RIGHT)
        self.player.stun(0.5)

        run_for(self.player, 0.6)

        self.assertIs(state_of(self.player), Walk)

    def test_keys_held_through_the_stun_make_the_player_run_when_it_ends(self):
        press(self.player, SDLK_RIGHT)
        press(self.player, SDLK_LSHIFT)
        self.player.stun(0.5)

        run_for(self.player, 0.6)

        self.assertIs(state_of(self.player), Run)

    def test_a_key_pressed_during_the_stun_is_remembered(self):
        self.player.stun(0.5)
        press(self.player, SDLK_RIGHT)

        run_for(self.player, 0.4)
        before_the_end = self.player.x
        run_for(self.player, 0.2)

        self.assertEqual(before_the_end, START_X)
        self.assertIs(state_of(self.player), Walk)

    def test_a_key_released_during_the_stun_is_remembered(self):
        press(self.player, SDLK_RIGHT)
        run_for(self.player, 0.1)
        self.player.stun(0.5)
        release(self.player, SDLK_RIGHT)

        run_for(self.player, 0.6)

        self.assertIs(state_of(self.player), Idle)

    def test_space_does_not_jump_while_stunned(self):
        self.player.stun(1.0)

        press(self.player, SDLK_SPACE)
        run_for(self.player, 0.2)

        self.assertEqual(self.player.height, 0.0)
        self.assertIs(state_of(self.player), Stunned)

    def test_a_longer_stun_extends_the_time_but_a_shorter_one_does_not_cut_it(self):
        self.player.stun(1.0)
        run_for(self.player, 0.5)

        self.player.stun(0.2)
        after_short = self.player.stun_remaining
        self.player.stun(1.5)
        after_long = self.player.stun_remaining

        self.assertAlmostEqual(after_short, 0.5, delta=0.02)
        self.assertAlmostEqual(after_long, 1.5, delta=0.001)

    def test_stunning_a_stunned_player_again_still_ends_in_one_stand_up(self):
        self.player.stun(0.5)
        self.player.stun(0.5)

        run_for(self.player, 0.6)

        self.assertIs(state_of(self.player), Idle)

    def test_a_stunned_player_is_not_running_even_with_run_keys_held(self):
        press(self.player, SDLK_RIGHT)
        press(self.player, SDLK_LSHIFT)
        run_for(self.player, 0.1)
        was_running = self.player.is_running()

        self.player.stun(1.0)

        self.assertTrue(was_running)
        self.assertFalse(self.player.is_running())

    def test_a_plain_stun_shows_the_standing_pose(self):
        self.player.stun(1.0)

        self.assertEqual(self.draw_name(), "player_calm_idle")

    def test_the_stunned_pose_keeps_the_way_the_player_faces(self):
        press(self.player, SDLK_LEFT)
        run_for(self.player, 0.1)
        self.player.stun(1.0)

        self.draw_name()

        self.assertTrue(self.book.draws[-1].flip)


class StunInTheAirTest(PlayerTestCase):
    def jump_and_stun(self, duration):
        press(self.player, SDLK_RIGHT)
        press(self.player, SDLK_SPACE)
        run_for(self.player, 0.1)
        self.assertGreater(self.player.height, 0)
        self.player.stun(duration)

    def test_a_stunned_player_drops_straight_down_to_the_ground(self):
        self.jump_and_stun(0.05)
        stopped_at = self.player.x

        for _ in range(
            round(1.5 / FRAME)
        ):  # → 키를 누른 채라 땅에 닿은 뒤에는 걸어간다
            if self.player.height <= 0:
                break
            run_for(self.player, FRAME)
            self.assertEqual(self.player.x, stopped_at)

        self.assertEqual(self.player.height, 0.0)
        self.assertEqual(self.player.vy, 0.0)

    def test_the_player_cannot_get_up_in_mid_air_even_if_the_stun_time_is_over(self):
        self.jump_and_stun(0.05)

        run_for(self.player, 0.2)
        in_the_air = (state_of(self.player), self.player.height > 0)
        run_for(self.player, 1.0)

        self.assertEqual(in_the_air, (Stunned, True))
        self.assertIs(state_of(self.player), Walk)  # → 키를 계속 누르고 있었다


class FallTest(PlayerTestCase):
    def test_a_fall_stuns_the_player_for_the_fall_time(self):
        self.player.fall()

        run_for(self.player, config.FALL_STOP_TIME - 0.1)
        still_down = state_of(self.player)
        run_for(self.player, 0.2)

        self.assertIs(still_down, Stunned)
        self.assertIs(state_of(self.player), Idle)

    def test_a_fall_raises_the_gauge_by_the_fall_penalty(self):
        self.player.fall()

        self.assertEqual(self.player.gauge.value, config.FALL_GAUGE_ADD)

    def test_a_fall_shows_the_lying_pose_of_the_current_mood(self):
        # 넘어지면서 게이지가 오르므로, 오른 뒤에도 같은 단계에 머무는 값을 고른다
        cases = ((5.0, "calm"), (60.0, "sweat"), (82.0, "strain"), (96.0, "limit"))
        for value, mood in cases:
            with self.subTest(mood=mood):
                player, book = make_player(x=START_X)
                player.gauge.set_value(value)

                player.fall()
                player.draw()

                self.assertEqual(book.draws[-1].name, f"player_{mood}_fall")

    def test_the_lying_pose_is_replaced_by_the_standing_pose_after_getting_up(self):
        self.player.fall()
        lying = self.draw_name()

        run_for(self.player, config.FALL_STOP_TIME + 0.2)

        self.assertEqual(lying, "player_calm_fall")
        self.assertEqual(self.draw_name(), "player_calm_idle")

    def test_a_fall_sends_up_stars_that_last_as_long_as_the_fall(self):
        self.player.fall()

        [stars] = game_world.world[game_world.LAYER_FX]

        self.assertEqual(stars.sprite_name, "fx_stars")
        self.assertEqual(stars.lifetime, config.FALL_STOP_TIME)


class SlowTest(PlayerTestCase):
    def test_a_slowed_player_walks_at_the_flyer_multiplier(self):
        self.player.slow(3.0)

        press(self.player, SDLK_RIGHT)
        run_for(self.player, 1.0)

        expected = START_X + config.WALK_SPEED * config.FLYER_SPEED_MULT
        self.assertAlmostEqual(self.player.x, expected, 2)

    def test_a_slowed_player_runs_at_the_flyer_multiplier(self):
        self.player.slow(3.0)

        press(self.player, SDLK_RIGHT)
        press(self.player, SDLK_LSHIFT)
        run_for(self.player, 1.0)

        expected = START_X + config.RUN_SPEED * config.FLYER_SPEED_MULT
        self.assertAlmostEqual(self.player.x, expected, 2)
        self.assertIs(state_of(self.player), Run)

    def test_the_slow_wears_off_after_its_time(self):
        self.player.slow(1.0)
        run_for(self.player, 1.1)

        press(self.player, SDLK_RIGHT)
        run_for(self.player, 1.0)

        self.assertEqual(self.player.speed_multiplier(), 1.0)
        self.assertAlmostEqual(self.player.x, START_X + config.WALK_SPEED, 2)

    def test_the_slow_stacks_with_the_stairs_and_the_sweat(self):
        player, _ = make_player(x=4300)
        player.gauge.set_value(60.0)

        player.slow(3.0)

        expected = (
            config.STAIRS_SPEED_MULT * config.SWEAT_SPEED_MULT * config.FLYER_SPEED_MULT
        )
        self.assertAlmostEqual(player.speed_multiplier(), expected)

    def test_a_shorter_slow_does_not_cut_a_longer_one(self):
        self.player.slow(3.0)
        self.player.slow(1.0)

        run_for(self.player, 2.0)

        self.assertEqual(self.player.speed_multiplier(), config.FLYER_SPEED_MULT)

    def test_a_fresh_slow_extends_one_that_is_nearly_over(self):
        self.player.slow(1.0)
        run_for(self.player, 0.9)

        self.player.slow(3.0)
        run_for(self.player, 1.0)

        self.assertEqual(self.player.speed_multiplier(), config.FLYER_SPEED_MULT)

    def test_the_slow_keeps_wearing_off_while_the_player_is_stunned(self):
        self.player.slow(1.0)
        self.player.stun(2.0)

        run_for(self.player, 1.2)

        self.assertIs(state_of(self.player), Stunned)
        self.assertEqual(self.player.speed_multiplier(), 1.0)


class PushTest(PlayerTestCase):
    def test_a_push_moves_the_player_by_the_signed_distance(self):
        self.player.push(120)
        pushed_right = self.player.x
        self.player.push(-120)

        self.assertEqual(pushed_right, START_X + 120)
        self.assertEqual(self.player.x, START_X)

    def test_a_push_cannot_throw_the_player_out_of_the_stage(self):
        left_edge, _ = make_player(x=50)
        right_edge, _ = make_player(x=STAGE.length - 50)

        left_edge.push(-120)
        right_edge.push(120)

        self.assertEqual(left_edge.x, 0)
        self.assertEqual(right_edge.x, STAGE.length)

    def test_a_push_makes_the_camera_glide_instead_of_jumping(self):
        before = self.player.camera.is_gliding

        self.player.push(120)

        self.assertFalse(before)
        self.assertTrue(self.player.camera.is_gliding)

    def test_a_push_does_not_interrupt_what_the_player_is_doing(self):
        press(self.player, SDLK_RIGHT)
        run_for(self.player, 0.1)

        self.player.push(-120)

        self.assertIs(state_of(self.player), Walk)


if __name__ == "__main__":
    unittest.main()
