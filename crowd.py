"""인파: 뚫고 지날 수 없는 사람 벽.

닿으면 뒤로 밀려난다 (달리다 닿았으면 넘어지기까지 한다). 2.5초 주기의 마지막 1초 동안은 틈이 열려서
충돌 상자가 꺼지고, 가운데 사람들이 위아래로 벌어지며 물러선다. 인파는 월드에서 사라지지 않는다.
"""

import config
import game_framework
import resource
from camera import Camera
from fx import SpriteLookup
from game_object import GameObject
from obstacle import PLAYER_OBSTACLE
from player import Player
from util import smoothstep

COMMUTER_SHEETS = ("npc_commuter1", "npc_commuter2", "npc_commuter3")
CLOSED_TIME = (
    config.CROWD_GAP_PERIOD - config.CROWD_GAP_OPEN_TIME
)  # 한 주기 중 틈이 닫혀 있는 시간


class Crowd(GameObject):
    def __init__(
        self,
        x: float,
        count: int,
        camera: Camera,
        player: Player,
        sprite_lookup: SpriteLookup = resource.get_sprite,
    ) -> None:
        self.x = float(x)
        self.count = count
        self.camera = camera
        self.player = player
        self._lookup = sprite_lookup
        self._clock = 0.0  # 한 주기 안에서 흐른 시간(초). 틈이 닫힌 채로 시작한다
        self._anim_time = 0.0

    @property
    def is_open(self) -> bool:
        return self._clock >= CLOSED_TIME

    def half_width(self) -> float:
        """인파 한가운데에서 가장자리까지."""
        return (self.count - 1) / 2 * config.CROWD_MEMBER_SPACING + config.NPC_BB_HALF_W

    # ------------------------------------------------------------ 충돌
    def get_bb(self) -> tuple[float, float, float, float] | None:
        if self.is_open:
            return None
        half = self.half_width()
        return (
            self.x - half,
            config.GROUND_Y,
            self.x + half,
            config.GROUND_Y + config.CROWD_BB_HEIGHT,
        )

    def handle_collision(self, group: str, other: GameObject) -> None:
        if group != PLAYER_OBSTACLE or other is not self.player:
            return
        was_running = self.player.is_running()
        away = -1 if self.player.x <= self.x else 1  # 온 쪽으로 되돌려 보낸다
        self.player.push(away * config.CROWD_PUSH_DISTANCE)
        if was_running:
            self.player.fall()

    # ------------------------------------------------------------ 움직임
    def step(self, dt: float) -> None:
        self._anim_time += dt
        self._clock = (self._clock + dt) % config.CROWD_GAP_PERIOD

    def update(self) -> None:
        self.step(game_framework.frame_time)

    def openness(self) -> float:
        """틈이 얼마나 벌어졌는지: 0(닫힘)~1(활짝). 열릴 때와 닫힐 때 EASE초 동안 부드럽게 변한다."""
        into_gap = self._clock - CLOSED_TIME
        until_close = config.CROWD_GAP_PERIOD - self._clock
        return smoothstep(min(into_gap, until_close) / config.CROWD_GAP_EASE)

    def _member_offset(self, index: int, openness: float) -> tuple[float, float]:
        """index번째 사람이 틈 때문에 비켜선 (가로, 세로) 거리. 맨 끝 두 사람은 제자리다."""
        if index in (0, self.count - 1):
            return 0.0, 0.0
        centre = (self.count - 1) / 2
        side = (index > centre) - (index < centre)  # 왼쪽 -1, 가운데 0, 오른쪽 1
        shift_x = side * config.CROWD_GAP_SHIFT_X * openness
        shift_y = (-1 if side > 0 else 1) * config.CROWD_GAP_SHIFT_Y * openness
        return shift_x, shift_y

    # ------------------------------------------------------------ 그리기
    def _draw_member(self, index: int, openness: float) -> None:
        sprite = self._lookup(COMMUTER_SHEETS[index % len(COMMUTER_SHEETS)])
        shift_x, lift = self._member_offset(index, openness)
        slot_x = self.x + (index - (self.count - 1) / 2) * config.CROWD_MEMBER_SPACING
        world_x = slot_x + shift_x
        if not self.camera.is_visible(world_x, sprite.frame_w / 2):
            return
        # 이웃끼리 한 칸씩 어긋나게 시작해서 인파 전체가 한꺼번에 깜박이지 않게 한다
        frame = (int(self._anim_time * sprite.fps) + index) % sprite.frames
        sprite.draw(
            self.camera.to_screen_x(world_x), sprite.ground_center_y(lift), frame
        )

    def draw(self) -> None:
        openness = self.openness()
        for index in range(self.count):
            self._draw_member(index, openness)
