import unittest

import background
import stage_data

VIEW_W = 1280


class ParallaxOffsetTest(unittest.TestCase):
    def test_scrolls_at_the_layer_factor(self):
        self.assertEqual(background.parallax_offset(1000, 0.3, 1344), 300)

    def test_wraps_at_the_tile_width(self):
        self.assertEqual(background.parallax_offset(5000, 0.6, 1344), 3000 % 1344)

    def test_is_zero_at_the_level_start(self):
        self.assertEqual(background.parallax_offset(0, 0.3, 1344), 0)

    def test_truncates_to_whole_pixels(self):
        self.assertIsInstance(background.parallax_offset(1001, 0.3, 1344), int)


class ParallaxTileLeftsTest(unittest.TestCase):
    def test_one_tile_covers_the_screen_when_the_offset_is_zero(self):
        self.assertEqual(background.parallax_tile_lefts(0, 1344, VIEW_W), [0])

    def test_a_second_tile_fills_the_gap_opened_by_the_offset(self):
        self.assertEqual(
            background.parallax_tile_lefts(100, 1344, VIEW_W), [-100, 1244]
        )

    def test_tiles_always_cover_the_whole_screen(self):
        for offset in range(0, 1344, 37):
            lefts = background.parallax_tile_lefts(offset, 1344, VIEW_W)
            self.assertLessEqual(lefts[0], 0)
            self.assertGreaterEqual(lefts[-1] + 1344, VIEW_W)


class FloorSegmentsTest(unittest.TestCase):
    def test_stage_two_has_normal_stairs_normal_floor(self):
        segments = background.floor_segments(stage_data.STAGE_2)
        self.assertEqual(
            [(s.start, s.end, s.sprite) for s in segments],
            [
                (0, 4200, "floor_tile"),
                (4200, 5400, "floor_stairs"),
                (5400, 9000, "floor_tile"),
            ],
        )

    def test_a_stage_without_stairs_is_one_flat_segment(self):
        import dataclasses

        flat = dataclasses.replace(stage_data.STAGE_2, stairs_zone=None)
        segments = background.floor_segments(flat)
        self.assertEqual(
            [(s.start, s.end, s.sprite) for s in segments], [(0, 9000, "floor_tile")]
        )


class FloorSpansTest(unittest.TestCase):
    def setUp(self):
        self.normal = background.FloorSegment(0, 4200, "floor_tile")

    def test_tiles_cover_the_view_from_the_level_start(self):
        spans = background.floor_spans(self.normal, 192, 0, VIEW_W)
        self.assertEqual([x for x, _ in spans], [i * 192 for i in range(7)])
        self.assertTrue(all(clip == 192 for _, clip in spans))

    def test_a_scrolled_camera_shifts_the_tiles_left(self):
        spans = background.floor_spans(self.normal, 192, 100, VIEW_W)
        self.assertEqual(spans[0][0], -100)
        self.assertEqual(spans[-1][0], 7 * 192 - 100)

    def test_the_last_tile_of_a_segment_is_clipped(self):
        segment = background.FloorSegment(0, 400, "floor_tile")
        spans = background.floor_spans(segment, 192, 0, VIEW_W)
        self.assertEqual(spans, [(0, 192), (192, 192), (384, 16)])

    def test_segment_outside_the_view_yields_nothing(self):
        far = background.FloorSegment(5400, 9000, "floor_tile")
        self.assertEqual(background.floor_spans(far, 192, 0, VIEW_W), [])

    def test_segment_that_ended_before_the_view_yields_nothing(self):
        self.assertEqual(background.floor_spans(self.normal, 192, 4500, VIEW_W), [])

    def test_segment_starting_inside_the_view_is_anchored_at_its_start(self):
        stairs = background.FloorSegment(4200, 5400, "floor_stairs")
        spans = background.floor_spans(stairs, 96, 3500, VIEW_W)
        self.assertEqual(spans[0], (700, 96))
        self.assertEqual(len(spans), 7)  # view ends at 4780 -> tiles 4200..4776

    def test_tiles_never_overlap_and_never_leave_a_gap(self):
        for cam_x in range(0, 4000, 53):
            spans = background.floor_spans(self.normal, 192, cam_x, VIEW_W)
            for (x1, clip1), (x2, _) in zip(spans, spans[1:], strict=False):
                self.assertEqual(x1 + clip1, x2)


class FakeCamera:
    x = 0


class BackgroundObjectsTest(unittest.TestCase):
    def test_layers_expose_the_game_object_interface(self):
        layer = background.ParallaxLayer(FakeCamera(), "bg_far", 0.3)
        layer.update()
        self.assertIsNone(layer.get_bb())
        layer.handle_collision("any", None)

    def test_floor_exposes_the_game_object_interface(self):
        floor = background.Floor(FakeCamera(), stage_data.STAGE_2)
        floor.update()
        self.assertIsNone(floor.get_bb())


if __name__ == "__main__":
    unittest.main()
