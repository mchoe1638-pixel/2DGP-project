"""모든 게임 오브젝트의 공통 인터페이스 기본 구현.

game_world는 update / get_bb / handle_collision을 부르고, 플레이 모드는 get_billboards로 받은
빌보드를 모아 레이캐스터에 넘긴다 (벽에 가려지는 부분은 레이캐스터가 띠 단위로 가린다).
필요한 메서드만 덮어쓰면 되고, 나머지는 아무 일도 하지 않는다.
"""

from typing import NamedTuple

import config
from resource import Sprite

# 충돌 원기둥: (x, y, 반지름, 아래 z, 위 z). 모두 월드 좌표(m)이고 z는 바닥에서의 높이다
Cylinder = tuple[float, float, float, float, float]


class Billboard(NamedTuple):
    """월드에 세운 그림 한 장. 늘 카메라를 마주 보고, 멀수록 작아진다.

    (x, y)는 그림 아래 가운데가 서 있는 월드 위치(m), z는 그 높이(m, 0 = 바닥).
    world_h는 그림 높이(m)이고 너비는 시트 칸의 가로세로 비로 정한다.
    flip은 좌우 반전, alpha는 투명도(1 = 불투명)다.
    """

    sprite: Sprite
    frame: int
    x: float
    y: float
    z: float
    world_h: float
    flip: bool = False
    alpha: float = 1.0


def natural_height(sprite: Sprite) -> float:
    """시트 칸을 원래 비율(SPRITE_M_PER_PX)로 세울 때의 월드 높이(m)."""
    return sprite.frame_h * config.SPRITE_M_PER_PX


class GameObject:
    def update(self) -> None:
        """매 프레임 상태를 갱신한다 (시간 값은 game_framework.frame_time)."""

    def draw(self) -> None:
        """화면에 바로 그린다. 월드에 서 있는 오브젝트는 이것 대신 get_billboard를 쓴다."""

    def get_billboard(self) -> Billboard | None:
        """이번 프레임에 월드에 세울 그림. 그리지 않으면 None."""
        return None

    def get_billboards(self) -> tuple[Billboard, ...]:
        """이번 프레임에 월드에 세울 그림 전부. 몸과 머리 위 표시처럼 여러 장을 세우는 오브젝트가 덮어쓴다."""
        board = self.get_billboard()
        return () if board is None else (board,)

    def get_bb(self) -> Cylinder | None:
        """(x, y, 반지름, 아래 z, 위 z) 충돌 원기둥. 충돌하지 않으면 None."""
        return None

    def handle_collision(self, group: str, other: "GameObject") -> None:
        """game_world.add_collision_pair로 등록한 그룹에서 충돌했을 때 호출된다."""
