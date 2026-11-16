"""참을성 게이지: 값, 단계 판정, 상승 속도, 단계 변화 콜백, 껌/디버그 정지, 꾸르륵 타이머."""

import unittest
from unittest import mock

import config
from gauge import Gauge, GaugeStage

DT = 1 / 60
BASE_RATE = config.GAUGE_BASE_RATE[2]


class FakeRandom:
    """uniform(low, high)이 미리 정해 둔 값을 차례로 돌려주는 난수기. 마지막 값은 계속 반복한다."""

    def __init__(self, *values: float) -> None:
        self.values = list(values)
        self.calls: list[tuple[float, float]] = []

    def uniform(self, low: float, high: float) -> float:
        self.calls.append((low, high))
        return self.values.pop(0) if len(self.values) > 1 else self.values[0]


def make_gauge(value: float = 0.0, *intervals: float, rate: float = BASE_RATE) -> Gauge:
    """value에서 시작하는 게이지. intervals는 꾸르륵 간격으로 뽑힐 값들(기본은 늘 10초)."""
    gauge = Gauge(rate, rng=FakeRandom(*(intervals or (10.0,))))
    if value:
        gauge.set_value(value)
    return gauge


class StageTest(unittest.TestCase):
    def test_stage_follows_the_configured_thresholds(self):
        cases = [
            (0, GaugeStage.CALM),
            (49.9, GaugeStage.CALM),
            (50, GaugeStage.SWEAT),
            (79.9, GaugeStage.SWEAT),
            (80, GaugeStage.STRAIN),
            (94.9, GaugeStage.STRAIN),
            (95, GaugeStage.LIMIT),
            (99.9, GaugeStage.LIMIT),
            (100, GaugeStage.FAIL),
        ]
        for value, expected in cases:
            with self.subTest(value=value):
                self.assertIs(make_gauge(value).stage, expected)

    def test_stage_boundaries_are_read_from_config(self):
        gauge = make_gauge(25)

        with mock.patch.object(config, "STAGE_THRESHOLDS", (10, 20, 30, 40)):
            stage = gauge.stage

        self.assertIs(stage, GaugeStage.STRAIN)

    def test_stages_are_ordered_so_rules_can_use_comparisons(self):
        self.assertLess(GaugeStage.CALM, GaugeStage.SWEAT)
        self.assertLess(GaugeStage.SWEAT, GaugeStage.STRAIN)
        self.assertLess(GaugeStage.STRAIN, GaugeStage.LIMIT)
        self.assertLess(GaugeStage.LIMIT, GaugeStage.FAIL)

    def test_only_a_full_gauge_is_full(self):
        self.assertFalse(make_gauge(99.99).is_full)
        self.assertTrue(make_gauge(100).is_full)


class ValueTest(unittest.TestCase):
    def test_starts_empty(self):
        self.assertEqual(Gauge(BASE_RATE).value, 0.0)

    def test_add_changes_the_value_by_the_amount(self):
        gauge = make_gauge(20)

        gauge.add(10)
        gauge.add(-15)

        self.assertAlmostEqual(gauge.value, 15)

    def test_add_clamps_to_the_valid_range(self):
        gauge = make_gauge(50)

        gauge.add(500)
        self.assertEqual(gauge.value, config.GAUGE_MAX)

        gauge.add(-500)
        self.assertEqual(gauge.value, 0)

    def test_set_value_clamps_to_the_valid_range(self):
        gauge = make_gauge()

        gauge.set_value(-5)
        self.assertEqual(gauge.value, 0)

        gauge.set_value(120)
        self.assertEqual(gauge.value, config.GAUGE_MAX)


class RiseTest(unittest.TestCase):
    def test_walking_rises_at_the_base_rate_per_second(self):
        gauge = make_gauge()

        gauge.step(1.0, running=False)

        self.assertAlmostEqual(gauge.value, BASE_RATE)

    def test_running_rises_faster_by_the_run_multiplier(self):
        gauge = make_gauge()

        gauge.step(1.0, running=True)

        self.assertAlmostEqual(gauge.value, BASE_RATE * config.RUN_GAUGE_MULT)

    def test_rise_is_proportional_to_elapsed_time(self):
        gauge = make_gauge()

        gauge.step(0.5, running=False)

        self.assertAlmostEqual(gauge.value, BASE_RATE * 0.5)

    def test_many_small_steps_add_up_to_one_big_step(self):
        gauge = make_gauge()

        for _ in range(60):
            gauge.step(DT, running=False)

        self.assertAlmostEqual(gauge.value, BASE_RATE, places=9)

    def test_rate_is_the_one_given_at_construction(self):
        gauge = make_gauge(rate=3.0)

        gauge.step(1.0, running=False)

        self.assertAlmostEqual(gauge.value, 3.0)

    def test_rise_stops_at_the_maximum(self):
        gauge = make_gauge(99.9)

        gauge.step(10.0, running=True)

        self.assertEqual(gauge.value, config.GAUGE_MAX)


