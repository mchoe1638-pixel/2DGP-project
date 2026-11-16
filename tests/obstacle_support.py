"""장애물 시험들이 함께 쓰는 바탕: 카메라·플레이어·그리기 장부와, 장애물 만들기·부딪히기·시간 보내기."""

import unittest

import config
import game_world
import level
from camera import Camera
from obstacle import PLAYER_OBSTACLE
from stage_data import ObstacleSpec
from tests.support import FRAME, STAGE, SpriteBook, make_player

PLAYER_START_X = 500.0  # 장애물(1000 이후)과는 멀리 떨어진 자리


class ObstacleTestCase(unittest.TestCase):
    """월드를 비운 채 시작해서, 시험이 만든 장애물과 그 이펙트만 월드에 올라 있게 한다."""

    def setUp(self):
        game_world.clear()
        self.addCleanup(game_world.clear)
        self.book = SpriteBook()
        self.camera = Camera(config.SCREEN_W, STAGE.length)
        self.player, _ = make_player(
            x=PLAYER_START_X, camera=self.camera, book=self.book
        )
        self.camera.snap_to(self.player.x)

    def make(self, kind, x, count=1):
        """kind 장애물을 x에 만들어 월드의 장애물 층에 올린다."""
        spec = ObstacleSpec(kind, x, count)
        obstacle = level.create_obstacle(spec, self.camera, self.player, self.book)
        game_world.add_object(obstacle, game_world.LAYER_OBSTACLE)
        return obstacle

    def touch(self, obstacle):
        """플레이어와 장애물이 겹쳤다고 장애물에 알린다 (겹침 검사 자체는 play_mode 시험이 맡는다)."""
        obstacle.handle_collision(PLAYER_OBSTACLE, self.player)

    @staticmethod
    def step_for(obstacle, seconds):
        """장애물을 1/60초 프레임으로 seconds초 진행한다."""
        for _ in range(round(seconds / FRAME)):
            obstacle.step(FRAME)

    def draw_of(self, obstacle):
        """장애물을 한 번 그리고, 마지막 그리기 기록을 돌려준다."""
        self.book.draws.clear()
        obstacle.draw()
        return self.book.draws[-1]

    @staticmethod
    def effects(sprite_name):
        """지금 월드에 떠 있는 sprite_name 이펙트들."""
        return [
            effect
            for effect in game_world.world[game_world.LAYER_FX]
            if effect.sprite_name == sprite_name
        ]

    @staticmethod
    def in_world(obstacle):
        return obstacle in game_world.world[game_world.LAYER_OBSTACLE]
