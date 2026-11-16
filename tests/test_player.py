import unittest
from typing import NamedTuple
from unittest import mock

from pico2d import (
    SDL_KEYDOWN,
    SDL_KEYUP,
    SDL_QUIT,
    SDLK_LEFT,
    SDLK_LSHIFT,
    SDLK_RIGHT,
    SDLK_RSHIFT,
    SDLK_SPACE,
    SDLK_a,
)

import config
import game_framework
import resource
import stage_data
from camera import Camera
from player import Idle, Jump, Player, Run, Walk, jump_step

FRAME = 1 / 60
STAGE = stage_data.get_stage(2)
SHIFT_KEYS = (SDLK_LSHIFT, SDLK_RSHIFT)


class FakeEvent:
    def __init__(self, event_type, key=None):
        self.type = event_type
        self.key = key


class Draw(NamedTuple):
    name: str
    x: float
    y: float
    frame: int
    flip: bool


class RecordingSprite(resource.Sprite):
    """실제 manifest의 프레임 수·fps를 쓰되, 이미지는 그리지 않고 호출만 기록한다."""

    def __init__(self, info, draws):
        super().__init__(info, loader=lambda path: None)
        self._draws = draws

    def draw(self, x, y, frame=0, flip=False, scale=1, alpha=1.0):
        self._draws.append(Draw(self.info.name, x, y, int(frame), flip))


class SpriteBook:
    """Player의 sprite_lookup 자리에 꽂는 가짜 조회 함수."""

    def __init__(self):
        self.manifest = resource.load_manifest()
        self.draws = []

    def __call__(self, name):
        return RecordingSprite(self.manifest[name], self.draws)


def make_player(x=None):
    camera = Camera(config.SCREEN_W, STAGE.length)
    book = SpriteBook()
    player = Player(STAGE, camera, sprite_lookup=book)
    if x is not None:
        player.x = float(x)
    return player, book


def press(player, key):
    player.handle_event(FakeEvent(SDL_KEYDOWN, key))


def release(player, key):
    player.handle_event(FakeEvent(SDL_KEYUP, key))


def run_for(player, seconds, dt=FRAME):
    for _ in range(round(seconds / dt)):
        player.step(dt)


def fly_until_landed(player, limit=200):
    """착지할 때까지 한 프레임씩 진행하고, 공중에 있던 프레임 수를 돌려준다."""
    steps = 0
    while player.state_machine.state is Jump:
        player.step(FRAME)
        steps += 1
        if steps > limit:
            raise AssertionError("점프가 끝나지 않았다")
    return steps


def state_of(player):
    return player.state_machine.state


class StartTest(unittest.TestCase):
    def test_player_starts_idle_on_the_ground_at_the_stage_start_facing_right(self):
        player, _ = make_player()

        self.assertEqual(player.x, STAGE.player_start_x)
        self.assertEqual(player.height, 0)
        self.assertEqual(player.facing, 1)
        self.assertIs(state_of(player), Idle)


