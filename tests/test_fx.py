"""이펙트: 잠깐 떴다가 사라지는 스프라이트 (별, 물음표, 느낌표, 전단지, 말풍선)."""

import unittest
from unittest import mock

import config
import fx
import game_framework
import game_world
import text
from camera import Camera
from tests.support import STAGE, SpriteBook, make_player

ANCHOR = (300.0, 200.0)


def fixed_anchor():
    return ANCHOR


class EffectTestCase(unittest.TestCase):
    def setUp(self):
        game_world.clear()
        self.addCleanup(game_world.clear)
        self.book = SpriteBook()

    @staticmethod
    def advance(effect, seconds):
        """게임 루프가 seconds초짜리 한 프레임을 보낸 것처럼 갱신한다."""
        with mock.patch.object(game_framework, "frame_time", seconds):
            effect.update()

    def draw_once(self, effect):
        """effect를 한 번 그리고 그 그리기 기록을 돌려준다."""
        self.book.draws.clear()
        effect.draw()
        return self.book.draws[-1]


class EffectTest(EffectTestCase):
    def make(self, name="fx_stars", lifetime=1.0, anchor=fixed_anchor, **options):
        return fx.Effect(name, lifetime, anchor, sprite_lookup=self.book, **options)

    def test_draws_the_sheet_with_its_bottom_centre_on_the_anchor(self):
        draw = self.draw_once(self.make("fx_question"))

        frame_h = self.book.manifest["fx_question"].frame_h
        self.assertEqual(draw.name, "fx_question")
        self.assertEqual(draw.x, ANCHOR[0])
        self.assertEqual(draw.y, ANCHOR[1] + frame_h / 2)

    def test_follows_the_anchor_each_time_it_is_drawn(self):
        position = [100.0, 150.0]
        effect = self.make(anchor=lambda: (position[0], position[1]))

        first = self.draw_once(effect)
        position[0] = 500.0
        second = self.draw_once(effect)

        self.assertEqual((first.x, second.x), (100.0, 500.0))

    def test_steps_through_the_frames_one_period_at_a_time_and_wraps(self):
        effect = self.make("fx_stars", lifetime=10, frame_period=0.25)  # 시트는 3칸

        seen = []
        for _ in range(4):
            seen.append(self.draw_once(effect).frame)
            self.advance(effect, 0.25)

        self.assertEqual(seen, [0, 1, 2, 0])

    def test_a_single_frame_sheet_stays_on_its_only_frame(self):
        effect = self.make("fx_question", lifetime=10, frame_period=0.25)

        self.advance(effect, 0.75)

        self.assertEqual(self.draw_once(effect).frame, 0)

    def test_the_default_frame_period_comes_from_the_config(self):
        effect = self.make("fx_stars", lifetime=10)

        self.advance(effect, config.FX_FRAME_PERIOD)

        self.assertEqual(self.draw_once(effect).frame, 1)

    def test_it_leaves_the_world_when_its_lifetime_is_over(self):
        effect = self.make(lifetime=1.0)
        game_world.add_object(effect, game_world.LAYER_FX)

        self.advance(effect, 0.5)
        self.assertIn(effect, game_world.world[game_world.LAYER_FX])
        self.advance(effect, 0.5)

        self.assertNotIn(effect, game_world.world[game_world.LAYER_FX])

    def test_an_effect_that_was_never_added_to_the_world_expires_quietly(self):
        effect = self.make(lifetime=0.1)

        self.advance(effect, 1.0)

        self.assertEqual(game_world.all_objects(), [])

    def test_it_has_no_collision_box(self):
        self.assertIsNone(self.make().get_bb())

    def test_draws_its_label_over_the_centre_of_the_sheet(self):
        effect = self.make("fx_speech", label="안녕")

        with mock.patch.object(text, "draw") as draw_text:
            effect.draw()

        frame_h = self.book.manifest["fx_speech"].frame_h
        offset_x, offset_y = config.FX_SPEECH_TEXT_OFFSET
        draw_text.assert_called_once_with(
            "안녕",
            ANCHOR[0] + offset_x,
            ANCHOR[1] + frame_h / 2 + offset_y,
            size=config.FX_SPEECH_TEXT_SIZE,
            color=config.FX_SPEECH_TEXT_COLOR,
            align="center",
        )

    def test_without_a_label_no_text_is_drawn(self):
        with mock.patch.object(text, "draw") as draw_text:
            self.make("fx_question").draw()

        draw_text.assert_not_called()


