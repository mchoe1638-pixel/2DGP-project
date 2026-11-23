"""플레이어 (1인칭): 가속도로 움직이는 몸, 점프와 넘어짐, 걸음에 맞춘 머리 흔들림, 카메라(눈) 맞추기.

이동
- ↑/↓는 바라보는 방향으로 앞뒤, ←/→는 옆걸음이다. 입력 방향은 길이 1로 맞춘다 (대각선이 더 빠르지 않게).
  한계 단계(95%~)에서는 ←/→만 뒤바뀐다.
- 목표 속도 = 입력 방향 × 최고 속도. 땅에서는 ACCEL_GROUND로 목표 속도를 따라가고, 손을 떼면
  DECEL_GROUND로 멈춘다 (달리다 손을 떼면 2m 남짓 미끄러진다). 공중에서는 ACCEL_AIR로 조금만 틀 수 있고,
  손을 떼면 속도를 그대로 유지한다.
- 최고 속도: 걷기 WALK_MAX, SHIFT 달리기 RUN_MAX, 뒤로 BACK_MAX. 긴장 단계(80%~)부터는 SHIFT를 무시한다.
  땀 단계(50%~)에서는 SWEAT_SPEED_MULT, 계단 위에서는 STAIRS_SPEED_MULT를 곱한다.
- 몸은 반지름 PLAYER_RADIUS의 원이다. 벽에 막히면 x·y축을 따로 밀어 벽을 따라 미끄러지고
  (map_grid.MapGrid.move_and_slide), 막힌 축의 속도는 0이 된다. 그 축으로 WALL_BUMP_SPEED 이상이었으면 쿵 소리.
- SPACE: 땅에 서 있고 멈춰 있지 않을 때 JUMP_V로 뛴다. 공중에서는 GRAVITY로 떨어진다.

상태: 서기(IDLE) < IDLE_SPEED_MAX ≤ 걷기(WALK) < RUN_SPEED_MIN ≤ 달리기(RUN),
그리고 공중(AIR)과 멈춤(STUNNED).
멈춤(stun) 동안은 움직이지 못한다. 넘어짐(fall)은 멈춤에 게이지·소리가 더해지고, 눈이 바닥 가까이로 내려갔다가
멈춤이 끝나면 일어서며 돌아온다.

머리 흔들림: 땅 위에서 움직인 거리만큼 걸음 위상(step_phase)이 흐른다 (한 걸음에 1).
위아래 bob_y(m)는 눈높이에 더하고, 좌우 bob_x(px)는 1인칭 팔만 민다 (벽과 빌보드는 밀지 않는다).
흔들림을 끄면(F6) 둘 다 0이지만 걸음 위상은 그대로 흘러, 팔은 계속 걸음에 맞춰 움직인다.
"""

import math
from enum import Enum, auto

from pico2d import (
    SDLK_DOWN,
    SDLK_LEFT,
    SDLK_LSHIFT,
    SDLK_RIGHT,
    SDLK_RSHIFT,
    SDLK_SPACE,
    SDLK_UP,
)

import config
import game_framework
import sound
from camera import Camera
from game_object import GameObject
from gauge import Gauge, GaugeStage
from input_state import InputState
from stage import Stage

FORWARD_KEY = SDLK_UP
BACK_KEY = SDLK_DOWN
LEFT_KEY = SDLK_LEFT
RIGHT_KEY = SDLK_RIGHT
RUN_KEYS = (SDLK_LSHIFT, SDLK_RSHIFT)
JUMP_KEY = SDLK_SPACE

# 걸음 위상의 한 바퀴: 왼발·오른발 두 걸음. 좌우 흔들림 sin(π·위상)이 제자리로 돌아온다
STEP_CYCLE = 2.0
# 걸음걸이 이름 (config.BOB_AMP / BOB_SWAY_PX의 키)
GAIT_WALK = "walk"
GAIT_RUN = "run"
GAIT_STRAIN = "strain"  # 긴장 단계(80%~)에서 움직일 때: 배를 움켜쥐고 좌우로 크게 흔들린다


