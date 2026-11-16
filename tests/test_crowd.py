"""인파: 뚫고 지날 수 없는 사람 벽. 닿으면 뒤로 밀려나고, 2.5초마다 1초 동안 틈이 열린다."""

import unittest
from unittest import mock

from pico2d import SDLK_LSHIFT, SDLK_RIGHT

import config
import game_world
import stage_data
from obstacle import PLAYER_OBSTACLE
from player import Stunned
from tests.obstacle_support import ObstacleTestCase
from tests.support import press, run_for, state_of

CROWD_X = 2000.0
CLOSED_TIME = (
    config.CROWD_GAP_PERIOD - config.CROWD_GAP_OPEN_TIME
)  # 한 주기 중 틈이 닫혀 있는 시간
OPEN_MIDDLE = CLOSED_TIME + config.CROWD_GAP_OPEN_TIME / 2  # 틈이 완전히 벌어져 있는 때
MARGIN = 0.05  # 경계에서 3프레임쯤 떨어진 시각을 고르기 위한 여유(초)


def half_width(count):
    """count명이 나란히 선 인파의 한가운데에서 가장자리까지."""
    return (count - 1) / 2 * config.CROWD_MEMBER_SPACING + config.NPC_BB_HALF_W


class CrowdTestCase(ObstacleTestCase):
    def setUp(self):
        super().setUp()
        self.camera.snap_to(CROWD_X)  # 인파가 화면 안에 보이게 한다

    def make_crowd(self, count):
        return self.make(stage_data.CROWD, CROWD_X, count)

    def members_after(self, count, seconds):
        """새 인파를 seconds초 진행시킨 뒤, 멤버들의 (화면 x, y)를 왼쪽부터 돌려준다."""
        crowd = self.make_crowd(count)
        self.step_for(crowd, seconds)
        self.book.draws.clear()
        crowd.draw()
        return [(draw.x, draw.y) for draw in self.book.draws]


class BoxTest(CrowdTestCase):
    def test_the_box_covers_every_member_standing_side_by_side(self):
        for count in (3, 4):
            with self.subTest(count=count):
                crowd = self.make_crowd(count)

                self.assertEqual(
                    crowd.get_bb(),
                    (
                        CROWD_X - half_width(count),
                        config.GROUND_Y,
                        CROWD_X + half_width(count),
                        config.GROUND_Y + config.CROWD_BB_HEIGHT,
                    ),
                )

    def test_even_the_highest_jump_cannot_clear_it(self):
        crowd = self.make_crowd(3)
        self.player.x = CROWD_X
        self.player.height = config.JUMP_V0**2 / (2 * config.GRAVITY)  # 점프의 정점

        self.assertTrue(game_world.collide(self.player, crowd))

    def test_it_never_leaves_the_world(self):
        crowd = self.make_crowd(3)

        self.step_for(crowd, 20.0)

        self.assertTrue(self.in_world(crowd))


class GapCycleTest(CrowdTestCase):
    def setUp(self):
        super().setUp()
        self.crowd = self.make_crowd(4)
        self.elapsed = 0.0

    def is_solid_at(self, seconds):
        """만든 지 seconds초가 될 때까지 진행하고, 그때 충돌 상자가 켜져 있는지 돌려준다."""
        self.step_for(self.crowd, seconds - self.elapsed)
        self.elapsed = seconds
        return self.crowd.get_bb() is not None

    def test_the_box_is_solid_then_off_for_the_gap_then_solid_again_period_after_period(
        self,
    ):
        period = config.CROWD_GAP_PERIOD
        timeline = [
            (0.0, True),
            (CLOSED_TIME - MARGIN, True),
            (CLOSED_TIME + MARGIN, False),
            (OPEN_MIDDLE, False),
            (period - MARGIN, False),
            (period + MARGIN, True),
            (period + CLOSED_TIME - MARGIN, True),
            (period + CLOSED_TIME + MARGIN, False),
            (2 * period - MARGIN, False),
            (2 * period + MARGIN, True),
        ]

        seen = [(seconds, self.is_solid_at(seconds)) for seconds, _ in timeline]

        self.assertEqual(seen, timeline)


