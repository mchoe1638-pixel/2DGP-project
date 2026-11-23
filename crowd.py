"""인파: 뚫고 지날 수 없는 사람 벽.

통로 폭 전체를 사람들이 줄지어 막는다 (한 줄이 CROWD_LANE_MAX 이하라 몸 사이로 비집고 지날 수
없다). 닿으면 가던 방향의 반대로 밀려난다 (속력이 FALL_SPEED 이상이었으면 넘어지기까지 한다).
2.5초 주기의 마지막 1초 동안은 한 줄에 틈이 열려서, 그 줄의 사람은 충돌이 꺼지고 벽 쪽으로 비켜선다.
틈이 열리는 줄은 주기마다 양 끝에서 번갈아 안쪽으로 옮겨 간다. 인파는 월드에서 사라지지 않는다.

사람 한 명이 CrowdMember 오브젝트이고, 틈을 돌리는 시계는 보이지도 부딪히지도 않는 Crowd 오브젝트다.
"""

import math
from collections.abc import Sequence

import config
import game_framework
import resource
import sound
from game_object import Billboard, Cylinder, GameObject, natural_height
from obstacle import PLAYER_OBSTACLE
from player import Player
from resource import Sprite, SpriteLookup
from util import clamp, smoothstep, unit_vector

COMMUTER_SHEETS = (
    "npc_commuter1_front",
    "npc_commuter2_front",
    "npc_commuter3_front",
)
CLOSED_TIME = config.CROWD_GAP_PERIOD - config.CROWD_GAP_OPEN_TIME  # 주기 중 닫힌 시간


def gap_openness(into: float) -> float:
    """주기 시작에서 into초 지난 때 틈이 얼마나 열렸는지: 0(닫힘)~1(활짝).

    열린 구간(CLOSED_TIME 이후)의 처음과 끝 EASE초 동안 부드럽게 열리고 닫힌다.
    """
    since_open = into - CLOSED_TIME
    until_close = config.CROWD_GAP_PERIOD - into
    return smoothstep(min(since_open, until_close) / config.CROWD_GAP_EASE)


def open_order(lanes: int) -> tuple[int, ...]:
    """틈이 열리는 줄의 차례: 양 끝에서 번갈아 안쪽으로 (0, 끝, 1, 끝 - 1, ...)."""
    order: list[int] = []
    low, high = 0, lanes - 1
    while low <= high:
        order.append(low)
        if low != high:
            order.append(high)
        low, high = low + 1, high - 1
    return tuple(order)


def aside_y(home_y: float, y_min: float, y_max: float) -> float:
    """틈이 열릴 때 비켜서는 자리: 더 가까운 벽 쪽으로 CROWD_GAP_SHIFT만큼 (벽에 박히지 않게)."""
    toward_low = home_y - y_min <= y_max - home_y
    shift = -config.CROWD_GAP_SHIFT if toward_low else config.CROWD_GAP_SHIFT
    return clamp(
        y_min + config.CROWD_RADIUS, home_y + shift, y_max - config.CROWD_RADIUS
    )


