"""스테이지: 원본 데이터(stage_data.py)를 격자 지도와 배치표로 바꾼다.

- 통로 구간은 map_grid.Segment로, 옆 통로는 구간 밖에 더 뚫는 바닥으로 바꿔 격자 지도를 만든다.
- 기둥은 바닥 칸을 벽으로, 표지판 칸과 골인 문 칸은 그 벽 칸의 텍스처를 바꾼다.
- 장애물·행인·아이템·장식·개찰구는 배치표(frozen dataclass)로 남긴다. 실제 오브젝트는 플레이 모드가 만든다.

Stage는 만든 뒤 바뀌지 않는다. 같은 번호로 다시 만들면 같은 스테이지가 나온다.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import config
import stage_data
from map_grid import Cell, FloorArea, MapGrid, Segment, build_grid

OBSTACLE_KINDS = (
    stage_data.TOURIST,
    stage_data.FLYER,
    stage_data.BOSS,
    stage_data.CROWD,
)
ITEM_KINDS = (stage_data.BREATH, stage_data.GUM, stage_data.SHORTCUT)
ITEM_HEIGHTS = (stage_data.ITEM_FLOOR, stage_data.ITEM_HIGH)
SIDES = (stage_data.SIDE_LEFT, stage_data.SIDE_RIGHT)


# ---------------------------------------------------------------- 배치표
@dataclass(frozen=True)
class ObstacleSpec:
    """장애물 한 줄. y가 None이면 통로 폭 전체를 쓴다 (인파). count는 인파의 사람 수."""

    kind: str
    x: float
    y: float | None
    count: int = 1


@dataclass(frozen=True)
class PedestrianSpec:
    """행인 한 줄: name 종류가 (x, y)에서 걷기 시작해 +x 쪽으로 걸어간다."""

    name: str
    x: float
    y: float


@dataclass(frozen=True)
class ItemSpec:
    """아이템 한 줄. y가 None이면 옆 통로 입구에 둔다 (지름길). height는 ITEM_FLOOR / ITEM_HIGH."""

    kind: str
    x: float
    y: float | None
    height: str


@dataclass(frozen=True)
class SidePassage:
    """본 통로 옆으로 뚫린 통로. [x0, x1) × [y0, y1)가 바닥이다."""

    x0: int
    x1: int
    y0: int
    y1: int
    side: str  # SIDE_LEFT / SIDE_RIGHT

    @property
    def center_y(self) -> float:
        return (self.y0 + self.y1) / 2


@dataclass(frozen=True)
class GateSpec:
    """개찰구: x 위치에 통로 폭을 lanes칸으로 나눈 문. open_lanes 번째 칸만 열려 있다."""

    x: float
    lanes: int
    open_lanes: tuple[int, ...]
    height: float  # 닫힌 칸 가로막의 높이(m)


@dataclass(frozen=True)
class DecoSpec:
    """장식 한 줄: sprite 그림을 x 위치의 place(벽 쪽)에 붙인다."""

    sprite: str
    x: float
    place: str


@dataclass(frozen=True)
class Stage:
    number: int
    length: float  # 스테이지 전체 길이(m)
    goal_x: float  # 플레이어 x가 이 값 이상이면 골인
    player_start: tuple[float, float, float]  # x, y, yaw
    base_rate: float  # 게이지가 오르는 기본 속도(%/s)
    grid: MapGrid
    segments: tuple[Segment, ...]
    side_passage: SidePassage | None
    gate: GateSpec | None
    goal_door: Cell
    obstacles: tuple[ObstacleSpec, ...]
    pedestrians: tuple[PedestrianSpec, ...]
    items: tuple[ItemSpec, ...]
    deco: tuple[DecoSpec, ...]

    def segment_at(self, x: float) -> Segment:
        """x 위치를 덮는 통로 구간. 구간 밖이면 가장 가까운 끝 구간."""
        for segment in self.segments:
            if segment.contains_x(x):
                return segment
        return self.segments[0] if x < self.segments[0].x0 else self.segments[-1]


# ---------------------------------------------------------------- 만들기
def build_stage(number: int) -> Stage:
    """number번 스테이지를 만든다. 데이터가 없으면 KeyError, 데이터가 잘못됐으면 ValueError."""
    data = stage_data.get_stage_data(number)
    segments = tuple(Segment(*row) for row in data["segments"])
    if not segments:
        raise ValueError(f"스테이지 {number}에 통로 구간이 없습니다.")
    side_passage = _side_passage(data.get("side_passage"), segments)
    extra_floors = (
        ()
        if side_passage is None
        else (
            FloorArea(side_passage.x0, side_passage.x1, side_passage.y0, side_passage.y1),
        )
    )
    goal_door: Cell = tuple(data["goal_door"])  # type: ignore[assignment]
    overrides = _sign_cells(data.get("wall_signs", ()), segments)
    overrides[goal_door] = stage_data.TEX_DOOR_WC
    pillars = [tuple(cell) for cell in data.get("pillars", ())]
    grid = build_grid(segments, extra_floors, pillars, overrides)  # type: ignore[arg-type]
    start_x, start_y, start_yaw = data["player_start"]
    if grid.is_wall(int(start_x), int(start_y)):
        raise ValueError(f"스테이지 {number}의 시작 위치가 벽 안입니다.")
    return Stage(
        number=number,
        length=float(data["length"]),
        goal_x=float(data["goal_x"]),
        player_start=(float(start_x), float(start_y), float(start_yaw)),
        base_rate=float(data["base_rate"]),
        grid=grid,
        segments=segments,
        side_passage=side_passage,
        gate=_gate(data.get("gates")),
        goal_door=goal_door,
        obstacles=tuple(_obstacle(row) for row in data.get("obstacles", ())),
        pedestrians=_pedestrians(data.get("pedestrians", ()), grid),
        items=tuple(_item(row) for row in data.get("items", ())),
        deco=tuple(DecoSpec(*row) for row in data.get("deco", ())),
    )


def _segment_for(x: float, segments: Sequence[Segment]) -> Segment:
    for segment in segments:
        if segment.contains_x(x):
            return segment
    raise ValueError(f"x = {x} 위치를 덮는 통로 구간이 없습니다.")


def _side_passage(
    raw: Mapping[str, Any] | None, segments: Sequence[Segment]
) -> SidePassage | None:
    """옆 통로: 본 통로의 벽 줄부터 바깥으로 width칸."""
    if raw is None:
        return None
    side = raw["y_side"]
    if side not in SIDES:
        raise ValueError(f"옆 통로 방향은 {SIDES} 중 하나여야 합니다: {side}")
    x0, x1, width = int(raw["x0"]), int(raw["x1"]), int(raw["width"])
    host = _segment_for(x0, segments)
    if side == stage_data.SIDE_LEFT:
        return SidePassage(x0, x1, host.y1, host.y1 + width, side)
    return SidePassage(x0, x1, host.y0 - width, host.y0, side)


def _sign_cells(
    rows: Sequence[tuple[int, str]], segments: Sequence[Segment]
) -> dict[Cell, str]:
    """표지판 자리 (x, 왼쪽/오른쪽) → 그 x 구간의 왼벽(y1 줄)·오른벽(y0 - 1 줄) 칸."""
    cells: dict[Cell, str] = {}
    for x, side in rows:
        if side not in SIDES:
            raise ValueError(f"표지판 방향은 {SIDES} 중 하나여야 합니다: {side}")
        segment = _segment_for(x, segments)
        row = segment.y1 if side == stage_data.SIDE_LEFT else segment.y0 - 1
        cells[(int(x), row)] = stage_data.TEX_WALL_SIGN_WC
    return cells


def _gate(raw: Mapping[str, Any] | None) -> GateSpec | None:
    if raw is None:
        return None
    lanes = int(raw["lanes"])
    open_lanes = tuple(int(lane) for lane in raw["open_lanes"])
    if any(not 0 <= lane < lanes for lane in open_lanes):
        raise ValueError(f"열린 개찰구 칸 번호는 0 ~ {lanes - 1}이어야 합니다: {open_lanes}")
    return GateSpec(float(raw["x"]), lanes, open_lanes, float(raw["height"]))


def _obstacle(row: Sequence[Any]) -> ObstacleSpec:
    kind, x, y, *rest = row
    if kind not in OBSTACLE_KINDS:
        raise ValueError(f"알 수 없는 장애물: {kind}")
    count = int(rest[0]) if rest else 1
    return ObstacleSpec(kind, float(x), None if y is None else float(y), count)


def _pedestrians(
    rows: Sequence[Sequence[Any]], grid: MapGrid
) -> tuple[PedestrianSpec, ...]:
    """행인 배치표. 알 수 없는 종류나 벽 안에서 시작하는 행인은 데이터 오류다."""
    specs: list[PedestrianSpec] = []
    for name, x, y in rows:
        if name not in config.PEDESTRIAN_SPEEDS:
            raise ValueError(f"알 수 없는 행인: {name}")
        if grid.is_wall(int(x), int(y)):
            raise ValueError(f"행인 {name}의 자리가 벽 안입니다: x = {x}, y = {y}")
        specs.append(PedestrianSpec(name, float(x), float(y)))
    return tuple(specs)


def _item(row: Sequence[Any]) -> ItemSpec:
    kind, x, y, height = row
    if kind not in ITEM_KINDS:
        raise ValueError(f"알 수 없는 아이템: {kind}")
    if height not in ITEM_HEIGHTS:
        raise ValueError(f"아이템 높이는 {ITEM_HEIGHTS} 중 하나여야 합니다: {height}")
    return ItemSpec(kind, float(x), None if y is None else float(y), height)
