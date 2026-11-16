"""홀로 서 있는 장애물(관광객·전단지 알바·상사): 충돌 상자, 닿았을 때의 효과, 퇴장, 그리기."""

import unittest
from unittest import mock

from pico2d import SDLK_LSHIFT, SDLK_RIGHT, SDLK_SPACE

import config
import game_framework
import game_world
import stage_data
from obstacle import PLAYER_OBSTACLE
from player import Stunned
from tests.obstacle_support import ObstacleTestCase
from tests.support import press, run_for, state_of

NPC_KINDS = (stage_data.TOURIST, stage_data.FLYER, stage_data.BOSS)
SHEET_BY_KIND = {
    stage_data.TOURIST: "npc_tourist",
    stage_data.FLYER: "npc_flyer",
    stage_data.BOSS: "npc_boss",
}
NPC_X = 1000.0
BOSS_X = 3300.0
FRAME_SLACK = (
    config.BOSS_WALK_SPEED / 60 * 3
)  # 프레임 단위 진행에서 생기는 몇 프레임 치 오차


def start_running(player):
    """→ 와 SHIFT를 누르고 잠깐 달려서 달리는 상태로 만든다."""
    press(player, SDLK_RIGHT)
    press(player, SDLK_LSHIFT)
    run_for(player, 0.1)


class NpcBoxTest(ObstacleTestCase):
    def test_every_npc_has_a_standing_box_around_its_feet(self):
        for kind in NPC_KINDS:
            with self.subTest(kind=kind):
                npc = self.make(kind, NPC_X)

                self.assertEqual(
                    npc.get_bb(),
                    (
                        NPC_X - config.NPC_BB_HALF_W,
                        config.GROUND_Y,
                        NPC_X + config.NPC_BB_HALF_W,
                        config.GROUND_Y + config.NPC_BB_HEIGHT,
                    ),
                )

    def test_a_player_on_the_ground_overlaps_the_box_but_one_high_in_the_air_does_not(
        self,
    ):
        tourist = self.make(stage_data.TOURIST, NPC_X)
        self.player.x = NPC_X

        self.player.height = 0.0
        on_the_ground = game_world.collide(self.player, tourist)
        self.player.height = config.NPC_BB_HEIGHT + 10
        over_the_head = game_world.collide(self.player, tourist)

        self.assertTrue(on_the_ground)
        self.assertFalse(over_the_head)

    def test_a_player_beside_the_box_does_not_overlap(self):
        tourist = self.make(stage_data.TOURIST, NPC_X)
        reach = config.NPC_BB_HALF_W + config.PLAYER_BB_HALF_W

        self.player.x = NPC_X - reach - 1

        self.assertFalse(game_world.collide(self.player, tourist))


class HitRulesTest(ObstacleTestCase):
    """모든 홀로 선 장애물에 같은 규칙: 관광객으로 확인한다."""

    def setUp(self):
        super().setUp()
        self.tourist = self.make(stage_data.TOURIST, NPC_X)

    def test_a_collision_from_another_group_is_ignored(self):
        self.tourist.handle_collision("player:item", self.player)

        self.assertIsNot(state_of(self.player), Stunned)
        self.assertTrue(self.tourist.active)

    def test_a_collision_with_anything_but_the_player_is_ignored(self):
        self.tourist.handle_collision(PLAYER_OBSTACLE, mock.Mock())

        self.assertIsNot(state_of(self.player), Stunned)
        self.assertTrue(self.tourist.active)

    def test_an_obstacle_hits_only_once(self):
        self.touch(self.tourist)
        run_for(self.player, 0.5)
        left_after_first = self.player.stun_remaining

        self.touch(self.tourist)

        self.assertAlmostEqual(self.player.stun_remaining, left_after_first, 6)
        self.assertEqual(len(self.effects("fx_question")), 1)

    def test_the_box_is_switched_off_after_the_hit(self):
        self.touch(self.tourist)

        self.assertFalse(self.tourist.active)
        self.assertIsNone(self.tourist.get_bb())

    def test_a_walking_hit_does_not_knock_the_player_down(self):
        press(self.player, SDLK_RIGHT)
        run_for(self.player, 0.1)

        self.touch(self.tourist)

        self.assertEqual(self.player.fall_remaining, 0.0)
        self.assertEqual(self.player.gauge.value, 0.0)
        self.assertEqual(self.effects("fx_stars"), [])

    def test_a_running_hit_adds_a_fall_on_top_of_the_effect(self):
        start_running(self.player)

        self.touch(self.tourist)

        self.assertEqual(self.player.gauge.value, config.FALL_GAUGE_ADD)
        [stars] = self.effects("fx_stars")
        self.assertEqual(stars.lifetime, config.FALL_STOP_TIME)
        self.assertGreater(self.player.fall_remaining, 0.0)

    def test_the_longer_of_the_two_stop_times_wins_when_a_run_ends_in_a_fall(self):
        start_running(self.player)

        self.touch(self.tourist)

        self.assertEqual(
            self.player.stun_remaining,
            max(config.TOURIST_STOP_TIME, config.FALL_STOP_TIME),
        )

    def test_a_hit_in_the_middle_of_a_running_jump_counts_as_running(self):
        press(self.player, SDLK_RIGHT)
        press(self.player, SDLK_LSHIFT)
        press(self.player, SDLK_SPACE)
        run_for(self.player, 0.05)
        self.assertGreater(self.player.height, 0)

        self.touch(self.tourist)

        self.assertIs(state_of(self.player), Stunned)
        self.assertGreater(self.player.fall_remaining, 0.0)


