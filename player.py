"""플레이어: 이동·달리기·점프를 상태 머신으로 구현한다.

상태는 Idle / Walk / Run / Jump 이다 (기절 상태는 4단계에서 추가).
어느 상태로 갈지는 지금 눌려 있는 키 집합에서 매번 새로 계산한다. 그래서 ← → 를 함께 눌러도,
점프 중에 키를 바꿔 눌러도 착지한 뒤 눌린 키에 맞는 상태로 돌아온다.
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
import game_framework
import resource
from camera import Camera
from game_object import GameObject
from stage_data import Stage
from state_machine import Event as MachineEvent
from state_machine import Predicate, State, StateMachine, Transitions
from util import clamp

INPUT_EVENT = "INPUT"  # ('INPUT', pico2d 키 이벤트)
LAND_EVENT = "LAND"  # ('LAND', None): 점프가 땅에 닿았다

CONTROL_KEYS = frozenset({SDLK_LEFT, SDLK_RIGHT, SDLK_LSHIFT, SDLK_RSHIFT})
SHIFT_KEYS = (SDLK_LSHIFT, SDLK_RSHIFT)

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
        owner.animate("walk", dt)

    @staticmethod
    def draw(owner: "Player") -> None:
        owner.draw_pose("walk")


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
        # 공중에서도 좌우로 움직일 수 있다. SHIFT를 누르고 있으면 달리기 속도다.
        speed = config.RUN_SPEED if owner.is_shift_held() else config.WALK_SPEED
        owner.move(speed, dt)
        owner.height, owner.vy = jump_step(owner.height, owner.vy, dt)
        if owner.height <= 0.0:
            owner.land()

    @staticmethod
    def draw(owner: "Player") -> None:
        rising = owner.vy > 0
        owner.draw_pose("jump", JUMP_FRAME_RISING if rising else JUMP_FRAME_FALLING)


class Player(GameObject):
    def __init__(
        self,
        stage: Stage,
        camera: Camera,
        sprite_lookup: Callable[[str], resource.Sprite] = resource.get_sprite,
    ) -> None:
        self.stage = stage
        self.camera = camera
        self._sprite_lookup = sprite_lookup
        self.x = float(stage.player_start_x)
        self.height = 0.0  # 발이 지면에서 떠 있는 높이
        self.vy = 0.0  # 위쪽 속도 (위가 +)
        self.facing = 1  # 1 = 오른쪽, -1 = 왼쪽 (멈춰도 마지막 방향을 유지한다)
        self.frame = 0.0  # 애니메이션 프레임 번호 (소수)
        self.mood = "calm"  # 시트 이름의 일부. 게이지 단계에 따라 3단계에서 바뀐다
        self.pressed: set[int] = set()
        self.state_machine = StateMachine(self)
        self.state_machine.set_transitions(self._build_transitions())
        self.state_machine.start(Idle)

    # ------------------------------------------------------------ 입력과 전이
    def _wants(self, kind: str, state: type[State]) -> Predicate:
        """kind 이벤트가 왔을 때, 눌린 키가 가리키는 지상 상태가 state이면 참인 판정 함수."""

        def matches(event: MachineEvent) -> bool:
            return event[0] == kind and self.ground_state() is state

        return matches

    def _build_transitions(self) -> Transitions:
        def on_input(state: type[State]) -> Predicate:
            return self._wants(INPUT_EVENT, state)

        def on_land(state: type[State]) -> Predicate:
            return self._wants(LAND_EVENT, state)

        return {
            Idle: {space_down: Jump, on_input(Walk): Walk, on_input(Run): Run},
            Walk: {space_down: Jump, on_input(Idle): Idle, on_input(Run): Run},
            Run: {space_down: Jump, on_input(Idle): Idle, on_input(Walk): Walk},
            Jump: {on_land(Idle): Idle, on_land(Walk): Walk, on_land(Run): Run},
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
        """눌린 방향키로 정한 이동 방향: 오른쪽 1, 왼쪽 -1, 둘 다 또는 둘 다 아니면 0."""
        return (SDLK_RIGHT in self.pressed) - (SDLK_LEFT in self.pressed)

    def is_shift_held(self) -> bool:
        return any(key in self.pressed for key in SHIFT_KEYS)

    def ground_state(self) -> type[State]:
        """지금 눌린 키가 가리키는 지상 상태 (정지 / 걷기 / 달리기)."""
        if self.direction() == 0:
            return Idle
        return Run if self.is_shift_held() else Walk

    # ------------------------------------------------------------ 움직임
    def speed_multiplier(self) -> float:
        """이동 속도에 곱하는 배율. 계단·게이지·방해 효과는 서로 곱해서 겹친다."""
        multiplier = 1.0
        if self.stage.in_stairs(self.x):
            multiplier *= config.STAIRS_SPEED_MULT
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

    # ------------------------------------------------------------ 게임 오브젝트
    def step(self, dt: float) -> None:
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
