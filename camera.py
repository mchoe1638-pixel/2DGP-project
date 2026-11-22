"""1인칭 카메라: 눈의 위치와 방향, 그리고 월드 → 화면 투영에 쓰는 값.

- 위치 (x, y)와 눈높이 eye_z(m)는 플레이어가 매 프레임 place()로 맞춘다.
- yaw(rad)는 마우스 가로 움직임으로 돈다. 0이 +x, 시계 반대 방향이 +이다 (+x를 볼 때 +y가 왼쪽).
- pitch_px는 위아래 보기를 지평선의 높이 차이(px)로 나타낸다 (y-shear). 화면 아래가 0인 pico2d 좌표에서
  위를 보면 지평선이 내려가고, 아래를 보면 올라간다.

투영: 화면 가로 반폭이 FOV의 반을 덮는다. PROJ = (W/2) / tan(FOV/2) px가 1m 앞에 있는 1m의 크기다.
"""

import math

import config
from util import clamp

FOV = math.radians(config.FOV_DEG)
PROJ = (config.SCREEN_W / 2) / math.tan(FOV / 2)
HALF_W = config.SCREEN_W / 2
HALF_H = config.SCREEN_H / 2


class Camera:
    def __init__(self, x: float, y: float, yaw: float) -> None:
        self.x = x
        self.y = y
        self.yaw = yaw
        self.pitch_px = 0.0
        self.eye_z = config.EYE_HEIGHT

    # ------------------------------------------------------------ 움직이기
    def look(self, dx: int, dy: int) -> None:
        """마우스 상대 이동(px)만큼 고개를 돌린다. SDL의 dy는 아래가 +다.

        마우스를 오른쪽으로 → yaw 감소(오른쪽을 본다). 마우스를 아래로 → 아래를 본다 → 지평선이 올라간다.
        """
        self.yaw = math.remainder(self.yaw - dx * config.MOUSE_SENS_YAW, math.tau)
        sign = -1.0 if config.MOUSE_INVERT_Y else 1.0
        self.pitch_px = clamp(
            -config.PITCH_MAX_PX,
            self.pitch_px + sign * dy * config.MOUSE_SENS_PITCH,
            config.PITCH_MAX_PX,
        )

    def place(self, x: float, y: float, eye_z: float) -> None:
        """눈을 월드 (x, y)의 높이 eye_z(m)에 둔다 (머리 흔들림의 위아래 몫이 들어 있다)."""
        self.x = x
        self.y = y
        self.eye_z = eye_z

    # ------------------------------------------------------------ 방향
    @property
    def horizon_y(self) -> float:
        """지평선(눈높이와 같은 높이)이 화면에 그려지는 y."""
        return HALF_H + self.pitch_px

    @property
    def forward(self) -> tuple[float, float]:
        return math.cos(self.yaw), math.sin(self.yaw)

    @property
    def right(self) -> tuple[float, float]:
        """오른쪽 방향: 앞을 시계 방향으로 90° 돌린 것."""
        return math.sin(self.yaw), -math.cos(self.yaw)

    def to_camera(self, wx: float, wy: float) -> tuple[float, float]:
        """월드 (wx, wy) → (앞으로의 거리 f, 오른쪽으로의 거리 l) m."""
        dx = wx - self.x
        dy = wy - self.y
        cos_yaw = math.cos(self.yaw)
        sin_yaw = math.sin(self.yaw)
        return dx * cos_yaw + dy * sin_yaw, dx * sin_yaw - dy * cos_yaw
