"""격자 지도: 벽 칸과 바닥 구역, 벽 충돌과 벽 미끄러짐.

월드는 위에서 내려다본 (x, y) 평면이다. 1칸 = 1m이고, 칸 (cx, cy)는 [cx, cx+1) × [cy, cy+1)를 덮는다.
칸마다 바닥이거나 벽이다. 벽 칸은 텍스처 이름을, 바닥 칸은 바닥 종류(보통·계단)를 가진다.

지도는 통로 구간(Segment)들로 만든다.
- 구간의 [x0, x1) × [y0, y1)가 바닥이다. y1 줄이 왼벽, y0 - 1 줄이 오른벽이다 (+x를 볼 때 +y가 왼쪽).
- 벽 줄의 텍스처는 먼저 정한 구간이 이긴다. 바닥은 벽 텍스처로 덮지 않는다.
- 그 밖의 바닥 아닌 칸은 모두 기본 벽(tex_wall_tile)이다. 통로 폭이 바뀌는 곳의 벽이 저절로 채워진다.
- 기둥과 표지판·문 칸은 마지막에 덮어쓴다.

지도는 만든 뒤 바뀌지 않는다. 지도 밖은 모두 벽으로 본다.
"""

import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

import config

FLOOR_NORMAL = "normal"
FLOOR_STAIRS = "stairs"
FLOOR_KINDS = (FLOOR_NORMAL, FLOOR_STAIRS)
DEFAULT_WALL = "tex_wall_tile"  # 어느 구간의 벽 줄도 아닌 벽 칸, 기둥
EMPTY = 0  # cells 값 0은 바닥, 1 이상은 textures[값 - 1] 텍스처의 벽
EPSILON = 1e-6  # 벽면에 딱 붙은 것은 겹친 것으로 보지 않는다

Cell = tuple[int, int]


# ---------------------------------------------------------------- 지도 재료
@dataclass(frozen=True)
class Segment:
    """통로 한 구간. [x0, x1) × [y0, y1)가 바닥이다."""

    x0: int
    x1: int
    y0: int
    y1: int
    left_texture: str  # y1 줄 벽
    right_texture: str  # y0 - 1 줄 벽
    floor: str = FLOOR_NORMAL

    def contains_x(self, x: float) -> bool:
        return self.x0 <= x < self.x1


@dataclass(frozen=True)
class FloorArea:
    """구간 밖에 더 뚫는 바닥 (옆 통로 등). [x0, x1) × [y0, y1)."""

    x0: int
    x1: int
    y0: int
    y1: int
    floor: str = FLOOR_NORMAL


@dataclass(frozen=True)
class SlideResult:
    """move_and_slide 결과: 옮겨진 위치와, 축마다 벽에 막혔는지."""

    x: float
    y: float
    hit_x: bool
    hit_y: bool


# ---------------------------------------------------------------- 지도
@dataclass(frozen=True)
class MapGrid:
    """칸 배열. 칸 (cx, cy)의 값은 cells[(cy - y_min) * width + (cx - x_min)]에 있다."""

    x_min: int
    y_min: int
    width: int
    height: int
    cells: bytes  # EMPTY(바닥) 또는 텍스처 번호 + 1
    stairs: bytes  # 바닥 칸이 계단이면 1
    textures: tuple[str, ...]

    # ------------------------------------------------------------ 칸 조회
    def _index(self, cx: int, cy: int) -> int:
        """칸의 배열 위치. 지도 밖이면 -1."""
        gx = cx - self.x_min
        gy = cy - self.y_min
        if 0 <= gx < self.width and 0 <= gy < self.height:
            return gy * self.width + gx
        return -1

    def is_wall(self, cx: int, cy: int) -> bool:
        index = self._index(cx, cy)
        return index < 0 or self.cells[index] != EMPTY

    def texture_at(self, cx: int, cy: int) -> str | None:
        """벽 칸의 텍스처 이름. 바닥이면 None, 지도 밖이면 기본 벽."""
        index = self._index(cx, cy)
        if index < 0:
            return DEFAULT_WALL
        code = self.cells[index]
        return None if code == EMPTY else self.textures[code - 1]

    def code_of(self, texture: str) -> int:
        """텍스처 이름의 칸 값 (그리는 쪽이 칸 값으로 텍스처를 찾을 때 쓴다)."""
        return self.textures.index(texture) + 1

    def is_stairs(self, x: float, y: float) -> bool:
        """월드 위치 (x, y)가 계단 바닥 위인지."""
        index = self._index(math.floor(x), math.floor(y))
        return index >= 0 and self.stairs[index] == 1

    # ------------------------------------------------------------ 이동
    def move_and_slide(
        self, x: float, y: float, dx: float, dy: float, radius: float
    ) -> SlideResult:
        """반지름 radius인 몸을 (dx, dy)만큼 옮긴다. 벽에 막힌 축만 멈추고 다른 축은 미끄러진다.

        x축과 y축을 따로 옮기고, 한 번에 COLLISION_SUBSTEP보다 길면 나눠 옮겨 벽을 뚫지 않는다.
        이미 벽과 겹쳐 있는 쪽은 막지 않는다 (밀려 들어간 경우에도 빠져나올 수 있게).
        """
        longest = max(abs(dx), abs(dy))
        steps = max(1, math.ceil(longest / config.COLLISION_SUBSTEP))
        step_x, step_y = dx / steps, dy / steps
        hit_x = hit_y = False
        for _ in range(steps):
            x, blocked = self._slide_x(x, y, step_x, radius)
            hit_x = hit_x or blocked
            y, blocked = self._slide_y(x, y, step_y, radius)
            hit_y = hit_y or blocked
        return SlideResult(x, y, hit_x, hit_y)

    def _slide_x(
        self, x: float, y: float, step: float, radius: float
    ) -> tuple[float, bool]:
        if step == 0.0:
            return x, False
        rows = _span(y, radius)
        edge = radius if step > 0 else -radius
        old_col = _edge_cell(x + edge, step)
        new_col = _edge_cell(x + step + edge, step)
        if new_col != old_col and any(self.is_wall(new_col, row) for row in rows):
            # 벽면에 딱 붙인다: 오른쪽으로 갔으면 벽 칸의 왼쪽 면, 왼쪽으로 갔으면 오른쪽 면
            return (new_col - radius if step > 0 else new_col + 1 + radius), True
        return x + step, False

    def _slide_y(
        self, x: float, y: float, step: float, radius: float
    ) -> tuple[float, bool]:
        if step == 0.0:
            return y, False
        cols = _span(x, radius)
        edge = radius if step > 0 else -radius
        old_row = _edge_cell(y + edge, step)
        new_row = _edge_cell(y + step + edge, step)
        if new_row != old_row and any(self.is_wall(col, new_row) for col in cols):
            return (new_row - radius if step > 0 else new_row + 1 + radius), True
        return y + step, False


