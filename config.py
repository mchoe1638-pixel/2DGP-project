"""BLADDER RUN 설정값.

게임 규칙·밸런스에 쓰이는 숫자는 모두 이 파일에서만 정의한다.
다른 모듈은 값을 읽기만 하고, 같은 숫자를 다시 적지 않는다.

단위: 월드는 m·s·rad (1칸 = 1m, 예전 60px = 1m). 화면에 그리는 값만 px이다.
"""

import os

# ---------------------------------------------------------------- 경로
MANIFEST_RELATIVE_PATH = os.path.join("resource", "image", "manifest.json")
ASSET_FOLDER_FALLBACK = "bladder_run_resource"


def find_asset_root(base_dir: str) -> str:
    """`resource/` 폴더를 품고 있는 폴더(= manifest의 file 경로 기준)를 찾는다.

    코드와 같은 폴더에 resource/ 가 있으면 그곳을, 없으면 bladder_run_resource/ 를 쓴다.
    """
    candidates = (base_dir, os.path.join(base_dir, ASSET_FOLDER_FALLBACK))
    for candidate in candidates:
        if os.path.isfile(os.path.join(candidate, MANIFEST_RELATIVE_PATH)):
            return candidate
    raise FileNotFoundError(
        "resource 폴더를 찾을 수 없습니다. "
        f"다음 위치 중 한 곳에 resource/image/manifest.json 이 있어야 합니다: {', '.join(candidates)}"
    )


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSET_ROOT = find_asset_root(BASE_DIR)
MANIFEST_PATH = os.path.join(ASSET_ROOT, MANIFEST_RELATIVE_PATH)
SOUND_DIR = os.path.join(ASSET_ROOT, "resource", "sound")
FONT_DIR = os.path.join(ASSET_ROOT, "resource", "font")
FONT_REGULAR = os.path.join(FONT_DIR, "Galmuri11.ttf")
FONT_BOLD = os.path.join(FONT_DIR, "Galmuri11-Bold.ttf")

# ---------------------------------------------------------------- 화면 / 루프
SCREEN_W = 1280
SCREEN_H = 720
MAX_FRAME_TIME = (
    0.05  # 창을 끌거나 로딩이 길어도 한 프레임이 이 시간 이상 흐르지 않게 한다
)

# ---------------------------------------------------------------- 지면 / 스프라이트
GROUND_Y = 120  # 바닥 윗면의 y (pico2d 좌표: 화면 아래가 0)
FOOT_OFFSET = 3  # 캐릭터 발이 바닥 윗면보다 이만큼 파묻혀 보이게 그린다
DEFAULT_ANIM_FPS = 2  # manifest에 fps가 없는 시트(NPC 등)의 기본 애니메이션 속도

# ---------------------------------------------------------------- 렌더링 (레이캐스팅)
FOV_DEG = 75  # 가로 시야각(도)
RAY_STRIP_W = 4  # 광선 하나가 맡는 화면 세로 띠의 폭(px). 시작 값
RAY_STRIP_CHOICES = (2, 4, 8)  # F5로 돌아가며 고르는 띠 폭(px)
RAY_MIN_DIST = 0.05  # 벽에 바짝 붙어도 벽까지 거리를 이보다 짧게 치지 않는다(m)
WALL_HEIGHT = 3.0  # 벽 높이(m)
PITCH_MAX_PX = 220  # 위아래로 볼 때 지평선이 화면 가운데에서 움직이는 최대 거리(px)
FOG_K = 0.12  # 거리 어둡게: 밝기 = 1 / (1 + 거리 × FOG_K)
SIDE_SHADE = 0.8  # y축에 수직인 벽면(side 1)은 이만큼 더 어둡게
GRADIENT_BANDS = 8  # 바닥·천장을 이 개수의 띠로 나눠 칠한다 (바닥 캐스팅 없음)
CEIL_COLOR = (58, 62, 78)
FLOOR_COLOR = (92, 96, 104)
FLOOR_COLOR_STAIRS = (110, 100, 88)  # 플레이어가 계단 구역에 있을 때의 바닥 색
SPRITE_M_PER_PX = 0.014  # 스프라이트 그림 1px이 월드에서 차지하는 높이(m)
# 벽 텍스처가 manifest에 없을 때 대신 칠하는 단색
WALL_FALLBACK_COLORS = {
    "tex_wall_tile": (150, 160, 170),
    "tex_wall_ad": (170, 140, 120),
    "tex_wall_train": (90, 130, 110),
    "tex_wall_stairs": (130, 120, 110),
    "tex_wall_sign_wc": (230, 200, 60),
    "tex_door_wc": (60, 110, 210),  # 닫힌 문: 파랑
}
DOOR_OPEN_FALLBACK_COLOR = (70, 180, 90)  # 열린 문: 초록