class CallbackTest(unittest.TestCase):
    def setUp(self):
        self.gauge = make_gauge()
        self.changes: list[tuple[GaugeStage, GaugeStage]] = []
        self.gauge.on_stage_change(lambda old, new: self.changes.append((old, new)))

    def test_reports_the_old_and_new_stage_when_it_changes(self):
        self.gauge.add(50)

        self.assertEqual(self.changes, [(GaugeStage.CALM, GaugeStage.SWEAT)])

    def test_stays_quiet_while_the_stage_is_unchanged(self):
        self.gauge.add(10)
        self.gauge.add(5)

        self.assertEqual(self.changes, [])

    def test_reports_a_drop_to_a_lower_stage(self):
        self.gauge.set_value(60)
        self.changes.clear()

        self.gauge.add(-15)

        self.assertEqual(self.changes, [(GaugeStage.SWEAT, GaugeStage.CALM)])

    def test_reports_once_when_a_change_skips_stages(self):
        self.gauge.set_value(96)

        self.assertEqual(self.changes, [(GaugeStage.CALM, GaugeStage.LIMIT)])

    def test_reports_a_stage_crossed_by_the_passage_of_time(self):
        self.gauge.set_value(49.99)
        self.changes.clear()

        self.gauge.step(1.0, running=False)

        self.assertEqual(self.changes, [(GaugeStage.CALM, GaugeStage.SWEAT)])

    def test_reaching_one_hundred_reports_the_fail_stage(self):
        self.gauge.set_value(99.9)
        self.changes.clear()

        self.gauge.step(1.0, running=True)

        self.assertEqual(self.changes, [(GaugeStage.LIMIT, GaugeStage.FAIL)])
        self.assertTrue(self.gauge.is_full)

    def test_callbacks_see_the_already_updated_gauge(self):
        seen: list[tuple[float, GaugeStage]] = []
        self.gauge.on_stage_change(
            lambda old, new: seen.append((self.gauge.value, self.gauge.stage))
        )

        self.gauge.add(85)

        self.assertEqual(seen, [(85, GaugeStage.STRAIN)])

    def test_every_listener_is_called_in_registration_order(self):
        order: list[str] = []
        self.gauge.on_stage_change(lambda old, new: order.append("first"))
        self.gauge.on_stage_change(lambda old, new: order.append("second"))

        self.gauge.add(50)

        self.assertEqual(order, ["first", "second"])

    def test_setting_a_value_in_the_same_stage_is_not_a_change(self):
        self.gauge.set_value(55)
        self.changes.clear()

        self.gauge.set_value(70)

        self.assertEqual(self.changes, [])


class FreezeTest(unittest.TestCase):
    def test_freeze_stops_the_rise(self):
        gauge = make_gauge()

        gauge.freeze(3.0)
        gauge.step(1.0, running=True)

        self.assertEqual(gauge.value, 0)
        self.assertTrue(gauge.is_frozen)

    def test_remaining_freeze_time_counts_down_and_is_readable(self):
        gauge = make_gauge()
        gauge.freeze(3.0)

        gauge.step(1.0, running=False)

        self.assertAlmostEqual(gauge.freeze_remaining, 2.0)

    def test_rise_resumes_only_for_the_part_of_a_step_after_the_freeze_ends(self):
        gauge = make_gauge()
        gauge.freeze(1.0)

        gauge.step(2.0, running=False)

        self.assertAlmostEqual(gauge.value, BASE_RATE * 1.0)
        self.assertEqual(gauge.freeze_remaining, 0)
        self.assertFalse(gauge.is_frozen)

    def test_a_second_freeze_refreshes_but_never_shortens_the_first(self):
        gauge = make_gauge()
        gauge.freeze(3.0)
        gauge.step(2.0, running=False)  # 1초 남음

        gauge.freeze(3.0)
        self.assertAlmostEqual(gauge.freeze_remaining, 3.0)

        gauge.freeze(1.0)
        self.assertAlmostEqual(gauge.freeze_remaining, 3.0)

    def test_debug_freeze_holds_the_gauge_until_toggled_off(self):
        gauge = make_gauge()

        gauge.toggle_debug_freeze()
        gauge.step(100.0, running=True)
        self.assertEqual(gauge.value, 0)
        self.assertTrue(gauge.is_frozen)

        gauge.toggle_debug_freeze()
        gauge.step(1.0, running=False)
        self.assertAlmostEqual(gauge.value, BASE_RATE)
        self.assertFalse(gauge.is_frozen)

    def test_debug_freeze_does_not_show_up_as_remaining_gum_time(self):
        gauge = make_gauge()

        gauge.toggle_debug_freeze()

        self.assertEqual(gauge.freeze_remaining, 0)

    def test_instant_changes_still_apply_while_frozen(self):
        gauge = make_gauge()
        gauge.freeze(3.0)

        gauge.add(15)

        self.assertEqual(gauge.value, 15)


