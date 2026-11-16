import unittest
from unittest import mock

from pico2d import (
    SDL_KEYDOWN,
    SDL_KEYUP,
    SDL_QUIT,
    SDLK_ESCAPE,
    SDLK_RIGHT,
    SDLK_SPACE,
    SDLK_a,
)

import config
import game_framework
import game_world
import play_mode
import title_mode
from player import Player
from util import snap

FRAME = 1 / 60


class FakeEvent:
    def __init__(self, event_type, key=None):
        self.type = event_type
        self.key = key


class TitleModeEventsTest(unittest.TestCase):
    def test_space_starts_the_play_mode(self):
        with mock.patch.object(game_framework, "change_mode") as change_mode:
            title_mode.handle_event(FakeEvent(SDL_KEYDOWN, SDLK_SPACE))
        change_mode.assert_called_once_with(play_mode)

    def test_escape_quits_the_game(self):
        with mock.patch.object(game_framework, "quit") as quit_game:
            title_mode.handle_event(FakeEvent(SDL_KEYDOWN, SDLK_ESCAPE))
        quit_game.assert_called_once_with()

    def test_closing_the_window_quits_the_game(self):
        with mock.patch.object(game_framework, "quit") as quit_game:
            title_mode.handle_event(FakeEvent(SDL_QUIT))
        quit_game.assert_called_once_with()

    def test_releasing_space_does_not_start_the_game(self):
        with mock.patch.object(game_framework, "change_mode") as change_mode:
            title_mode.handle_event(FakeEvent(SDL_KEYUP, SDLK_SPACE))
        change_mode.assert_not_called()

    def test_other_keys_do_nothing(self):
        with mock.patch.object(
            game_framework, "change_mode"
        ) as change_mode, mock.patch.object(game_framework, "quit") as quit_game:
            title_mode.handle_event(FakeEvent(SDL_KEYDOWN, SDLK_a))
        change_mode.assert_not_called()
        quit_game.assert_not_called()


class TitleBlinkTest(unittest.TestCase):
    def test_prompt_is_visible_during_the_first_half_of_each_period(self):
        self.assertTrue(title_mode.blink_visible(0.0, 1.0))
        self.assertTrue(title_mode.blink_visible(0.4, 1.0))

    def test_prompt_is_hidden_during_the_second_half_of_each_period(self):
        self.assertFalse(title_mode.blink_visible(0.5, 1.0))
        self.assertFalse(title_mode.blink_visible(0.9, 1.0))

    def test_blinking_repeats_every_period(self):
        self.assertTrue(title_mode.blink_visible(3.1, 1.0))
        self.assertFalse(title_mode.blink_visible(3.6, 1.0))


class PlayModeEventsTest(unittest.TestCase):
    def test_escape_returns_to_the_title(self):
        with mock.patch.object(game_framework, "change_mode") as change_mode:
            play_mode.handle_event(FakeEvent(SDL_KEYDOWN, SDLK_ESCAPE))
        change_mode.assert_called_once_with(title_mode)

    def test_closing_the_window_quits_the_game(self):
        with mock.patch.object(game_framework, "quit") as quit_game:
            play_mode.handle_event(FakeEvent(SDL_QUIT))
        quit_game.assert_called_once_with()


class PlayModeWorldTest(unittest.TestCase):
    """init()으로 실제 월드를 만든 플레이 화면 (그리기는 하지 않으므로 캔버스는 필요 없다)."""

    def setUp(self):
        play_mode.init()
        self.addCleanup(play_mode.finish)

    @staticmethod
    def advance(dt=FRAME):
        with mock.patch.object(game_framework, "frame_time", dt):
            play_mode.update()

    def test_init_puts_the_player_on_the_player_layer_at_the_stage_start(self):
        player = play_mode.player

        self.assertIsInstance(player, Player)
        self.assertEqual(player.x, play_mode.stage.player_start_x)
        self.assertEqual(game_world.world[game_world.LAYER_PLAYER], [player])

    def test_init_builds_a_fresh_player_each_time_the_mode_is_entered(self):
        first = play_mode.player

        play_mode.init()

        self.assertIsNot(play_mode.player, first)
        self.assertEqual(len(game_world.world[game_world.LAYER_PLAYER]), 1)

    def test_arrow_keys_are_forwarded_to_the_player(self):
        start = play_mode.player.x

        play_mode.handle_event(FakeEvent(SDL_KEYDOWN, SDLK_RIGHT))
        self.advance(0.5)

        self.assertAlmostEqual(play_mode.player.x, start + config.WALK_SPEED * 0.5)

    def test_escape_still_returns_to_the_title_once_the_world_exists(self):
        with mock.patch.object(game_framework, "change_mode") as change_mode:
            play_mode.handle_event(FakeEvent(SDL_KEYDOWN, SDLK_ESCAPE))

        change_mode.assert_called_once_with(title_mode)

    def test_camera_starts_at_the_left_end_of_the_stage(self):
        self.assertEqual(play_mode.camera.x, 0)

    def test_camera_follows_the_player_within_the_same_frame(self):
        play_mode.player.x = 1000.0
        play_mode.handle_event(FakeEvent(SDL_KEYDOWN, SDLK_RIGHT))

        self.advance(FRAME)

        anchor = config.SCREEN_W // config.CAMERA_ANCHOR_DIV
        self.assertEqual(
            play_mode.camera.x, snap(1000 + config.WALK_SPEED * FRAME) - anchor
        )

    def test_player_stays_a_third_of_the_screen_from_the_left_edge(self):
        play_mode.player.x = 3000.0

        self.advance()

        anchor = config.SCREEN_W // config.CAMERA_ANCHOR_DIV
        self.assertEqual(play_mode.camera.to_screen_x(3000.0), anchor)

    def test_camera_stops_at_both_ends_of_the_stage(self):
        play_mode.player.x = float(play_mode.stage.length)
        self.advance()
        self.assertEqual(play_mode.camera.x, play_mode.stage.length - config.SCREEN_W)

        play_mode.player.x = 0.0
        self.advance()
        self.assertEqual(play_mode.camera.x, 0)


if __name__ == "__main__":
    unittest.main()
