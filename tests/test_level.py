"""장애물 만들기: 배치표 한 줄(ObstacleSpec)이 어떤 객체가 되는지, 표 전체가 순서대로 만들어지는지."""

import dataclasses
import unittest

import config
import crowd
import game_world
import level
import obstacle
import stage_data
from camera import Camera
from obstacle import PLAYER_OBSTACLE
from player import Stunned
from stage_data import ObstacleSpec
from tests.support import STAGE, SpriteBook, make_player, state_of

CLASS_BY_KIND = {
    stage_data.TOURIST: obstacle.Tourist,
    stage_data.FLYER: obstacle.Flyer,
    stage_data.BOSS: obstacle.Boss,
    stage_data.CROWD: crowd.Crowd,
}
STAGE_2_CLASSES = [  # 기획서 2스테이지 배치표의 순서
    obstacle.Tourist,
    obstacle.Flyer,
    obstacle.Boss,
    crowd.Crowd,
    obstacle.Tourist,
    obstacle.Flyer,
    crowd.Crowd,
]
SOMEWHERE_X = 1234.0


class LevelTestCase(unittest.TestCase):
    """월드를 비운 채 시작해서, 만들어진 것이 월드에 저절로 올라가지 않는지 볼 수 있게 한다."""

    def setUp(self):
        game_world.clear()
        self.addCleanup(game_world.clear)
        self.book = SpriteBook()
        self.camera = Camera(config.SCREEN_W, STAGE.length)
        self.player, _ = make_player(camera=self.camera, book=self.book)

    def create(self, kind, x, count=1):
        spec = ObstacleSpec(kind, x, count)
        return level.create_obstacle(spec, self.camera, self.player, self.book)

    def create_table(self, stage=STAGE):
        return level.create_obstacles(stage, self.camera, self.player, self.book)


class CreateObstacleTest(LevelTestCase):
    def test_each_kind_becomes_its_own_class_standing_at_the_table_position(self):
        for kind, expected_class in CLASS_BY_KIND.items():
            with self.subTest(kind=kind):
                created = self.create(kind, SOMEWHERE_X)

                self.assertIs(type(created), expected_class)
                self.assertEqual(created.x, SOMEWHERE_X)

    def test_a_crowd_is_as_wide_as_the_number_of_people_in_the_spec(self):
        for count in (3, 4):
            with self.subTest(count=count):
                left, _, right, _ = self.create(
                    stage_data.CROWD, SOMEWHERE_X, count
                ).get_bb()

                self.assertEqual(right - left, count * config.CROWD_MEMBER_SPACING)

    def test_an_unknown_kind_is_a_readable_error_naming_the_kind(self):
        with self.assertRaisesRegex(ValueError, "dragon"):
            self.create("dragon", SOMEWHERE_X)

    def test_nothing_is_put_into_the_world(self):
        for kind in CLASS_BY_KIND:
            self.create(kind, SOMEWHERE_X)

        self.assertEqual(game_world.all_objects(), [])

    def test_the_obstacle_hits_the_player_it_was_made_for(self):
        tourist = self.create(stage_data.TOURIST, SOMEWHERE_X)

        tourist.handle_collision(PLAYER_OBSTACLE, self.player)

        self.assertIs(state_of(self.player), Stunned)

    def test_the_sprite_lookup_that_was_handed_in_is_the_one_used_to_draw(self):
        self.camera.snap_to(SOMEWHERE_X)
        tourist = self.create(stage_data.TOURIST, SOMEWHERE_X)

        tourist.draw()

        self.assertEqual([draw.name for draw in self.book.draws], ["npc_tourist"])


class CreateObstaclesTest(LevelTestCase):
    def test_the_whole_table_is_built_in_table_order(self):
        built = self.create_table()

        self.assertEqual([type(each) for each in built], STAGE_2_CLASSES)
        self.assertEqual(
            [each.x for each in built], [spec.x for spec in STAGE.obstacles]
        )

    def test_the_crowds_in_the_table_keep_their_sizes(self):
        built = self.create_table()

        widths = []
        for each in built:
            if isinstance(each, crowd.Crowd):
                left, _, right, _ = each.get_bb()
                widths.append(right - left)
        self.assertEqual(
            widths, [4 * config.CROWD_MEMBER_SPACING, 3 * config.CROWD_MEMBER_SPACING]
        )

    def test_a_stage_without_obstacles_builds_none(self):
        bare = dataclasses.replace(STAGE, obstacles=())

        self.assertEqual(list(self.create_table(bare)), [])

    def test_building_the_table_does_not_touch_the_world(self):
        self.create_table()

        self.assertEqual(game_world.all_objects(), [])


if __name__ == "__main__":
    unittest.main()
