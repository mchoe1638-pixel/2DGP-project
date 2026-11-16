"""플레이어: 이동·달리기·점프·기절을 상태 머신으로 구현한다.

상태는 Idle / Walk / Run / Jump / Stunned 이다.
어느 상태로 갈지는 지금 눌려 있는 키 집합에서 매번 새로 계산한다. 그래서 ← → 를 함께 눌러도,
점프 중에 키를 바꿔 눌러도, 기절해 있는 동안 키를 눌러 두어도 끝난 뒤 눌린 키에 맞는 상태로 돌아온다.

참을성 게이지(gauge.Gauge)의 단계가 플레이어의 겉모습과 조작을 바꾼다:
땀(50~) 속도 ×0.9 / 긴장(80~) 달리기 금지 + 뒤뚱 걸음 / 한계(95~) 좌우 반전.
게이지를 흘려보내는 일(step)은 플레이 모드가 맡고, 플레이어는 단계를 읽기만 한다.

장애물(obstacle.py, crowd.py)은 부딪혔을 때 플레이어의 stun(멈춤) / fall(넘어짐) /
slow(느려짐) / push(밀려남)를 부른다. 어떤 장애물이 무엇을 부르는지는 장애물이 정한다.
"""

from collections.abc import Callable

from pico2d import (
    SDL_KEYDOWN,
    SDL_KEYUP,
    SDLK_LEFT,
    SDLK_LSHIFT,
    SDLK_RIGHT,
    SDLK_RSHIFT,
    SDLK_SPACE,
    Event,
)

import config
import fx
import game_framework
import resource
from camera import Camera
from game_object import GameObject
from gauge import Gauge, GaugeStage
from stage_data import Stage
from state_machine import Event as MachineEvent
from state_machine import Predicate, State, StateMachine, Transitions
from util import clamp

INPUT_EVENT = "INPUT"  # ('INPUT', pico2d 키 이벤트)
LAND_EVENT = "LAND"  # ('LAND', None): 점프가 땅에 닿았다
STAGE_EVENT = "STAGE"  # ('STAGE', None): 게이지 단계가 바뀌었다
STUN_EVENT = "STUN"  # ('STUN', None): 장애물에 걸려 꼼짝 못 하게 됐다
WAKE_EVENT = "WAKE"  # ('WAKE', None): 기절이 끝나고 땅 위에 있다

# 키 입력이나 게이지 단계가 바뀌면 걷기/달리기/멈춤을 다시 따져 본다
RECHECK_EVENTS = (INPUT_EVENT, STAGE_EVENT)

CONTROL_KEYS = frozenset({SDLK_LEFT, SDLK_RIGHT, SDLK_LSHIFT, SDLK_RSHIFT})
SHIFT_KEYS = (SDLK_LSHIFT, SDLK_RSHIFT)

# 게이지 단계 -> player_{mood}_* 시트. 실패(100%)는 따로 시트가 없어 한계 시트를 쓴다.
MOOD_BY_STAGE = {
    GaugeStage.CALM: "calm",
    GaugeStage.SWEAT: "sweat",
    GaugeStage.STRAIN: "strain",
    GaugeStage.LIMIT: "limit",
    GaugeStage.FAIL: "limit",
}

# player_*_jump 시트: 0번 칸은 올라가는 중, 1번 칸은 내려오는 중
JUMP_FRAME_RISING = 0
JUMP_FRAME_FALLING = 1


def jump_step(height: float, vy: float, dt: float) -> tuple[float, float]:
    """등가속도 운동으로 dt초 뒤의 (높이, 위쪽 속도)를 구한다. dt가 얼마든 값이 같다."""
    new_height = height + vy * dt - config.GRAVITY * dt * dt / 2
    new_vy = vy - config.GRAVITY * dt
    return new_height, new_vy


def space_down(event: MachineEvent) -> bool:
    name, payload = event
    return (
        name == INPUT_EVENT
        and payload.type == SDL_KEYDOWN
        and payload.key == SDLK_SPACE
    )


def is_stun(event: MachineEvent) -> bool:
    return event[0] == STUN_EVENT


class Idle(State):
    @staticmethod
    def enter(owner: "Player", event: MachineEvent) -> None:
        owner.frame = 0.0

    @staticmethod
    def do(owner: "Player", dt: float) -> None:
        owner.animate("idle", dt)

    @staticmethod
    def draw(owner: "Player") -> None:
        owner.draw_pose("idle")