class TouristTest(ObstacleTestCase):
    def setUp(self):
        super().setUp()
        self.tourist = self.make(stage_data.TOURIST, NPC_X)

    def test_stops_the_player_for_the_stop_time(self):
        self.touch(self.tourist)

        self.assertIs(state_of(self.player), Stunned)
        self.assertEqual(self.player.stun_remaining, config.TOURIST_STOP_TIME)

    def test_asks_the_way_with_a_question_mark_for_as_long_as_the_stop(self):
        self.touch(self.tourist)

        [question] = self.effects("fx_question")
        self.assertEqual(question.lifetime, config.TOURIST_STOP_TIME)

    def test_stays_while_the_player_is_stopped_then_walks_off_to_the_right(self):
        self.touch(self.tourist)

        self.step_for(self.tourist, config.TOURIST_STOP_TIME - 0.3)
        staying = (self.tourist.x, self.draw_of(self.tourist).flip)
        self.step_for(self.tourist, 0.3 + 0.5)

        self.assertEqual(staying, (NPC_X, False))
        self.assertGreater(self.tourist.x, NPC_X)
        self.assertTrue(self.draw_of(self.tourist).flip)  # 그림은 왼쪽을 보고 있다

    def test_fades_out_while_walking_off_and_is_gone_in_the_end(self):
        self.touch(self.tourist)

        self.step_for(self.tourist, config.TOURIST_STOP_TIME + 0.3)
        fading = self.draw_of(self.tourist).alpha
        self.step_for(self.tourist, config.NPC_FADE_TIME + 0.5)

        self.assertTrue(0.0 < fading < 1.0)
        self.assertFalse(self.in_world(self.tourist))


class FlyerTest(ObstacleTestCase):
    def setUp(self):
        super().setUp()
        self.flyer = self.make(stage_data.FLYER, NPC_X)

    def test_slows_the_player_down_without_stopping_them(self):
        self.touch(self.flyer)

        self.assertIsNot(state_of(self.player), Stunned)
        self.assertEqual(self.player.slow_remaining, config.FLYER_SLOW_TIME)
        self.assertEqual(self.player.speed_multiplier(), config.FLYER_SPEED_MULT)

    def test_sticks_a_leaflet_on_the_player_for_as_long_as_the_slow(self):
        self.touch(self.flyer)

        [paper] = self.effects("fx_paper")
        self.assertEqual(paper.lifetime, config.FLYER_SLOW_TIME)

    def test_walks_off_to_the_right_at_once(self):
        self.touch(self.flyer)

        self.step_for(self.flyer, 0.5)

        self.assertGreater(self.flyer.x, NPC_X)
        self.assertTrue(self.draw_of(self.flyer).flip)

    def test_a_running_hit_both_slows_and_knocks_the_player_down(self):
        start_running(self.player)

        self.touch(self.flyer)

        self.assertIs(state_of(self.player), Stunned)
        self.assertEqual(self.player.speed_multiplier(), config.FLYER_SPEED_MULT)
        self.assertEqual(self.player.gauge.value, config.FALL_GAUGE_ADD)