# ---------------------------------------------------------------- 마우스
MOUSE_SENS_YAW = 0.0025  # rad / px
MOUSE_SENS_PITCH = 0.9  # px / px
MOUSE_INVERT_Y = False  # True면 마우스를 내릴 때 위를 본다

# ---------------------------------------------------------------- 이동 / 점프 (m, s)
WALK_MAX = 3.3  # 걷기 최고 속도(m/s)
RUN_MAX = 6.7  # SHIFT 달리기 최고 속도(m/s)
BACK_MAX = 2.0  # 뒤로 걸을 때 최고 속도(m/s)
ACCEL_GROUND = 9.0  # 땅에서 입력이 있을 때 가속(m/s²)
DECEL_GROUND = 10.0  # 땅에서 입력이 없을 때 감속(m/s²)
ACCEL_AIR = 2.5  # 공중에서 방향을 바꾸는 가속(m/s²)
JUMP_V = 4.7  # 점프 첫 속도(m/s). 정점 약 0.79m, 체공 약 0.67초
GRAVITY = 14.0  # m/s²
PLAYER_RADIUS = 0.3  # 플레이어 충돌 원 반지름(m)
EYE_HEIGHT = 1.6  # 서 있을 때 눈높이(m)
EYE_FALL_HEIGHT = 0.5  # 넘어졌을 때 눈높이(m)
FALL_SPEED = 4.5  # 이 수평 속도(m/s) 이상으로 장애물에 부딪히면 넘어진다
WALL_BUMP_SPEED = 5.0  # 이 속도(m/s) 이상으로 벽에 부딪히면 쿵 소리
CROWD_PUSH = 2.0  # 인파에 닿으면 뒤로 밀려나는 거리(m)
HIGH_ITEM_Z = 2.1  # 'high' 아이템이 떠 있는 높이(m)
HIGH_ITEM_NEED_Z = 0.3  # 'high' 아이템을 먹으려면 발이 이만큼 떠 있어야 한다(m)
STAIRS_SPEED_MULT = 0.7  # 계단 구역에서 최고 속도에 곱한다
COLLISION_SUBSTEP = 0.25  # 한 번에 이보다 길게 움직이면 나눠서 벽을 검사한다(m)

# ---------------------------------------------------------------- 충돌 박스 (발 기준)
NPC_BB_HALF_W = 22
NPC_BB_HEIGHT = 100  # 걷는 중 점프로도 넘을 수 있는 높이
CROWD_BB_HEIGHT = 220  # 인파는 점프로 넘을 수 없다

# ---------------------------------------------------------------- 참을성 게이지
GAUGE_MAX = 100.0
# 상승 속도(%/s)는 스테이지 데이터의 base_rate를 쓴다 (stage_data.py)
RUN_GAUGE_MULT = 1.6  # 달리는 동안 게이지 상승 배율
# 단계 경계값: 50 땀 / 80 긴장 / 95 한계 / 100 실패 (0~49는 평온)
STAGE_THRESHOLDS = (50, 80, 95, 100)
SWEAT_SPEED_MULT = 0.9  # 땀 단계(50%~)부터 이동 속도에 곱한다
GROWL_INTERVAL = (8.0, 12.0)  # 땀 단계부터 꾸르륵 소리 간격(초)의 범위

