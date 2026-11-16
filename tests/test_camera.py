import unittest

import camera

VIEW_W = 1280
LEVEL_W = 9000


class TargetXTest(unittest.TestCase):
    def test_player_stays_one_third_from_the_left_edge(self):
        self.assertEqual(camera.target_x(1000, VIEW_W, LEVEL_W), 1000 - VIEW_W // 3)

    def test_clamps_at_the_start_of_the_level(self):
        self.assertEqual(camera.target_x(150, VIEW_W, LEVEL_W), 0)

    def test_clamps_at_the_end_of_the_level(self):
        self.assertEqual(camera.target_x(8900, VIEW_W, LEVEL_W), LEVEL_W - VIEW_W)

    def test_level_narrower_than_the_screen_pins_the_camera_to_zero(self):
        self.assertEqual(camera.target_x(500, VIEW_W, 800), 0)


class CameraTest(unittest.TestCase):
    def setUp(self):
        self.camera = camera.Camera(VIEW_W, LEVEL_W)

    def test_snap_to_places_the_camera_on_the_target(self):
        self.camera.snap_to(2000)
        self.assertEqual(self.camera.x, 2000 - VIEW_W // 3)

    def test_x_is_a_whole_number_so_every_object_shares_one_pixel_offset(self):
        self.camera.update(0.016, 2000.7)
        self.assertIsInstance(self.camera.x, int)

    def test_world_to_screen_subtracts_the_camera(self):
        self.camera.snap_to(2000)
        self.assertEqual(self.camera.to_screen_x(2000), VIEW_W // 3)

    def test_update_follows_the_player_instantly_when_not_gliding(self):
        self.camera.update(0.016, 3000)
        self.assertEqual(self.camera.x, 3000 - VIEW_W // 3)

    def test_camera_never_leaves_the_level(self):
        self.camera.update(0.016, -500)
        self.assertEqual(self.camera.x, 0)
        self.camera.update(0.016, 99999)
        self.assertEqual(self.camera.x, LEVEL_W - VIEW_W)

    def test_glide_starts_from_the_old_position(self):
        self.camera.snap_to(0)
        self.camera.start_glide(0.4)
        self.camera.update(0.0, 1000)
        self.assertEqual(self.camera.x, 0)

    def test_glide_is_halfway_after_half_its_duration(self):
        self.camera.snap_to(0)
        self.camera.start_glide(0.4)
        self.camera.update(0.2, 1000)
        self.assertEqual(self.camera.x, (1000 - VIEW_W // 3) // 2)

    def test_glide_lands_exactly_on_the_target_and_then_stops_gliding(self):
        self.camera.snap_to(0)
        self.camera.start_glide(0.4)
        self.camera.update(0.2, 1000)
        self.camera.update(0.2, 1000)
        self.assertEqual(self.camera.x, 1000 - VIEW_W // 3)
        self.assertFalse(self.camera.is_gliding)
        self.camera.update(0.016, 2000)
        self.assertEqual(self.camera.x, 2000 - VIEW_W // 3)

    def test_glide_tracks_a_moving_target(self):
        self.camera.snap_to(0)
        self.camera.start_glide(0.4)
        self.camera.update(0.2, 1000)
        self.camera.update(0.2, 1400)
        self.assertEqual(self.camera.x, 1400 - VIEW_W // 3)


class VisibilityTest(unittest.TestCase):
    def setUp(self):
        self.camera = camera.Camera(VIEW_W, LEVEL_W)
        self.camera.snap_to(2000)  # camera.x == 1574, view [1574, 2854)

    def test_object_inside_the_view_is_visible(self):
        self.assertTrue(self.camera.is_visible(2000, 50))

    def test_object_fully_left_of_the_view_is_hidden(self):
        self.assertFalse(self.camera.is_visible(1500, 50))

    def test_object_fully_right_of_the_view_is_hidden(self):
        self.assertFalse(self.camera.is_visible(2950, 50))

    def test_object_overlapping_the_left_edge_is_visible(self):
        self.assertTrue(self.camera.is_visible(1560, 50))

    def test_margin_widens_the_visible_range(self):
        self.assertFalse(self.camera.is_visible(1500, 50))
        self.assertTrue(self.camera.is_visible(1500, 50, margin=100))


if __name__ == "__main__":
    unittest.main()