class WalkAndRunTest(unittest.TestCase):
    def test_holding_right_walks_at_walk_speed(self):
        player, _ = make_player()

        press(player, SDLK_RIGHT)
        run_for(player, 1.0)

        self.assertAlmostEqual(player.x, STAGE.player_start_x + config.WALK_SPEED, 2)
        self.assertIs(state_of(player), Walk)

    def test_holding_left_walks_left_and_faces_left(self):
        player, _ = make_player(x=1000)

        press(player, SDLK_LEFT)
        run_for(player, 1.0)

        self.assertAlmostEqual(player.x, 1000 - config.WALK_SPEED, 2)
        self.assertEqual(player.facing, -1)

    def test_shift_with_a_direction_runs_at_run_speed(self):
        for shift in SHIFT_KEYS:
            with self.subTest(shift=shift):
                player, _ = make_player()

                press(player, SDLK_RIGHT)
                press(player, shift)
                run_for(player, 1.0)

                self.assertAlmostEqual(
                    player.x, STAGE.player_start_x + config.RUN_SPEED, 2
                )
                self.assertIs(state_of(player), Run)

    def test_shift_alone_does_not_move_the_player(self):
        player, _ = make_player()

        press(player, SDLK_LSHIFT)
        run_for(player, 0.5)

        self.assertEqual(player.x, STAGE.player_start_x)
        self.assertIs(state_of(player), Idle)

    def test_left_and_right_together_cancel_out_until_one_is_released(self):
        player, _ = make_player(x=1000)

        press(player, SDLK_LEFT)
        press(player, SDLK_RIGHT)
        run_for(player, 0.5)
        self.assertEqual(player.x, 1000)
        self.assertIs(state_of(player), Idle)

        release(player, SDLK_LEFT)
        run_for(player, 0.5)
        self.assertGreater(player.x, 1000)
        self.assertIs(state_of(player), Walk)

    def test_releasing_the_direction_returns_to_idle(self):
        player, _ = make_player()
        press(player, SDLK_RIGHT)
        run_for(player, 0.2)

        release(player, SDLK_RIGHT)

        self.assertIs(state_of(player), Idle)

    def test_shift_switches_between_walk_and_run_while_moving(self):
        player, _ = make_player()
        press(player, SDLK_RIGHT)
        self.assertIs(state_of(player), Walk)

        press(player, SDLK_LSHIFT)
        self.assertIs(state_of(player), Run)

        release(player, SDLK_LSHIFT)
        self.assertIs(state_of(player), Walk)

    def test_releasing_the_direction_while_running_stops_the_player(self):
        player, _ = make_player()
        press(player, SDLK_RIGHT)
        press(player, SDLK_LSHIFT)

        release(player, SDLK_RIGHT)

        self.assertIs(state_of(player), Idle)

    def test_stairs_slow_walking_down_to_the_configured_multiplier(self):
        player, _ = make_player(x=4300)

        press(player, SDLK_RIGHT)
        run_for(player, 1.0)

        expected = 4300 + config.WALK_SPEED * config.STAIRS_SPEED_MULT
        self.assertAlmostEqual(player.x, expected, 2)

    def test_stairs_slow_running_down_too(self):
        player, _ = make_player(x=4300)

        press(player, SDLK_RIGHT)
        press(player, SDLK_LSHIFT)
        run_for(player, 1.0)

        expected = 4300 + config.RUN_SPEED * config.STAIRS_SPEED_MULT
        self.assertAlmostEqual(player.x, expected, 2)

    def test_player_cannot_walk_past_the_left_edge(self):
        player, _ = make_player(x=5)

        press(player, SDLK_LEFT)
        run_for(player, 1.0)

        self.assertEqual(player.x, 0)

    def test_player_cannot_walk_past_the_right_edge(self):
        player, _ = make_player(x=STAGE.length - 5)

        press(player, SDLK_RIGHT)
        run_for(player, 1.0)

        self.assertEqual(player.x, STAGE.length)

    def test_player_keeps_the_last_facing_after_stopping(self):
        player, _ = make_player(x=1000)
        press(player, SDLK_LEFT)
        run_for(player, 0.3)

        release(player, SDLK_LEFT)
        run_for(player, 0.3)

        self.assertIs(state_of(player), Idle)
        self.assertEqual(player.facing, -1)

    def test_update_advances_by_the_framework_frame_time(self):
        player, _ = make_player()
        press(player, SDLK_RIGHT)

        with mock.patch.object(game_framework, "frame_time", 0.5):
            player.update()

        self.assertAlmostEqual(player.x, STAGE.player_start_x + config.WALK_SPEED * 0.5)


class SpeedMultiplierTest(unittest.TestCase):
    def test_multiplier_is_one_on_flat_ground(self):
        player, _ = make_player(x=300)

        self.assertEqual(player.speed_multiplier(), 1.0)

    def test_multiplier_is_the_stairs_value_inside_the_stairs_zone(self):
        player, _ = make_player(x=4300)

        self.assertEqual(player.speed_multiplier(), config.STAIRS_SPEED_MULT)


class JumpStepTest(unittest.TestCase):
    def test_step_follows_constant_acceleration_exactly(self):
        height, vy = jump_step(0.0, config.JUMP_V0, 0.5)

        self.assertAlmostEqual(
            height, config.JUMP_V0 * 0.5 - config.GRAVITY * 0.5**2 / 2
        )
        self.assertAlmostEqual(vy, config.JUMP_V0 - config.GRAVITY * 0.5)

    def test_many_small_steps_land_where_one_big_step_does(self):
        big = jump_step(0.0, config.JUMP_V0, 0.4)
        height, vy = 0.0, config.JUMP_V0
        for _ in range(40):
            height, vy = jump_step(height, vy, 0.01)

        self.assertAlmostEqual(height, big[0])
        self.assertAlmostEqual(vy, big[1])


