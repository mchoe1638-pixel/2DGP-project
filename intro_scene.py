"""인트로 장면 그리기: 지하철 안 배경 (그림이 없으면 윤곽선만 그린 대용 배경)."""

import config
import gfx
import resource

BACKGROUND_SPRITE = "bg_train_inside"
MISSING_NOTE = "윤곽선만 그린 대용 배경을 씁니다"


def draw_background() -> None:
    """지하철 안 배경을 원래 크기로 화면 한가운데에 그린다."""
    background = resource.find_sprite(BACKGROUND_SPRITE, MISSING_NOTE)
    if background is None:
        draw_fallback_background()
        return
    background.draw(config.SCREEN_W // 2, config.SCREEN_H // 2)


def draw_fallback_background() -> None:
    """검은 바탕에 창 세 개·손잡이 기둥·문·바닥선의 윤곽선만 그린다."""
    gfx.fill_screen(config.INTRO_FALLBACK_BG_COLOR)
    color = config.INTRO_FALLBACK_LINE_COLOR
    boxes = (
        *config.INTRO_FALLBACK_WINDOWS,
        *config.INTRO_FALLBACK_POLES,
        config.INTRO_FALLBACK_DOOR,
    )
    for left, bottom, right, top in boxes:
        gfx.outline_box(left, bottom, right, top, color)
    floor_y = config.INTRO_FLOOR_Y
    gfx.outline_box(0, floor_y, config.SCREEN_W - 1, floor_y, color)
