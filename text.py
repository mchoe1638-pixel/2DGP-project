"""Galmuri11 한글 텍스트 그리기.

pico2d.Font는 draw할 때마다 텍스처를 새로 만들므로, 여기서는 폰트 객체만 크기별로 캐시한다.
"""

import ctypes
from typing import TYPE_CHECKING

import config
import resource

if TYPE_CHECKING:
    from pico2d import Font

_fonts: dict[tuple[int, bool], "Font"] = {}


def aligned_left(x: int, text_width: int, align: str) -> int:
    """정렬 기준점 x에서 글자 왼쪽 끝의 x를 구한다."""
    if align == "left":
        return x
    if align == "center":
        return x - text_width // 2
    if align == "right":
        return x - text_width
    raise ValueError(f"알 수 없는 정렬 방식: {align!r} (left / center / right 중 하나)")


def _font(size: int, bold: bool) -> "Font":
    key = (size, bold)
    font = _fonts.get(key)
    if font is None:
        import pico2d  # 지연 import: 캔버스 없이 이 모듈을 import하는 테스트를 위해

        path = resource.require_font_file(
            config.FONT_BOLD if bold else config.FONT_REGULAR
        )
        font = pico2d.load_font(path, size)
        _fonts[key] = font
    return font


def measure(string: str, size: int, bold: bool = False) -> int:
    """글자가 차지하는 가로 픽셀 수."""
    import pico2d

    width, height = ctypes.c_int(0), ctypes.c_int(0)
    pico2d.TTF_SizeUTF8(
        _font(size, bold).font,
        string.encode("utf-8"),
        ctypes.byref(width),
        ctypes.byref(height),
    )
    return width.value


def draw(
    string: str,
    x: int,
    y: int,
    size: int = 24,
    color: tuple[int, int, int] = (255, 255, 255),
    bold: bool = False,
    align: str = "left",
) -> None:
    """(x, y)에 글자를 그린다. y는 글자의 세로 중심, x는 align이 가리키는 기준점이다."""
    if not string:
        return  # 빈 문자열은 SDL_ttf가 표면을 만들지 못한다
    left = aligned_left(x, measure(string, size, bold), align)
    _font(size, bold).draw(left, y, string, color)