class Walk(State):
    @staticmethod
    def enter(owner: "Player", event: MachineEvent) -> None:
        owner.frame = 0.0

    @staticmethod
    def do(owner: "Player", dt: float) -> None:
        owner.move(config.WALK_SPEED, dt)
        owner.animate(owner.walk_anim(), dt)

    @staticmethod
    def draw(owner: "Player") -> None:
        owner.draw_pose(owner.walk_anim())


class Run(State):
    @staticmethod
    def enter(owner: "Player", event: MachineEvent) -> None:
        owner.frame = 0.0

    @staticmethod
    def do(owner: "Player", dt: float) -> None:
        owner.move(config.RUN_SPEED, dt)
        owner.animate("run", dt)

    @staticmethod
    def draw(owner: "Player") -> None:
        owner.draw_pose("run")


class Jump(State):
    @staticmethod
    def enter(owner: "Player", event: MachineEvent) -> None:
        owner.vy = config.JUMP_V0

    @staticmethod
    def do(owner: "Player", dt: float) -> None:
        # 공중에서도 좌우로 움직일 수 있다. 달릴 수 있는 상태에서 SHIFT를 누르고 있으면 달리기 속도다.
        speed = config.RUN_SPEED if owner.ground_state() is Run else config.WALK_SPEED
        owner.move(speed, dt)
        owner.height, owner.vy = jump_step(owner.height, owner.vy, dt)
        if owner.height <= 0.0:
            owner.land()

    @staticmethod
    def draw(owner: "Player") -> None:
        rising = owner.vy > 0
        owner.draw_pose("jump", JUMP_FRAME_RISING if rising else JUMP_FRAME_FALLING)


class Stunned(State):
    """기절: 키를 눌러도 움직이지 못하고, 공중이었다면 그 자리에서 곧장 떨어진다.

    멈춰 있는 시간이 다 되고 땅에 닿아 있으면 눌린 키에 맞는 상태로 일어난다.
    """

    @staticmethod
    def enter(owner: "Player", event: MachineEvent) -> None:
        owner.frame = 0.0

    @staticmethod
    def do(owner: "Player", dt: float) -> None:
        owner.drop(dt)
        owner.animate(owner.stunned_anim(), dt)
        if owner.can_get_up():
            owner.state_machine.add_event((WAKE_EVENT, None))

    @staticmethod
    def draw(owner: "Player") -> None:
        owner.draw_pose(owner.stunned_anim())


