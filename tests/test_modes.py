import unittest
from unittest import mock

from pico2d import SDL_KEYDOWN, SDL_KEYUP, SDL_QUIT, SDLK_ESCAPE, SDLK_SPACE, SDLK_a

import game_framework
import play_mode
import title_mode


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


if __name__ == "__main__":
    unittest.main()
