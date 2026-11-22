"""홀로 서 있는 장애물: 관광객·전단지 알바·상사.

모두 같은 바탕(Npc)을 쓴다. 발치에 서 있는 충돌 상자를 가지고, 플레이어가 닿으면 한 번만 효과를 낸 뒤
상자를 끄고, 볼일이 끝나면 오른쪽으로 걸어 나가며 서서히 사라진다. 효과의 내용만 종류마다 다르다.
달리다가 닿았으면 어떤 효과든 거기에 넘어짐(player.fall)이 더해진다.
"""

from enum import Enum

import config
import fx
import game_framework
import game_world
import resource
import sound
from camera import Camera
from game_object import GameObject
from player import Player
from resource import SpriteLookup

PLAYER_OBSTACLE = "player:obstacle"  # 충돌 그룹: 왼쪽은 플레이어, 오른쪽은 장애물들


class Npc(GameObject):
    sheet = ""  # 종류마다 정하는 스프라이트 시트 이름

    def __init__(
        self,
        x: float,
        camera: Camera,
        player: Player,
        sprite_lookup: SpriteLookup = resource.get_sprite,
    ) -> None:
        self.x = float(x)
        self.active = True  # 아직 부딪히지 않았다 (충돌 상자가 켜져 있다)
        self.alpha = 1.0
        self.flip = False  # 그림은 왼쪽을 보고 있다. 오른쪽으로 걸어 나갈 때 뒤집는다
        self.frame = 0.0
        self.camera = camera
        self.player = player
        self._lookup = sprite_lookup
        self._leaving = False
        self._leave_delay = 0.0  # 걸어 나가기 전에 더 기다릴 시간(초)
        self._walked = 0.0  # 걸어 나가기 시작한 뒤 흐른 시간(초). 투명해지는 데 쓴다

    def _sprite(self) -> resource.Sprite:
        return self._lookup(self.sheet)

    # ------------------------------------------------------------ 충돌
    def get_bb(self) -> tuple[float, float, float, float] | None:
        if not self.active:
            return None
        return (
            self.x - config.NPC_BB_HALF_W,
            config.GROUND_Y,
            self.x + config.NPC_BB_HALF_W,
            config.GROUND_Y + config.NPC_BB_HEIGHT,
        )

    def handle_collision(self, group: str, other: GameObject) -> None:
        if group != PLAYER_OBSTACLE or other is not self.player or not self.active:
            return
        self.active = False
        sound.play_sfx(sound.BUMP)
        # 효과가 걸리면 플레이어는 기절해서 달리는 중이 아니게 되므로, 달렸는지는 먼저 본다
        was_running = self.player.is_running()
        self.affect(self.player)
        if was_running:
            self.player.fall()

    def affect(self, player: Player) -> None:
        """닿았을 때 플레이어에게 거는 효과 (종류마다 덮어쓴다)."""

    # ------------------------------------------------------------ 움직임
    def leave(self, delay: float = 0.0) -> None:
        """delay초 기다렸다가 오른쪽으로 걸어 나가며 서서히 사라진다."""
        self._leaving = True
        self._leave_delay = delay

    def _walk_off(self, dt: float) -> None:
        waited = min(self._leave_delay, dt)
        self._leave_delay -= waited
        walking = dt - waited
        if walking <= 0.0:
            return
        self.flip = True
        self._walked += walking
        self.x += config.NPC_EXIT_SPEED * walking
        self.alpha = max(0.0, 1.0 - self._walked / config.NPC_FADE_TIME)
        if self.alpha <= 0.0:
            game_world.remove_object(self)

    def behave(self, dt: float) -> None:
        """서 있는 동안 하는 일 (종류마다 덮어쓴다)."""

    def step(self, dt: float) -> None:
        self.frame = self._sprite().next_frame(self.frame, dt)
        if self._leaving:
            self._walk_off(dt)
        else:
            self.behave(dt)

    def update(self) -> None:
        self.step(game_framework.frame_time)

    # ------------------------------------------------------------ 그리기
    def frame_index(self) -> int:
        return int(self.frame)

    def draw(self) -> None:
        sprite = self._sprite()
        if not self.camera.is_visible(self.x, sprite.frame_w / 2):
            return
        sprite.draw(
            self.camera.to_screen_x(self.x),
            sprite.ground_center_y(),
            self.frame_index(),
            flip=self.flip,
            alpha=self.alpha,
        )