class Player(GameObject):
    def __init__(
        self,
        stage: Stage,
        camera: Camera,
        sprite_lookup: Callable[[str], resource.Sprite] = resource.get_sprite,
        gauge: Gauge | None = None,
    ) -> None:
        """gauge: 플레이 모드가 흘려보내는 게이지. 없으면 이 스테이지의 기본 속도로 새로 만든다."""
        self.stage = stage
        self.camera = camera
        self._sprite_lookup = sprite_lookup
        if gauge is None:
            gauge = Gauge(config.GAUGE_BASE_RATE[stage.number])
        self.gauge = gauge
        self.x = float(stage.player_start_x)
        self.height = 0.0  # 발이 지면에서 떠 있는 높이
        self.vy = 0.0  # 위쪽 속도 (위가 +)
        self.facing = 1  # 1 = 오른쪽, -1 = 왼쪽 (멈춰도 마지막 방향을 유지한다)
        self.frame = 0.0  # 애니메이션 프레임 번호 (소수)
        self.stun_remaining = 0.0  # 앞으로 꼼짝 못 하는 시간(초)
        # 앞으로 넘어져 누워 있는 시간(초). 기절 시간 안에 든다
        self.fall_remaining = 0.0
        self.slow_remaining = 0.0  # 앞으로 전단지 때문에 느린 시간(초)
        self.pressed: set[int] = set()
        self.state_machine = StateMachine(self)
        self.state_machine.set_transitions(self._build_transitions())
        self.state_machine.start(Idle)
        self.gauge.on_stage_change(self._on_gauge_stage_change)

    # ------------------------------------------------------------ 입력과 전이
    def _wants(self, kinds: tuple[str, ...], state: type[State]) -> Predicate:
        """kinds 중 하나가 왔을 때, 눌린 키가 가리키는 지상 상태가 state이면 참인 판정 함수."""

        def matches(event: MachineEvent) -> bool:
            return event[0] in kinds and self.ground_state() is state

        return matches

    def _on_gauge_stage_change(self, old: GaugeStage, new: GaugeStage) -> None:
        """단계가 바뀌면(달리기 금지·해제 등) 눌린 키에 맞는 상태를 다음 갱신에서 다시 따져 본다."""
        self.state_machine.add_event((STAGE_EVENT, None))

    def _build_transitions(self) -> Transitions:
        def on_input(state: type[State]) -> Predicate:
            return self._wants(RECHECK_EVENTS, state)

        def on_land(state: type[State]) -> Predicate:
            return self._wants((LAND_EVENT,), state)

        def on_wake(state: type[State]) -> Predicate:
            return self._wants((WAKE_EVENT,), state)

        # 기절은 어느 상태에서든 걸리고, 기절 중에는 키 입력(점프 포함)에 반응하지 않는다
        return {
            Idle: {
                is_stun: Stunned,
                space_down: Jump,
                on_input(Walk): Walk,
                on_input(Run): Run,
            },
            Walk: {
                is_stun: Stunned,
                space_down: Jump,
                on_input(Idle): Idle,
                on_input(Run): Run,
            },
            Run: {
                is_stun: Stunned,
                space_down: Jump,
                on_input(Idle): Idle,
                on_input(Walk): Walk,
            },
            Jump: {
                is_stun: Stunned,
                on_land(Idle): Idle,
                on_land(Walk): Walk,
                on_land(Run): Run,
            },
            Stunned: {on_wake(Idle): Idle, on_wake(Walk): Walk, on_wake(Run): Run},
        }

    def handle_event(self, event: Event) -> None:
        if event.type == SDL_KEYDOWN:
            if event.key in CONTROL_KEYS:
                self.pressed.add(event.key)
        elif event.type == SDL_KEYUP:
            self.pressed.discard(event.key)
        else:
            return
        self.state_machine.handle_state_event((INPUT_EVENT, event))

    def direction(self) -> int:
        """눌린 방향키로 정한 이동 방향: 오른쪽 1, 왼쪽 -1, 둘 다 또는 둘 다 아니면 0.

        한계 단계(95%~)에서는 좌우가 뒤바뀐다.
        """
        direction = (SDLK_RIGHT in self.pressed) - (SDLK_LEFT in self.pressed)
        return -direction if self.gauge.stage >= GaugeStage.LIMIT else direction

    def is_shift_held(self) -> bool:
        return any(key in self.pressed for key in SHIFT_KEYS)

    def ground_state(self) -> type[State]:
        """지금 눌린 키가 가리키는 지상 상태 (정지 / 걷기 / 달리기).

        긴장 단계(80%~)부터는 SHIFT를 눌러도 달릴 수 없다.
        """
        if self.direction() == 0:
            return Idle
        can_run = self.gauge.stage < GaugeStage.STRAIN
        return Run if can_run and self.is_shift_held() else Walk

    def is_running(self) -> bool:
        """달리는 속도로 움직이는 중인가 (점프 중에 달리기 속도를 유지하는 것도 포함).

        게이지가 이 동안 더 빨리 오른다.
        """
        return self.state_machine.state in (Run, Jump) and self.ground_state() is Run

    # ------------------------------------------------------------ 움직임
    def speed_multiplier(self) -> float:
        """이동 속도에 곱하는 배율. 계단·게이지·방해 효과는 서로 곱해서 겹친다."""
        multiplier = 1.0
        if self.stage.in_stairs(self.x):
            multiplier *= config.STAIRS_SPEED_MULT
        if self.gauge.stage >= GaugeStage.SWEAT:
            multiplier *= config.SWEAT_SPEED_MULT
        if self.slow_remaining > 0.0:
            multiplier *= config.FLYER_SPEED_MULT
        return multiplier

    def move(self, speed: float, dt: float) -> None:
        """눌린 방향으로 dt초 동안 speed(px/s)로 움직이고, 스테이지 밖으로 나가지 않게 한다."""
        direction = self.direction()
        if direction == 0:
            return
        self.facing = direction
        step = direction * speed * self.speed_multiplier() * dt
        self.x = clamp(0, self.x + step, self.stage.length)

    def land(self) -> None:
        """착지: 높이를 0으로 맞추고, 눌린 키에 맞는 지상 상태로 돌아가게 알린다."""
        self.height = 0.0
        self.vy = 0.0
        self.state_machine.add_event((LAND_EVENT, None))

    def drop(self, dt: float) -> None:
        """공중에 떠 있으면 중력만 받아 곧장 떨어진다 (좌우로는 움직이지 않는다)."""
        if self.height <= 0.0 and self.vy == 0.0:
            return
        self.height, self.vy = jump_step(self.height, self.vy, dt)
        if self.height <= 0.0:
            self.land()

    # ------------------------------------------------------------ 장애물이 거는 효과
    def stun(self, duration: float) -> None:
        """duration초 동안 꼼짝 못 하게 한다. 어느 상태에서든 곧바로 걸리고, 이미 기절해 있으면
        남은 시간과 비교해 더 긴 쪽만 남는다 (짧은 기절이 긴 기절을 끊지 않는다)."""
        self.stun_remaining = max(self.stun_remaining, duration)
        self.state_machine.handle_state_event((STUN_EVENT, None))

    def fall(self) -> None:
        """넘어진다: 잠깐 못 움직이고, 게이지가 한 번 오르고, 머리 둘레에 별이 돈다."""
        self.fall_remaining = max(self.fall_remaining, config.FALL_STOP_TIME)
        self.gauge.add(config.FALL_GAUGE_ADD)
        self.stun(config.FALL_STOP_TIME)
        fx.spawn_stars(self, self.camera, config.FALL_STOP_TIME, self._sprite_lookup)

    def slow(self, duration: float) -> None:
        """duration초 동안 이동 속도를 줄인다 (더 긴 쪽만 남는다)."""
        self.slow_remaining = max(self.slow_remaining, duration)

    def push(self, dx: float) -> None:
        """dx(오른쪽 +, 왼쪽 -)만큼 곧바로 밀려난다. 하던 동작은 끊기지 않고, 카메라는 따라 미끄러진다."""
        self.x = clamp(0, self.x + dx, self.stage.length)
        self.camera.start_glide(config.CAMERA_GLIDE_TIME)

    def can_get_up(self) -> bool:
        return self.stun_remaining <= 0.0 and self.height <= 0.0

    def stunned_anim(self) -> str:
        """기절해 있는 모습의 시트 이름: 넘어졌으면 누운 모습, 그냥 멈춘 것이면 선 모습."""
        return "fall" if self.fall_remaining > 0.0 else "idle"

    # ------------------------------------------------------------ 게임 오브젝트
    def _tick_timers(self, dt: float) -> None:
        self.stun_remaining = max(0.0, self.stun_remaining - dt)
        self.fall_remaining = max(0.0, self.fall_remaining - dt)
        self.slow_remaining = max(0.0, self.slow_remaining - dt)

    def step(self, dt: float) -> None:
        self._tick_timers(dt)
        self.state_machine.update(dt)

    def update(self) -> None:
        self.step(game_framework.frame_time)

    def get_bb(self) -> tuple[float, float, float, float]:
        bottom = config.GROUND_Y + self.height
        return (
            self.x - config.PLAYER_BB_HALF_W,
            bottom,
            self.x + config.PLAYER_BB_HALF_W,
            bottom + config.PLAYER_BB_HEIGHT,
        )

    # ------------------------------------------------------------ 그리기
    @property
    def mood(self) -> str:
        """시트 이름(player_{mood}_*)에 들어가는 모습: 게이지 단계에서 정해진다."""
        return MOOD_BY_STAGE[self.gauge.stage]

    def walk_anim(self) -> str:
        """걷는 모습의 시트 이름. 긴장 단계(80%~)부터는 뒤뚱거린다."""
        return "waddle" if self.gauge.stage >= GaugeStage.STRAIN else "walk"

    def _sprite(self, anim: str) -> resource.Sprite:
        return self._sprite_lookup(f"player_{self.mood}_{anim}")

    def animate(self, anim: str, dt: float) -> None:
        self.frame = self._sprite(anim).next_frame(self.frame, dt)

    def draw_pose(self, anim: str, frame: float | None = None) -> None:
        """현재 위치에 anim 시트를 그린다. 왼쪽을 보고 있으면 좌우 반전한다."""
        sprite = self._sprite(anim)
        sprite.draw(
            self.camera.to_screen_x(self.x),
            sprite.ground_center_y(self.height),
            self.frame if frame is None else frame,
            flip=self.facing < 0,
        )

    def draw(self) -> None:
        self.state_machine.draw()
