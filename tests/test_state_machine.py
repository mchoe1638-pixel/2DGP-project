import subprocess
import sys
import unittest

import config
from state_machine import State, StateMachine


class Owner:
    """상태가 남긴 호출 기록을 모으는 가짜 주인 객체."""

    def __init__(self):
        self.log = []


def make_state(name):
    """enter/exit/do/draw 호출을 owner.log에 남기는 상태 클래스를 만든다."""

    class Recording(State):
        @staticmethod
        def enter(owner, event):
            owner.log.append((name + ".enter", event))

        @staticmethod
        def exit(owner, event):
            owner.log.append((name + ".exit", event))

        @staticmethod
        def do(owner, dt):
            owner.log.append((name + ".do", dt))

        @staticmethod
        def draw(owner):
            owner.log.append((name + ".draw",))

    Recording.__name__ = name
    return Recording


A = make_state("A")
B = make_state("B")
C = make_state("C")


def is_go(event):
    return event[0] == "GO"


def always(event):
    return True


def started(transitions=None):
    """A 상태로 시작한 (owner, machine). 시작 때 남은 기록은 비워 둔다."""
    owner = Owner()
    machine = StateMachine(owner)
    machine.set_transitions(transitions or {})
    machine.start(A)
    owner.log.clear()
    return owner, machine


class StartTest(unittest.TestCase):
    def test_start_enters_the_first_state_with_a_start_event(self):
        owner = Owner()
        machine = StateMachine(owner)

        machine.start(A)

        self.assertIs(machine.state, A)
        self.assertEqual(owner.log, [("A.enter", ("START", None))])


class UpdateAndDrawTest(unittest.TestCase):
    def test_update_runs_do_of_the_current_state_with_the_elapsed_time(self):
        owner, machine = started()

        machine.update(0.25)

        self.assertEqual(owner.log, [("A.do", 0.25)])

    def test_draw_delegates_to_the_current_state(self):
        owner, machine = started()

        machine.draw()

        self.assertEqual(owner.log, [("A.draw",)])

    def test_states_only_need_to_override_what_they_use(self):
        class Bare(State):
            pass

        owner = Owner()
        machine = StateMachine(owner)
        machine.start(Bare)

        machine.update(0.1)
        machine.draw()

        self.assertIs(machine.state, Bare)


class HandleStateEventTest(unittest.TestCase):
    def test_matching_event_exits_then_enters_and_switches_the_state(self):
        owner, machine = started({A: {is_go: B}})

        handled = machine.handle_state_event(("GO", 7))

        self.assertTrue(handled)
        self.assertIs(machine.state, B)
        self.assertEqual(owner.log, [("A.exit", ("GO", 7)), ("B.enter", ("GO", 7))])

    def test_event_without_a_matching_predicate_changes_nothing(self):
        owner, machine = started({A: {is_go: B}})

        handled = machine.handle_state_event(("STOP", None))

        self.assertFalse(handled)
        self.assertIs(machine.state, A)
        self.assertEqual(owner.log, [])

    def test_the_first_matching_predicate_in_table_order_wins(self):
        _, machine = started({A: {is_go: B, always: C}})
        machine.handle_state_event(("GO", None))
        self.assertIs(machine.state, B)

        _, machine = started({A: {is_go: B, always: C}})
        machine.handle_state_event(("STOP", None))
        self.assertIs(machine.state, C)

    def test_state_missing_from_the_table_ignores_events(self):
        _, machine = started({B: {is_go: A}})

        handled = machine.handle_state_event(("GO", None))

        self.assertFalse(handled)
        self.assertIs(machine.state, A)


class EventQueueTest(unittest.TestCase):
    def test_queued_event_is_handled_after_do_inside_update(self):
        owner, machine = started({A: {is_go: B}})
        machine.add_event(("GO", None))

        machine.update(0.1)

        self.assertEqual(
            owner.log,
            [("A.do", 0.1), ("A.exit", ("GO", None)), ("B.enter", ("GO", None))],
        )
        self.assertIs(machine.state, B)

    def test_queued_event_nobody_wants_is_dropped(self):
        owner, machine = started({A: {is_go: B}})
        machine.add_event(("NOISE", None))
        machine.update(0.1)
        owner.log.clear()

        machine.update(0.1)

        self.assertEqual(owner.log, [("A.do", 0.1)])
        self.assertIs(machine.state, A)

    def test_event_queued_while_handling_waits_for_the_next_update(self):
        owner, machine = started({A: {is_go: B}, B: {is_go: C}})
        machine.add_event(("GO", None))
        original_enter = B.enter

        def enter_and_queue_again(owner_, event):
            original_enter(owner_, event)
            machine.add_event(("GO", None))

        B.enter = staticmethod(enter_and_queue_again)
        try:
            machine.update(0.1)
            self.assertIs(machine.state, B)
            machine.update(0.1)
            self.assertIs(machine.state, C)
        finally:
            B.enter = staticmethod(original_enter)


class IndependenceTest(unittest.TestCase):
    def test_importing_the_state_machine_does_not_pull_in_the_player(self):
        code = "import sys, state_machine; sys.exit(int('player' in sys.modules))"

        result = subprocess.run(
            [sys.executable, "-c", code], cwd=config.BASE_DIR, capture_output=True
        )

        self.assertEqual(result.returncode, 0, result.stderr.decode(errors="replace"))


if __name__ == "__main__":
    unittest.main()
