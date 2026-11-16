"""결과 화면: 성공이면 노란 배경에 걸린 시간·최종 게이지를, 실패면 검은 화면에 한 줄만 보여 준다.

SPACE → 곧바로 다시 플레이, ESC → 타이틀, 창 닫기 → 종료.
점프하던 SPACE 연타로 화면이 뜨자마자 다시 시작해 버리지 않도록, 처음 잠깐은 키를 받지 않는다.
최고 기록 같은 것은 나중에 RunResult를 받아 붙이면 된다 (지금은 저장하지 않는다).
"""

from dataclasses import dataclass

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
import game_framework
import gfx
import play_mode  # 순환 import지만 서로를 호출 시점에 모듈 속성으로만 쓰므로 안전하다
import text
import title_mode  # 위와 같은 이유로 안전하다

CENTER_X = config.SCREEN_W // 2
CLEAR_HEADLINE = "CLEAR! 무사 도착"
FAIL_LINE = "…늦었다"
PROMPT_TEXT = "SPACE 다시하기 / ESC 타이틀"
HEADLINE_POS = (CENTER_X, 470)
TIME_POS = (CENTER_X, 360)
GAUGE_POS = (CENTER_X, 300)
FAIL_LINE_POS = (CENTER_X, 420)
PROMPT_POS = (CENTER_X, 170)
HEADLINE_SIZE = 66  # Galmuri11은 11의 배수 크기에서 또렷하다
STAT_SIZE = 33
PROMPT_SIZE = 22
CLEAR_INK = config.TITLE_BG_COLOR  # 노란 배경 위의 짙은 남색 글자
FAIL_INK = (255, 255, 255)
FAIL_PROMPT_COLOR = (170, 170, 180)


@dataclass(frozen=True)
class RunResult:
    """한 판의 결과: 성공했는지, 걸린 시간(초), 끝났을 때의 게이지(%)."""

    cleared: bool
    seconds: float
    gauge: float


result = RunResult(cleared=False, seconds=0.0, gauge=0.0)
elapsed = 0.0  # 이 화면이 뜬 뒤 흐른 시간(초)


def prepare(new_result: RunResult) -> None:
    """다음에 보여 줄 결과를 정한다. 결과 화면으로 넘어가기 직전에 부른다."""
    global result
    result = new_result


def init() -> None:
    global elapsed
    elapsed = 0.0


def finish() -> None:
    pass


def pause() -> None:
    pass


def resume() -> None:
    pass


def handle_event(event: Event) -> None:
    if event.type == SDL_QUIT:
        game_framework.quit()
    elif event.type != SDL_KEYDOWN or elapsed < config.RESULT_INPUT_GUARD:
        return
    elif event.key == SDLK_SPACE:
        game_framework.change_mode(play_mode)
    elif event.key == SDLK_ESCAPE:
        game_framework.change_mode(title_mode)


def handle_events() -> None:
    for event in get_events():
        handle_event(event)


def update() -> None:
    global elapsed
    elapsed += game_framework.frame_time


def draw_clear() -> None:
    gfx.fill_screen(config.RESULT_CLEAR_BG_COLOR)
    text.draw(
        CLEAR_HEADLINE,
        *HEADLINE_POS,
        size=HEADLINE_SIZE,
        color=CLEAR_INK,
        bold=True,
        align="center",
    )
    text.draw(
        f"걸린 시간 {result.seconds:.1f}초",
        *TIME_POS,
        size=STAT_SIZE,
        color=CLEAR_INK,
        align="center",
    )
    text.draw(
        f"최종 게이지 {int(result.gauge)}%",  # 99.9%로 깼는데 100%로 보이지 않게 버린다
        *GAUGE_POS,
        size=STAT_SIZE,
        color=CLEAR_INK,
        align="center",
    )
    draw_prompt(CLEAR_INK)


def draw_fail() -> None:
    gfx.fill_screen(config.RESULT_FAIL_BG_COLOR)
    text.draw(
        FAIL_LINE,
        *FAIL_LINE_POS,
        size=HEADLINE_SIZE,
        color=FAIL_INK,
        bold=True,
        align="center",
    )
    draw_prompt(FAIL_PROMPT_COLOR)


def draw_prompt(color: tuple[int, int, int]) -> None:
    text.draw(PROMPT_TEXT, *PROMPT_POS, size=PROMPT_SIZE, color=color, align="center")


def draw() -> None:
    clear_canvas()
    if result.cleared:
        draw_clear()
    else:
        draw_fail()
    update_canvas()
