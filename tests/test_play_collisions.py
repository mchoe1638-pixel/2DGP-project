"""플레이 화면의 장애물: 배치와 충돌 등록, 실제로 걸어가서 부딪히는 흐름, B 키 충돌 상자."""

import unittest
from unittest import mock

from pico2d import SDL_KEYUP, SDLK_LSHIFT, SDLK_RIGHT, SDLK_SPACE, SDLK_b

import config
import game_world
import gfx
import play_mode
import stage_data
from obstacle import PLAYER_OBSTACLE
from player import Stunned
from tests.play_support import PlayModeTestCase
from tests.support import FRAME, STAGE, state_of


def first_spec(kind):
    """배치표에서 kind 장애물 중 가장 앞에 있는 줄."""
    return next(spec for spec in STAGE.obstacles if spec.kind == kind)


TOURIST_X = first_spec(stage_data.TOURIST).x
BOSS_X = first_spec(stage_data.BOSS).x
CROWD_SPEC = first_spec(stage_data.CROWD)
CROWD_X = CROWD_SPEC.x
CROWD_HALF_WIDTH = (
    CROWD_SPEC.count - 1
) / 2 * config.CROWD_MEMBER_SPACING + config.NPC_BB_HALF_W
BODY = config.PLAYER_BB_HALF_W  # 플레이어 몸의 반폭
TOURIST_REACH = (
    TOURIST_X - config.NPC_BB_HALF_W - BODY
)  # 이 x를 넘으면 오른쪽으로 걷다 닿는다
CROWD_REACH = CROWD_X - CROWD_HALF_WIDTH - BODY
CROWD_FAR_REACH = (
    CROWD_X + CROWD_HALF_WIDTH + BODY
)  # 이 x를 넘으면 인파를 완전히 빠져나온 것
CROWD_CLOSED_TIME = config.CROWD_GAP_PERIOD - config.CROWD_GAP_OPEN_TIME
OBSTACLE_COUNT = len(STAGE.obstacles)
BOX_COUNT = 1 + OBSTACLE_COUNT  # 플레이어 + 장애물 전부
BEFORE_TOURIST = 60  # 관광객 앞 이만큼에서 걷기 시작하면 곧 닿는다
JUMP_TAKEOFF = 170  # 관광객 앞 이만큼에서 달리며 뛰면 머리 위를 지난다
JUMP_FLIGHT_TIME = 1.2  # 점프(0.88초)가 끝나고도 남는 시간
BEFORE_CROWD = 12  # 인파에 닿기 이만큼 전에서 걷기 시작한다
CROSSING_LIMIT_FRAMES = 3 * 60


class CollisionTestCase(PlayModeTestCase):
    def setUp(self):
        super().setUp()
        self.player = play_mode.player

    def place_player(self, x):
        self.player.x = float(x)
        play_mode.camera.snap_to(self.player.x)

    def advance_until(self, condition, limit=2.0):
        """condition()이 참이 될 때까지 한 프레임씩 진행한다. 제한 시간 안에 안 되면 시험이 실패한다."""
        for _ in range(round(limit / FRAME)):
            self.advance()
            if condition():
                return
        self.fail("제한 시간 안에 기대한 일이 일어나지 않았다")

    def advance_until_stunned(self):
        self.advance_until(lambda: state_of(self.player) is Stunned)

    def run_right(self):
        self.key(SDLK_RIGHT)
        self.key(SDLK_LSHIFT)


class PlacementTest(CollisionTestCase):
    def test_the_whole_table_stands_in_the_obstacle_layer_in_table_order(self):
        placed = game_world.world[game_world.LAYER_OBSTACLE]

        self.assertEqual(len(placed), OBSTACLE_COUNT)
        self.assertEqual(
            [each.x for each in placed], [spec.x for spec in STAGE.obstacles]
        )

    def test_the_player_and_every_obstacle_are_registered_to_collide(self):
        placed = list(game_world.world[game_world.LAYER_OBSTACLE])

        self.assertEqual(
            game_world.collision_pairs[PLAYER_OBSTACLE], [[self.player], placed]
        )

    def test_entering_the_mode_again_builds_a_fresh_set_without_duplicates(self):
        old = list(game_world.world[game_world.LAYER_OBSTACLE])

        play_mode.init()

        placed = game_world.world[game_world.LAYER_OBSTACLE]
        self.assertEqual(len(placed), OBSTACLE_COUNT)
        self.assertTrue(all(each not in old for each in placed))
        pair = game_world.collision_pairs[PLAYER_OBSTACLE]
        self.assertEqual([len(side) for side in pair], [1, OBSTACLE_COUNT])


