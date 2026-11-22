"""이펙트: 잠깐 떴다가 사라지는 스프라이트 (별, 물음표, 느낌표, 전단지, 말풍선).

위치는 그릴 때마다 anchor()에서 새로 읽으므로 플레이어나 NPC를 따라다닌다.
anchor()가 돌려주는 (x, y)는 화면 좌표이고, 이펙트 그림의 '아래쪽 가운데'가 그 점에 놓인다.
"""

from collections.abc import Callable
from typing import Protocol

import config
import game_framework
import game_world
import resource
import text
from camera import Camera
from game_object import GameObject
from resource import SpriteLookup
from util import snap

Anchor = Callable[[], tuple[float, float]]


class Located(Protocol):
    """월드 x 좌표를 가진 것 (NPC)."""

    x: float


class Airborne(Protocol):
    """월드 x 좌표와, 지면 위로 떠 있는 높이를 가진 것 (플레이어)."""

    x: float
    height: float


class Effect(GameObject):
    """lifetime초 동안 떠 있다가 스스로 월드에서 빠지는 이펙트. label이 있으면 그림 위에 글자를 얹는다."""

    def __init__(
        self,
        sprite_name: str,
        lifetime: float,
        anchor: Anchor,
        sprite_lookup: SpriteLookup = resource.get_sprite,
        frame_period: float | None = None,
        label: str | None = None,
    ) -> None:
        self.sprite_name = sprite_name
        self.lifetime = lifetime
        self.label = label
        self._anchor = anchor
        self._lookup = sprite_lookup
        self._frame_period = (
            config.FX_FRAME_PERIOD if frame_period is None else frame_period
        )
        self._elapsed = 0.0

    def update(self) -> None:
        self._elapsed += game_framework.frame_time
        if self._elapsed >= self.lifetime:
            game_world.remove_object(self)

    def draw(self) -> None:
        sprite = self._lookup(self.sprite_name)
        anchor_x, anchor_y = self._anchor()
        centre_y = anchor_y + sprite.frame_h / 2
        frame = int(self._elapsed / self._frame_period) % sprite.frames
        sprite.draw(anchor_x, centre_y, frame)
        if self.label:
            offset_x, offset_y = config.FX_SPEECH_TEXT_OFFSET
            text.draw(
                self.label,
                snap(anchor_x + offset_x),
                snap(centre_y + offset_y),
                size=config.FX_SPEECH_TEXT_SIZE,
                color=config.FX_SPEECH_TEXT_COLOR,
                align="center",
            )


def _spawn(effect: Effect) -> Effect:
    game_world.add_object(effect, game_world.LAYER_FX)
    return effect


def _body_anchor(player: Airborne, camera: Camera, rise: float) -> Anchor:
    """플레이어 발밑 위 rise 높이. 점프로 뜬 만큼 함께 떠오른다."""

    def anchor() -> tuple[float, float]:
        return (
            camera.to_screen_x(player.x),
            config.GROUND_Y + rise + player.height,
        )

    return anchor


def _head_anchor(who: Located, camera: Camera, offset_x: float = 0) -> Anchor:
    """NPC 머리 바로 위. offset_x는 가로로 얼마나 어긋나게 띄울지."""

    def anchor() -> tuple[float, float]:
        head = config.GROUND_Y + config.NPC_HEAD_HEIGHT + config.FX_HEAD_GAP
        return camera.to_screen_x(who.x) + offset_x, head

    return anchor


def _ground_anchor(world_x: float, camera: Camera) -> Anchor:
    """월드 x의 바닥 위. 카메라가 움직여도 그 자리에 머문다."""

    def anchor() -> tuple[float, float]:
        return camera.to_screen_x(world_x), config.GROUND_Y

    return anchor


def spawn_dust(
    world_x: float,
    camera: Camera,
    lifetime: float,
    sprite_lookup: SpriteLookup = resource.get_sprite,
) -> Effect:
    """월드 x의 바닥에서 먼지가 일어난다 (지름길로 떠나고 닿는 자리)."""
    anchor = _ground_anchor(world_x, camera)
    return _spawn(Effect("fx_dust", lifetime, anchor, sprite_lookup))


def spawn_stars(
    player: Airborne,
    camera: Camera,
    lifetime: float,
    sprite_lookup: SpriteLookup = resource.get_sprite,
) -> Effect:
    """넘어진 플레이어 머리 둘레에 별이 돈다."""
    anchor = _body_anchor(player, camera, config.FX_STARS_HEIGHT)
    return _spawn(Effect("fx_stars", lifetime, anchor, sprite_lookup))


def spawn_paper(
    player: Airborne,
    camera: Camera,
    lifetime: float,
    sprite_lookup: SpriteLookup = resource.get_sprite,
) -> Effect:
    """전단지를 받은 플레이어 몸에 종이가 붙어 있다."""
    anchor = _body_anchor(player, camera, config.FX_PAPER_HEIGHT)
    return _spawn(Effect("fx_paper", lifetime, anchor, sprite_lookup))


def spawn_question(
    asker: Located,
    camera: Camera,
    lifetime: float,
    sprite_lookup: SpriteLookup = resource.get_sprite,
) -> Effect:
    """길을 묻는 NPC 머리 위에 물음표가 뜬다."""
    anchor = _head_anchor(asker, camera)
    return _spawn(Effect("fx_question", lifetime, anchor, sprite_lookup))


def spawn_exclaim(
    lifetime: float, sprite_lookup: SpriteLookup = resource.get_sprite
) -> Effect:
    """화면 오른쪽 끝에 느낌표를 띄운다 (화면 밖에서 다가오는 상사 경고). 카메라와 상관없이 고정이다."""
    head = config.GROUND_Y + config.NPC_HEAD_HEIGHT + config.FX_HEAD_GAP
    edge_x = config.SCREEN_W - config.FX_EXCLAIM_MARGIN

    def anchor() -> tuple[float, float]:
        return edge_x, head

    return _spawn(Effect("fx_exclaim", lifetime, anchor, sprite_lookup))


def spawn_speech(
    speaker: Located,
    camera: Camera,
    line: str,
    lifetime: float,
    sprite_lookup: SpriteLookup = resource.get_sprite,
) -> Effect:
    """말하는 NPC 머리 옆에 말풍선과 대사를 띄운다."""
    anchor = _head_anchor(speaker, camera, config.FX_SPEECH_OFFSET_X)
    return _spawn(Effect("fx_speech", lifetime, anchor, sprite_lookup, label=line))