class BossTest(ObstacleTestCase):
    def setUp(self):
        super().setUp()
        self.camera.snap_to(
            BOSS_X
        )  # 상사가 화면 안에 보이게 한다 (플레이어는 따로 멀리 둔다)
        self.boss = self.make(stage_data.BOSS, BOSS_X)
        self.just_outside = BOSS_X - config.BOSS_WARN_DISTANCE - 1
        self.just_inside = BOSS_X - config.BOSS_WARN_DISTANCE + 1

    def trigger_warning(self):
        self.player.x = self.just_inside
        self.boss.step(1 / 60)

    def test_waits_on_its_first_frame_while_the_player_is_far_away(self):
        self.step_for(self.boss, 3.0)

        draw = self.draw_of(self.boss)
        self.assertEqual((self.boss.x, draw.frame), (BOSS_X, 0))
        self.assertEqual(self.effects("fx_exclaim"), [])

    def test_no_warning_while_the_player_is_just_outside_the_warn_distance(self):
        self.player.x = self.just_outside

        self.step_for(self.boss, 0.5)

        self.assertEqual(self.effects("fx_exclaim"), [])

    def test_warns_with_an_exclaim_mark_once_the_player_is_within_the_distance(self):
        self.trigger_warning()

        [exclaim] = self.effects("fx_exclaim")
        self.assertEqual(exclaim.lifetime, config.BOSS_EXCLAIM_TIME)

    def test_warns_only_once(self):
        self.trigger_warning()

        self.step_for(self.boss, 2.0)

        self.assertEqual(len(self.effects("fx_exclaim")), 1)

    def test_stands_still_while_the_exclaim_blinks(self):
        self.trigger_warning()

        self.step_for(self.boss, config.BOSS_EXCLAIM_TIME / 2)

        self.assertEqual(self.boss.x, BOSS_X)
        self.assertEqual(self.draw_of(self.boss).frame, 0)

    def test_then_walks_towards_the_player_with_the_raised_hand(self):
        self.trigger_warning()

        self.step_for(self.boss, config.BOSS_EXCLAIM_TIME + 1.0)

        walked = BOSS_X - self.boss.x
        self.assertAlmostEqual(walked, config.BOSS_WALK_SPEED * 1.0, delta=FRAME_SLACK)
        self.assertEqual(self.draw_of(self.boss).frame, 1)

    def test_is_removed_once_it_has_walked_off_the_left_edge_of_the_screen(self):
        self.trigger_warning()
        self.camera.snap_to(self.player.x)  # 화면 왼쪽 끝은 플레이어보다 426px 뒤

        self.step_for(self.boss, 3.0)
        still_there = self.in_world(self.boss)
        self.step_for(self.boss, 5.0)

        self.assertTrue(still_there)
        self.assertFalse(self.in_world(self.boss))

    def test_talking_stops_the_player_and_raises_the_gauge(self):
        self.touch(self.boss)

        self.assertIs(state_of(self.player), Stunned)
        self.assertEqual(self.player.stun_remaining, config.BOSS_STOP_TIME)
        self.assertEqual(self.player.gauge.value, config.BOSS_GAUGE_ADD)

    def test_says_its_line_in_a_speech_bubble_for_as_long_as_the_talk(self):
        self.touch(self.boss)

        [bubble] = self.effects("fx_speech")
        self.assertEqual(bubble.label, config.BOSS_SPEECH_TEXT)
        self.assertEqual(bubble.lifetime, config.BOSS_STOP_TIME)

    def test_stands_still_through_the_talk_then_leaves_to_the_right(self):
        self.touch(self.boss)

        self.step_for(self.boss, config.BOSS_STOP_TIME - 0.3)
        during_talk = self.boss.x
        self.step_for(self.boss, 0.3 + 0.5)

        self.assertEqual(during_talk, BOSS_X)
        self.assertGreater(self.boss.x, BOSS_X)
        self.assertTrue(self.draw_of(self.boss).flip)

    def test_a_boss_that_is_walking_stops_where_it_meets_the_player(self):
        self.trigger_warning()
        self.step_for(self.boss, config.BOSS_EXCLAIM_TIME + 0.5)
        met_at = self.boss.x

        self.touch(self.boss)
        self.step_for(self.boss, config.BOSS_STOP_TIME / 2)

        self.assertLess(met_at, BOSS_X)
        self.assertEqual(self.boss.x, met_at)

    def test_a_running_hit_adds_a_fall_and_the_longer_stop_wins(self):
        start_running(self.player)

        self.touch(self.boss)

        self.assertEqual(
            self.player.gauge.value, config.BOSS_GAUGE_ADD + config.FALL_GAUGE_ADD
        )
        self.assertEqual(
            self.player.stun_remaining,
            max(config.BOSS_STOP_TIME, config.FALL_STOP_TIME),
        )


