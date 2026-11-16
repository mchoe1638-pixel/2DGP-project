"""pico2d의 draw_rectangle을 감싼 작은 그리기 도우미."""

from pico2d import draw_rectangle

import config

Color = tuple[int, int, int]


def fill_screen(color: Color) -> None:
    """화면 전체를 한 색으로 칠한다 (draw_rectangle 좌표는 끝점을 포함한다)."""
    red, green, blue = color
    draw_rectangle(
        0, 0, config.SCREEN_W - 1, config.SCREEN_H - 1, red, green, blue, 255, True
    )


def outline_box(
    left: float, bottom: float, right: float, top: float, color: Color
) -> None:
    """속이 빈 사각형 테두리 (충돌 상자 표시 등)."""
    red, green, blue = color
    draw_rectangle(
        int(left), int(bottom), int(right), int(top), red, green, blue, 255, False
    )