class JumpTest(unittest.TestCase):
    def test_space_on_the_ground_starts_a_jump(self):
        for setup in (None, SDLK_RIGHT, SDLK_LSHIFT):
            with self.subTest(setup=setup):
                player, _ = make_player()
                if setup == SDLK_LSHIFT:
                    press(player, SDLK_RIGHT)
                if setup is not None:
                    press(player, setup)

                press(player, SDLK_SPACE)

                self.assertIs(state_of(player), Jump)

    def test_releasing_space_does_not_jump(self):
        player, _ = make_player()

        release(player, SDLK_SPACE)

        self.assertIs(state_of(player), Idle)

    def test_jump_apex_is_v0_squared_over_two_g_and_airtime_is_two_v0_over_g(self):
        player, _ = make_player()
        press(player, SDLK_SPACE)
        heights = []
        while state_of(player) is Jump and len(heights) < 200:
            player.step(FRAME)
            heights.append(player.height)

        apex = config.JUMP_V0**2 / (2 * config.GRAVITY)
        airtime = 2 * config.JUMP_V0 / config.GRAVITY
        self.assertAlmostEqual(max(heights), apex, delta=1)
        self.assertAlmostEqual(len(heights) * FRAME, airtime, delta=FRAME)
        self.assertEqual(player.height, 0)
        self.assertGreaterEqual(min(heights), 0)
        self.assertIs(state_of(player), Idle)

    def test_jump_apex_does_not_depend_on_the_frame_rate(self):
        apex = config.JUMP_V0**2 / (2 * config.GRAVITY)
        for dt in (1 / 30, 1 / 60, 1 / 144):
            with self.subTest(dt=dt):
                player, _ = make_player()
                press(player, SDLK_SPACE)
                highest = 0.0
                for _ in range(round(1.0 / dt)):
                    player.step(dt)
                    highest = max(highest, player.height)

                self.assertAlmostEqual(highest, apex, delta=1)

    def test_pressing_space_again_in_the_air_does_nothing(self):
        def height_trace(extra_space_at):
            player, _ = make_player()
            press(player, SDLK_SPACE)
            heights = []
            for index in range(70):
                if index == extra_space_at:
                    press(player, SDLK_SPACE)
                player.step(FRAME)
                heights.append(player.height)
            return heights

        self.assertEqual(height_trace(None), height_trace(20))

    def test_jump_pose_is_frame_0_while_rising_and_frame_1_while_falling(self):
        player, book = make_player()
        press(player, SDLK_SPACE)

        run_for(player, 0.2)
        player.draw()
        run_for(player, 0.5)
        player.draw()

        rising, falling = book.draws
        self.assertEqual((rising.name, rising.frame), ("player_calm_jump", 0))
        self.assertEqual((falling.name, falling.frame), ("player_calm_jump", 1))

    def test_right_key_moves_the_player_forward_in_the_air_at_walk_speed(self):
        player, _ = make_player()
        press(player, SDLK_RIGHT)
        press(player, SDLK_SPACE)

        airborne_frames = fly_until_landed(player)

        flown = config.WALK_SPEED * airborne_frames * FRAME
        self.assertAlmostEqual(player.x, STAGE.player_start_x + flown, 2)

    def test_holding_shift_in_the_air_moves_at_run_speed(self):
        player, _ = make_player()
        press(player, SDLK_RIGHT)
        press(player, SDLK_LSHIFT)
        press(player, SDLK_SPACE)

        airborne_frames = fly_until_landed(player)

        flown = config.RUN_SPEED * airborne_frames * FRAME
        self.assertAlmostEqual(player.x, STAGE.player_start_x + flown, 2)

    def test_pressing_left_in_the_air_turns_the_player_around(self):
        player, _ = make_player(x=1000)
        press(player, SDLK_SPACE)
        press(player, SDLK_LEFT)

        run_for(player, 0.2)

        self.assertLess(player.x, 1000)
        self.assertEqual(player.facing, -1)
        self.assertIs(state_of(player), Jump)

    def test_landing_returns_to_idle_walk_or_run_by_the_keys_held_then(self):
        cases = {
            "nothing held": ((), (), Idle),
            "direction held all along": ((SDLK_RIGHT,), (), Walk),
            "direction and shift held": ((SDLK_RIGHT, SDLK_LSHIFT), (), Run),
            "direction released in the air": ((SDLK_RIGHT,), ("up", SDLK_RIGHT), Idle),
            "direction pressed in the air": ((), ("down", SDLK_RIGHT), Walk),
            "shift pressed in the air": (
                (SDLK_RIGHT,),
                ("down", SDLK_RSHIFT),
                Run,
            ),
        }
        for name, (at_takeoff, in_air, expected) in cases.items():
            with self.subTest(name):
                player, _ = make_player()
                for key in at_takeoff:
                    press(player, key)
                press(player, SDLK_SPACE)
                run_for(player, 0.2)
                if in_air:
                    action, key = in_air
                    (press if action == "down" else release)(player, key)

                fly_until_landed(player)

                self.assertIs(state_of(player), expected)
                self.assertEqual(player.height, 0)