def _span(center: float, radius: float) -> range:
    """center ± radius 구간이 걸치는 칸 번호들 (면에 딱 붙은 칸은 빼고)."""
    return range(
        math.floor(center - radius + EPSILON), math.floor(center + radius - EPSILON) + 1
    )


def _edge_cell(edge: float, step: float) -> int:
    """앞쪽 가장자리가 들어가 있는 칸. 면에 딱 붙은 경우는 아직 들어가지 않은 것으로 본다."""
    if step > 0:
        return math.floor(edge - EPSILON)
    return math.floor(edge + EPSILON)


# ---------------------------------------------------------------- 지도 만들기
def build_grid(
    segments: Sequence[Segment],
    extra_floors: Iterable[FloorArea] = (),
    pillars: Iterable[Cell] = (),
    overrides: Mapping[Cell, str] | None = None,
) -> MapGrid:
    """통로 구간들로 지도를 만든다. overrides는 {칸: 텍스처} (표지판·문)."""
    floors = _collect_floors(segments, extra_floors)
    walls = _wall_rows(segments, floors)
    for cell in pillars:
        floors.pop(cell, None)
        walls[cell] = DEFAULT_WALL
    walls.update(overrides or {})
    xs = [cx for cx, _ in floors]
    ys = [cy for _, cy in floors]
    x_min, x_max = min(xs) - 1, max(xs) + 1
    y_min, y_max = min(ys) - 1, max(ys) + 1
    width, height = x_max - x_min + 1, y_max - y_min + 1
    textures = _texture_list(walls.values())
    cells = bytearray(width * height)
    stairs = bytearray(width * height)
    for gy in range(height):
        for gx in range(width):
            cell = (gx + x_min, gy + y_min)
            index = gy * width + gx
            if cell in floors:
                stairs[index] = 1 if floors[cell] == FLOOR_STAIRS else 0
            else:
                cells[index] = textures.index(walls.get(cell, DEFAULT_WALL)) + 1
    return MapGrid(x_min, y_min, width, height, bytes(cells), bytes(stairs), textures)


def _collect_floors(
    segments: Sequence[Segment], extra_floors: Iterable[FloorArea]
) -> dict[Cell, str]:
    """{바닥 칸: 바닥 종류}. 여러 구간이 겹치면 먼저 적은 쪽의 종류를 쓴다."""
    floors: dict[Cell, str] = {}
    for area in (*segments, *extra_floors):
        if area.floor not in FLOOR_KINDS:
            raise ValueError(f"알 수 없는 바닥 종류: {area.floor}")
        for cx in range(area.x0, area.x1):
            for cy in range(area.y0, area.y1):
                floors.setdefault((cx, cy), area.floor)
    if not floors:
        raise ValueError("바닥 칸이 하나도 없습니다.")
    return floors


def _wall_rows(
    segments: Sequence[Segment], floors: Mapping[Cell, str]
) -> dict[Cell, str]:
    """구간마다 왼벽(y1 줄)·오른벽(y0 - 1 줄) 텍스처를 정한다. 먼저 정한 쪽이 이기고, 바닥은 건너뛴다."""
    walls: dict[Cell, str] = {}
    for segment in segments:
        for cx in range(segment.x0, segment.x1):
            for cell, texture in (
                ((cx, segment.y1), segment.left_texture),
                ((cx, segment.y0 - 1), segment.right_texture),
            ):
                if cell not in floors:
                    walls.setdefault(cell, texture)
    return walls


def _texture_list(used: Iterable[str]) -> tuple[str, ...]:
    """칸 값으로 쓸 텍스처 목록 (기본 벽이 1번). 칸 값은 1바이트라 255개까지."""
    names = [DEFAULT_WALL]
    for name in used:
        if name not in names:
            names.append(name)
    if len(names) > 255:
        raise ValueError("벽 텍스처 종류가 너무 많습니다 (최대 255).")
    return tuple(names)
