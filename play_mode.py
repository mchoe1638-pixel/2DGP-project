"""플레이 화면 (1인칭).

레이캐스터가 격자 지도의 바닥·천장과 벽을 그리고, 월드에 서 있는 오브젝트(get_billboard)를
빌보드로 그린 뒤(벽에 가려지는 부분은 레이캐스터가 가린다), 그 위에 1인칭 팔과 HUD를 얹는다.
플레이어는 움직일 때마다 카메라(눈)를 자기 위치로 옮기고, 마우스는 카메라의 고개를 돌린다.
참을성 게이지는 여기서 만들고 매 프레임 흘려보낸다 (플레이어는 단계를 읽기만 한다).

마우스: 화면에 들어오거나 다시 돌아오면 상대 모드로 잡아 커서를 숨기고, 나가거나 멈추면 풀어 준다.
움직인 양은 매 프레임 한 번 읽는다 (MOUSEMOTION 이벤트는 쓰지 않는다).

판이 끝나는 길은 둘이다.
- 게이지가 가득 차면 곧바로 실패 → 결과 화면.
- 골인 문 앞(goal_x)에 닿으면 문이 열리고, 시간·게이지·조작이 멈춘 채 잠깐 두었다가 성공 → 결과 화면.

ESC → 타이틀, 창 닫기 → 종료.
디버그 키 (화면에는 켜졌다는 표시를 하지 않는다): F1~F4 게이지를 평온·땀·긴장·한계 단계 시작 값으로,
G 게이지 정지, B 충돌 원 표시(미니맵), M 미니맵, F5 광선 띠 폭 바꾸기, F6 머리 흔들림 켜기/끄기,
F7 평균 FPS를 콘솔에.
나머지 키는 InputState가 받아 두고 플레이어가 읽는다 (골인한 뒤에는 받지 않는다).

소리는 게이지 단계가 바뀔 때의 배경음 전환, 꾸르륵, 한계 단계의 심장박동, 성공·실패음을 여기서 맡는다.

인트로가 끝나고 들어올 때만 화면이 검정에서 서서히 밝아지며 시작한다 (intro_mode가 prepare_fade_in으로 예약한다).
"""

from functools import partial

from pico2d import (
    SDL_KEYDOWN,
    SDL_QUIT,
    SDLK_ESCAPE,
    SDLK_F1,
    SDLK_F2,
    SDLK_F3,
    SDLK_F4,
    SDLK_F5,
    SDLK_F6,
    SDLK_F7,
    Event,
    SDLK_b,
    SDLK_g,
    SDLK_m,
    clear_canvas,
    get_events,
    update_canvas,
)

import config
import fade
import game_framework
import game_world
import input_state
import prop
import result_mode  # 순환 import지만 서로를 호출 시점에 모듈 속성으로만 쓰므로 안전하다
import sound
import title_mode  # 위와 같은 이유로 안전하다
from camera import Camera
from fps_meter import FpsMeter
from game_object import Billboard
from gauge import Gauge, GaugeStage
from hud import Hud
from input_state import InputState
from minimap import Minimap
from player import Player
from raycaster import Color, Raycaster
from stage import Stage, build_stage
from viewmodel import Viewmodel

STAGE_NUMBER = 2  # 3주차에는 스테이지 2만 있다

# 디버그 키: F1~F4는 게이지를 평온·땀·긴장·한계 단계의 시작 값으로 옮긴다 (값은 config의 경계값에서 따온다)
DEBUG_GAUGE_VALUES = {
    SDLK_F1: 0.0,
    SDLK_F2: float(config.STAGE_THRESHOLDS[0]),
    SDLK_F3: float(config.STAGE_THRESHOLDS[1]),
    SDLK_F4: float(config.STAGE_THRESHOLDS[2]),
}
DEBUG_FREEZE_KEY = SDLK_g  # 게이지 정지 켜기/끄기
DEBUG_BB_KEY = SDLK_b  # 충돌 원 표시 켜기/끄기
DEBUG_MINIMAP_KEY = SDLK_m  # 미니맵 켜기/끄기
DEBUG_STRIP_KEY = SDLK_F5  # 광선 띠 폭 바꾸기
DEBUG_HEAD_BOB_KEY = SDLK_F6  # 머리 흔들림 켜기/끄기
DEBUG_FPS_KEY = SDLK_F7  # 평균 FPS 기록 켜기/끄기
DEBUG_KEYS = frozenset(
    {
        *DEBUG_GAUGE_VALUES,
        DEBUG_FREEZE_KEY,
        DEBUG_BB_KEY,
        DEBUG_MINIMAP_KEY,
        DEBUG_STRIP_KEY,
        DEBUG_HEAD_BOB_KEY,
        DEBUG_FPS_KEY,
    }
)

