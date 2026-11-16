import unittest

import util


class ClampTest(unittest.TestCase):
    def test_returns_the_value_when_it_is_inside_the_range(self):
        self.assertEqual(util.clamp(0, 5, 10), 5)

    def test_returns_the_minimum_when_the_value_is_below_it(self):
        self.assertEqual(util.clamp(0, -3, 10), 0)

    def test_returns_the_maximum_when_the_value_is_above_it(self):
        self.assertEqual(util.clamp(0, 99, 10), 10)

    def test_a_maximum_below_the_minimum_resolves_to_the_minimum(self):
        # camera on a level that is narrower than the screen
        self.assertEqual(util.clamp(0, 50, -100), 0)


class SnapTest(unittest.TestCase):
    def test_rounds_halves_up(self):
        self.assertEqual(util.snap(100.5), 101)
        self.assertEqual(util.snap(100.4), 100)

    def test_rounds_negative_values_consistently(self):
        self.assertEqual(util.snap(-0.4), 0)
        self.assertEqual(util.snap(-0.6), -1)

    def test_returns_an_int(self):
        self.assertIsInstance(util.snap(3.2), int)


class SmoothstepTest(unittest.TestCase):
    def test_endpoints(self):
        self.assertEqual(util.smoothstep(0.0), 0.0)
        self.assertEqual(util.smoothstep(1.0), 1.0)

    def test_midpoint_is_one_half(self):
        self.assertAlmostEqual(util.smoothstep(0.5), 0.5)

    def test_values_outside_the_unit_range_are_clamped(self):
        self.assertEqual(util.smoothstep(-2.0), 0.0)
        self.assertEqual(util.smoothstep(7.0), 1.0)

    def test_eases_in_slower_than_linear(self):
        self.assertLess(util.smoothstep(0.25), 0.25)


if __name__ == "__main__":
    unittest.main()