# ---------------------------------------------------------------- 장애물 공통
FALL_STOP_TIME = 1.0  # 달리다 부딪혀 넘어졌을 때 못 움직이는 시간(초)
FALL_GAUGE_ADD = 10.0  # 넘어질 때 게이지가 한 번에 오르는 양(%)
NPC_EXIT_SPEED = 60  # 볼일을 마친 NPC가 오른쪽으로 걸어 나가는 속도(px/s)
NPC_FADE_TIME = 0.8  # 걸어 나가며 서서히 사라지는 시간(초)

# ---------------------------------------------------------------- 관광객 / 전단지 / 상사
TOURIST_STOP_TIME = 2.0  # 관광객에게 붙잡혀 멈추는 시간(초)
FLYER_SLOW_TIME = 3.0  # 전단지를 받고 느려지는 시간(초)
FLYER_SPEED_MULT = 0.5  # 전단지를 든 동안 이동 속도에 곱한다 (계단·땀 감속과 겹친다)
BOSS_WARN_DISTANCE = 600  # 상사가 이만큼 가까이 오면 "!"가 뜬다 (화면 밖에서도 경고)
BOSS_EXCLAIM_TIME = 0.5  # "!"가 떠 있는 시간. 이 동안 상사는 제자리에 서 있다
BOSS_WALK_SPEED = 160  # 경고 뒤 상사가 왼쪽(플레이어 쪽)으로 걸어오는 속도(px/s)
BOSS_STOP_TIME = 1.5  # 상사의 잔소리 때문에 멈추는 시간(초)
BOSS_GAUGE_ADD = 15.0  # 상사를 만났을 때 게이지가 오르는 양(%)
BOSS_SPEECH_TEXT = "김대리~ 잠깐만!"  # 말풍선 대사 (기획서)

# ---------------------------------------------------------------- 인파
CROWD_MEMBER_SPACING = (
    44  # 인파 속 사람 사이 간격 = NPC 충돌 박스 폭 (어깨를 맞대고 선다)
)
CROWD_PUSH_DISTANCE = (
    120  # 인파에 닿으면 이만큼 뒤로 밀려난다 (가장 넓은 인파를 벗어날 만큼)
)
CROWD_GAP_PERIOD = 2.5  # 틈이 열렸다 닫히는 한 주기(초)
CROWD_GAP_OPEN_TIME = 1.0  # 한 주기 중 틈이 열려 있는 시간(초). 주기의 끝에 온다
CROWD_GAP_EASE = 0.25  # 틈이 벌어지고 닫힐 때 사람들이 움직이는 시간(초)
CROWD_GAP_SHIFT_X = 30  # 틈이 열릴 때 가운데 사람이 옆으로 비켜서는 거리(px)
CROWD_GAP_SHIFT_Y = 40  # 틈이 열릴 때 가운데 사람이 위아래로 비켜서는 거리(px)

# ---------------------------------------------------------------- 아이템 / 장식
ITEM_BB_SCALE = 0.8  # 아이템 충돌 상자는 이미지 크기의 이 비율
ITEM_BOB_AMPLITUDE = 5  # 둥둥 뜨는 폭(px). 배치표 높이보다 아래로는 안 내려간다
ITEM_BOB_PERIOD = 1.4  # 한 번 오르내리는 시간(초)
ITEM_BREATH_GAUGE_DROP = 15.0  # 심호흡이 게이지에서 덜어 내는 양(%)
ITEM_GUM_FREEZE_TIME = 3.0  # 껌이 게이지 상승을 붙잡는 시간(초)
ITEM_SHORTCUT_DISTANCE = 800  # 지름길이 플레이어를 앞으로 보내는 거리(px)

