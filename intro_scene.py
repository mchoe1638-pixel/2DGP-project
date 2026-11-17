"""인트로 장면 그리기: 지하철 안 배경(그림이 없으면 윤곽선만 그린 대용 배경), 행인, 김급해, 머리 위 느낌표.

배경과 캐릭터는 열차를 따라 함께 위아래로 흔들린다. 레터박스·자막·페이드는 여기서 그리지 않으니 흔들리지 않는다.
캐릭터와 이펙트는 INTRO_CHAR_SCALE배로 키워 그리고, 배경은 원래 크기 그대로다.
"""

import math

import config
import gfx
import intro_data
import resource
from util import snap

BACKGROUND_SPRITE = "bg_train_inside"
MISSING_NOTE = "윤곽선만 그린 대용 배경을 씁니다"
EXCLAIM_SPRITE = "fx_exclaim"


def sway_offset(cut: intro_data.Cut, t: float) -> int:
    """컷이 시작된 뒤 t초일 때 장면이 위아래로 흔들린 픽셀 수. 사인 곡선이고, 컷에 따라 점점 잦아든다."""
    wave = math.sin(config.INTRO_SWAY_SPEED * t)
    return snap(config.INTRO_SWAY_AMPLITUDE * cut.sway_strength(t) * wave)


def draw_background(sway: int) -> None:
    """지하철 안 배경을 원래 크기로 화면 한가운데에, sway만큼 위아래로 옮겨 그린다."""
    background = resource.find_sprite(BACKGROUND_SPRITE, MISSING_NOTE)
    if background is None:
        draw_fallback_background(sway)
        return
    background.draw(config.SCREEN_W // 2, config.SCREEN_H // 2 + sway)


def draw_fallback_background(sway: int) -> None:
    """검은 바탕에 창 세 개·손잡이 기둥·문·바닥선의 윤곽선만 그린다."""
    gfx.fill_screen(config.INTRO_FALLBACK_BG_COLOR)
    color = config.INTRO_FALLBACK_LINE_COLOR
    boxes = (
        *config.INTRO_FALLBACK_WINDOWS,
        *config.INTRO_FALLBACK_POLES,
        config.INTRO_FALLBACK_DOOR,
    )
    for left, bottom, right, top in boxes:
        gfx.outline_box(left, bottom + sway, right, top + sway, color)
    floor_y = config.INTRO_FLOOR_Y + sway
    gfx.outline_box(0, floor_y, config.SCREEN_W - 1, floor_y, color)


def standing_center_y(sprite: resource.Sprite, sway: int) -> float:
    """발바닥이 지하철 바닥선(INTRO_FLOOR_Y)에 닿도록 키워 그린 스프라이트의 중심 y.

    그림 칸 맨 아래에는 FOOT_OFFSET만큼 빈 줄이 있고, 키운 만큼 그 빈 줄도 커진다.
    """
    scale = config.INTRO_CHAR_SCALE
    return (
        config.INTRO_FLOOR_Y
        + sprite.frame_h * scale / 2
        - config.FOOT_OFFSET * scale
        + sway
    )


def draw_character(
    sprite: resource.Sprite, x: float, sway: int, age: float, flip: bool = False
) -> None:
    """발이 바닥선에 닿게 선 캐릭터를 키워서 그린다. age(초)로 그 자세의 애니메이션 칸을 고른다."""
    sprite.draw(
        x,
        standing_center_y(sprite, sway),
        frame=age * sprite.fps,
        flip=flip,
        scale=config.INTRO_CHAR_SCALE,
    )


def draw_exclaim(x: float, age: float, sway: int) -> None:
    """김급해 머리 위의 느낌표. x는 머리 가운데이고, age(초)로 깜박이는 칸을 고른다.

    김급해도 행인과 몸 크기가 같아 머리 위 높이(NPC_HEAD_HEIGHT)를 그대로 쓴다. 머리와의 간격도 함께 키운다.
    """
    sprite = resource.get_sprite(EXCLAIM_SPRITE)
    scale = config.INTRO_CHAR_SCALE
    head_gap = config.NPC_HEAD_HEIGHT + config.FX_HEAD_GAP
    anchor_y = config.INTRO_FLOOR_Y + head_gap * scale  # 그림의 아래쪽 가운데
    centre_y = anchor_y + sprite.frame_h * scale / 2 + sway
    sprite.draw(x, centre_y, frame=age / config.FX_FRAME_PERIOD, scale=scale)


def draw_scene(cut: intro_data.Cut, t: float) -> None:
    """컷이 시작된 뒤 t초의 장면을 뒤에서 앞으로 그린다: 배경 → 행인 → 김급해 → 느낌표."""
    sway = sway_offset(cut, t)
    draw_background(sway)
    for extra in intro_data.CROWD:
        sprite = resource.get_sprite(extra.sprite)
        draw_character(sprite, extra.x, sway, t, extra.flip)
    pose = cut.pose_at(t)
    player_x = config.INTRO_CHAR_X["player"]
    draw_character(resource.get_sprite(pose.sprite), player_x, sway, t - pose.at)
    exclaim_age = cut.exclaim_age(t)
    if exclaim_age is not None:
        draw_exclaim(player_x, exclaim_age, sway)