stage: Stage  # init()에서 채운다
camera: Camera
gauge: Gauge
player: Player
viewmodel: Viewmodel
hud: Hud
controls: InputState
raycaster: Raycaster
minimap: Minimap
fps_meter = FpsMeter()  # 다시 하기를 눌러도 켜 둔 상태가 이어진다
head_bob_enabled = config.HEAD_BOB_ENABLED  # 머리 흔들림. F6으로 바꾼 값이 다시 하기에도 이어진다
elapsed = 0.0  # 이번 판에서 달린 시간(초). 골인한 뒤에는 흐르지 않는다
# 골인한 뒤 결과 화면까지 남은 시간(초). None이면 아직 달리는 중
goal_countdown: float | None = None
show_bb = False  # 충돌 원을 그릴지 (화면에 들어올 때마다 꺼진 채로 시작한다)
show_minimap = False  # 미니맵을 그릴지 (위와 같다)
# 검정에서 밝아지며 시작하는 연출. 인트로에서 들어올 때만 쓰고, 타이틀·결과 화면에서 들어올 때는 0이다
# 다음 init()에서 시작할 밝아짐의 길이(초). 시작하면 0으로 되돌린다
pending_fade_in = 0.0
fade_in_total = 0.0  # 이번 밝아짐의 전체 길이(초)
fade_in_left = 0.0  # 밝아짐이 끝나기까지 남은 시간(초)


def music_for(level_of_gauge: GaugeStage) -> str:
    """게이지 단계에 맞는 배경음: 긴장 단계(80%~)부터는 긴장된 곡."""
    if level_of_gauge >= GaugeStage.STRAIN:
        return sound.BGM_TENSE
    return sound.BGM_NORMAL


def switch_music(old: GaugeStage, new: GaugeStage) -> None:
    """게이지 단계가 바뀔 때 곡을 맞춘다. 같은 곡이면 sound가 그대로 둔다."""
    sound.play_bgm(music_for(new))


def prepare_fade_in(duration: float) -> None:
    """다음 init()에서 화면이 검정에서 duration초에 걸쳐 밝아지게 예약한다 (한 번 쓰면 사라진다)."""
    global pending_fade_in
    pending_fade_in = duration


def start_fade_in() -> None:
    """예약된 밝아짐을 시작하고 예약은 지운다. 예약이 없으면 밝아짐 없이 시작한다."""
    global pending_fade_in, fade_in_total, fade_in_left
    fade_in_total = pending_fade_in
    fade_in_left = pending_fade_in
    pending_fade_in = 0.0


# ---------------------------------------------------------------- 모드 함수
def init() -> None:
    global stage, camera, gauge, player, viewmodel, hud, controls, raycaster, minimap
    global elapsed, goal_countdown, show_bb, show_minimap
    game_world.clear()
    show_bb = False
    show_minimap = False
    elapsed = 0.0
    goal_countdown = None
    start_fade_in()
    stage = build_stage(STAGE_NUMBER)
    camera = Camera(*stage.player_start)
    gauge = Gauge(stage.base_rate)
    gauge.on_stage_change(switch_music)
    gauge.on_growl(partial(sound.play_sfx, sound.GROWL))
    controls = InputState()
    player = Player(stage, camera, controls, gauge, head_bob_enabled)
    viewmodel = Viewmodel(player, gauge)
    hud = Hud(stage, gauge, player)
    raycaster = Raycaster(stage.grid)
    minimap = Minimap(stage.grid)
    game_world.add_object(player, game_world.LAYER_PLAYER)
    for spec in stage.deco:
        game_world.add_object(prop.deco_prop(spec, stage), game_world.LAYER_PROP)
    sound.play_bgm(music_for(gauge.stage))
    input_state.set_mouse_captured(True)
    fps_meter.restart()


def silence_music() -> None:
    """배경음과 심장박동을 멈춘다. 이미 울리기 시작한 효과음(성공·실패음 포함)은 끝까지 울린다."""
    sound.stop_bgm()
    sound.stop_heartbeat()


def finish() -> None:
    silence_music()
    game_world.clear()
    input_state.set_mouse_captured(False)


def pause() -> None:
    input_state.set_mouse_captured(False)


def resume() -> None:
    # 멈춘 동안 뗀 키는 KEYUP을 받지 못했으니, 모두 뗀 것으로 치고 다시 시작한다
    controls.release_all()
    input_state.set_mouse_captured(True)


# ---------------------------------------------------------------- 입력
def toggle_head_bob() -> None:
    """머리 흔들림을 켜고 끈다 (꺼도 1인칭 팔은 걸음에 맞춰 움직인다)."""
    global head_bob_enabled
    head_bob_enabled = not head_bob_enabled
    player.head_bob = head_bob_enabled


