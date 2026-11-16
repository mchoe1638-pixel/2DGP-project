import unittest

import text


class AlignedLeftTest(unittest.TestCase):
    def test_left_alignment_keeps_the_given_x(self):
        self.assertEqual(text.aligned_left(100, 60, "left"), 100)

    def test_center_alignment_moves_half_the_width_to_the_left(self):
        self.assertEqual(text.aligned_left(100, 60, "center"), 70)

    def test_center_alignment_of_an_odd_width_stays_on_whole_pixels(self):
        self.assertEqual(text.aligned_left(100, 61, "center"), 70)

    def test_right_alignment_moves_the_full_width_to_the_left(self):
        self.assertEqual(text.aligned_left(100, 60, "right"), 40)

    def test_unknown_alignment_is_rejected_with_its_name(self):
        with self.assertRaises(ValueError) as ctx:
            text.aligned_left(100, 60, "middle")
        self.assertIn("middle", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
