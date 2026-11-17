"""인트로 컷신: 게임을 처음 시작할 때, 플레이에 들어가기 전에 한 번만 보여 준다.

SPACE: 자막이 나오는 중이면 한꺼번에 보여 주고, 다 나왔으면 다음 컷 (마지막 컷이면 플레이).
ESC: 인트로를 통째로 건너뛰고 플레이. 창 닫기: 종료.
컷의 자막과 길이는 intro_data.py, 수치는 config.py의 INTRO_* 에 있다.
"""

from pico2d import (
    SDL_KEYDOWN,
    SDL_QUIT,
    SDLK_ESCAPE,
    SDLK_SPACE,
    Event,
    clear_canvas,
    get_events,
    update_canvas,
)

import config
import fade
import game_framework
import intro_data
import intro_scene
import play_mode  # 순환 import지만 서로를 호출 시점에 모듈 속성으로만 쓰므로 안전하다
import text
from util import snap

# 이번 실행에서 인트로를 봤는가. 메모리에만 두고 파일에는 저장하지 않는다
intro_seen = False
cut_index = 0
cut_time = 0.0  # 지금 컷이 시작된 뒤 흐른 시간(초)
typed_chars = 0.0  # 자막을 몇 글자째까지 쳤는가 (글자 사이의 시간까지 담는 소수)
subtitle_lefts: tuple[int, ...] = ()  # 지금 컷 자막 각 줄의 왼쪽 끝 x


def current_cut() -> intro_data.Cut:
    return intro_data.CUTS[cut_index]


def typed_text(cut_text: str, chars: float) -> str:
    """자막을 chars글자째까지 친 모습. 공백·문장부호·줄바꿈도 한 글자로 센다."""
    return cut_text[: int(chars)]


def subtitle_left_edges(cut_text: str) -> tuple[int, ...]:
    """자막 각 줄의 왼쪽 끝 x.

    글자가 나오는 동안 줄이 좌우로 흔들리지 않게, 줄 전체 너비로 가운데를 맞춘 자리를 미리 구한다.
    """
    center_x = config.SCREEN_W // 2
    size = config.INTRO_SUBTITLE_SIZE
    return tuple(
        text.aligned_left(center_x, text.measure(line, size), "center")
        for line in cut_text.split("\n")
    )


def subtitle_row_y(row: int, rows: int) -> int:
    """자막 row번째 줄(위에서 0번)의 세로 중심 y. 줄 묶음 전체가 아래 띠 한가운데에 놓인다."""
    gap = config.INTRO_SUBTITLE_LINE_HEIGHT
    first_row_y = config.INTRO_LETTERBOX_H / 2 + (rows - 1) * gap / 2
    return snap(first_row_y - row * gap)


def start_cut(index: int) -> None:
    global cut_index, cut_time, typed_chars, subtitle_lefts
    cut_index = index
    cut_time = 0.0
    typed_chars = 0.0
    subtitle_lefts = subtitle_left_edges(current_cut().text)


def next_cut() -> None:
    """다음 컷으로 간다. 마지막 컷이었으면 인트로를 마친다."""
    if cut_index + 1 < len(intro_data.CUTS):
        start_cut(cut_index + 1)
    else:
        end_intro()


def end_intro() -> None:
    """인트로를 마치고 플레이로 간다 (끝까지 봤을 때도, ESC로 건너뛰었을 때도)."""
    global intro_seen
    intro_seen = True
    game_framework.change_mode(play_mode)


def complete_or_next() -> None:
    """SPACE: 자막이 나오는 중이면 한꺼번에 완성하고, 다 나와 있으면 다음 컷으로 간다."""
    global typed_chars
    length = len(current_cut().text)
    if typed_chars < length:
        typed_chars = float(length)
    else:
        next_cut()


def init() -> None:
    start_cut(0)


def finish() -> None:
    pass


def pause() -> None:
    pass


def resume() -> None:
    pass


def handle_event(event: Event) -> None:
    if event.type == SDL_QUIT:
        game_framework.quit()
    elif event.type == SDL_KEYDOWN:
        if event.key == SDLK_ESCAPE:
            end_intro()
        elif event.key == SDLK_SPACE:
            complete_or_next()


def handle_events() -> None:
    for event in get_events():
        handle_event(event)


def update() -> None:
    global cut_time, typed_chars
    dt = game_framework.frame_time
    cut = current_cut()
    cut_time += dt
    typed_chars = min(typed_chars + dt / config.INTRO_CHAR_INTERVAL, len(cut.text))
    if cut_time >= cut.run_time:
        next_cut()


def draw_subtitle() -> None:
    full_text = current_cut().text
    rows = full_text.count("\n") + 1
    typed_lines = typed_text(full_text, typed_chars).split("\n")
    for row, (left, line) in enumerate(zip(subtitle_lefts, typed_lines)):
        text.draw(
            line,
            left,
            subtitle_row_y(row, rows),
            size=config.INTRO_SUBTITLE_SIZE,
            color=config.INTRO_SUBTITLE_COLOR,
            align="left",
        )


def draw_hint() -> None:
    hint_x, hint_y = config.INTRO_HINT_POS
    text.draw(
        config.INTRO_HINT_TEXT,
        hint_x,
        hint_y,
        size=config.INTRO_HINT_SIZE,
        color=config.INTRO_HINT_COLOR,
        align="right",
    )


def draw() -> None:
    clear_canvas()
    intro_scene.draw_background()
    fade.letterbox()
    draw_subtitle()
    draw_hint()
    update_canvas()