class TouristEncounterTest(CollisionTestCase):
    def test_walking_into_the_tourist_stops_the_player_without_a_fall(self):
        self.place_player(TOURIST_X - BEFORE_TOURIST)
        self.key(SDLK_RIGHT)

        self.advance_until_stunned()

        self.assertAlmostEqual(
            self.player.stun_remaining, config.TOURIST_STOP_TIME, delta=0.05
        )
        self.assertEqual(self.player.fall_remaining, 0.0)

    def test_running_into_the_tourist_knocks_the_player_down_as_well(self):
        self.place_player(TOURIST_X - BEFORE_TOURIST)
        self.run_right()

        self.advance_until_stunned()

        self.assertGreater(self.player.fall_remaining, 0.0)
        self.assertGreaterEqual(self.player.gauge.value, config.FALL_GAUGE_ADD)

    def test_the_player_is_stopped_on_the_very_frame_the_boxes_first_touch(self):
        self.place_player(TOURIST_X - BEFORE_TOURIST)
        self.key(SDLK_RIGHT)

        self.advance_until(lambda: self.player.x > TOURIST_REACH)

        self.assertIs(state_of(self.player), Stunned)

    def test_a_running_jump_clears_the_tourist(self):
        self.place_player(TOURIST_X - JUMP_TAKEOFF)
        self.run_right()
        self.key(SDLK_SPACE)
        tourist = game_world.world[game_world.LAYER_OBSTACLE][0]

        for _ in range(round(JUMP_FLIGHT_TIME / FRAME)):
            self.advance()
            self.assertIsNot(state_of(self.player), Stunned)

        self.assertTrue(tourist.active)
        self.assertGreater(self.player.x, TOURIST_X + config.NPC_BB_HALF_W + BODY)


class BossWarningTest(CollisionTestCase):
    @staticmethod
    def exclamations():
        return [
            effect
            for effect in game_world.world[game_world.LAYER_FX]
            if effect.sprite_name == "fx_exclaim"
        ]

    def test_coming_within_the_warning_distance_raises_one_exclamation(self):
        self.place_player(BOSS_X - config.BOSS_WARN_DISTANCE + 10)

        self.advance()
        self.assertEqual(len(self.exclamations()), 1)

        self.advance(0.2)  # 계속 가까이 있어도 경고는 한 번뿐이다
        self.assertEqual(len(self.exclamations()), 1)

    def test_staying_outside_the_warning_distance_raises_nothing(self):
        self.place_player(BOSS_X - config.BOSS_WARN_DISTANCE - 10)

        self.advance(0.2)

        self.assertEqual(self.exclamations(), [])


class CrowdEncounterTest(CollisionTestCase):
    def test_walking_into_the_closed_crowd_pushes_the_player_back(self):
        start = CROWD_REACH - BEFORE_CROWD
        self.place_player(start)
        self.key(SDLK_RIGHT)

        self.advance_until(
            lambda: self.player.x < start
        )  # 처음 1.5초 동안은 인파가 닫혀 있다

        # 닿은 자리(한 걸음 안)에서 밀어내는 거리만큼 물러났다
        self.assertAlmostEqual(
            self.player.x,
            CROWD_REACH - config.CROWD_PUSH_DISTANCE,
            delta=config.WALK_SPEED * FRAME,
        )
        self.assertTrue(play_mode.camera.is_gliding)
        self.assertIsNot(state_of(self.player), Stunned)

    def test_a_runner_goes_straight_through_the_gap_while_it_is_open(self):
        self.advance(CROWD_CLOSED_TIME + 0.05)  # 틈이 막 열렸다
        self.place_player(CROWD_REACH - 5)
        self.run_right()
        positions = [self.player.x]

        while self.player.x <= CROWD_FAR_REACH:
            self.assertLess(
                len(positions), CROSSING_LIMIT_FRAMES, "틈을 지나는 데 너무 오래 걸린다"
            )
            self.advance()
            positions.append(self.player.x)
            self.assertIsNot(state_of(self.player), Stunned)

        self.assertEqual(positions, sorted(positions))  # 한 번도 뒤로 밀리지 않았다
        self.assertEqual(self.player.fall_remaining, 0.0)


