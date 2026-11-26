"""pico2d 없이 쓸 수 있는 작은 수학 도우미."""

import math
from typing import TypeVar

Number = TypeVar("Number", int, float)


def clamp(minimum: Number, value: Number, maximum: Number) -> Number:
    """value를 [minimum, maximum]에 가둔다. 범위가 뒤집혀 있으면 minimum을 돌려준다."""
    return max(minimum, min(value, maximum))


def unit_vector(
    dx: float, dy: float, fallback: tuple[float, float] = (1.0, 0.0)
) -> tuple[float, float]:
    """(dx, dy)를 길이 1로 맞춘다. 길이가 0이라 방향이 없으면 fallback을 그대로 돌려준다."""
    length = math.hypot(dx, dy)
    if length == 0.0:
        return fallback
    return dx / length, dy / length


def separation(
    x: float, y: float, cx: float, cy: float, min_dist: float
) -> tuple[float, float]:
    """(x, y)가 원 (cx, cy)에서 min_dist 안에 있으면, 중심에서 멀어져 min_dist가 되게 하는 움직임 (dx, dy).

    이미 바깥이면 (0, 0). 중심에 딱 겹쳐 방향이 없으면 -x 쪽(스테이지를 거슬러 온 쪽)으로 민다.
    """
    gap = math.hypot(x - cx, y - cy)
    if gap >= min_dist:
        return 0.0, 0.0
    away_x, away_y = unit_vector(x - cx, y - cy, fallback=(-1.0, 0.0))
    reach = min_dist - gap
    return away_x * reach, away_y * reach


def snap(value: float) -> int:
    """그리기 좌표를 정수 픽셀로 반올림한다 (0.5는 올림)."""
    return math.floor(value + 0.5)


def smoothstep(t: float) -> float:
    """0~1 구간에서 부드럽게 가속·감속하는 보간 계수."""
    t = clamp(0.0, t, 1.0)
    return t * t * (3.0 - 2.0 * t)