# ---------------------------------------------------------------- 이펙트 / 디버그
FX_FRAME_PERIOD = 0.12  # 이펙트 시트가 한 칸 넘어가는 시간(초)
FX_DUST_TIME = 0.36  # 먼지 한 덩이가 떠 있는 시간(초). 3칸을 한 번씩 보여 준다
FX_DUST_OFFSETS = (-28, 0, 28)  # 먼지 세 덩이가 한 자리 둘레에 놓이는 가로 위치(px)
NPC_HEAD_HEIGHT = 132  # 바닥에서 NPC 머리 꼭대기까지 (이펙트 위치 기준)
FX_HEAD_GAP = 6  # 머리 위에 띄우는 이펙트와 머리 사이 틈
FX_STARS_HEIGHT = 118  # 바닥에서 별 이펙트 아래끝까지 (플레이어 머리 둘레)
FX_PAPER_HEIGHT = 70  # 바닥에서 전단지 이펙트 아래끝까지 (플레이어 가슴 높이)
FX_EXCLAIM_MARGIN = 60  # "!"는 화면 오른쪽 끝에서 이만큼 안쪽에 고정해 띄운다
FX_SPEECH_OFFSET_X = -61  # 말풍선은 말하는 사람의 이만큼 옆(왼쪽)에 띄운다
FX_SPEECH_TEXT_OFFSET = (0, 4)  # 말풍선 그림 중심에서 대사 글자까지의 어긋남
FX_SPEECH_TEXT_SIZE = 16
FX_SPEECH_TEXT_COLOR = (40, 40, 48)  # 말풍선은 밝은 바탕이라 어두운 글자
DEBUG_BB_COLOR = (255, 64, 64)  # B 키로 켜는 충돌 원 색

# ---------------------------------------------------------------- 디버그 미니맵 (M) / FPS (F7)
MINIMAP_CELL_PX = 8  # 격자 한 칸을 미니맵에서 그리는 크기(px)
MINIMAP_VIEW_COLS = 36  # 플레이어 둘레로 보여 주는 가로 칸 수 (세로는 지도 전체)
MINIMAP_MARGIN = 16  # 화면 오른쪽 아래 모서리에서 떨어진 거리(px)
MINIMAP_FLOOR_COLOR = (28, 28, 38)
MINIMAP_STAIRS_COLOR = (64, 52, 40)
MINIMAP_PLAYER_COLOR = (255, 210, 63)
MINIMAP_PLAYER_PX = 3  # 플레이어 점 반지름(px)
MINIMAP_OBJECT_COLOR = (90, 200, 255)  # 오브젝트 점 색
MINIMAP_OBJECT_PX = 2  # 오브젝트 점 반지름(px)
MINIMAP_VIEW_LINE = 2.0  # 바라보는 방향 선의 길이(칸)
FPS_LOG_INTERVAL = 1.0  # F7을 켜면 이 간격(초)마다 평균 FPS를 콘솔에 남긴다

# ---------------------------------------------------------------- 타이틀
TITLE_BG_COLOR = (29, 27, 58)  # #1D1B3A
TITLE_BLINK_PERIOD = 1.0  # "SPACE 키로 시작" 깜박임 주기(초)
TITLE_WADDLE_SCALE = 2  # 타이틀에서만 허용되는 확대 배율

# ---------------------------------------------------------------- 골인 / 결과
GOAL_RESULT_DELAY = 1.5  # 골인한 뒤 결과 화면이 뜨기까지(초). 그동안 문이 열려 있다
RESULT_INPUT_GUARD = 0.4  # 결과 화면이 뜬 직후 키를 무시하는 시간(초). 점프 연타가 곧장 재시작이 되지 않게
RESULT_CLEAR_BG_COLOR = (255, 224, 102)  # 성공: 노란 배경
RESULT_FAIL_BG_COLOR = (0, 0, 0)  # 실패: 검은 화면

# ---------------------------------------------------------------- HUD / 소리
SOUND_VOLUME = 0.8  # 전체 볼륨 0.0~1.0. sound.set_volume()으로 한 번에 바꾼다
BGM_VOLUME_RATIO = 0.5  # 배경음은 이 비율만큼 더 낮게 (효과음이 묻히지 않게)
HEARTBEAT_PERIOD = 1.0  # 심장박동 소리를 이어 붙이는 간격(초). 소리 파일 길이와 같다