class Motion(Enum):
    """플레이어의 움직임 상태. 1인칭 팔과 머리 흔들림이 읽는다."""

    IDLE = auto()
    WALK = auto()
    RUN = auto()
    AIR = auto()
    STUNNED = auto()


def approach(
    vx: float, vy: float, target_x: float, target_y: float, max_change: float
) -> tuple[float, float]:
    """속도 (vx, vy)를 목표 (target_x, target_y) 쪽으로 최대 max_change만큼 옮긴다 (목표를 넘지 않는다)."""
    gap_x = target_x - vx
    gap_y = target_y - vy
    gap = math.hypot(gap_x, gap_y)
    if gap <= max_change:
        return target_x, target_y
    scale = max_change / gap
    return vx + gap_x * scale, vy + gap_y * scale


class Player(GameObject):
    def __init__(
        self,
        stage: Stage,
        camera: Camera,
        controls: InputState,
        gauge: Gauge,
        head_bob: bool,
    ) -> None:
        self.stage = stage
        self.camera = camera
        self.controls = controls
        self.gauge = gauge
        self.head_bob = head_bob  # 머리 흔들림을 보일지 (F6으로 바뀐다)
        self.x, self.y, _yaw = stage.player_start  # 바라보는 방향은 카메라가 갖는다
        self.z = 0.0  # 발 높이(m)
        self.vx = 0.0  # 수평 속도(m/s)
        self.vy = 0.0
        self.vz = 0.0  # 위로 +인 속도(m/s)
        self.state = Motion.IDLE
        self.state_time = 0.0  # 지금 상태가 이어진 시간(초)
        self.stun_remaining = 0.0  # 못 움직이는 남은 시간(초)
        self.fallen = False  # 넘어져 있는지 (멈춤이 끝나면 일어선다)
        self.eye_base = config.EYE_HEIGHT  # 흔들림을 빼고 발에서 잰 눈높이(m)
        self.step_phase = 0.0  # 걸음 위상: 한 걸음에 1씩 오르고 STEP_CYCLE에서 0으로 돌아간다
        self._bob_amp = 0.0  # 지금 위아래 흔들림 폭(m). 걸음걸이의 목표 폭 쪽으로 서서히 옮겨 간다
        self._bob_sway = 0.0  # 지금 좌우 흔들림 폭(px)
        self.bob_y = 0.0  # 이번 프레임에 머리가 올라간 높이(m)
        self.bob_x = 0.0  # 이번 프레임에 팔이 옆으로 밀린 거리(px)
        self._place_camera()

    # ------------------------------------------------------------ 상태 읽기
    @property
    def speed(self) -> float:
        """수평 속력(m/s)."""
        return math.hypot(self.vx, self.vy)

    @property
    def is_grounded(self) -> bool:
        return self.z <= 0.0

    @property
    def is_stunned(self) -> bool:
        return self.stun_remaining > 0.0

    def is_running(self) -> bool:
        """달리는 빠르기(RUN_SPEED_MIN 이상)로 움직이는 중인지 (게이지가 더 빨리 오른다)."""
        return not self.is_stunned and self.speed >= config.RUN_SPEED_MIN

    def gait(self) -> str | None:
        """머리 흔들림에 쓸 걸음걸이 (GAIT_*). 땅에서 걷거나 달리는 중이 아니면 None."""
        if self.state not in (Motion.WALK, Motion.RUN):
            return None
        if self.gauge.stage >= GaugeStage.STRAIN:
            return GAIT_STRAIN
        if self.state is Motion.RUN:
            return GAIT_RUN
        return GAIT_WALK

    # ------------------------------------------------------------ 입력
    def wish_input(self) -> tuple[float, float]:
        """누른 키로 정한 (앞, 오른쪽) 입력. 각각 -1, 0, 1. 한계 단계(95%~)에서는 ←/→가 뒤바뀐다."""
        held = self.controls.is_held
        ahead = float(held(FORWARD_KEY)) - float(held(BACK_KEY))
        aside = float(held(RIGHT_KEY)) - float(held(LEFT_KEY))  # +가 오른쪽
        if self.gauge.stage >= GaugeStage.LIMIT:
            aside = -aside
        return ahead, aside

    def wish_direction(self, ahead: float, aside: float) -> tuple[float, float]:
        """(앞, 오른쪽) 입력을 월드 방향으로 바꾼다. 길이는 1이고, 입력이 없으면 (0, 0)."""
        length = math.hypot(ahead, aside)
        if length == 0.0:
            return 0.0, 0.0
        forward_x, forward_y = self.camera.forward
        right_x, right_y = self.camera.right
        return (
            (forward_x * ahead + right_x * aside) / length,
            (forward_y * ahead + right_y * aside) / length,
        )

    def wants_to_run(self) -> bool:
        """SHIFT를 누르고 있는지. 긴장 단계(80%~)부터는 눌러도 달리지 못한다."""
        return self.gauge.stage < GaugeStage.STRAIN and self.controls.is_held(*RUN_KEYS)

    def max_speed(self, ahead: float) -> float:
        """지금 낼 수 있는 최고 수평 속도(m/s). 뒤로 갈 때(ahead < 0)는 BACK_MAX에서 시작한다."""
        if ahead < 0.0:
            top = config.BACK_MAX
        elif self.wants_to_run():
            top = config.RUN_MAX
        else:
            top = config.WALK_MAX
        if self.gauge.stage >= GaugeStage.SWEAT:
            top *= config.SWEAT_SPEED_MULT
        if self.stage.grid.is_stairs(self.x, self.y):
            top *= config.STAIRS_SPEED_MULT
        return top

    # ------------------------------------------------------------ 갱신
    def update(self) -> None:
        dt = game_framework.frame_time
        self._tick_stun(dt)
        self._steer(dt)
        self._update_vertical(dt)
        self._move(dt)
        self._update_state(dt)
        self._update_eye(dt)
        self._update_bob(dt)
        self._place_camera()

    def _tick_stun(self, dt: float) -> None:
        if not self.is_stunned:
            return
        self.stun_remaining = max(0.0, self.stun_remaining - dt)
        if not self.is_stunned:
            self.fallen = False  # 멈춤이 끝나면 일어선다

    def _steer(self, dt: float) -> None:
        """입력과 최고 속도로 정한 목표 속도 쪽으로 수평 속도를 옮긴다."""
        if self.is_stunned:
            self.vx = self.vy = 0.0
            return
        ahead, aside = self.wish_input()
        has_input = ahead != 0.0 or aside != 0.0
        if self.is_grounded:
            rate = config.ACCEL_GROUND if has_input else config.DECEL_GROUND
        elif has_input:
            rate = config.ACCEL_AIR
        else:
            return  # 공중에서 손을 떼면 속도를 그대로 둔다
        direction_x, direction_y = self.wish_direction(ahead, aside)
        top = self.max_speed(ahead)
        self.vx, self.vy = approach(
            self.vx, self.vy, direction_x * top, direction_y * top, rate * dt
        )

    def _update_vertical(self, dt: float) -> None:
        """SPACE로 뛰고, 떠 있으면 중력으로 떨어진다. 바닥에 닿으면 선다."""
        can_jump = self.is_grounded and not self.is_stunned
        if can_jump and self.controls.was_pressed(JUMP_KEY):
            self.vz = config.JUMP_V
            sound.play_sfx(sound.JUMP)
        if self.is_grounded and self.vz <= 0.0:
            return
        self.vz -= config.GRAVITY * dt
        self.z += self.vz * dt
        if self.z <= 0.0:
            self.z = 0.0
            self.vz = 0.0

    def _move(self, dt: float) -> None:
        """속도만큼 옮기되 벽에 막힌 축은 멈춘다. 그 축으로 빨랐으면 쿵 소리."""
        if self.vx == 0.0 and self.vy == 0.0:
            return
        moved = self.stage.grid.move_and_slide(
            self.x, self.y, self.vx * dt, self.vy * dt, config.PLAYER_RADIUS
        )
        self.x, self.y = moved.x, moved.y
        bump = config.WALL_BUMP_SPEED
        if (moved.hit_x and abs(self.vx) >= bump) or (
            moved.hit_y and abs(self.vy) >= bump
        ):
            sound.play_sfx(sound.BUMP)
        if moved.hit_x:
            self.vx = 0.0
        if moved.hit_y:
            self.vy = 0.0

    def _update_state(self, dt: float) -> None:
        state = self._current_motion()
        if state is self.state:
            self.state_time += dt
        else:
            self.state = state
            self.state_time = 0.0

    def _current_motion(self) -> Motion:
        if self.is_stunned:
            return Motion.STUNNED
        if not self.is_grounded:
            return Motion.AIR
        speed = self.speed
        if speed < config.IDLE_SPEED_MAX:
            return Motion.IDLE
        if speed < config.RUN_SPEED_MIN:
            return Motion.WALK
        return Motion.RUN

    def _update_eye(self, dt: float) -> None:
        """넘어져 있으면 눈을 EYE_FALL_HEIGHT까지 내리고, 일어서면 EYE_HEIGHT로 되돌린다 (일정한 빠르기로)."""
        drop = config.EYE_HEIGHT - config.EYE_FALL_HEIGHT
        if self.fallen:
            lowered = self.eye_base - drop / config.EYE_DROP_TIME * dt
            self.eye_base = max(config.EYE_FALL_HEIGHT, lowered)
        else:
            raised = self.eye_base + drop / config.EYE_RISE_TIME * dt
            self.eye_base = min(config.EYE_HEIGHT, raised)

    def _update_bob(self, dt: float) -> None:
        """걸음 위상을 흘리고, 흔들림 폭을 걸음걸이의 목표 쪽으로 옮긴 뒤 이번 프레임의 흔들림을 정한다."""
        if self.is_grounded and not self.is_stunned:
            if self.state is Motion.RUN:
                step_length = config.STEP_LENGTH_RUN
            else:
                step_length = config.STEP_LENGTH_WALK
            self.step_phase = (
                self.step_phase + self.speed * dt / step_length
            ) % STEP_CYCLE
        gait = self.gait()
        target_amp = 0.0 if gait is None else config.BOB_AMP[gait]
        target_sway = 0.0 if gait is None else config.BOB_SWAY_PX[gait]
        blend = 1.0 - math.exp(-dt / config.BOB_BLEND_TIME)
        self._bob_amp += (target_amp - self._bob_amp) * blend
        self._bob_sway += (target_sway - self._bob_sway) * blend
        if not self.head_bob:
            self.bob_y = 0.0
            self.bob_x = 0.0
            return
        wave = math.sin(math.pi * self.step_phase)
        self.bob_y = self._bob_amp * abs(wave)
        self.bob_x = self._bob_sway * wave

    def _place_camera(self) -> None:
        self.camera.place(self.x, self.y, self.eye_base + self.z + self.bob_y)

    # ------------------------------------------------------------ 다른 쪽에서 부르는 것
    def stun(self, duration: float) -> None:
        """duration초 동안 못 움직이게 하고 수평 속도를 0으로. 이미 멈춰 있으면 더 긴 쪽을 따른다."""
        self.stun_remaining = max(self.stun_remaining, duration)
        self.vx = 0.0
        self.vy = 0.0

    def fall(self) -> None:
        """넘어진다: FALL_STOP_TIME 멈춤, 게이지 +FALL_GAUGE_ADD, 넘어지는 소리. 눈이 바닥 가까이로 내려간다."""
        self.stun(config.FALL_STOP_TIME)
        self.fallen = True
        self.gauge.add(config.FALL_GAUGE_ADD)
        sound.play_sfx(sound.FALL)

    def halt(self) -> None:
        """그 자리에 선다 (골인했을 때: 미끄러져 문에 부딪히지 않게). 떠 있으면 그대로 내려온다."""
        self.vx = 0.0
        self.vy = 0.0