class DrawTest(CrowdTestCase):
    def draws_of(self, crowd):
        self.book.draws.clear()
        crowd.draw()
        return list(self.book.draws)

    def test_the_members_stand_side_by_side_on_the_ground(self):
        crowd = self.make_crowd(4)

        draws = self.draws_of(crowd)

        spacing = config.CROWD_MEMBER_SPACING
        expected_x = [
            self.camera.to_screen_x(CROWD_X + (index - 1.5) * spacing)
            for index in range(4)
        ]
        self.assertEqual([draw.x for draw in draws], expected_x)
        for draw in draws:
            ground_centre = self.book(draw.name).ground_center_y()
            self.assertEqual(
                (draw.y, draw.flip, draw.alpha), (ground_centre, False, 1.0)
            )

    def test_the_members_wear_the_three_commuter_sheets_in_turn(self):
        names = [draw.name for draw in self.draws_of(self.make_crowd(4))]

        self.assertEqual(
            names,
            ["npc_commuter1", "npc_commuter2", "npc_commuter3", "npc_commuter1"],
        )

    def test_neighbours_are_out_of_step_so_the_crowd_does_not_pulse_together(self):
        frames = {draw.frame for draw in self.draws_of(self.make_crowd(3))}

        self.assertGreater(len(frames), 1)

    def test_the_members_move_through_their_frames_over_time(self):
        crowd = self.make_crowd(3)
        before = [draw.frame for draw in self.draws_of(crowd)]

        self.step_for(crowd, 0.6)  # 시트 속도 2fps: 0.5초에 한 칸
        after = [draw.frame for draw in self.draws_of(crowd)]

        self.assertNotEqual(before, after)

    def test_a_crowd_far_off_screen_is_not_drawn(self):
        crowd = self.make_crowd(4)
        crowd.x = self.camera.x + config.SCREEN_W + 500

        self.assertEqual(self.draws_of(crowd), [])


class GapChoreographyTest(CrowdTestCase):
    """틈이 열리면 가운데 사람들이 위아래로 벌어지며 물러선다. 맨 끝 두 사람은 제자리다."""

    def test_the_outermost_members_stay_where_they_are(self):
        for count in (3, 4):
            with self.subTest(count=count):
                closed = self.members_after(count, 0.0)

                opened = self.members_after(count, OPEN_MIDDLE)

                self.assertEqual((opened[0], opened[-1]), (closed[0], closed[-1]))

    def test_the_inner_members_of_four_part_ways_one_up_and_one_down_stepping_outward(
        self,
    ):
        _, (left_x, left_y), (right_x, right_y), _ = self.members_after(4, 0.0)

        _, left, right, _ = self.members_after(4, OPEN_MIDDLE)

        shift_x, shift_y = config.CROWD_GAP_SHIFT_X, config.CROWD_GAP_SHIFT_Y
        self.assertAlmostEqual(left[0] - left_x, -shift_x, delta=0.01)
        self.assertAlmostEqual(left[1] - left_y, shift_y, delta=0.01)
        self.assertAlmostEqual(right[0] - right_x, shift_x, delta=0.01)
        self.assertAlmostEqual(right[1] - right_y, -shift_y, delta=0.01)

    def test_the_middle_member_of_three_only_steps_up_without_moving_sideways(self):
        _, (middle_x, middle_y), _ = self.members_after(3, 0.0)

        _, middle, _ = self.members_after(3, OPEN_MIDDLE)

        self.assertEqual(middle[0], middle_x)
        self.assertAlmostEqual(
            middle[1] - middle_y, config.CROWD_GAP_SHIFT_Y, delta=0.01
        )

    def test_everyone_is_back_in_line_while_the_gap_is_closed(self):
        closed = self.members_after(4, 0.0)
        period = config.CROWD_GAP_PERIOD

        for seconds in (
            CLOSED_TIME - MARGIN,
            period + MARGIN,
            period + CLOSED_TIME - MARGIN,
        ):
            with self.subTest(seconds=seconds):
                self.assertEqual(self.members_after(4, seconds)[1:3], closed[1:3])

    def test_the_parting_eases_in_as_the_gap_opens(self):
        rest_y = self.members_after(4, 0.0)[1][1]

        def lift(seconds):
            return self.members_after(4, seconds)[1][1] - rest_y

        early = lift(CLOSED_TIME + MARGIN)
        later = lift(CLOSED_TIME + 3 * MARGIN)
        full = lift(CLOSED_TIME + config.CROWD_GAP_EASE + MARGIN)

        self.assertTrue(0 < early < later < full)
        self.assertLess(early, config.CROWD_GAP_SHIFT_Y / 4)
        self.assertAlmostEqual(full, config.CROWD_GAP_SHIFT_Y, delta=0.01)

    def test_the_parting_eases_out_as_the_gap_closes(self):
        rest_y = self.members_after(4, 0.0)[1][1]

        def lift(seconds):
            return self.members_after(4, seconds)[1][1] - rest_y

        period = config.CROWD_GAP_PERIOD
        full = lift(period - config.CROWD_GAP_EASE - MARGIN)
        later = lift(period - 3 * MARGIN)
        last = lift(period - MARGIN)

        self.assertTrue(full > later > last > 0)
        self.assertLess(last, config.CROWD_GAP_SHIFT_Y / 4)


