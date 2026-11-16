"""플레이 화면.

배경·바닥·장식과 플레이어, 배치표의 장애물·아이템을 월드에 올리고, 카메라가 플레이어를 따라간다.
참을성 게이지는 여기서 만들고 매 프레임 흘려보낸다 (플레이어는 단계를 읽기만 한다).
플레이어와 장애물·아이템의 충돌은 매 프레임 갱신 뒤에 검사한다.

판이 끝나는 길은 둘이다.
- 게이지가 가득 차면 곧바로 실패 → 결과 화면.
- 골인 문에 닿으면 문이 열리고, 시간·게이지·충돌·조작이 멈춘 채 잠깐 두었다가 성공 → 결과 화면.

ESC → 타이틀, 창 닫기 → 종료, 디버그 키 F1~F4·G → 게이지 조작, B → 충돌 상자 표시.
나머지 입력은 플레이어가 받는다 (골인한 뒤에는 받지 않는다).
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
    SDLK_b,
    SDLK_g,
    clear_canvas,
    get_events,
    update_canvas,
)

import config
import game_framework
import game_world
import gfx
import level
import result_mode  # 순환 import지만 서로를 호출 시점에 모듈 속성으로만 쓰므로 안전하다
import stage_data
import title_mode  # 위와 같은 이유로 안전하다
from background import Floor, ParallaxLayer
from camera import Camera
from gauge import Gauge
from item import PLAYER_ITEM
from obstacle import PLAYER_OBSTACLE
from player import Player
from prop import WcDoor

# 디버그 키: F1~F4는 게이지를 평온·땀·긴장·한계 단계의 시작 값으로 옮긴다 (값은 config의 경계값에서 따온다)
DEBUG_GAUGE_VALUES = {
    SDLK_F1: 0.0,
    SDLK_F2: float(config.STAGE_THRESHOLDS[0]),
    SDLK_F3: float(config.STAGE_THRESHOLDS[1]),
    SDLK_F4: float(config.STAGE_THRESHOLDS[2]),
}
DEBUG_FREEZE_KEY = SDLK_g  # 게이지 정지 켜기/끄기
DEBUG_BB_KEY = SDLK_b  # 충돌 상자 표시 켜기/끄기
DEBUG_KEYS = frozenset({*DEBUG_GAUGE_VALUES, DEBUG_FREEZE_KEY, DEBUG_BB_KEY})

stage: stage_data.Stage  # init()에서 채운다
camera: Camera
gauge: Gauge
player: Player
door: WcDoor
elapsed = 0.0  # 이번 판에서 달린 시간(초). 골인한 뒤에는 흐르지 않는다
# 골인한 뒤 결과 화면까지 남은 시간(초). None이면 아직 달리는 중
goal_countdown: float | None = None
show_bb = False  # 충돌 상자를 그릴지 (화면에 들어올 때마다 꺼진 채로 시작한다)


def init() -> None:
    global stage, camera, gauge, player, elapsed, goal_countdown, show_bb
    game_world.clear()
    show_bb = False
    elapsed = 0.0
    goal_countdown = None
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
    place_props()
    place_items()
    place_obstacles()


def place_props() -> None:
    """배치표의 장식과 골인 문을 월드에 올린다 (닿는 것이 아니니 충돌 쌍은 없다)."""
    global door
    for prop in level.create_props(stage, camera):
        game_world.add_object(prop, game_world.LAYER_PROP)
    door = level.create_goal_door(stage, camera)
    game_world.add_object(door, game_world.LAYER_PROP)


def place_items() -> None:
    """배치표의 아이템을 월드에 올리고, 플레이어가 줍도록 충돌 쌍에 등록한다."""
    game_world.add_collision_pair(PLAYER_ITEM, player, None)
    for each in level.create_items(stage, camera, player):
        game_world.add_object(each, game_world.LAYER_ITEM)
        game_world.add_collision_pair(PLAYER_ITEM, None, each)


def place_obstacles() -> None:
    """배치표의 장애물을 월드에 올리고, 플레이어와 부딪히도록 충돌 쌍에 등록한다."""
    game_world.add_collision_pair(PLAYER_OBSTACLE, player, None)
    for obstacle in level.create_obstacles(stage, camera, player):
        game_world.add_object(obstacle, game_world.LAYER_OBSTACLE)
        game_world.add_collision_pair(PLAYER_OBSTACLE, None, obstacle)


def finish() -> None:
    game_world.clear()


def pause() -> None:
    pass


def resume() -> None:
    pass


def handle_debug_key(key: int) -> None:
    """F1~F4: 게이지를 각 단계의 시작 값으로. G: 게이지 정지 토글. B: 충돌 상자 표시 토글."""
    global show_bb
    if key == DEBUG_BB_KEY:
        show_bb = not show_bb
    elif key == DEBUG_FREEZE_KEY:
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
    elif goal_countdown is None:  # 골인한 뒤에는 조작을 받지 않는다
        player.handle_event(event)


def handle_events() -> None:
    for event in get_events():
        handle_event(event)


def finish_run(cleared: bool) -> None:
    """이번 판의 결과를 정해 결과 화면으로 넘어간다."""
    result_mode.prepare(result_mode.RunResult(cleared, elapsed, gauge.value))
    game_framework.change_mode(result_mode)


def start_goal_sequence() -> None:
    """문을 열고 플레이어를 세운다. 잠깐 뒤 결과 화면으로 넘어간다."""
    global goal_countdown
    door.open()
    player.release_keys()
    goal_countdown = config.GOAL_RESULT_DELAY


def check_run_end() -> None:
    """게이지가 가득 찼으면 실패, 골인 문에 닿았으면 골인 연출을 시작한다.

    같은 프레임에 둘이 겹치면 실패가 먼저다 (게이지는 플레이어가 움직이기 전에 오른다).
    """
    if gauge.is_full:
        finish_run(cleared=False)
    elif player.x >= stage.goal_x:
        start_goal_sequence()


def update_run(dt: float) -> None:
    """달리는 중의 한 프레임: 시간과 게이지를 흘리고, 움직이고, 부딪히고, 끝났는지 본다."""
    global elapsed
    elapsed += dt
    gauge.step(dt, player.is_running())
    game_world.update()
    game_world.handle_collisions()  # 모두 움직인 뒤의 위치로 겹침을 본다
    # 밀려난 위치까지 반영한 플레이어 위치로 카메라를 맞춰야 화면에서 흔들려 보이지 않는다
    camera.update(dt, player.x)
    check_run_end()


def update_goal_sequence(dt: float, remaining: float) -> None:
    """골인한 뒤의 한 프레임: 시간·게이지·충돌은 멈추고 월드만 흐른다. 다 되면 결과 화면으로."""
    global goal_countdown
    game_world.update()
    camera.update(dt, player.x)
    goal_countdown = remaining - dt
    if goal_countdown <= 0.0:
        finish_run(cleared=True)


def update() -> None:
    dt = game_framework.frame_time
    if goal_countdown is None:
        update_run(dt)
    else:
        update_goal_sequence(dt, goal_countdown)


def draw_collision_boxes() -> None:
    """충돌 상자를 가진 모든 오브젝트의 상자를 화면 좌표로 그린다 (개발용)."""
    for each in game_world.all_objects():
        box = each.get_bb()
        if box is None:
            continue
        left, bottom, right, top = box
        gfx.outline_box(
            camera.to_screen_x(left),
            bottom,
            camera.to_screen_x(right),
            top,
            config.DEBUG_BB_COLOR,
        )


def draw() -> None:
    clear_canvas()
    game_world.render()
    if show_bb:
        draw_collision_boxes()
    update_canvas()
