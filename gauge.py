"""참을성 게이지: 값(0~100), 5단계 판정, 상승 속도, 정지(껌·디버그), 꾸르륵 타이머.

화면·소리·입력은 전혀 모른다. 단계가 바뀌거나 꾸르륵 순간이 오면 등록된 콜백만 부른다.
단계는 값에서 그때그때 계산하므로 config.STAGE_THRESHOLDS를 바꾸면 곧바로 반영된다.
"""

import random
from collections.abc import Callable
from enum import IntEnum
from typing import Protocol

import config
from util import clamp


class GaugeStage(IntEnum):
    """게이지 단계. 크기를 비교할 수 있어서 "땀 단계 이상" 같은 규칙을 그대로 쓸 수 있다."""

    CALM = 0  # 평온 0~49
    SWEAT = 1  # 땀 50~79
    STRAIN = 2  # 긴장 80~94
    LIMIT = 3  # 한계 95~99
    FAIL = 4  # 100 = 실패


StageListener = Callable[[GaugeStage, GaugeStage], None]  # (이전 단계, 새 단계)
GrowlListener = Callable[[], None]


class RandomSource(Protocol):
    """꾸르륵 간격을 뽑는 데 필요한 것: random 모듈과 random.Random이 그대로 맞는다."""

    def uniform(self, low: float, high: float, /) -> float: ...


def stage_for(value: float) -> GaugeStage:
    """게이지 값이 속한 단계."""
    passed = sum(value >= threshold for threshold in config.STAGE_THRESHOLDS)
    return GaugeStage(passed)


class Gauge:
    def __init__(self, rate: float, rng: RandomSource = random) -> None:
        """rate: 걷는 동안 오르는 속도(%/s). rng: 꾸르륵 간격을 뽑는 난수기."""
        self.rate = rate
        self._rng = rng
        self._value = 0.0
        self._freeze_remaining = 0.0  # 껌이 남긴 정지 시간(초)
        self._debug_frozen = False  # 디버그 G키 정지
        self._growl_timer = 0.0  # 땀 단계 이상에서 다음 꾸르륵까지 남은 시간(초)
        self._stage_listeners: list[StageListener] = []
        self._growl_listeners: list[GrowlListener] = []

    # ------------------------------------------------------------ 읽기
    @property
    def value(self) -> float:
        return self._value

    @property
    def stage(self) -> GaugeStage:
        return stage_for(self._value)

    @property
    def is_full(self) -> bool:
        return self._value >= config.GAUGE_MAX

    @property
    def freeze_remaining(self) -> float:
        """껌이 게이지를 붙잡아 둘 남은 시간(초). 디버그 정지는 세지 않는다."""
        return self._freeze_remaining

    @property
    def is_frozen(self) -> bool:
        return self._debug_frozen or self._freeze_remaining > 0.0

    # ------------------------------------------------------------ 구독
    def on_stage_change(self, listener: StageListener) -> None:
        """단계가 바뀔 때마다 listener(이전 단계, 새 단계)를 부른다 (등록한 순서대로)."""
        self._stage_listeners.append(listener)

    def on_growl(self, listener: GrowlListener) -> None:
        """꾸르륵 소리를 낼 순간마다 listener()를 부른다."""
        self._growl_listeners.append(listener)

    # ------------------------------------------------------------ 값 바꾸기
    def add(self, amount: float) -> None:
        """게이지를 amount만큼 즉시 바꾼다(음수는 감소). 정지 중에도 적용된다."""
        self.set_value(self._value + amount)

    def set_value(self, value: float) -> None:
        old_stage = self.stage
        self._value = clamp(0.0, value, config.GAUGE_MAX)
        new_stage = self.stage
        if new_stage == old_stage:
            return
        for listener in list(self._stage_listeners):
            listener(old_stage, new_stage)
        if old_stage < GaugeStage.SWEAT <= new_stage:
            self._growl()

    def freeze(self, seconds: float) -> None:
        """seconds초 동안 게이지를 붙잡는다. 이미 더 길게 남아 있으면 줄이지 않는다."""
        self._freeze_remaining = max(self._freeze_remaining, seconds)

    def toggle_debug_freeze(self) -> None:
        self._debug_frozen = not self._debug_frozen

    # ------------------------------------------------------------ 시간
    def step(self, dt: float, running: bool) -> None:
        """dt초가 흘렀다. running이면 달리는 배율로 오른다."""
        self._tick_growl(dt)
        rising_time = self._tick_freeze(dt)
        if rising_time > 0.0:
            multiplier = config.RUN_GAUGE_MULT if running else 1.0
            self.set_value(self._value + self.rate * multiplier * rising_time)

    def _tick_freeze(self, dt: float) -> float:
        """껌 정지 시간을 깎고, 이번 dt 중 게이지가 실제로 오를 수 있는 시간을 돌려준다."""
        held = min(dt, self._freeze_remaining)
        self._freeze_remaining -= held
        return 0.0 if self._debug_frozen else dt - held

    def _tick_growl(self, dt: float) -> None:
        """땀 단계 이상이면 타이머를 돌려, 0이 되면 꾸르륵 한 번. 정지 중에도 돈다."""
        if self.stage < GaugeStage.SWEAT:
            return
        self._growl_timer -= dt
        if self._growl_timer <= 0.0:
            self._growl()

    def _growl(self) -> None:
        self._growl_timer = self._rng.uniform(*config.GROWL_INTERVAL)
        for listener in list(self._growl_listeners):
            listener()
