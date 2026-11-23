"""홀로 서 있는 장애물: 관광객·전단지 알바·상사.

모두 같은 바탕(Npc)을 쓴다. 충돌 몸체는 바닥에 선 원기둥(NPC_RADIUS, NPC_HEIGHT)이고,
1인칭 화면에는 플레이어를 마주 보는 빌보드로 보인다. 플레이어가 닿으면 한 번만 효과를 낸 뒤
몸체를 끄고, 볼일이 끝나면 플레이어에게서 멀어지는 쪽으로 걸어 나가며 서서히 사라진다.
효과의 내용만 종류마다 다르다.

닿은 순간 플레이어의 속력이 FALL_SPEED 이상이면 어떤 효과든 거기에 넘어짐(player.fall)이
더해진다. 사람은 점프로 넘을 수 없다: 몸체가 점프 높이보다 훨씬 높아서 옆으로 비켜야 한다.
"""

import math
from enum import Enum

import config
import game_framework
import game_world
import resource
import sound
from game_object import Billboard, Cylinder, GameObject, natural_height
from map_grid import MapGrid, SlideResult
from player import Player
from resource import Sprite, SpriteLookup
from util import clamp, unit_vector

PLAYER_OBSTACLE = "player:obstacle"  # 충돌 그룹: 왼쪽은 플레이어, 오른쪽은 장애물들
NO_MARKER = "머리 위 표시 없이 그린다"  # 표시 그림이 manifest에 없을 때 로그에 적는 대신 하는 일


class Npc(GameObject):
    sheet = ""  # 종류마다 정하는 몸 시트 이름

    def __init__(
        self,
        x: float,
        y: float,
        grid: MapGrid,
        player: Player,
        sprite_lookup: SpriteLookup = resource.get_sprite,
    ) -> None:
        self.x = float(x)
        self.y = float(y)
        self.grid = grid
        self.player = player
        self.active = True  # 아직 부딪히지 않았다 (충돌 원기둥이 켜져 있다)
        self.alpha = 1.0
        self.flip = False  # 그림은 플레이어를 마주 본다. 멀어져 갈 때 뒤집는다
        self.frame = 0.0
        self._body = sprite_lookup(self.sheet)
        self._leaving = False
        self._leave_delay = 0.0  # 걸어 나가기 전에 더 기다릴 시간(초)
        self._leave_dir = (1.0, 0.0)  # 걸어 나가는 방향: 닿은 순간 플레이어에게서 먼 쪽
        self._walked = 0.0  # 걸어 나가기 시작한 뒤 흐른 시간(초). 투명해지는 데 쓴다

    # ------------------------------------------------------------ 충돌
    def get_bb(self) -> Cylinder | None:
        if not self.active:
            return None
        return (self.x, self.y, config.NPC_RADIUS, 0.0, config.NPC_HEIGHT)

    def handle_collision(self, group: str, other: GameObject) -> None:
        if group != PLAYER_OBSTACLE or other is not self.player or not self.active:
            return
        self.active = False
        sound.play_sfx(sound.BUMP)
        # 멈춤·밀림은 속도를 0으로 만들므로, 얼마나 세게 부딪혔는지는 효과 전에 읽는다
        hit_hard = self.player.falls_on_impact
        self.affect(self.player)
        if hit_hard:
            self.player.fall()

    def affect(self, player: Player) -> None:
        """닿았을 때 플레이어에게 거는 효과 (종류마다 덮어쓴다)."""

    # ------------------------------------------------------------ 움직임
    def leave(self, delay: float = 0.0) -> None:
        """delay초 기다렸다가 플레이어에게서 멀어지는 쪽으로 걸어 나가며 사라진다."""
        self._leaving = True
        self._leave_delay = delay
        self._leave_dir = unit_vector(self.x - self.player.x, self.y - self.player.y)

    def _move(self, dx: float, dy: float) -> SlideResult:
        """벽에 막히면 미끄러지며 (dx, dy)만큼 가려 한다. 막힌 축은 결과에 표시된다."""
        moved = self.grid.move_and_slide(self.x, self.y, dx, dy, config.NPC_RADIUS)
        self.x, self.y = moved.x, moved.y
        return moved

    def _walk_off(self, dt: float) -> None:
        waited = min(self._leave_delay, dt)
        self._leave_delay -= waited
        walking = dt - waited
        if walking <= 0.0:
            return
        self.flip = True
        self._walked += walking
        step = config.NPC_EXIT_SPEED * walking
        self._move(self._leave_dir[0] * step, self._leave_dir[1] * step)
        self.alpha = max(0.0, 1.0 - self._walked / config.NPC_FADE_TIME)
        if self.alpha <= 0.0:
            game_world.remove_object(self)

    def distance_to_player(self) -> float:
        """바닥 위에서 플레이어까지의 거리(m)."""
        return math.hypot(self.player.x - self.x, self.player.y - self.y)

    def behave(self, dt: float) -> None:
        """서 있는 동안 하는 일 (종류마다 덮어쓴다)."""

    def step(self, dt: float) -> None:
        self.frame = self._body.next_frame(self.frame, dt)
        if self._leaving:
            self._walk_off(dt)
        else:
            self.behave(dt)

    def update(self) -> None:
        self.step(game_framework.frame_time)

    # ------------------------------------------------------------ 그리기
    def frame_index(self) -> int:
        return int(self.frame)

    def head_marker(self) -> tuple[Sprite, int] | None:
        """머리 위에 띄울 표시 (그림, 칸 번호). 없으면 None (종류마다 덮어쓴다)."""
        return None

    def get_billboard(self) -> Billboard:
        return Billboard(
            self._body,
            self.frame_index(),
            self.x,
            self.y,
            0.0,
            natural_height(self._body),
            self.flip,
            self.alpha,
        )

    def get_billboards(self) -> tuple[Billboard, ...]:
        shown = self.head_marker()
        if shown is None:
            return (self.get_billboard(),)
        sprite, frame = shown
        marker = Billboard(
            sprite,
            frame,
            self.x,
            self.y,
            config.FX_HEAD_Z,
            natural_height(sprite),
            alpha=self.alpha,
        )
        return (self.get_billboard(), marker)


