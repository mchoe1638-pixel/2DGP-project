"""행인: 플레이어와 같은 방향(+x)을 보고 걸어가는 배경 사람.

장애물이 아니라 길 풍경이다. 충돌 몸체가 없어서 부딪히지 않고, 효과도 없고, 미니맵에도 나오지 않는다.
플레이어가 뒤로 PEDESTRIAN_WAKE_DIST 안에 올 때까지는 선 채로 있다가, 그때부터 종류마다 정해진
속도로 +x 쪽으로 걷는다. PEDESTRIAN_WALK_DISTANCE만큼 걸으면 그 자리에 서고, 플레이어에게서
PEDESTRIAN_FADE_NEAR 넘게 떨어졌을 때 서서히 사라진다(눈앞에서는 사라지지 않는다). 걸음은 모두
걷기 최고 속도보다 느려서 플레이어는 걷기만 해도 앞지르고, 뒤에서 가까이 다가오면 옆으로 비켜서
길을 터 준다.

그림은 뒷모습(npc_<이름>_back)이다. 아직 manifest에 없으면 앞모습(npc_<이름>_front)으로 대신 그린다.
"""

import math

import config
import game_framework
import game_world
import resource
from game_object import Billboard, GameObject, natural_height
from map_grid import MapGrid
from player import Player
from resource import Sprite

BACK_MISSING = "앞모습 그림으로 대신 그린다"  # 뒷모습 그림이 manifest에 없을 때 로그에 적는 대신 하는 일


def walker_sheet(name: str) -> Sprite:
    """행인 name의 몸 시트. 뒷모습이 manifest에 없으면 앞모습으로 대신한다."""
    back = resource.find_sprite(f"npc_{name}_back", BACK_MISSING)
    if back is not None:
        return back
    return resource.get_sprite(f"npc_{name}_front")


class Pedestrian(GameObject):
    """같은 방향으로 걷는 배경 사람 한 명. name은 config.PEDESTRIAN_SPEEDS의 키다."""

    def __init__(
        self,
        name: str,
        x: float,
        y: float,
        grid: MapGrid,
        player: Player,
        index: int = 0,
    ) -> None:
        self.name = name
        self.x = float(x)
        self.y = float(y)
        self.grid = grid
        self.player = player
        self.alpha = 1.0
        self._speed = config.PEDESTRIAN_SPEEDS[name]
        self._body = walker_sheet(name)
        self.frame = float(index % self._body.frames)  # 사람마다 발 모양이 어긋나게 시작한다
        self._awake = False  # 걷기 시작했다
        self._walked = 0.0  # 걷기 시작한 뒤 나아간 거리(m). 벽에 막혀도 간 만큼 센다
        self._fade_time = 0.0  # 사라지기 시작한 뒤 흐른 시간(초)

    # ------------------------------------------------------------ 움직임
    def update(self) -> None:
        self.step(game_framework.frame_time)

    def step(self, dt: float) -> None:
        """dt초만큼 나아간다: 깨어날 때를 보고, 걷고, 다 걸었으면 서서히 사라진다."""
        if not self._awake:
            self._awake = self.player.x >= self.x - config.PEDESTRIAN_WAKE_DIST
            if not self._awake:
                return
        self._walk(dt)
        if self._fade_time > 0.0 or self._is_done():  # 사라지기 시작하면 끝까지 간다
            self._fade_out(dt)

    def _is_done(self) -> bool:
        """다 걸었고 플레이어에게서 멀어서, 사라져도 눈에 띄지 않는 때."""
        if self._walked < config.PEDESTRIAN_WALK_DISTANCE:
            return False
        away = math.hypot(self.x - self.player.x, self.y - self.player.y)
        return away >= config.PEDESTRIAN_FADE_NEAR

    def _walk(self, dt: float) -> None:
        """+x 쪽으로 걷고, 다 걸었으면 선다. 벽에 막히면 미끄러지고 발도 멈춘다."""
        walking = self._walked < config.PEDESTRIAN_WALK_DISTANCE
        ahead = self._speed * dt if walking else 0.0
        moved = self.grid.move_and_slide(
            self.x, self.y, ahead, self._sidestep(dt), config.NPC_RADIUS
        )
        travelled = math.hypot(moved.x - self.x, moved.y - self.y)  # 실제로 움직인 거리
        self.x, self.y = moved.x, moved.y
        self._walked += ahead  # 벽에 막혀도 가려던 만큼 센다
        steps = travelled / config.PEDESTRIAN_STRIDE
        self.frame = (self.frame + steps) % self._body.frames

    def _sidestep(self, dt: float) -> float:
        """뒤에서 플레이어가 가까이 다가오면 그 줄에서 벗어나는 옆걸음(m). 평소에는 0."""
        behind = self.x - self.player.x  # 플레이어보다 앞에 있으면 0 이상
        if not 0.0 <= behind <= config.PEDESTRIAN_YIELD_DIST:
            return 0.0
        offset = self.y - self.player.y
        room = config.PEDESTRIAN_YIELD_GAP - abs(offset)  # 더 벌려야 하는 간격
        if room <= 0.0:
            return 0.0
        side = 1.0 if offset >= 0.0 else -1.0  # 플레이어 줄에서 먼 쪽으로 비킨다
        return side * min(config.PEDESTRIAN_YIELD_SPEED * dt, room)

    def _fade_out(self, dt: float) -> None:
        self._fade_time += dt
        self.alpha = max(0.0, 1.0 - self._fade_time / config.NPC_FADE_TIME)
        if self.alpha <= 0.0:
            game_world.remove_object(self)

    # ------------------------------------------------------------ 그리기
    def get_billboard(self) -> Billboard:
        return Billboard(
            self._body,
            int(self.frame),
            self.x,
            self.y,
            0.0,
            natural_height(self._body),
            alpha=self.alpha,
        )
