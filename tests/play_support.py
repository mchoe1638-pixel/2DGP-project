"""플레이 화면을 실제 월드로 만들어 놓고 시험하는 테스트들의 공통 바탕."""

import unittest
from unittest import mock

from pico2d import SDL_KEYDOWN

import game_framework
import play_mode
from tests.support import FRAME, FakeEvent


class PlayModeTestCase(unittest.TestCase):
    """init()으로 실제 월드를 만든 플레이 화면 (그리기는 하지 않으므로 캔버스는 필요 없다)."""

    def setUp(self):
        play_mode.init()
        self.addCleanup(play_mode.finish)

    @staticmethod
    def advance(seconds=FRAME):
        """seconds초를 1/60초 프레임으로 나눠 플레이 화면을 갱신한다."""
        with mock.patch.object(game_framework, "frame_time", FRAME):
            for _ in range(round(seconds / FRAME)):
                play_mode.update()

    @staticmethod
    def key(key_code, event_type=SDL_KEYDOWN):
        play_mode.handle_event(FakeEvent(event_type, key_code))
