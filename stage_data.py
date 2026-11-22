"""스테이지별 원본 데이터: 통로 구간과 배치표. 밸런스 수치는 config.py에 둔다.

좌표는 위에서 내려다본 월드 (x, y) m 단위이고, 1칸 = 1m이다. 스테이지는 +x 방향으로 나아간다.
+x를 볼 때 +y가 왼쪽이다. 그래서 구간의 y1 줄이 왼벽, y0 - 1 줄이 오른벽이다.

이 파일은 데이터만 적는다. 격자 지도와 오브젝트 배치로 바꾸는 일은 stage.py가 맡는다.
"""

from typing import Any

# ---------------------------------------------------------------- 배치표 이름
TOURIST = "tourist"  # 관광객: 길을 묻는다 (멈춤)
FLYER = "flyer"  # 전단지 나눔이: 느려짐
BOSS = "boss"  # 상사: 경고 뒤 걸어와 붙잡는다
CROWD = "crowd"  # 인파: 통로를 가로막고, 주기적으로 한 자리가 비켜선다

BREATH = "breath"  # 심호흡: 게이지를 덜어 낸다
GUM = "gum"  # 껌: 잠깐 게이지 상승을 붙잡는다
SHORTCUT = "shortcut"  # 지름길: 옆 통로로 앞질러 간다

ITEM_FLOOR = "floor"  # 바닥에 놓인 아이템
ITEM_HIGH = "high"  # 높이 떠 있어 점프해야 닿는 아이템

SIDE_LEFT = "left"  # 옆 통로·표지판이 왼벽(y1 줄) 쪽
SIDE_RIGHT = "right"  # 오른벽(y0 - 1 줄) 쪽
WALL_LEFT = "wall_left"  # 장식을 왼벽에 붙인다

TEX_WALL_SIGN_WC = "tex_wall_sign_wc"  # 화장실 안내 표지판 벽
TEX_DOOR_WC = "tex_door_wc"  # 골인 문

# ---------------------------------------------------------------- 스테이지 2
STAGE2: dict[str, Any] = {
    "length": 150,
    "goal_x": 147,
    "player_start": (2.5, 3.0, 0.0),  # x, y, yaw
    "base_rate": 1.4,
    "segments": [  # x0, x1, y0, y1, 왼벽(y1쪽) 텍스처, 오른벽(y0쪽) 텍스처, 바닥
        # 승강장: 오른쪽이 방금 내린 열차
        (0, 40, 0, 6, "tex_wall_tile", "tex_wall_train", "normal"),
        (40, 46, 0, 8, "tex_wall_tile", "tex_wall_tile", "normal"),  # 개찰구
        (46, 70, 0, 8, "tex_wall_ad", "tex_wall_tile", "normal"),  # 대합실
        (70, 90, 1, 6, "tex_wall_stairs", "tex_wall_stairs", "stairs"),  # 계단: 좁음
        # 윗층 통로 (x=148이 끝벽)
        (90, 148, 0, 7, "tex_wall_tile", "tex_wall_ad", "normal"),
    ],
    # 지름길 옆 통로 (y 7~9)
    "side_passage": {"x0": 108, "x1": 121, "y_side": "left", "width": 2},
    "pillars": [(55, 2), (55, 5), (100, 2), (130, 5)],  # 1칸 기둥 벽 (격자 칸 좌표)
    # tex_wall_sign_wc 로 바꿀 칸
    "wall_signs": [(30, "left"), (60, "right"), (95, "left"), (125, "right")],
    # 끝벽 가운데 칸을 tex_door_wc 로. 플레이어 x ≥ goal_x 면 골인
    "goal_door": (148, 3),
    # 닫힌 칸은 점프로 넘기
    "gates": {"x": 42.5, "lanes": 4, "open_lanes": [3], "height": 0.5},
    "obstacles": [
        ("tourist", 17, 3.0),
        ("flyer", 30, 4.0),
        ("boss", 55, 4.0),
        ("crowd", 78, None, 4),  # 계단 폭 전체를 4명이 막음
        ("tourist", 98, 3.5),
        ("flyer", 117, 2.5),
        ("crowd", 127, None, 3),
    ],
    "items": [  # kind, x, y, h ('floor' | 'high' = 점프해야 닿음)
        ("breath", 19, 4.5, "high"),
        ("gum", 59, 6.5, "floor"),
        ("breath", 101, 1.5, "high"),
        ("shortcut", 108, None, "floor"),
    ],
    "deco": [("prop_stairs_sign", 69, "wall_left")],
}

STAGES: dict[int, dict[str, Any]] = {2: STAGE2}


def get_stage_data(number: int) -> dict[str, Any]:
    """number번 스테이지의 원본 데이터. 아직 없는 스테이지면 KeyError."""
    try:
        return STAGES[number]
    except KeyError:
        raise KeyError(f"스테이지 {number} 데이터는 아직 없습니다.") from None