class BoundingBoxTest(unittest.TestCase):
    def test_standing_box_sits_on_the_ground_around_the_player(self):
        player, _ = make_player(x=500)

        left = 500 - config.PLAYER_BB_HALF_W
        right = 500 + config.PLAYER_BB_HALF_W
        top = config.GROUND_Y + config.PLAYER_BB_HEIGHT
        self.assertEqual(player.get_bb(), (left, config.GROUND_Y, right, top))

    def test_box_rises_with_the_jump_height(self):
        player, _ = make_player(x=500)
        player.height = 50.0

        _, bottom, _, top = player.get_bb()

        self.assertEqual(bottom, config.GROUND_Y + 50)
        self.assertEqual(top, config.GROUND_Y + 50 + config.PLAYER_BB_HEIGHT)


class DrawTest(unittest.TestCase):
    def test_draws_the_calm_sheet_for_the_current_state_at_the_screen_position(self):
        player, book = make_player(x=700)
        player.camera.x = 300
        expected_y = book("player_calm_idle").ground_center_y(0)
        book.draws.clear()

        player.draw()

        self.assertEqual(
            book.draws, [Draw("player_calm_idle", 400, expected_y, 0, False)]
        )

    def test_draw_follows_the_state_walk_then_run(self):
        player, book = make_player()
        press(player, SDLK_RIGHT)
        player.draw()
        press(player, SDLK_LSHIFT)
        player.draw()

        self.assertEqual(
            [draw.name for draw in book.draws],
            ["player_calm_walk", "player_calm_run"],
        )

    def test_the_sprite_is_flipped_only_while_facing_left(self):
        player, book = make_player(x=1000)
        player.draw()
        press(player, SDLK_LEFT)
        run_for(player, 0.1)
        player.draw()
        release(player, SDLK_LEFT)
        player.draw()
        press(player, SDLK_RIGHT)
        run_for(player, 0.1)
        player.draw()

        self.assertEqual([draw.flip for draw in book.draws], [False, True, True, False])

    def test_the_jump_sprite_is_lifted_by_the_jump_height(self):
        player, book = make_player()
        on_ground = book("player_calm_jump").ground_center_y(0)
        press(player, SDLK_SPACE)
        run_for(player, 0.3)

        player.draw()

        self.assertAlmostEqual(book.draws[-1].y, on_ground + player.height)
        self.assertGreater(player.height, 0)

    def test_walk_animation_follows_the_sheet_fps_and_restarts_in_each_state(self):
        player, book = make_player()
        press(player, SDLK_RIGHT)
        run_for(player, 0.3)  # walk 8 fps -> 2.4 frames
        player.draw()
        release(player, SDLK_RIGHT)
        player.draw()

        walk, idle = book.draws
        self.assertEqual((walk.name, walk.frame), ("player_calm_walk", 2))
        self.assertEqual((idle.name, idle.frame), ("player_calm_idle", 0))


class InputTest(unittest.TestCase):
    def test_unrelated_events_are_ignored(self):
        player, _ = make_player()

        press(player, SDLK_a)
        release(player, SDLK_RIGHT)
        player.handle_event(FakeEvent(SDL_QUIT))
        run_for(player, 0.2)

        self.assertEqual(player.x, STAGE.player_start_x)
        self.assertIs(state_of(player), Idle)


if __name__ == "__main__":
    unittest.main()
