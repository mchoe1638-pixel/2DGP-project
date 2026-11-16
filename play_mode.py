"""플레이 화면.

배경·바닥과 플레이어를 월드에 올리고, 카메라가 플레이어를 따라간다.
참을성 게이지는 여기서 만들고 매 프레임 흘려보낸다 (플레이어는 단계를 읽기만 한다).
ESC → 타이틀, 창 닫기 → 종료, 디버그 키 F1~F4·G → 게이지 조작. 나머지 입력은 플레이어가 받는다.
"""

from pico2d import (
    SDL_KEYDOWN,
    SDL_QUIT,
    SDLK_ESCAPE,
    SDLK_F1,
    SDLK_F2,
    SDLK_F3,
    SDLK_F4,
    Event,
    SDLK_g,
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
from gauge import Gauge
from player import Player

# 디버그 키: F1~F4는 게이지를 평온·땀·긴장·한계 단계의 시작 값으로 옮긴다 (값은 config의 경계값에서 따온다)
DEBUG_GAUGE_VALUES = {
    SDLK_F1: 0.0,
    SDLK_F2: float(config.STAGE_THRESHOLDS[0]),
    SDLK_F3: float(config.STAGE_THRESHOLDS[1]),
    SDLK_F4: float(config.STAGE_THRESHOLDS[2]),
}
DEBUG_FREEZE_KEY = SDLK_g  # 게이지 정지 켜기/끄기
DEBUG_KEYS = frozenset({*DEBUG_GAUGE_VALUES, DEBUG_FREEZE_KEY})

stage: stage_data.Stage  # init()에서 채운다
camera: Camera
gauge: Gauge
player: Player


def init() -> None:
    global stage, camera, gauge, player
    game_world.clear()
    stage = stage_data.get_stage(2)
    camera = Camera(config.SCREEN_W, stage.length)
    gauge = Gauge(config.GAUGE_BASE_RATE[stage.number])
    player = Player(stage, camera, gauge=gauge)
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


def handle_debug_key(key: int) -> None:
    """F1~F4: 게이지를 각 단계의 시작 값으로. G: 게이지 정지 토글."""
    if key == DEBUG_FREEZE_KEY:
        gauge.toggle_debug_freeze()
    else:
        gauge.set_value(DEBUG_GAUGE_VALUES[key])


def handle_event(event: Event) -> None:
    if event.type == SDL_QUIT:
        game_framework.quit()
    elif event.type == SDL_KEYDOWN and event.key == SDLK_ESCAPE:
        game_framework.change_mode(title_mode)
    elif event.type == SDL_KEYDOWN and event.key in DEBUG_KEYS:
        handle_debug_key(event.key)
    else:
        player.handle_event(event)


def handle_events() -> None:
    for event in get_events():
        handle_event(event)


def update() -> None:
    dt = game_framework.frame_time
    gauge.step(dt, player.is_running())
    game_world.update()
    # 플레이어가 이번 프레임에 움직인 뒤의 위치로 카메라를 맞춰야 화면에서 흔들려 보이지 않는다
    camera.update(dt, player.x)


def draw() -> None:
    clear_canvas()
    game_world.render()
    update_canvas()
