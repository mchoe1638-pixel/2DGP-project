"""플레이어 (1인칭): 월드 위치와 이동, 그리고 카메라(눈) 맞추기.

- W/S는 바라보는 방향으로 앞뒤, A/D는 옆걸음이다. 입력 방향은 길이 1로 맞춘다 (대각선이 더 빠르지 않게).
- 몸은 반지름 PLAYER_RADIUS의 원이다. 벽에 막히면 x·y축을 따로 밀어 벽을 따라 미끄러진다
  (map_grid.MapGrid.move_and_slide).
- 매 프레임 끝에 카메라를 플레이어의 눈 위치로 옮긴다.

지금은 고정 속도(WALK_MAX)로만 걷는다. 가속·달리기·점프·머리 흔들림은 다음 단계에서 붙인다.
"""

import math

from pico2d import SDLK_a, SDLK_d, SDLK_s, SDLK_w

import config
import game_framework
from camera import Camera
from game_object import GameObject
from input_state import InputState
from stage import Stage

FORWARD_KEY = SDLK_w
BACK_KEY = SDLK_s
LEFT_KEY = SDLK_a
RIGHT_KEY = SDLK_d


class Player(GameObject):
    def __init__(self, stage: Stage, camera: Camera, controls: InputState) -> None:
        self.stage = stage
        self.camera = camera
        self.controls = controls
        self.x, self.y, _yaw = stage.player_start  # 바라보는 방향은 카메라가 갖는다
        self.z = 0.0  # 발 높이(m)
        self._place_camera()

    # ------------------------------------------------------------ 갱신
    def update(self) -> None:
        move_x, move_y = self.wish_direction()
        if move_x or move_y:
            step = config.WALK_MAX * game_framework.frame_time
            moved = self.stage.grid.move_and_slide(
                self.x, self.y, move_x * step, move_y * step, config.PLAYER_RADIUS
            )
            self.x, self.y = moved.x, moved.y
        self._place_camera()

    def wish_direction(self) -> tuple[float, float]:
        """누른 키로 정한 이동 방향(월드 좌표). 길이는 1이고, 아무 키도 없으면 (0, 0)."""
        held = self.controls.is_held
        ahead = float(held(FORWARD_KEY)) - float(held(BACK_KEY))
        aside = float(held(RIGHT_KEY)) - float(held(LEFT_KEY))  # +가 오른쪽
        length = math.hypot(ahead, aside)
        if length == 0.0:
            return 0.0, 0.0
        forward_x, forward_y = self.camera.forward
        right_x, right_y = self.camera.right
        return (
            (forward_x * ahead + right_x * aside) / length,
            (forward_y * ahead + right_y * aside) / length,
        )

    def _place_camera(self) -> None:
        self.camera.place(self.x, self.y, config.EYE_HEIGHT + self.z)

    # ------------------------------------------------------------ 상태
    def is_running(self) -> bool:
        """달리는 중인지 (게이지가 더 빨리 오른다). 아직 달리기가 없다."""
        return False
