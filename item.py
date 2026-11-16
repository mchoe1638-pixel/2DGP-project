"""아이템 3종: 심호흡·껌·지름길.

닿으면 한 번만 효과를 내고 월드에서 사라진다. 위아래로 살짝 둥둥 뜬다.
효과의 내용만 종류마다 다르다 (collect). 충돌 상자는 이미지 크기의 80%다.
"""

import math

import config
import fx
import game_framework
import game_world
import resource
import sound
from camera import Camera
from fx import SpriteLookup
from game_object import GameObject
from player import Player

PLAYER_ITEM = "player:item"  # 충돌 그룹: 왼쪽은 플레이어, 오른쪽은 아이템들


def bob_offset(elapsed: float) -> float:
    """둥둥 뜨는 높이(0 ~ 2*폭). 가장 낮을 때가 배치표에 적은 높이다."""
    phase = elapsed / config.ITEM_BOB_PERIOD * math.tau
    return config.ITEM_BOB_AMPLITUDE * (1.0 - math.cos(phase))


class Item(GameObject):
    sheet = ""  # 종류마다 정하는 스프라이트 시트 이름
    sfx = ""  # 종류마다 정하는, 주웠을 때의 효과음 이름

    def __init__(
        self,
        x: float,
        height: float,
        camera: Camera,
        player: Player,
        sprite_lookup: SpriteLookup = resource.get_sprite,
    ) -> None:
        """height: 이미지 아래끝이 바닥 위로 떠 있는 높이 (둥둥 뜨는 가장 낮은 자리)."""
        self.x = float(x)
        self.height = float(height)
        self.frame = 0.0
        self.camera = camera
        self.player = player
        self._lookup = sprite_lookup
        self._elapsed = 0.0

    def _sprite(self) -> resource.Sprite:
        return self._lookup(self.sheet)

    def _bottom(self) -> float:
        """지금 이미지 아래끝의 y."""
        return config.GROUND_Y + self.height + bob_offset(self._elapsed)

    # ------------------------------------------------------------ 게임 오브젝트
    def update(self) -> None:
        dt = game_framework.frame_time
        self._elapsed += dt
        self.frame = self._sprite().next_frame(self.frame, dt)

    def get_bb(self) -> tuple[float, float, float, float]:
        sprite = self._sprite()
        half_w = sprite.frame_w * config.ITEM_BB_SCALE / 2
        box_h = sprite.frame_h * config.ITEM_BB_SCALE
        bottom = self._bottom() + (sprite.frame_h - box_h) / 2
        return (self.x - half_w, bottom, self.x + half_w, bottom + box_h)

    def draw(self) -> None:
        sprite = self._sprite()
        if not self.camera.is_visible(self.x, sprite.frame_w / 2):
            return
        centre_y = self._bottom() + sprite.frame_h / 2
        sprite.draw(self.camera.to_screen_x(self.x), centre_y, self.frame)

    def handle_collision(self, group: str, other: GameObject) -> None:
        sound.play_sfx(self.sfx)
        self.collect()
        game_world.remove_object(self)

    # ------------------------------------------------------------ 효과
    def collect(self) -> None:
        """플레이어가 주웠을 때의 효과. 종류마다 덮어쓴다."""


class Breath(Item):
    """심호흡: 게이지를 덜어 낸다."""

    sheet = "item_breath"
    sfx = sound.ITEM_BREATH

    def collect(self) -> None:
        self.player.gauge.add(-config.ITEM_BREATH_GAUGE_DROP)


class Gum(Item):
    """껌: 잠깐 게이지 상승을 붙잡는다."""

    sheet = "item_gum"
    sfx = sound.ITEM_GUM

    def collect(self) -> None:
        self.player.gauge.freeze(config.ITEM_GUM_FREEZE_TIME)


class Shortcut(Item):
    """지름길: 먼지를 일으키며 앞으로 순간이동한다. 카메라는 미끄러지며 따라간다."""

    sheet = "item_shortcut"
    sfx = sound.ITEM_SHORTCUT

    def collect(self) -> None:
        self._puff(self.player.x)
        # push는 스테이지 끝을 넘지 않게 잘라 준다
        self.player.push(config.ITEM_SHORTCUT_DISTANCE)
        self._puff(self.player.x)

    def _puff(self, world_x: float) -> None:
        for offset in config.FX_DUST_OFFSETS:
            fx.spawn_dust(
                world_x + offset, self.camera, config.FX_DUST_TIME, self._lookup
            )