class Tourist(Npc):
    """길을 묻는다: 플레이어는 잠시 붙잡혀 멈추고, 관광객은 그동안 그 자리에 있다가 떠난다."""

    sheet = "npc_tourist"

    def affect(self, player: Player) -> None:
        player.stun(config.TOURIST_STOP_TIME)
        fx.spawn_question(self, self.camera, config.TOURIST_STOP_TIME, self._lookup)
        self.leave(config.TOURIST_STOP_TIME)


class Flyer(Npc):
    """전단지를 건넨다: 플레이어는 멈추지 않고 한동안 느려지고, 전단지 알바는 곧바로 떠난다."""

    sheet = "npc_flyer"

    def affect(self, player: Player) -> None:
        player.slow(config.FLYER_SLOW_TIME)
        fx.spawn_paper(player, self.camera, config.FLYER_SLOW_TIME, self._lookup)
        self.leave(0.0)


class BossPhase(Enum):
    WAIT = "wait"  # 제자리에 서서 플레이어가 가까이 오길 기다린다
    WARN = "warn"  # "!"가 떠 있는 동안 제자리에 서 있다
    WALK = "walk"  # 손을 들고 왼쪽(플레이어 쪽)으로 걸어온다
    TALK = "talk"  # 붙잡고 잔소리하는 중


class Boss(Npc):
    """경고("!") 뒤 걸어와서 붙잡는다: 플레이어는 멈추고 게이지가 오르고, 상사는 말이 끝나면 떠난다."""

    sheet = "npc_boss"

    def __init__(
        self,
        x: float,
        camera: Camera,
        player: Player,
        sprite_lookup: SpriteLookup = resource.get_sprite,
    ) -> None:
        super().__init__(x, camera, player, sprite_lookup)
        self.phase = BossPhase.WAIT
        self._warn_left = 0.0

    def affect(self, player: Player) -> None:
        self.phase = BossPhase.TALK
        player.stun(config.BOSS_STOP_TIME)
        player.gauge.add(config.BOSS_GAUGE_ADD)
        sound.play_sfx(sound.BOSS_TALK)
        fx.spawn_speech(
            self,
            self.camera,
            config.BOSS_SPEECH_TEXT,
            config.BOSS_STOP_TIME,
            self._lookup,
        )
        self.leave(config.BOSS_STOP_TIME)

    def behave(self, dt: float) -> None:
        if self.phase is BossPhase.WAIT:
            self._watch_for_player()
        elif self.phase is BossPhase.WARN:
            self._blink(dt)
        elif self.phase is BossPhase.WALK:
            self._walk_left(dt)

    def _watch_for_player(self) -> None:
        if abs(self.x - self.player.x) >= config.BOSS_WARN_DISTANCE:
            return
        fx.spawn_exclaim(config.BOSS_EXCLAIM_TIME, self._lookup)
        sound.play_sfx(sound.WARNING)
        self._warn_left = config.BOSS_EXCLAIM_TIME
        self.phase = BossPhase.WARN

    def _blink(self, dt: float) -> None:
        self._warn_left -= dt
        if self._warn_left <= 0.0:
            self.phase = BossPhase.WALK

    def _walk_left(self, dt: float) -> None:
        self.x -= config.BOSS_WALK_SPEED * dt
        half_width = self._sprite().frame_w / 2
        if self.x + half_width <= self.camera.x:  # 화면 왼쪽 끝을 완전히 벗어났다
            game_world.remove_object(self)

    def frame_index(self) -> int:
        """서서 기다리는 동안은 팔을 내린 첫 칸, 걸어오며 말하는 동안은 팔을 든 둘째 칸."""
        return 0 if self.phase in (BossPhase.WAIT, BossPhase.WARN) else 1