# ---------------------------------------------------------------- 인트로 컷신
# 화면 위·아래 검은 띠의 높이(px). 자막과 안내 문구는 아래 띠 안에 놓인다
INTRO_LETTERBOX_H = 90
# 자막이 한 글자씩 나타나는 간격(초). 공백·문장부호도 한 글자로 센다
INTRO_CHAR_INTERVAL = 0.05
# 자막이 다 나온 뒤 컷이 머무는 최소 시간(초). 자막이 길면 컷이 이만큼 늘어난다
INTRO_LINE_HOLD = 1.5
INTRO_FLOOR_Y = 150  # 지하철 안 바닥선의 y (bg_train_inside 기준)
INTRO_SUBTITLE_SIZE = 28
INTRO_SUBTITLE_COLOR = (255, 255, 255)  # #FFFFFF
INTRO_SUBTITLE_MAX_LINES = 2
INTRO_SUBTITLE_LINE_HEIGHT = 34  # 두 줄일 때 줄 사이 간격(px)
INTRO_HINT_TEXT = "SPACE 다음 · ESC 건너뛰기"
INTRO_HINT_SIZE = 16
INTRO_HINT_COLOR = (136, 136, 136)  # #888888
# 안내 문구 자리: 오른쪽 아래 띠 안. (글자 오른쪽 끝 x, 글자 세로 중심 y)
INTRO_HINT_POS = (SCREEN_W - 20, 18)
# 배경 그림(bg_train_inside)이 없을 때 대신 그리는 윤곽선. 상자는 (왼쪽, 아래, 오른쪽, 위)
INTRO_FALLBACK_BG_COLOR = (0, 0, 0)
INTRO_FALLBACK_LINE_COLOR = (96, 96, 112)
INTRO_FALLBACK_WINDOWS = (
    (60, 450, 340, 590),
    (400, 450, 680, 590),
    (740, 450, 1020, 590),
)
INTRO_FALLBACK_POLES = (  # 손잡이 기둥: 바닥선에서 위쪽 띠까지
    (366, INTRO_FLOOR_Y, 374, SCREEN_H - INTRO_LETTERBOX_H),
    (706, INTRO_FLOOR_Y, 714, SCREEN_H - INTRO_LETTERBOX_H),
)
INTRO_FALLBACK_DOOR = (1090, INTRO_FLOOR_Y, 1190, 420)  # 오른쪽 끝의 문
# 컷이 시작할 때 검정에서 장면으로 밝아지는 시간(초)
INTRO_FADE_CUT = 0.3
# 마지막 컷이 끝나기 전, 장면이 검정으로 어두워지는 시간(초)
INTRO_FADE_OUT = 1.0
# 인트로가 끝나고 플레이에 들어갈 때 검정에서 밝아지는 시간(초)
INTRO_FADE_IN_PLAY = 0.5
INTRO_SWAY_AMPLITUDE = 2  # 달리는 열차의 위아래 흔들림 폭(px)
INTRO_SWAY_SPEED = 6.0  # 흔들림 속도(rad/s)
# 인트로의 캐릭터·이펙트 확대 배율. 정수 배율이라 흐려지지 않는다 (배경은 원래 크기)
INTRO_CHAR_SCALE = 2
# 인트로 캐릭터가 서는 가로 위치 (발 가운데 x)
INTRO_CHAR_X = {"player": 560, "commuter1": 360, "commuter2": 760, "commuter3": 960}
# 컷 2: 꾸르륵 소리, 머리 위 "!", 땀 흘리는 자세가 한꺼번에 시작하는 때 (컷이 시작된 뒤 초)
INTRO_REACT_AT = 0.5
INTRO_EXCLAIM_TIME = 0.5  # 컷 2: "!"가 깜박이며 떠 있는 시간(초)
INTRO_WADDLE_AT = 2.5  # 컷 2: 안절부절 못하는 자세로 바뀌는 때(초)
# 컷 3: 열차 흔들림이 서서히 줄어 완전히 멈추는 때(초). 열차가 선다
INTRO_SWAY_HALT_TIME = 2.5
