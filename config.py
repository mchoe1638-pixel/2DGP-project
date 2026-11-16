"""BLADDER RUN 설정값.

게임 규칙·밸런스에 쓰이는 숫자는 모두 이 파일에서만 정의한다.
다른 모듈은 값을 읽기만 하고, 같은 숫자를 다시 적지 않는다.
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

# ---------------------------------------------------------------- 배경 (시차 스크롤)
PARALLAX_FAR = 0.3
PARALLAX_MID = 0.6
PARALLAX_FLOOR = 1.0

# ---------------------------------------------------------------- 카메라
CAMERA_ANCHOR_DIV = 3  # 플레이어는 화면 왼쪽에서 가로폭의 1/3 지점에 머문다
CAMERA_GLIDE_TIME = 0.35  # 지름길 순간이동 뒤 카메라가 따라잡는 시간(초)

# ---------------------------------------------------------------- 이동 / 점프
WALK_SPEED = 200  # px/s
RUN_SPEED = 400  # px/s (SHIFT)
STAIRS_SPEED_MULT = 0.7  # 계단 구간(stage.in_stairs)에서 이동 속도에 곱한다
JUMP_V0 = 880  # px/s, 정점 높이 약 190px
GRAVITY = 2000  # px/s^2

# ---------------------------------------------------------------- 충돌 박스 (발 기준)
PLAYER_BB_HALF_W = 20
PLAYER_BB_HEIGHT = 125
NPC_BB_HALF_W = 22
NPC_BB_HEIGHT = 100  # 걷는 중 점프로도 넘을 수 있는 높이
CROWD_BB_HEIGHT = 220  # 인파는 점프로 넘을 수 없다

# ---------------------------------------------------------------- 참을성 게이지
GAUGE_MAX = 100.0
# 상승 속도(%/s). 2스테이지만 사용하고 1·3은 이후 주차에서 쓴다.
GAUGE_BASE_RATE = {1: 1.0, 2: 1.4, 3: 1.6}
RUN_GAUGE_MULT = 1.6  # 달리는 동안 게이지 상승 배율
# 단계 경계값: 50 땀 / 80 긴장 / 95 한계 / 100 실패 (0~49는 평온)
STAGE_THRESHOLDS = (50, 80, 95, 100)

# ---------------------------------------------------------------- 타이틀
TITLE_BG_COLOR = (29, 27, 58)  # #1D1B3A
TITLE_BLINK_PERIOD = 1.0  # "SPACE 키로 시작" 깜박임 주기(초)
TITLE_WADDLE_SCALE = 2  # 타이틀에서만 허용되는 확대 배율
