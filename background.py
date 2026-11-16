"""시차 스크롤 배경(bg_far, bg_mid)과 바닥(floor_tile, floor_stairs).

타일 배치 계산은 순수 함수로 분리해 두어 캔버스 없이 테스트한다.
"""

from typing import NamedTuple

import config
import resource
from camera import Camera
from game_object import GameObject
from stage_data import Stage

FLOOR_FLAT = "floor_tile"
FLOOR_STAIRS = "floor_stairs"


class FloorSegment(NamedTuple):
    """같은 바닥 타일이 이어지는 월드 구간 [start, end)."""

    start: int
    end: int
    sprite: str


def parallax_offset(camera_x: int, factor: float, tile_w: int) -> int:
    """배경 한 장 안에서 왼쪽 가장자리가 잘려 나간 픽셀 수 (factor배로 느리게 스크롤)."""
    return int(camera_x * factor) % tile_w


def parallax_tile_lefts(offset: int, tile_w: int, view_w: int) -> list[int]:
    """화면을 빈틈없이 덮는 데 필요한 배경 타일들의 화면 x(왼쪽 모서리)."""
    lefts = []
    left = -offset
    while left < view_w:
        lefts.append(left)
        left += tile_w
    return lefts


def floor_segments(stage: Stage) -> list[FloorSegment]:
    """스테이지를 평지/계단 구간으로 나눈다."""
    if stage.stairs_zone is None:
        return [FloorSegment(0, stage.length, FLOOR_FLAT)]
    stairs_start, stairs_end = stage.stairs_zone
    candidates = (
        FloorSegment(0, stairs_start, FLOOR_FLAT),
        FloorSegment(stairs_start, stairs_end, FLOOR_STAIRS),
        FloorSegment(stairs_end, stage.length, FLOOR_FLAT),
    )
    return [segment for segment in candidates if segment.start < segment.end]


def floor_spans(
    segment: FloorSegment, tile_w: int, camera_x: int, view_w: int
) -> list[tuple[int, int]]:
    """화면에 보이는 타일들을 (화면 x, 잘라 그릴 너비)로 돌려준다.

    타일은 구간 시작점부터 이어 붙이고, 구간 끝의 마지막 타일은 남은 너비만 그린다.
    """
    first_visible = max(segment.start, camera_x)
    last_visible = min(segment.end, camera_x + view_w)
    if first_visible >= last_visible:
        return []
    tile_start = segment.start + (first_visible - segment.start) // tile_w * tile_w
    spans = []
    while tile_start < last_visible:
        spans.append((tile_start - camera_x, min(tile_w, segment.end - tile_start)))
        tile_start += tile_w
    return spans


class ParallaxLayer(GameObject):
    """카메라보다 factor배 느리게 흐르는 가로 반복 배경."""

    def __init__(self, camera: Camera, sprite_name: str, factor: float) -> None:
        self.camera = camera
        self.sprite = resource.get_sprite(sprite_name)
        self.factor = factor

    def draw(self) -> None:
        tile_w = self.sprite.frame_w
        offset = parallax_offset(self.camera.x, self.factor, tile_w)
        for left in parallax_tile_lefts(offset, tile_w, config.SCREEN_W):
            self.sprite.draw_at_origin(left, 0)


class Floor(GameObject):
    """카메라와 같은 속도(1.0)로 흐르는 바닥. 계단 구간은 floor_stairs로 바뀐다."""

    def __init__(self, camera: Camera, stage: Stage) -> None:
        self.camera = camera
        self.segments = floor_segments(stage)

    def draw(self) -> None:
        for segment in self.segments:
            sprite = resource.get_sprite(segment.sprite)
            for x, clip_w in floor_spans(
                segment, sprite.frame_w, self.camera.x, config.SCREEN_W
            ):
                sprite.draw_at_origin(x, 0, clip_w=clip_w)
