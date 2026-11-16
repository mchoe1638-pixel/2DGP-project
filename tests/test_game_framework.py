import unittest

import config
import game_framework


class FakeMode:
    def __init__(self, name, log, quit_after_updates=None):
        self.name = name
        self.log = log
        self.updates = 0
        self.quit_after_updates = quit_after_updates

    def init(self):
        self.log.append((self.name, "init"))

    def finish(self):
        self.log.append((self.name, "finish"))

    def pause(self):
        self.log.append((self.name, "pause"))

    def resume(self):
        self.log.append((self.name, "resume"))

    def handle_events(self):
        self.log.append((self.name, "events"))

    def update(self):
        self.updates += 1
        self.log.append((self.name, "update"))
        if (
            self.quit_after_updates is not None
            and self.updates >= self.quit_after_updates
        ):
            game_framework.quit()

    def draw(self):
        self.log.append((self.name, "draw"))


class FakeClock:
    def __init__(self, ticks):
        self.ticks = list(ticks)

    def __call__(self):
        return self.ticks.pop(0) if len(self.ticks) > 1 else self.ticks[0]


class ModeStackTest(unittest.TestCase):
    def setUp(self):
        self.log = []
        game_framework.stack = []
        game_framework.running = True

    def test_change_mode_finishes_current_and_inits_next(self):
        first, second = FakeMode("a", self.log), FakeMode("b", self.log)
        game_framework.stack = [first]
        game_framework.change_mode(second)
        self.assertEqual(self.log, [("a", "finish"), ("b", "init")])
        self.assertEqual(game_framework.stack, [second])

    def test_push_mode_pauses_current_and_inits_new(self):
        first, second = FakeMode("a", self.log), FakeMode("b", self.log)
        game_framework.stack = [first]
        game_framework.push_mode(second)
        self.assertEqual(self.log, [("a", "pause"), ("b", "init")])
        self.assertEqual(game_framework.stack, [first, second])

    def test_pop_mode_finishes_top_and_resumes_previous(self):
        first, second = FakeMode("a", self.log), FakeMode("b", self.log)
        game_framework.stack = [first, second]
        game_framework.pop_mode()
        self.assertEqual(self.log, [("b", "finish"), ("a", "resume")])
        self.assertEqual(game_framework.stack, [first])

    def test_quit_stops_the_loop(self):
        game_framework.quit()
        self.assertFalse(game_framework.running)


class RunLoopTest(unittest.TestCase):
    def setUp(self):
        self.log = []
        self.original_clock = game_framework.clock

    def tearDown(self):
        game_framework.clock = self.original_clock

    def test_run_inits_loops_in_order_and_finishes_on_quit(self):
        game_framework.clock = FakeClock([0.0, 0.016, 0.032, 0.048])
        mode = FakeMode("a", self.log, quit_after_updates=2)
        game_framework.run(mode)
        self.assertEqual(self.log[0], ("a", "init"))
        self.assertEqual(
            self.log[1:4], [("a", "events"), ("a", "update"), ("a", "draw")]
        )
        self.assertEqual(self.log[-1], ("a", "finish"))
        self.assertEqual(mode.updates, 2)

    def test_frame_time_is_measured_between_frames(self):
        game_framework.clock = FakeClock([0.0, 0.020, 0.040])
        mode = FakeMode("a", self.log, quit_after_updates=1)
        game_framework.run(mode)
        self.assertAlmostEqual(game_framework.frame_time, 0.020)

    def test_frame_time_is_clamped_after_a_long_stall(self):
        game_framework.clock = FakeClock([0.0, 5.0, 10.0])
        mode = FakeMode("a", self.log, quit_after_updates=1)
        game_framework.run(mode)
        self.assertEqual(game_framework.frame_time, config.MAX_FRAME_TIME)

    def test_run_finishes_every_mode_left_on_the_stack(self):
        game_framework.clock = FakeClock([0.0, 0.016, 0.032])

        class Pusher(FakeMode):
            def update(self_inner):
                super().update()
                game_framework.push_mode(FakeMode("top", self.log))
                game_framework.quit()

        game_framework.run(Pusher("pusher", self.log))
        finishes = [entry for entry in self.log if entry[1] == "finish"]
        self.assertEqual(finishes, [("top", "finish"), ("pusher", "finish")])
        self.assertEqual(game_framework.stack, [])


if __name__ == "__main__":
    unittest.main()
