"""플레이 화면의 게이지 연결: 시간 흘리기, 달리기 배율, 디버그 키, 한 스테이지 걷기 검증."""

import unittest
from unittest import mock

from pico2d import (
    SDL_KEYUP,
    SDLK_F1,
    SDLK_F2,
    SDLK_F3,
    SDLK_F4,
    SDLK_LSHIFT,
    SDLK_RIGHT,
    SDLK_g,
)

import config
import game_framework
import game_world
import play_mode
from gauge import Gauge, GaugeStage
from player import Run, Walk
from tests.play_support import PlayModeTestCase
from tests.support import FRAME

BASE_RATE = config.GAUGE_BASE_RATE[2]  # 플레이 화면은 2스테이지
WALK_LIMIT_FRAMES = 60 * 120  # 한 스테이지 걷기가 이 안에 끝나지 않으면 뭔가 잘못된 것


class PlayGaugeTestCase(PlayModeTestCase):
    """게이지 시험은 플레이 화면 공통 바탕을 그대로 쓴다."""


class SetupTest(PlayGaugeTestCase):
    def test_init_builds_a_calm_gauge_at_the_stage_rate(self):
        self.assertIsInstance(play_mode.gauge, Gauge)
        self.assertEqual(play_mode.gauge.value, 0)
        self.assertEqual(play_mode.gauge.rate, BASE_RATE)

    def test_the_player_reads_the_same_gauge(self):
        self.assertIs(play_mode.player.gauge, play_mode.gauge)

    def test_entering_the_mode_again_starts_over_with_an_empty_gauge(self):
        old = play_mode.gauge
        old.set_value(70)

        play_mode.init()

        self.assertIsNot(play_mode.gauge, old)
        self.assertEqual(play_mode.gauge.value, 0)


class RiseTest(PlayGaugeTestCase):
    def test_standing_still_fills_at_the_base_rate(self):
        self.advance(1.0)

        self.assertAlmostEqual(play_mode.gauge.value, BASE_RATE, 6)

    def test_walking_fills_at_the_base_rate_too(self):
        self.key(SDLK_RIGHT)

        self.advance(1.0)

        self.assertAlmostEqual(play_mode.gauge.value, BASE_RATE, 6)

    def test_running_fills_faster_by_the_run_multiplier(self):
        self.key(SDLK_RIGHT)
        self.key(SDLK_LSHIFT)

        self.advance(1.0)

        self.assertAlmostEqual(
            play_mode.gauge.value, BASE_RATE * config.RUN_GAUGE_MULT, 6
        )

    def test_gum_holds_the_gauge_and_counts_down(self):
        play_mode.gauge.freeze(3.0)

        self.advance(1.0)

        self.assertEqual(play_mode.gauge.value, 0)
        self.assertAlmostEqual(play_mode.gauge.freeze_remaining, 2.0, 6)


class DebugKeysTest(PlayGaugeTestCase):
    def test_function_keys_jump_the_gauge_to_the_start_of_each_stage(self):
        first, second, third = config.STAGE_THRESHOLDS[:3]
        cases = ((SDLK_F1, 0), (SDLK_F2, first), (SDLK_F3, second), (SDLK_F4, third))
        for key_code, expected in cases:
            with self.subTest(key=key_code):
                play_mode.gauge.set_value(70)  # 어느 키의 값과도 다른 값에서 출발한다

                self.key(key_code)

                self.assertEqual(play_mode.gauge.value, expected)

    def test_releasing_a_function_key_does_nothing(self):
        self.key(SDLK_F4, SDL_KEYUP)

        self.assertEqual(play_mode.gauge.value, 0)

    def test_g_freezes_the_gauge_until_it_is_pressed_again(self):
        self.key(SDLK_g)
        self.advance(1.0)
        self.assertEqual(play_mode.gauge.value, 0)

        self.key(SDLK_g)
        self.advance(1.0)

        self.assertGreater(play_mode.gauge.value, 0)

    def test_a_debug_jump_into_the_strain_stage_stops_a_running_player(self):
        self.key(SDLK_RIGHT)
        self.key(SDLK_LSHIFT)
        self.assertIs(play_mode.player.state_machine.state, Run)

        self.key(SDLK_F3)
        self.advance()

        self.assertIs(play_mode.player.state_machine.state, Walk)
        self.assertEqual(play_mode.player.mood, "strain")


class StageWalkAcceptanceTest(PlayGaugeTestCase):
    """기획 검증: 2스테이지를 쉬지 않고 걸으면 약 46.9초 걸리고 게이지는 약 65.7%가 된다."""

    def walk_to_goal(self):
        """→ 키만 누른 채 골까지 걷는다. (걸린 시간, 땀 단계가 시작된 x좌표)를 돌려준다.

        기준 시간은 장애물이 없는 길의 값이므로, 먼저 길 위의 장애물을 모두 치운다.
        """
        for obstacle in list(game_world.world[game_world.LAYER_OBSTACLE]):
            game_world.remove_object(obstacle)
        self.key(SDLK_RIGHT)
        sweat_x = None
        with mock.patch.object(game_framework, "frame_time", FRAME):
            for frame in range(1, WALK_LIMIT_FRAMES + 1):
                play_mode.update()
                if sweat_x is None and play_mode.gauge.stage >= GaugeStage.SWEAT:
                    sweat_x = play_mode.player.x
                if play_mode.player.x >= play_mode.stage.goal_x:
                    return frame * FRAME, sweat_x
        self.fail("제한 시간 안에 골에 닿지 못했다")

    def test_whole_stage_walk_time_and_final_gauge(self):
        elapsed, _ = self.walk_to_goal()

        self.assertAlmostEqual(elapsed, 46.9, delta=0.2)
        self.assertAlmostEqual(play_mode.gauge.value, 65.7, delta=1.0)
        self.assertIs(play_mode.gauge.stage, GaugeStage.SWEAT)

    def test_sweat_begins_beyond_the_stairs(self):
        _, sweat_x = self.walk_to_goal()

        stairs_end = play_mode.stage.stairs_zone[1]
        self.assertAlmostEqual(sweat_x, 6778, delta=30)
        self.assertGreater(sweat_x, stairs_end)


if __name__ == "__main__":
    unittest.main()