class BoundingBoxKeyTest(CollisionTestCase):
    """B 키: 충돌 상자 표시를 켜고 끈다 (개발 중에 상자와 그림이 맞는지 보는 용도)."""

    def setUp(self):
        super().setUp()
        self.patch(play_mode, "clear_canvas")
        self.update_canvas = self.patch(play_mode, "update_canvas")
        self.render = self.patch(game_world, "render")
        self.outline_box = self.patch(gfx, "outline_box")

    def patch(self, target, name):
        patcher = mock.patch.object(target, name)
        patched = patcher.start()
        self.addCleanup(patcher.stop)
        return patched

    def boxes_drawn(self):
        """한 프레임을 그려 보고, 그려진 상자들의 인자 묶음 목록을 돌려준다."""
        self.outline_box.reset_mock()
        play_mode.draw()
        return [call.args for call in self.outline_box.call_args_list]

    @staticmethod
    def expected_boxes():
        """월드에서 충돌 상자를 가진 오브젝트마다, 화면 좌표로 바꾼 상자."""
        camera = play_mode.camera
        boxes = set()
        for each in game_world.all_objects():
            box = each.get_bb()
            if box is None:
                continue
            left, bottom, right, top = box
            boxes.add(
                (
                    camera.to_screen_x(left),
                    bottom,
                    camera.to_screen_x(right),
                    top,
                    config.DEBUG_BB_COLOR,
                )
            )
        return boxes

    def test_no_boxes_are_drawn_until_b_is_pressed(self):
        self.assertEqual(self.boxes_drawn(), [])

    def test_b_shows_one_box_for_the_player_and_each_obstacle(self):
        self.key(SDLK_b)

        drawn = self.boxes_drawn()

        self.assertEqual(len(drawn), BOX_COUNT)
        self.assertEqual(set(drawn), self.expected_boxes())

    def test_b_again_hides_them(self):
        self.key(SDLK_b)
        self.key(SDLK_b)

        self.assertEqual(self.boxes_drawn(), [])

    def test_releasing_b_changes_nothing(self):
        self.key(SDLK_b, SDL_KEYUP)
        self.assertEqual(self.boxes_drawn(), [])

        self.key(SDLK_b)
        self.key(SDLK_b, SDL_KEYUP)
        self.assertEqual(len(self.boxes_drawn()), BOX_COUNT)

    def test_entering_the_mode_again_hides_the_boxes(self):
        self.key(SDLK_b)

        play_mode.init()

        self.assertEqual(self.boxes_drawn(), [])

    def test_an_obstacle_that_already_hit_has_no_box_to_show(self):
        self.key(SDLK_b)
        tourist = game_world.world[game_world.LAYER_OBSTACLE][0]
        tourist.handle_collision(PLAYER_OBSTACLE, self.player)

        self.assertEqual(len(self.boxes_drawn()), BOX_COUNT - 1)

    def test_the_boxes_are_drawn_over_the_world_just_before_the_frame_is_shown(self):
        order = []
        self.render.side_effect = lambda: order.append("render")
        self.outline_box.side_effect = lambda *args: order.append("box")
        self.update_canvas.side_effect = lambda: order.append("flip")
        self.key(SDLK_b)

        play_mode.draw()

        self.assertEqual(order[0], "render")
        self.assertEqual(order[-1], "flip")
        self.assertEqual(order[1:-1], ["box"] * BOX_COUNT)


if __name__ == "__main__":
    unittest.main()
