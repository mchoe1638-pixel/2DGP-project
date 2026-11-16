"""플레이 화면.

1단계: 배경·바닥 스크롤 확인용 뼈대. ← → 로 임시 시점을 옮긴다 (2단계에서 플레이어로 교체).
ESC → 타이틀, 창 닫기 → 종료.
"""

from pico2d import (
    SDL_KEYDOWN,
    SDL_KEYUP,
    SDL_QUIT,
    SDLK_ESCAPE,
    SDLK_LEFT,
    SDLK_RIGHT,
    Event,
    clear_canvas,
    get_events,
    update_canvas,
)

import config
import game_framework
import game_world
import stage_data
import title_mode  # 순환 import지만 서로를 호출 시점에 모듈 속성으로만 쓰므로 안전하다
from background import Floor, ParallaxLayer
from camera import Camera
from util import clamp

stage: stage_data.Stage  # init()에서 채운다
camera: Camera
focus_x = 0.0
held_keys: set[int] = set()


def init() -> None:
    global stage, camera, focus_x
    game_world.clear()
    held_keys.clear()
    stage = stage_data.get_stage(2)
    camera = Camera(config.SCREEN_W, stage.length)
    focus_x = stage.player_start_x
    camera.snap_to(focus_x)
    background = game_world.LAYER_BACKGROUND
    game_world.add_object(
        ParallaxLayer(camera, "bg_far", config.PARALLAX_FAR), background
    )
    game_world.add_object(
        ParallaxLayer(camera, "bg_mid", config.PARALLAX_MID), background
    )
    game_world.add_object(Floor(camera, stage), background)


def finish() -> None:
    game_world.clear()


def pause() -> None:
    pass


def resume() -> None:
    pass


def handle_event(event: Event) -> None:
    if event.type == SDL_QUIT:
        game_framework.quit()
    elif event.type == SDL_KEYDOWN and event.key == SDLK_ESCAPE:
        game_framework.change_mode(title_mode)
    elif event.type == SDL_KEYDOWN and event.key in (SDLK_LEFT, SDLK_RIGHT):
        held_keys.add(event.key)
    elif event.type == SDL_KEYUP:
        held_keys.discard(event.key)


def handle_events() -> None:
    for event in get_events():
        handle_event(event)


def update() -> None:
    global focus_x
    dt = game_framework.frame_time
    direction = (SDLK_RIGHT in held_keys) - (SDLK_LEFT in held_keys)
    focus_x = clamp(0, focus_x + direction * config.RUN_SPEED * dt, stage.length)
    camera.update(dt, focus_x)
    game_world.update()


def draw() -> None:
    clear_canvas()
    game_world.render()
    update_canvas()