class SpawnTest(EffectTestCase):
    def setUp(self):
        super().setUp()
        self.camera = Camera(config.SCREEN_W, STAGE.length)
        self.player, _ = make_player(x=1000, camera=self.camera, book=self.book)
        self.camera.snap_to(self.player.x)

    def sheet_height(self, name):
        return self.book.manifest[name].frame_h

    def only_effect(self):
        [effect] = game_world.world[game_world.LAYER_FX]
        return effect

    def test_stars_hover_over_the_body_and_follow_the_player(self):
        fx.spawn_stars(self.player, self.camera, 1.0, self.book)
        effect = self.only_effect()

        first = self.draw_once(effect)
        self.player.x += 30
        self.player.height = 50
        second = self.draw_once(effect)

        lift = (
            config.GROUND_Y + config.FX_STARS_HEIGHT + self.sheet_height("fx_stars") / 2
        )
        self.assertEqual(first.name, "fx_stars")
        self.assertEqual((first.x, first.y), (self.camera.to_screen_x(1000), lift))
        self.assertEqual(
            (second.x, second.y), (self.camera.to_screen_x(1030), lift + 50)
        )

    def test_the_paper_sticks_to_the_body_and_follows_the_player(self):
        fx.spawn_paper(self.player, self.camera, 1.0, self.book)
        effect = self.only_effect()

        first = self.draw_once(effect)
        self.player.x += 30
        self.player.height = 50
        second = self.draw_once(effect)

        lift = (
            config.GROUND_Y + config.FX_PAPER_HEIGHT + self.sheet_height("fx_paper") / 2
        )
        self.assertEqual(first.name, "fx_paper")
        self.assertEqual((first.x, first.y), (self.camera.to_screen_x(1000), lift))
        self.assertEqual(
            (second.x, second.y), (self.camera.to_screen_x(1030), lift + 50)
        )

    def test_the_question_mark_floats_over_the_head_of_whoever_is_asking(self):
        asker = mock.Mock(x=1100.0)
        fx.spawn_question(asker, self.camera, 2.0, self.book)

        draw = self.draw_once(self.only_effect())

        head = config.GROUND_Y + config.NPC_HEAD_HEIGHT + config.FX_HEAD_GAP
        self.assertEqual(draw.name, "fx_question")
        self.assertEqual(draw.x, self.camera.to_screen_x(1100))
        self.assertEqual(draw.y, head + self.sheet_height("fx_question") / 2)

    def test_the_exclaim_sits_at_the_right_edge_of_the_screen_at_head_height(self):
        fx.spawn_exclaim(0.5, self.book)

        draw = self.draw_once(self.only_effect())

        head = config.GROUND_Y + config.NPC_HEAD_HEIGHT + config.FX_HEAD_GAP
        self.assertEqual(draw.name, "fx_exclaim")
        self.assertEqual(draw.x, config.SCREEN_W - config.FX_EXCLAIM_MARGIN)
        self.assertEqual(draw.y, head + self.sheet_height("fx_exclaim") / 2)

    def test_the_exclaim_stays_on_the_screen_edge_when_the_camera_moves(self):
        fx.spawn_exclaim(0.5, self.book)
        effect = self.only_effect()

        before = self.draw_once(effect)
        self.camera.snap_to(3000)
        after = self.draw_once(effect)

        self.assertEqual(before.x, after.x)

    def test_the_speech_bubble_carries_the_line_beside_the_speaker(self):
        speaker = mock.Mock(x=1100.0)
        fx.spawn_speech(speaker, self.camera, "안녕하세요", 1.5, self.book)
        effect = self.only_effect()

        with mock.patch.object(text, "draw") as draw_text:
            draw = self.draw_once(effect)

        head = config.GROUND_Y + config.NPC_HEAD_HEIGHT + config.FX_HEAD_GAP
        self.assertEqual(draw.name, "fx_speech")
        self.assertEqual(
            draw.x, self.camera.to_screen_x(1100) + config.FX_SPEECH_OFFSET_X
        )
        self.assertEqual(draw.y, head + self.sheet_height("fx_speech") / 2)
        self.assertEqual(draw_text.call_args.args[0], "안녕하세요")

    def test_every_spawn_goes_to_the_fx_layer_with_the_given_lifetime(self):
        speaker = mock.Mock(x=1100.0)
        spawned = [
            (fx.spawn_stars(self.player, self.camera, 1.1, self.book), 1.1),
            (fx.spawn_paper(self.player, self.camera, 1.2, self.book), 1.2),
            (fx.spawn_question(speaker, self.camera, 1.3, self.book), 1.3),
            (fx.spawn_exclaim(1.4, self.book), 1.4),
            (fx.spawn_speech(speaker, self.camera, "말", 1.5, self.book), 1.5),
        ]

        for effect, lifetime in spawned:
            with self.subTest(sheet=effect.sprite_name):
                self.assertIn(effect, game_world.world[game_world.LAYER_FX])
                self.assertEqual(effect.lifetime, lifetime)


if __name__ == "__main__":
    unittest.main()