def handle_debug_key(key: int) -> None:
    """디버그 키 하나를 처리한다 (어떤 키가 무엇인지는 모듈 설명 참고)."""
    global show_bb, show_minimap
    if key == DEBUG_BB_KEY:
        show_bb = not show_bb
    elif key == DEBUG_MINIMAP_KEY:
        show_minimap = not show_minimap
    elif key == DEBUG_STRIP_KEY:
        raycaster.cycle_strip_width()
    elif key == DEBUG_HEAD_BOB_KEY:
        toggle_head_bob()
    elif key == DEBUG_FPS_KEY:
        fps_meter.toggle()
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
        controls.handle_event(event)


def handle_events() -> None:
    for event in get_events():
        handle_event(event)


# ---------------------------------------------------------------- 판 진행
def finish_run(cleared: bool) -> None:
    """이번 판의 결과를 정해 결과 화면으로 넘어간다."""
    result_mode.prepare(result_mode.RunResult(cleared, elapsed, gauge.value))
    game_framework.change_mode(result_mode)


def start_goal_sequence() -> None:
    """문을 열고 플레이어를 세운다. 잠깐 뒤 결과 화면으로 넘어간다."""
    global goal_countdown
    raycaster.set_door_open(True)
    controls.release_all()
    player.halt()  # 미끄러지다 닫힌 문 칸에 부딪혀 쿵 소리가 나지 않게
    goal_countdown = config.GOAL_RESULT_DELAY
    silence_music()
    sound.play_sfx(sound.CLEAR)


def fail_run() -> None:
    """실패음을 울리고 곧바로 결과 화면으로 넘어간다 (그 뒤는 정적)."""
    silence_music()
    sound.play_sfx(sound.FAIL)
    finish_run(cleared=False)


def check_run_end() -> None:
    """게이지가 가득 찼으면 실패, 골인 문 앞에 닿았으면 골인 연출을 시작한다.

    같은 프레임에 둘이 겹치면 실패가 먼저다 (게이지는 플레이어가 움직이기 전에 오른다).
    """
    if gauge.is_full:
        fail_run()
    elif player.x >= stage.goal_x:
        start_goal_sequence()


def update_run(dt: float) -> None:
    """달리는 중의 한 프레임: 시간과 게이지를 흘리고, 움직이고, 부딪히고, 끝났는지 본다."""
    global elapsed
    elapsed += dt
    gauge.step(dt, player.is_running())
    # 심장박동은 한계 단계(95%~)에서만: 가득 찬(실패) 프레임에는 새로 울리지 않는다
    sound.update_heartbeat(dt, gauge.stage is GaugeStage.LIMIT)
    game_world.update()
    game_world.handle_collisions()  # 모두 움직인 뒤의 위치로 겹침을 본다
    check_run_end()


def update_goal_sequence(dt: float, remaining: float) -> None:
    """골인한 뒤의 한 프레임: 시간·게이지·충돌은 멈추고 월드만 흐른다. 다 되면 결과 화면으로."""
    global goal_countdown
    game_world.update()
    goal_countdown = remaining - dt
    if goal_countdown <= 0.0:
        finish_run(cleared=True)


def update() -> None:
    global fade_in_left
    dt = game_framework.frame_time
    fade_in_left = max(0.0, fade_in_left - dt)
    # 마우스 움직임은 매 프레임 읽어 비운다 (골인한 뒤에 쌓인 양이 나중에 한꺼번에 튀지 않게)
    mouse_dx, mouse_dy = input_state.poll_mouse()
    if goal_countdown is None:
        camera.look(mouse_dx, mouse_dy)
        update_run(dt)
    else:
        update_goal_sequence(dt, goal_countdown)
    viewmodel.update()
    controls.end_frame()
    fps_meter.tick(raycaster.strip_w)


# ---------------------------------------------------------------- 그리기
def floor_color() -> Color:
    """지금 밟고 있는 바닥의 색: 계단 위면 계단 색."""
    if stage.grid.is_stairs(player.x, player.y):
        return config.FLOOR_COLOR_STAIRS
    return config.FLOOR_COLOR


def billboards() -> list[Billboard]:
    """이번 프레임에 월드에 세울 그림들 (그리지 않는 오브젝트는 건너뛴다)."""
    boards = (obj.get_billboard() for obj in game_world.all_objects())
    return [board for board in boards if board is not None]


def draw() -> None:
    clear_canvas()
    raycaster.render(camera, floor_color())
    raycaster.draw_billboards(camera, billboards())
    viewmodel.draw()
    hud.draw()
    if show_minimap:
        minimap.draw(camera, show_bb=show_bb)
    if fade_in_left > 0.0:
        fade.to_black(fade_in_left / fade_in_total)
    update_canvas()
