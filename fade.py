"""검은 가림막: 인트로의 레터박스(위·아래 띠)와 화면 전체 페이드.

둘 다 manifest의 ui_black(단색 검정 그림)을 늘려 그린다.
ui_black이 없으면 아무것도 그리지 않는다 (레터박스와 페이드를 건너뛰고 곧바로 넘어간다).
"""

import config
import resource
from util import clamp

BLACK_SPRITE = "ui_black"
MISSING_NOTE = "레터박스와 페이드를 건너뜁니다"


def _black() -> resource.Sprite | None:
    return resource.find_sprite(BLACK_SPRITE, MISSING_NOTE)


def letterbox() -> None:
    """화면 위·아래에 INTRO_LETTERBOX_H 높이의 검은 띠를 그린다."""
    black = _black()
    if black is None:
        return
    height = config.INTRO_LETTERBOX_H
    black.draw_stretched(0, 0, config.SCREEN_W, height)
    black.draw_stretched(0, config.SCREEN_H - height, config.SCREEN_W, height)


def to_black(alpha: float) -> None:
    """화면 전체를 짙기 alpha(0 투명 ~ 1 새까맘)의 검정으로 덮는다. 맨 마지막에 그려야 모두 덮인다."""
    alpha = clamp(0.0, alpha, 1.0)
    if alpha <= 0.0:
        return
    black = _black()
    if black is None:
        return
    black.draw_stretched(0, 0, config.SCREEN_W, config.SCREEN_H, alpha)