class CrowdMember(GameObject):
    """인파 속 한 사람. 제자리에 서 있다가 자기 줄에 틈이 열리면 벽 쪽으로 비켜선다."""

    def __init__(
        self,
        x: float,
        home_y: float,
        walls: tuple[float, float],
        body: Sprite,
        index: int,
        player: Player,
    ) -> None:
        self.x = float(x)
        self.home_y = float(home_y)
        self.player = player
        self.openness = 0.0  # 비켜선 정도: 0(제자리)~1(다 비킴). Crowd 시계가 정한다
        self.passable = False  # 틈이 열려 있어 부딪히지 않는다. Crowd 시계가 정한다
        # 이웃끼리 한 칸씩 어긋나게 시작해서 인파 전체가 한꺼번에 깜박이지 않게 한다
        self.frame = float(index)
        self._body = body
        self._aside_y = aside_y(self.home_y, *walls)

    @property
    def y(self) -> float:
        """지금 서 있는 y: 틈이 열리면 비켜선 자리로 옮겨 간다."""
        return self.home_y + (self._aside_y - self.home_y) * self.openness

    def apply_gap(self, openness: float, passable: bool) -> None:
        self.openness = openness
        self.passable = passable

    # ------------------------------------------------------------ 충돌
    def get_bb(self) -> Cylinder | None:
        if self.passable:
            return None  # 닫혀 있는 동안은 제자리(home_y)에 서 있으므로 y는 home_y다
        return (self.x, self.home_y, config.CROWD_RADIUS, 0.0, config.CROWD_HEIGHT)

    def handle_collision(self, group: str, other: GameObject) -> None:
        if group != PLAYER_OBSTACLE or other is not self.player or self.passable:
            return
        sound.play_sfx(sound.PUSH)
        # 밀리면 속도가 0이 되므로, 세게 부딪혔는지와 밀 방향은 밀기 전에 읽는다
        hit_hard = self.player.falls_on_impact
        dir_x, dir_y = self._push_direction()
        self.player.push(dir_x, dir_y, config.CROWD_PUSH)
        if hit_hard:
            self.player.fall()

    def _push_direction(self) -> tuple[float, float]:
        """밀어낼 방향: 플레이어가 가던 쪽의 반대. 서 있었다면 이 사람에게서 멀어지는 쪽."""
        away = unit_vector(
            self.player.x - self.x, self.player.y - self.home_y, fallback=(-1.0, 0.0)
        )
        return unit_vector(-self.player.vx, -self.player.vy, fallback=away)

    # ------------------------------------------------------------ 움직임·그리기
    def update(self) -> None:
        self.frame = self._body.next_frame(self.frame, game_framework.frame_time)

    def get_billboard(self) -> Billboard:
        return Billboard(
            self._body,
            int(self.frame) % self._body.frames,
            self.x,
            self.y,
            0.0,
            natural_height(self._body),
        )


class Crowd(GameObject):
    """인파의 틈 시계: 주기마다 한 줄씩 틈을 열도록 사람들에게 알린다."""

    def __init__(self, members: Sequence[CrowdMember]) -> None:
        if not members:
            raise ValueError("인파에는 사람이 한 명 이상 있어야 합니다.")
        self.members = tuple(members)
        self._order = open_order(len(self.members))
        self._time = 0.0  # 틈이 닫힌 채로 시작한다

    def step(self, dt: float) -> None:
        self._time += dt
        cycle, into = divmod(self._time, config.CROWD_GAP_PERIOD)
        opening = self._order[int(cycle) % len(self._order)]
        for index, member in enumerate(self.members):
            if index == opening:
                member.apply_gap(gap_openness(into), into >= CLOSED_TIME)
            else:
                member.apply_gap(0.0, False)

    def update(self) -> None:
        self.step(game_framework.frame_time)


def make_crowd(
    x: float,
    y_min: float,
    y_max: float,
    count: int,
    player: Player,
    sprite_lookup: SpriteLookup = resource.get_sprite,
) -> list[GameObject]:
    """[y_min, y_max) 폭 전체를 막는 인파를 만든다: 틈 시계 하나와 줄마다 사람 한 명.

    한 줄이 CROWD_LANE_MAX를 넘으면 몸 사이로 지날 수 있으므로, 사람 수는 count와 폭을 다
    덮는 데 필요한 줄 수 중 큰 쪽이다. 시계가 사람들보다 먼저 갱신되도록 맨 앞에 둔다.
    """
    width = y_max - y_min
    if width <= 0.0:
        raise ValueError(f"인파가 막을 통로 폭이 없습니다: y = {y_min} ~ {y_max}")
    lanes = max(count, math.ceil(width / config.CROWD_LANE_MAX))
    slot = width / lanes
    members = [
        CrowdMember(
            x,
            y_min + (index + 0.5) * slot,
            (y_min, y_max),
            sprite_lookup(COMMUTER_SHEETS[index % len(COMMUTER_SHEETS)]),
            index,
            player,
        )
        for index in range(lanes)
    ]
    return [Crowd(members), *members]
