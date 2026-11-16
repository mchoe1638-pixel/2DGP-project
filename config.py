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

# ---------------------------------------------------------------- 이펙트 / 디버그
FX_FRAME_PERIOD = 0.12  # 이펙트 시트가 한 칸 넘어가는 시간(초)
NPC_HEAD_HEIGHT = 132  # 바닥에서 NPC 머리 꼭대기까지 (이펙트 위치 기준)
FX_HEAD_GAP = 6  # 머리 위에 띄우는 이펙트와 머리 사이 틈
FX_STARS_HEIGHT = 118  # 바닥에서 별 이펙트 아래끝까지 (플레이어 머리 둘레)
FX_PAPER_HEIGHT = 70  # 바닥에서 전단지 이펙트 아래끝까지 (플레이어 가슴 높이)
FX_EXCLAIM_MARGIN = 60  # "!"는 화면 오른쪽 끝에서 이만큼 안쪽에 고정해 띄운다
FX_SPEECH_OFFSET_X = -61  # 말풍선은 말하는 사람의 이만큼 옆(왼쪽)에 띄운다
FX_SPEECH_TEXT_OFFSET = (0, 4)  # 말풍선 그림 중심에서 대사 글자까지의 어긋남
FX_SPEECH_TEXT_SIZE = 16
FX_SPEECH_TEXT_COLOR = (40, 40, 48)  # 말풍선은 밝은 바탕이라 어두운 글자
DEBUG_BB_COLOR = (255, 64, 64)  # B 키로 켜는 충돌 상자 테두리 색

# ---------------------------------------------------------------- 타이틀
TITLE_BG_COLOR = (29, 27, 58)  # #1D1B3A
TITLE_BLINK_PERIOD = 1.0  # "SPACE 키로 시작" 깜박임 주기(초)
TITLE_WADDLE_SCALE = 2  # 타이틀에서만 허용되는 확대 배율
