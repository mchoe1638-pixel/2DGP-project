"""pico2d 없이 쓸 수 있는 작은 수학 도우미."""

import math
from typing import TypeVar

Number = TypeVar("Number", int, float)


def clamp(minimum: Number, value: Number, maximum: Number) -> Number:
    """value를 [minimum, maximum]에 가둔다. 범위가 뒤집혀 있으면 minimum을 돌려준다."""
    return max(minimum, min(value, maximum))


def snap(value: float) -> int:
    """그리기 좌표를 정수 픽셀로 반올림한다 (0.5는 올림)."""
    return math.floor(value + 0.5)


def smoothstep(t: float) -> float:
    """0~1 구간에서 부드럽게 가속·감속하는 보간 계수."""
    t = clamp(0.0, t, 1.0)
    return t * t * (3.0 - 2.0 * t)
