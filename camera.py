"""가로 스크롤 카메라.

플레이어가 화면 왼쪽에서 가로폭의 1/3 지점에 머물도록 따라가고, 스테이지 양 끝에서는 멈춘다.
x는 항상 정수라서 모든 오브젝트가 같은 픽셀 오프셋으로 그려진다.
"""

from typing import NamedTuple

import config
from util import clamp, smoothstep, snap


def target_x(player_x: float, view_w: int, level_w: int) -> int:
    """플레이어를 따라가는 카메라의 목표 x (스테이지 범위로 제한)."""
    wanted = snap(player_x) - view_w // config.CAMERA_ANCHOR_DIV
    return clamp(0, wanted, level_w - view_w)


class _Glide(NamedTuple):
    start_x: int
    elapsed: float
    duration: float


class Camera:
    def __init__(self, view_w: int, level_w: int) -> None:
        self.view_w = view_w
        self.level_w = level_w
        self.x = 0
        self._glide: _Glide | None = None

    @property
    def is_gliding(self) -> bool:
        return self._glide is not None

    def snap_to(self, player_x: float) -> None:
        """보간 없이 곧바로 목표 위치로 옮긴다."""
        self._glide = None
        self.x = target_x(player_x, self.view_w, self.level_w)

    def start_glide(self, duration: float) -> None:
        """지금 위치에서 목표까지 duration초에 걸쳐 부드럽게 따라잡게 한다 (순간이동 직후용)."""
        self._glide = _Glide(self.x, 0.0, duration)

    def update(self, dt: float, player_x: float) -> None:
        target = target_x(player_x, self.view_w, self.level_w)
        glide = self._glide
        if glide is None:
            self.x = target
            return
        elapsed = glide.elapsed + dt
        if elapsed >= glide.duration:
            self._glide = None
            self.x = target
            return
        self._glide = glide._replace(elapsed=elapsed)
        progress = smoothstep(elapsed / glide.duration)
        self.x = snap(glide.start_x + (target - glide.start_x) * progress)

    def to_screen_x(self, world_x: float) -> float:
        return world_x - self.x

    def is_visible(self, world_x: float, half_width: float, margin: float = 0) -> bool:
        """world_x를 중심으로 좌우 half_width인 물체가 화면(+margin)에 조금이라도 걸치는지."""
        return (
            world_x + half_width > self.x - margin
            and world_x - half_width < self.x + self.view_w + margin
        )
