"""타이틀 화면: 로고, 배를 움켜쥐고 걷는 김급해, 깜박이는 시작 안내.

SPACE → 플레이, ESC / 창 닫기 → 종료.
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
import game_framework
import gfx
import play_mode  # 순환 import지만 서로를 호출 시점에 모듈 속성으로만 쓰므로 안전하다
import resource
import text

LOGO_POS = (config.SCREEN_W // 2, 440)
WADDLE_POS = (1030, 270)
PROMPT_POS = (config.SCREEN_W // 2, 210)
PROMPT_TEXT = "SPACE 키로 시작"
PROMPT_SIZE = 32
PROMPT_COLOR = (255, 224, 102)

logo: resource.Sprite  # init()에서 채운다
waddle: resource.Sprite
elapsed = 0.0
waddle_frame = 0.0


def blink_visible(t: float, period: float) -> bool:
    """깜박임 주기의 앞 절반 동안만 보인다."""
    return t % period < period / 2


def init() -> None:
    global logo, waddle, elapsed, waddle_frame
    logo = resource.get_sprite("title_logo")
    waddle = resource.get_sprite("player_strain_waddle")
    elapsed = 0.0
    waddle_frame = 0.0


def finish() -> None:
    pass


def pause() -> None:
    pass


def resume() -> None:
    pass


def handle_event(event: Event) -> None:
    is_key_down = event.type == SDL_KEYDOWN
    if event.type == SDL_QUIT or (is_key_down and event.key == SDLK_ESCAPE):
        game_framework.quit()
    elif is_key_down and event.key == SDLK_SPACE:
        game_framework.change_mode(play_mode)


def handle_events() -> None:
    for event in get_events():
        handle_event(event)


def update() -> None:
    global elapsed, waddle_frame
    dt = game_framework.frame_time
    elapsed += dt
    waddle_frame = waddle.next_frame(waddle_frame, dt)


def draw() -> None:
    clear_canvas()
    gfx.fill_screen(config.TITLE_BG_COLOR)
    logo.draw(*LOGO_POS)
    waddle.draw(*WADDLE_POS, frame=waddle_frame, scale=config.TITLE_WADDLE_SCALE)
    if blink_visible(elapsed, config.TITLE_BLINK_PERIOD):
        text.draw(
            PROMPT_TEXT,
            *PROMPT_POS,
            size=PROMPT_SIZE,
            color=PROMPT_COLOR,
            bold=True,
            align="center"
        )
    update_canvas()
