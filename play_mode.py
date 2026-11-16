"""플레이 화면.

배경·바닥과 플레이어를 월드에 올리고, 카메라가 플레이어를 따라간다.
ESC → 타이틀, 창 닫기 → 종료. 나머지 입력은 모두 플레이어가 받는다.
"""

from pico2d import (
    SDL_KEYDOWN,
    SDL_QUIT,
    SDLK_ESCAPE,
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
from player import Player

stage: stage_data.Stage  # init()에서 채운다
camera: Camera
player: Player


def init() -> None:
    global stage, camera, player
    game_world.clear()
    stage = stage_data.get_stage(2)
    camera = Camera(config.SCREEN_W, stage.length)
    player = Player(stage, camera)
    camera.snap_to(player.x)
    background = game_world.LAYER_BACKGROUND
    game_world.add_object(
        ParallaxLayer(camera, "bg_far", config.PARALLAX_FAR), background
    )
    game_world.add_object(
        ParallaxLayer(camera, "bg_mid", config.PARALLAX_MID), background
    )
    game_world.add_object(Floor(camera, stage), background)
    game_world.add_object(player, game_world.LAYER_PLAYER)


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
    else:
        player.handle_event(event)


def handle_events() -> None:
    for event in get_events():
        handle_event(event)


def update() -> None:
    game_world.update()
    # 플레이어가 이번 프레임에 움직인 뒤의 위치로 카메라를 맞춰야 화면에서 흔들려 보이지 않는다
    camera.update(game_framework.frame_time, player.x)


def draw() -> None:
    clear_canvas()
    game_world.render()
    update_canvas()
