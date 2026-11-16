import json
import os
import tempfile
import unittest
from unittest import mock

import config
import resource


class FakeImage:
    """pico2d.Image 대신 그리기 호출을 기록한다."""

    def __init__(self):
        self.calls = []

    def clip_draw(self, *args):
        self.calls.append(("clip_draw",) + args)

    def clip_composite_draw(self, *args):
        self.calls.append(("clip_composite_draw",) + args)

    def clip_draw_to_origin(self, *args):
        self.calls.append(("clip_draw_to_origin",) + args)

    def opacify(self, value):
        self.calls.append(("opacify", value))


def make_sprite(frames=4, frame_w=144, frame_h=144, fps=8.0):
    image = FakeImage()
    info = resource.SpriteInfo(
        "test", "/nowhere/test.png", frame_w, frame_h, frames, fps
    )
    return resource.Sprite(info, loader=lambda path: image), image


class LoadManifestTest(unittest.TestCase):
    def _load(self, data):
        with tempfile.TemporaryDirectory() as root:
            path = os.path.join(root, "manifest.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f)
            return resource.load_manifest(path, root), root

    def test_every_entry_becomes_a_sprite_info(self):
        manifest, _ = self._load(
            {
                "a": {
                    "file": "resource/image/a.png",
                    "frame_w": 10,
                    "frame_h": 20,
                    "frames": 3,
                    "fps": 6,
                },
                "b": {
                    "file": "resource/image/b.png",
                    "frame_w": 1,
                    "frame_h": 2,
                    "frames": 1,
                },
            }
        )
        self.assertEqual(set(manifest), {"a", "b"})
        self.assertEqual(manifest["a"].frame_w, 10)
        self.assertEqual(manifest["a"].frame_h, 20)
        self.assertEqual(manifest["a"].frames, 3)
        self.assertEqual(manifest["a"].fps, 6)

    def test_paths_are_resolved_against_the_asset_root(self):
        manifest, root = self._load(
            {
                "a": {
                    "file": "resource/image/a.png",
                    "frame_w": 1,
                    "frame_h": 1,
                    "frames": 1,
                }
            }
        )
        self.assertEqual(
            manifest["a"].path, os.path.join(root, "resource", "image", "a.png")
        )

    def test_fps_is_none_when_the_manifest_omits_it(self):
        manifest, _ = self._load(
            {
                "a": {
                    "file": "resource/image/a.png",
                    "frame_w": 1,
                    "frame_h": 1,
                    "frames": 2,
                }
            }
        )
        self.assertIsNone(manifest["a"].fps)

    def test_entry_missing_a_field_raises_an_error_naming_entry_and_field(self):
        with self.assertRaises(ValueError) as ctx:
            self._load(
                {"broken": {"file": "resource/image/a.png", "frame_w": 1, "frames": 1}}
            )
        message = str(ctx.exception)
        self.assertIn("broken", message)
        self.assertIn("frame_h", message)

    def test_entry_that_is_not_an_object_raises_an_error_naming_the_entry(self):
        with self.assertRaises(ValueError) as ctx:
            self._load({"oops": ["resource/image/a.png"]})
        self.assertIn("oops", str(ctx.exception))

    def test_malformed_json_raises_a_readable_error_naming_the_file(self):
        with tempfile.TemporaryDirectory() as root:
            path = os.path.join(root, "manifest.json")
            with open(path, "w", encoding="utf-8") as f:
                f.write("{ not json")
            with self.assertRaises(ValueError) as ctx:
                resource.load_manifest(path, root)
        self.assertIn("manifest.json", str(ctx.exception))

    def test_missing_manifest_raises_a_readable_error(self):
        with (
            tempfile.TemporaryDirectory() as root,
            self.assertRaises(FileNotFoundError) as ctx,
        ):
            resource.load_manifest(os.path.join(root, "manifest.json"), root)
        self.assertIn("manifest.json", str(ctx.exception))


class RealManifestTest(unittest.TestCase):
    def test_every_referenced_image_exists(self):
        for name, info in resource.load_manifest().items():
            self.assertTrue(os.path.isfile(info.path), name)

    def test_player_has_every_mood_and_animation_sheet(self):
        manifest = resource.load_manifest()
        for mood in ("calm", "sweat", "strain", "limit"):
            for anim in ("idle", "walk", "run", "jump", "waddle", "fall"):
                self.assertIn(f"player_{mood}_{anim}", manifest)

    def test_get_sprite_reads_frame_data_from_the_manifest(self):
        walk = resource.get_sprite("player_calm_walk")
        self.assertEqual(
            (walk.frame_w, walk.frame_h, walk.frames, walk.fps), (144, 144, 4, 8)
        )

    def test_get_sprite_returns_the_cached_instance(self):
        self.assertIs(resource.get_sprite("bg_far"), resource.get_sprite("bg_far"))

    def test_unknown_sprite_raises_a_readable_key_error(self):
        with self.assertRaises(KeyError) as ctx:
            resource.get_sprite("no_such_sprite")
        self.assertIn("no_such_sprite", str(ctx.exception))


class SpriteDrawTest(unittest.TestCase):
    def test_draw_clips_the_requested_frame_from_the_single_row_sheet(self):
        sprite, image = make_sprite()
        sprite.draw(200, 189, frame=2)
        self.assertEqual(image.calls, [("clip_draw", 288, 0, 144, 144, 200, 189)])

    def test_flipped_draw_passes_an_explicit_size(self):
        sprite, image = make_sprite()
        sprite.draw(200, 189, frame=1, flip=True)
        self.assertEqual(
            image.calls,
            [("clip_composite_draw", 144, 0, 144, 144, 0, "h", 200, 189, 144, 144)],
        )

    def test_scaled_draw_passes_the_scaled_size(self):
        sprite, image = make_sprite()
        sprite.draw(200, 189, scale=2)
        self.assertEqual(
            image.calls, [("clip_draw", 0, 0, 144, 144, 200, 189, 288, 288)]
        )

    def test_flipped_scaled_draw_passes_the_scaled_size(self):
        sprite, image = make_sprite()
        sprite.draw(200, 189, flip=True, scale=2)
        self.assertEqual(
            image.calls,
            [("clip_composite_draw", 0, 0, 144, 144, 0, "h", 200, 189, 288, 288)],
        )

    def test_coordinates_are_snapped_to_whole_pixels(self):
        sprite, image = make_sprite()
        sprite.draw(200.6, 189.4)
        self.assertEqual(image.calls, [("clip_draw", 0, 0, 144, 144, 201, 189)])

    def test_fractional_frame_numbers_are_floored_and_wrapped(self):
        sprite, image = make_sprite(frames=4)
        sprite.draw(0, 0, frame=5.7)
        self.assertEqual(image.calls[0][1], 144)

    def test_partial_alpha_is_applied_around_the_draw_and_restored(self):
        sprite, image = make_sprite()
        sprite.draw(0, 0, alpha=0.5)
        self.assertEqual(
            [call[0] for call in image.calls], ["opacify", "clip_draw", "opacify"]
        )
        self.assertEqual(image.calls[0], ("opacify", 0.5))
        self.assertEqual(image.calls[2], ("opacify", 1.0))

    def test_full_alpha_never_touches_the_texture(self):
        sprite, image = make_sprite()
        sprite.draw(0, 0)
        self.assertEqual([call[0] for call in image.calls], ["clip_draw"])

    def test_draw_at_origin_clips_the_whole_frame_by_default(self):
        sprite, image = make_sprite(frames=1, frame_w=192, frame_h=120)
        sprite.draw_at_origin(-30, 0)
        self.assertEqual(image.calls, [("clip_draw_to_origin", 0, 0, 192, 120, -30, 0)])

    def test_draw_at_origin_can_clip_the_width(self):
        sprite, image = make_sprite(frames=1, frame_w=192, frame_h=120)
        sprite.draw_at_origin(400, 0, clip_w=16)
        self.assertEqual(image.calls, [("clip_draw_to_origin", 0, 0, 16, 120, 400, 0)])

    def test_image_is_loaded_lazily_and_only_once(self):
        loads = []
        image = FakeImage()

        def loader(path):
            loads.append(path)
            return image

        info = resource.SpriteInfo("t", "/nowhere/t.png", 10, 10, 1, None)
        sprite = resource.Sprite(info, loader=loader)
        self.assertEqual(loads, [])
        sprite.draw(0, 0)
        sprite.draw(0, 0)
        self.assertEqual(loads, ["/nowhere/t.png"])


class PreloadTest(unittest.TestCase):
    def test_load_reads_the_image_up_front_and_the_first_draw_does_not_load_again(self):
        loads = []
        image = FakeImage()

        def loader(path):
            loads.append(path)
            return image

        info = resource.SpriteInfo("t", "/nowhere/t.png", 10, 10, 1, None)
        sprite = resource.Sprite(info, loader=loader)
        sprite.load()
        self.assertEqual(loads, ["/nowhere/t.png"])
        sprite.draw(0, 0)
        self.assertEqual(loads, ["/nowhere/t.png"])

    def test_preload_all_loads_every_sprite_listed_in_the_manifest(self):
        # Sprite.load needs an open canvas, so only that call is replaced; which sprites
        # preload_all asks to load is what is being checked.
        with mock.patch.object(resource.Sprite, "load", autospec=True) as load:
            resource.preload_all()
        loaded = {call.args[0].info.name for call in load.call_args_list}
        self.assertEqual(loaded, set(resource.load_manifest()))


class SpriteAnimationTest(unittest.TestCase):
    def test_next_frame_advances_by_fps_times_dt(self):
        sprite, _ = make_sprite(frames=4, fps=8.0)
        self.assertAlmostEqual(sprite.next_frame(0.0, 0.25), 2.0)

    def test_next_frame_wraps_around_the_sheet(self):
        sprite, _ = make_sprite(frames=4, fps=8.0)
        self.assertAlmostEqual(sprite.next_frame(3.5, 0.25), 1.5)

    def test_missing_fps_falls_back_to_the_default(self):
        sprite, _ = make_sprite(frames=2, fps=None)
        self.assertEqual(sprite.fps, config.DEFAULT_ANIM_FPS)

    def test_ground_center_y_puts_the_feet_three_pixels_into_the_floor(self):
        sprite, _ = make_sprite(frame_h=144)
        self.assertEqual(sprite.ground_center_y(), 189)

    def test_ground_center_y_rises_with_the_given_height(self):
        sprite, _ = make_sprite(frame_h=144)
        self.assertEqual(sprite.ground_center_y(100), 289)


class FontPathTest(unittest.TestCase):
    def test_missing_font_file_raises_a_clear_error_naming_the_file(self):
        with tempfile.TemporaryDirectory() as root:
            missing = os.path.join(root, "Galmuri11.ttf")
            with self.assertRaises(FileNotFoundError) as ctx:
                resource.require_font_file(missing)
        self.assertIn("Galmuri11.ttf", str(ctx.exception))

    def test_existing_font_file_is_returned(self):
        self.assertEqual(
            resource.require_font_file(config.FONT_REGULAR), config.FONT_REGULAR
        )
        self.assertEqual(resource.require_font_file(config.FONT_BOLD), config.FONT_BOLD)


if __name__ == "__main__":
    unittest.main()