class Tourist(Npc):
    """길을 묻는다: 플레이어는 잠시 붙잡혀 멈추고, 관광객은 그동안 그 자리에 있다가 떠난다.

    서 있는 동안 머리 위에 물음표를 띄우고, 길을 찾는 듯 제자리 둘레(폭 방향 y로 ±TOURIST_WANDER)를
    천천히 서성인다.
    """

    sheet = "npc_tourist_front"

    def __init__(
        self,
        x: float,
        y: float,
        grid: MapGrid,
        player: Player,
        sprite_lookup: SpriteLookup = resource.get_sprite,
    ) -> None:
        super().__init__(x, y, grid, player, sprite_lookup)
        self._home_y = self.y
        self._side = 1.0  # 서성이는 방향: +1은 +y(왼쪽), -1은 -y(오른쪽)
        self._question = resource.find_sprite("fx_question", NO_MARKER)

    def affect(self, player: Player) -> None:
        player.stun(config.TOURIST_STOP_TIME)
        self.leave(config.TOURIST_STOP_TIME)

    def behave(self, dt: float) -> None:
        low = self._home_y - config.TOURIST_WANDER
        high = self._home_y + config.TOURIST_WANDER
        wanted = self.y + self._side * config.TOURIST_WANDER_SPEED * dt
        reached = clamp(low, wanted, high)
        moved = self._move(0.0, reached - self.y)
        if reached != wanted or moved.hit_y:  # 서성이는 범위 끝이나 벽에 닿으면 돌아선다
            self._side = -self._side

    def head_marker(self) -> tuple[Sprite, int] | None:
        return None if self._question is None else (self._question, 0)


