"""장식: 바닥에 서 있거나 벽에 걸린 그림 (기차, 개찰구, 표지판, 골인 문).

닿지도 움직이지도 않는다. 화면에 걸칠 때만 그린다.
"""

import config
import resource
from camera import Camera
from fx import SpriteLookup
from game_object import GameObject

WC_DOOR_SHEET = "prop_wc_door"
DOOR_CLOSED_FRAME = 0
DOOR_OPEN_FRAME = 1


class Prop(GameObject):
    def __init__(
        self,
        sheet: str,
        x: float,
        height: float,
        camera: Camera,
        sprite_lookup: SpriteLookup = resource.get_sprite,
    ) -> None:
        """sheet: manifest의 스프라이트 이름. height: 이미지 아래끝이 바닥 위로 떠 있는 높이."""
        self.sheet = sheet
        self.x = float(x)
        self.height = float(height)
        self.frame = 0
        self.camera = camera
        self._lookup = sprite_lookup

    def draw(self) -> None:
        sprite = self._lookup(self.sheet)
        if not self.camera.is_visible(self.x, sprite.frame_w / 2):
            return
        centre_y = config.GROUND_Y + self.height + sprite.frame_h / 2
        sprite.draw(self.camera.to_screen_x(self.x), centre_y, self.frame)


class WcDoor(Prop):
    """골인 문. 처음엔 닫혀 있다가 플레이어가 닿으면 열린다."""

    def __init__(
        self,
        x: float,
        camera: Camera,
        sprite_lookup: SpriteLookup = resource.get_sprite,
    ) -> None:
        super().__init__(WC_DOOR_SHEET, x, 0, camera, sprite_lookup)
        self.frame = DOOR_CLOSED_FRAME

    @property
    def is_open(self) -> bool:
        return self.frame == DOOR_OPEN_FRAME

    def open(self) -> None:
        self.frame = DOOR_OPEN_FRAME