class GrowlTest(unittest.TestCase):
    def setUp(self):
        self.growls = 0

    def count_growl(self) -> None:
        self.growls += 1

    def gauge_with_growl_counter(self, value: float, *intervals: float) -> Gauge:
        gauge = make_gauge(value, *intervals)
        gauge.on_growl(self.count_growl)
        return gauge

    def test_growls_once_when_the_sweat_stage_begins(self):
        gauge = self.gauge_with_growl_counter(0)

        gauge.add(50)

        self.assertEqual(self.growls, 1)

    def test_growls_when_time_carries_the_gauge_into_the_sweat_stage(self):
        gauge = self.gauge_with_growl_counter(49.99)

        gauge.step(1.0, running=False)

        self.assertEqual(self.growls, 1)

    def test_moving_up_between_later_stages_adds_no_extra_growl(self):
        gauge = self.gauge_with_growl_counter(0)
        gauge.add(50)  # 땀 단계에 들어서며 한 번

        gauge.add(30)  # 땀 -> 긴장
        gauge.add(15)  # 긴장 -> 한계

        self.assertEqual(self.growls, 1)

    def test_does_not_growl_in_the_calm_stage(self):
        gauge = self.gauge_with_growl_counter(0)

        gauge.step(30.0, running=False)  # 게이지는 42%까지만 오른다

        self.assertEqual(self.growls, 0)

    def test_growls_again_after_the_random_interval(self):
        gauge = self.gauge_with_growl_counter(0, 9.0, 11.0)
        gauge.add(50)  # 첫 번째 꾸르륵, 다음은 9초 뒤

        gauge.step(8.9, running=False)
        self.assertEqual(self.growls, 1)

        gauge.step(0.2, running=False)
        self.assertEqual(self.growls, 2)

        gauge.step(10.8, running=False)  # 다음은 두 번째 꾸르륵 11초 뒤
        self.assertEqual(self.growls, 2)

        gauge.step(0.4, running=False)
        self.assertEqual(self.growls, 3)

    def test_interval_is_drawn_from_the_configured_range(self):
        rng = FakeRandom(10.0)
        gauge = Gauge(BASE_RATE, rng=rng)

        gauge.add(50)

        self.assertEqual(rng.calls, [config.GROWL_INTERVAL])

    def test_keeps_growling_in_the_later_stages(self):
        gauge = self.gauge_with_growl_counter(0, 10.0)
        gauge.set_value(85)  # 평온에서 바로 들어왔다: 첫 번째 꾸르륵

        for _ in range(2):
            gauge.freeze(100.0)  # 시간이 흘러도 게이지가 100에 닿지 않게 붙잡아 둔다
            gauge.step(10.0, running=False)

        self.assertEqual(self.growls, 3)

    def test_stops_below_fifty_and_growls_again_on_re_entry(self):
        gauge = self.gauge_with_growl_counter(0, 10.0)
        gauge.add(60)  # 첫 번째 꾸르륵
        gauge.add(-20)  # 평온으로 돌아와 타이머가 멈춘다
        gauge.freeze(100.0)

        gauge.step(30.0, running=False)
        self.assertEqual(self.growls, 1)

        gauge.add(20)  # 다시 땀 단계에 들어선다
        self.assertEqual(self.growls, 2)

    def test_the_growl_timer_keeps_running_while_the_gauge_is_frozen(self):
        gauge = self.gauge_with_growl_counter(0, 10.0)
        gauge.add(60)  # 첫 번째 꾸르륵
        gauge.freeze(100.0)

        gauge.step(10.5, running=False)

        self.assertEqual(self.growls, 2)


if __name__ == "__main__":
    unittest.main()