class PushTest(CrowdTestCase):
    def setUp(self):
        super().setUp()
        self.crowd = self.make_crowd(3)

    def push_from(self, offset):
        """플레이어를 인파 한가운데에서 offset만큼 떨어진 곳에 세워 부딪히게 하고, 밀려난 거리를 돌려준다."""
        start = CROWD_X + offset
        self.player.x = start
        self.touch(self.crowd)
        return self.player.x - start

    def test_a_player_coming_from_the_left_is_pushed_back_to_the_left(self):
        self.assertEqual(self.push_from(-50), -config.CROWD_PUSH_DISTANCE)

    def test_a_player_coming_from_the_right_is_pushed_back_to_the_right(self):
        self.assertEqual(self.push_from(50), config.CROWD_PUSH_DISTANCE)

    def test_a_player_dead_centre_is_pushed_to_the_left(self):
        self.assertEqual(self.push_from(0), -config.CROWD_PUSH_DISTANCE)

    def test_the_camera_glides_to_the_pushed_player_instead_of_jumping(self):
        self.push_from(-50)

        self.assertTrue(self.camera.is_gliding)

    def test_a_walking_push_does_not_stop_or_knock_down_the_player(self):
        press(self.player, SDLK_RIGHT)
        run_for(self.player, 0.1)

        self.push_from(-50)

        self.assertIsNot(state_of(self.player), Stunned)
        self.assertEqual(self.player.fall_remaining, 0.0)
        self.assertEqual(self.player.gauge.value, 0.0)

    def test_the_crowd_pushes_again_every_time_it_is_touched(self):
        first = self.push_from(-50)
        self.player.x = CROWD_X - 50  # 다시 걸어와 닿았다
        second = self.push_from(-50)

        self.assertEqual((first, second), (-config.CROWD_PUSH_DISTANCE,) * 2)
        self.assertIsNotNone(self.crowd.get_bb())

    def test_running_into_the_crowd_pushes_the_player_back_and_knocks_them_down(self):
        press(self.player, SDLK_RIGHT)
        press(self.player, SDLK_LSHIFT)
        run_for(self.player, 0.1)

        pushed = self.push_from(-50)

        self.assertEqual(pushed, -config.CROWD_PUSH_DISTANCE)
        self.assertIs(state_of(self.player), Stunned)
        self.assertEqual(self.player.gauge.value, config.FALL_GAUGE_ADD)
        self.assertEqual(len(self.effects("fx_stars")), 1)

    def test_a_crowd_that_was_touched_stays_in_the_world(self):
        self.push_from(-50)

        self.assertTrue(self.in_world(self.crowd))

    def test_a_collision_from_another_group_is_ignored(self):
        self.player.x = CROWD_X - 50

        self.crowd.handle_collision("player:item", self.player)

        self.assertEqual(self.player.x, CROWD_X - 50)

    def test_a_collision_with_anything_but_the_player_is_ignored(self):
        self.player.x = CROWD_X - 50

        self.crowd.handle_collision(PLAYER_OBSTACLE, mock.Mock())

        self.assertEqual(self.player.x, CROWD_X - 50)


if __name__ == "__main__":
    unittest.main()