class Flyer(Npc):
    """전단지를 건넨다: 플레이어는 멈추지 않고 한동안 느려지고, 전단지 알바는 곧바로 떠난다.

    FLYER_TRIGGER_DIST 안으로 들어오면 길을 막으려고 플레이어의 y를 따라 옆으로 움직인다.
    """

    sheet = "npc_flyer_front"

    def affect(self, player: Player) -> None:
        player.slow(config.FLYER_SLOW_TIME)
        self.leave(0.0)

    def behave(self, dt: float) -> None:
        if self.distance_to_player() > config.FLYER_TRIGGER_DIST:
            return
        gap = self.player.y - self.y
        step = min(abs(gap), config.FLYER_SPEED * dt)  # 목표를 지나쳐 떨지 않게
        self._move(0.0, math.copysign(step, gap))


class BossPhase(Enum):
    WAIT = "wait"  # 제자리에 서서 플레이어가 가까이 오길 기다린다
    WARN = "warn"  # "!"가 깜박이는 동안 제자리에 서 있다
    WALK = "walk"  # 손을 들고 플레이어 쪽으로 걸어온다
    TALK = "talk"  # 붙잡고 잔소리하는 중


class Boss(Npc):
    """경고("!") 뒤 걸어와서 붙잡는다: 플레이어는 멈추고 게이지가 오르고, 상사는 말이 끝나면 떠난다.

    대사 말풍선은 화면에 붙는 HUD가 그리므로 여기서는 소리(BOSS_TALK)만 낸다.
    """

    sheet = "npc_boss_front"

    def __init__(
        self,
        x: float,
        y: float,
        grid: MapGrid,
        player: Player,
        sprite_lookup: SpriteLookup = resource.get_sprite,
    ) -> None:
        super().__init__(x, y, grid, player, sprite_lookup)
        self.phase = BossPhase.WAIT
        self._warn_time = 0.0  # 경고("!")가 뜬 뒤 흐른 시간(초)
        self._exclaim = resource.find_sprite("fx_exclaim", NO_MARKER)

    def affect(self, player: Player) -> None:
        self.phase = BossPhase.TALK
        player.stun(config.BOSS_STOP_TIME)
        player.gauge.add(config.BOSS_GAUGE_ADD)
        sound.play_sfx(sound.BOSS_TALK)
        self.leave(config.BOSS_STOP_TIME)

    def behave(self, dt: float) -> None:
        if self.phase is BossPhase.WAIT:
            self._watch_for_player()
        elif self.phase is BossPhase.WARN:
            self._blink(dt)
        elif self.phase is BossPhase.WALK:
            self._walk_toward_player(dt)

    def _watch_for_player(self) -> None:
        if self.distance_to_player() > config.BOSS_TRIGGER_DIST:
            return
        sound.play_sfx(sound.WARNING)
        self._warn_time = 0.0
        self.phase = BossPhase.WARN

    def _blink(self, dt: float) -> None:
        self._warn_time += dt
        if self._warn_time >= config.BOSS_EXCLAIM_TIME:
            self.phase = BossPhase.WALK

    def _walk_toward_player(self, dt: float) -> None:
        dir_x, dir_y = unit_vector(self.player.x - self.x, self.player.y - self.y)
        step = config.BOSS_SPEED * dt
        self._move(dir_x * step, dir_y * step)

    def frame_index(self) -> int:
        """서서 기다리는 동안은 팔을 내린 첫 칸, 걸어오며 말하는 동안은 팔을 든 둘째 칸."""
        return 0 if self.phase in (BossPhase.WAIT, BossPhase.WARN) else 1

    def head_marker(self) -> tuple[Sprite, int] | None:
        if self.phase is not BossPhase.WARN or self._exclaim is None:
            return None
        blink = int(self._warn_time / config.FX_FRAME_PERIOD)
        return self._exclaim, blink % self._exclaim.frames
