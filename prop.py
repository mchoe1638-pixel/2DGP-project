"""장식: 월드에 서 있는 그림 (표지판 등). 닿지도 움직이지도 않는다.

장식은 빌보드로 그린다. 배치표의 자리(DecoSpec.place)를 월드 좌표로 바꿔 세운다.
골인 문은 벽 텍스처(tex_door_wc)라 여기에 없다 (열고 닫는 일은 레이캐스터가 맡는다).
"""

import config
import resource
from game_object import Billboard, GameObject, natural_height
from resource import Sprite, SpriteLookup
from stage import DecoSpec, Stage
from stage_data import WALL_LEFT


class Prop(GameObject):
    """월드에 서 있는 그림 한 장. (x, y)는 그림 아래 가운데, z는 그 높이(m)다."""

    def __init__(
        self,
        sprite: Sprite,
        x: float,
        y: float,
        z: float = 0.0,
        world_h: float | None = None,
    ) -> None:
        """world_h가 None이면 시트 칸의 원래 비율로 정한 높이(m)를 쓴다."""
        self.sprite = sprite
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)
        self.world_h = natural_height(sprite) if world_h is None else float(world_h)

    def get_billboard(self) -> Billboard:
        return Billboard(self.sprite, 0, self.x, self.y, self.z, self.world_h)


def deco_prop(
    spec: DecoSpec, stage: Stage, lookup: SpriteLookup = resource.get_sprite
) -> Prop:
    """배치표 한 줄(DecoSpec)을 월드에 세울 장식으로 바꾼다.

    왼벽(WALL_LEFT)에 거는 장식은 그 x를 덮는 통로 구간의 왼벽에서 DECO_WALL_INSET만큼
    앞에, 눈높이보다 조금 높은 DECO_SIGN_Z에 선다. 모르는 자리면 ValueError.
    """
    if spec.place == WALL_LEFT:
        y = stage.segment_at(spec.x).y1 - config.DECO_WALL_INSET
        return Prop(lookup(spec.sprite), spec.x, y, config.DECO_SIGN_Z)
    raise ValueError(f"알 수 없는 장식 자리: {spec.place}")
