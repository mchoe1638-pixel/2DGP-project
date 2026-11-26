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
        # 승강장: 왼쪽은 난간 너머 바깥 풍경, 오른쪽은 스크린도어 (오른벽 무늬는 wall_runs)
        (0, 40, 0, 6, "tex_rail", "tex_psd_panel", "normal"),
        (40, 46, 0, 8, "tex_wall_tile", "tex_wall_tile", "normal"),  # 개찰구
        (46, 70, 0, 8, "tex_wall_ad", "tex_wall_tile", "normal"),  # 대합실
        (70, 90, 1, 6, "tex_wall_stairs", "tex_wall_stairs", "stairs"),  # 계단: 좁음
        # 윗층 통로 (x=148이 끝벽)
        (90, 148, 0, 7, "tex_wall_tile", "tex_wall_ad", "normal"),
    ],
    # 지름길 옆 통로 (y 7~9)
    "side_passage": {"x0": 108, "x1": 121, "y_side": "left", "width": 2},
    "pillars": [(55, 2), (55, 5), (100, 2), (130, 5)],  # 1칸 기둥 벽 (격자 칸 좌표)
    # 벽 무늬 덧씌우기 (방향, x0, x1, 무늬): [x0, x1) 칸에 무늬를 x0 칸부터 차례로 되풀이해 깐다.
    # 오른벽은 보는 쪽에서 왼쪽이 x가 큰 쪽이라, 그림 한 장을 칸으로 나눈 무늬(쌍문·이름판)는
    # 화면에서 왼쪽 조각이 x가 큰 칸에 오도록 적는다 (그래서 x 순서로는 r → l, 3 → 2 → 1)
    "wall_runs": [
        # 승강장 오른벽 스크린도어: 화면에서 [문 l][문 r][패널]이 되풀이된다 (패널은 x % 3 == 2).
        # x < 12는 열차가 서 있다. 마지막 칸(39)은 구간 기본 무늬(패널)로 둔다
        ("right", 0, 12, ("tex_psd_train_r", "tex_psd_train_l", "tex_psd_panel")),
        ("right", 12, 17, ("tex_psd_door_r", "tex_psd_door_l", "tex_psd_panel")),
        # 역 이름판: 3칸짜리 한 장 (화면에서 왼쪽부터 1, 2, 3 = x 19, 18, 17)
        (
            "right",
            17,
            20,
            ("tex_station_sign_3", "tex_station_sign_2", "tex_station_sign_1"),
        ),
        ("right", 20, 39, ("tex_psd_panel", "tex_psd_door_r", "tex_psd_door_l")),
        # 화장실 입구 양옆 벽 (끝벽 바로 앞 3칸)
        ("left", 145, 148, ("tex_wc_tile",)),
        ("right", 145, 148, ("tex_wc_tile",)),
    ],
    # 끝벽 (마지막 구간 x1 줄): 7칸짜리 한 장 그림을 보이는 대로 왼쪽부터 적는다.
    # 네 번째가 골인 문 칸이다 (goal_door 와 같은 칸)
    "end_wall": (
        "tex_wc_end_1",
        "tex_wc_end_2",
        "tex_wc_end_3",
        TEX_DOOR_WC,
        "tex_wc_end_5",
        "tex_wc_end_6",
        "tex_wc_end_7",
    ),
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
    # 승강장 기둥·벤치 (그림 이름, x, y): 몸으로 막는 장식이다. 이름은 config.SOLID_PROP_COLLIDERS의
    # 키이고, 크기(충돌 원기둥)도 거기서 정한다. 기둥은 통로 가운데에서 왼쪽으로 조금 비킨 줄(y 3.7)에
    # 8칸마다 세워, 시작 줄(y 3.0)로 곧장 달리면 스치지 않고 지나간다. 벤치는 그 사이사이 왼벽(y=6)에
    # 붙여 둔다. 어느 x에서도 오른쪽으로 3m 넘는 길이 비어 있어서 돌아가는 길이 늘 있다
    "props": [
        ("prop_pillar_pink", 18, 3.7),
        ("prop_bench", 23, 5.35),
        ("prop_pillar_pink", 26, 3.7),
        ("prop_bench", 31, 5.35),
        ("prop_pillar_pink", 34, 3.7),
    ],
    # 행인 (이름, x, y): 장애물이 아니라 같은 방향(+x)으로 걸어가는 배경 사람이다.
    # 이름은 config.PEDESTRIAN_SPEEDS의 키이고, 그림은 npc_<이름>_back(없으면 _front)이다.
    # x는 걷기 시작하는 자리, y는 걷는 줄이다. 플레이어가 뒤로 20m 안에 오면 걷기 시작해 14m 가서
    # 서고, 플레이어에게서 10m 넘게 떨어지면 사라진다. 기둥 칸과 옆 통로 입구를 피해 놓았고,
    # 구간 끝(개찰구·계단·두 번째 인파) 앞에서 서게 14m를 맞췄다
    "pedestrians": [
        # 승강장: 개찰구(x=42.5) 앞에서 끝나게 둔다. 벤치(y 5.35)와 기둥(y 3.7) 곁을 지나는 사람은
        # y 3.0 이하 줄로 걷게 한다 (걷는 줄이 그 둘에 걸리면 장식에 밀려 돌아가게 된다)
        ("commuter1", 9.0, 1.0),
        ("commuter3", 12.0, 2.5),
        ("commuter4", 21.0, 1.2),
        ("commuter2", 24.0, 2.0),
        ("commuter5", 26.5, 3.0),
        # 대합실: 기둥(55, 2)·(55, 5) 줄과 상사 줄(y=4)을 비켜 간다
        ("commuter2", 45.0, 7.0),  # 열린 개찰구 칸(y 6~8)으로 나온 사람
        ("commuter1", 48.0, 1.0),
        ("commuter3", 52.0, 6.8),
        ("commuter4", 56.0, 4.0),  # 계단(x=70) 앞에서 끝난다
        # 윗층 통로: 두 번째 인파(x=127) 앞에서 끝나게 둔다
        ("commuter5", 92.0, 5.8),
        ("commuter1", 95.0, 1.0),
        ("commuter3", 104.0, 5.0),
        ("commuter2", 106.0, 1.2),
        ("commuter4", 110.0, 6.2),
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