class NpcDrawTest(ObstacleTestCase):
    def setUp(self):
        super().setUp()
        self.camera.snap_to(NPC_X)
        self.tourist = self.make(stage_data.TOURIST, NPC_X)

    def test_every_npc_draws_its_own_sheet_with_the_feet_on_the_ground(self):
        for kind, sheet in SHEET_BY_KIND.items():
            with self.subTest(kind=kind):
                npc = self.make(kind, NPC_X)

                draw = self.draw_of(npc)

                ground_centre = self.book(sheet).ground_center_y()
                self.assertEqual(draw.name, sheet)
                self.assertEqual(draw.x, self.camera.to_screen_x(NPC_X))
                self.assertEqual(draw.y, ground_centre)
                self.assertEqual((draw.flip, draw.alpha), (False, 1.0))

    def test_an_npc_moves_through_its_two_frames_while_standing(self):
        first = self.draw_of(self.tourist).frame
        self.step_for(self.tourist, 0.6)  # 시트 속도 2fps: 0.5초에 한 칸

        second = self.draw_of(self.tourist).frame

        self.assertEqual((first, second), (0, 1))

    def test_an_npc_partly_on_screen_is_drawn(self):
        self.tourist.x = self.camera.x + config.SCREEN_W + 50  # 중심은 밖, 몸은 걸친다

        self.book.draws.clear()
        self.tourist.draw()

        self.assertEqual(len(self.book.draws), 1)

    def test_an_npc_off_screen_is_not_drawn(self):
        self.tourist.x = self.camera.x + config.SCREEN_W + 150

        self.book.draws.clear()
        self.tourist.draw()

        self.assertEqual(self.book.draws, [])

    def test_the_frame_time_drives_update(self):
        self.tourist.leave(0.0)

        with mock.patch.object(game_framework, "frame_time", 0.5):
            self.tourist.update()

        self.assertAlmostEqual(self.tourist.x, NPC_X + config.NPC_EXIT_SPEED * 0.5, 6)


class NpcLeaveTest(ObstacleTestCase):
    def setUp(self):
        super().setUp()
        self.tourist = self.make(stage_data.TOURIST, NPC_X)

    def test_waits_for_the_delay_then_walks_right_at_the_exit_speed(self):
        self.tourist.leave(1.0)

        self.step_for(self.tourist, 0.9)
        waiting = self.tourist.x
        self.step_for(self.tourist, 0.1 + 0.4)

        self.assertEqual(waiting, NPC_X)
        self.assertAlmostEqual(
            self.tourist.x - NPC_X, config.NPC_EXIT_SPEED * 0.4, delta=2.0
        )

    def test_stays_fully_visible_until_it_starts_walking(self):
        self.tourist.leave(1.0)

        self.step_for(self.tourist, 0.9)

        self.assertEqual(self.tourist.alpha, 1.0)

    def test_becomes_more_transparent_while_walking_and_is_removed_when_invisible(self):
        self.tourist.leave(0.0)

        self.step_for(self.tourist, config.NPC_FADE_TIME / 2)
        half_way = self.tourist.alpha
        self.step_for(self.tourist, config.NPC_FADE_TIME / 2 + 0.2)

        self.assertAlmostEqual(half_way, 0.5, delta=0.05)
        self.assertFalse(self.in_world(self.tourist))

    def test_a_removed_npc_leaves_the_collision_lists_too(self):
        game_world.add_collision_pair(PLAYER_OBSTACLE, self.player, self.tourist)
        self.tourist.leave(0.0)

        self.step_for(self.tourist, config.NPC_FADE_TIME + 0.2)

        _, obstacles = game_world.collision_pairs[PLAYER_OBSTACLE]
        self.assertEqual(obstacles, [])


if __name__ == "__main__":
    unittest.main()
