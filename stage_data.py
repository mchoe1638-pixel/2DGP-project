"""스테이지별 데이터(길이, 목표 지점, 구간, 배치표). 밸런스 수치는 config.py에 둔다."""

from dataclasses import dataclass

import config

TOURIST = "tourist"  # 관광객: 길을 묻는다 (멈춤)
FLYER = "flyer"  # 전단지 나눔이: 느려짐
BOSS = "boss"  # 상사: 경고 뒤 걸어와 붙잡는다
CROWD = "crowd"  # 인파: 뚫을 수 없는 벽, 주기적으로 틈이 열린다

BREATH = "breath"  # 심호흡: 게이지를 덜어 낸다
GUM = "gum"  # 껌: 잠깐 게이지 상승을 붙잡는다
SHORTCUT = "shortcut"  # 지름길: 앞으로 순간이동

PROP_TRAIN = "prop_train"
PROP_GATE = "prop_gate"
PROP_STAIRS_SIGN = "prop_stairs_sign"
PROP_SIGN_WC = "prop_sign_wc"
WALL = config.PROP_WALL_HEIGHT  # 배치표에서 "벽 높이"라고 적는 값


@dataclass(frozen=True)
class ObstacleSpec:
    """배치표 한 줄: kind 장애물을 월드 x에 둔다. count는 인파의 사람 수."""

    kind: str
    x: int
    count: int = 1


@dataclass(frozen=True)
class ItemSpec:
    """배치표 한 줄: kind 아이템을 월드 x에 둔다. height는 이미지 아래끝이 바닥에서 떠 있는 높이(px)."""

    kind: str
    x: int
    height: int = 0


@dataclass(frozen=True)
class PropSpec:
    """배치표 한 줄: manifest의 sheet 장식을 월드 x에 둔다. height는 이미지 아래끝의 바닥 위 높이(px)."""

    sheet: str
    x: int
    height: int = 0


@dataclass(frozen=True)
class Stage:
    number: int
    length: int
    goal_x: int
    player_start_x: int
    stairs_zone: tuple[int, int] | None = None  # [시작, 끝) 월드 x. 없으면 None
    obstacles: tuple[ObstacleSpec, ...] = ()  # x 오름차순
    items: tuple[ItemSpec, ...] = ()  # x 오름차순
    props: tuple[PropSpec, ...] = ()  # x 오름차순. 골인 문은 goal_x에 따로 세운다

    def in_stairs(self, x: float) -> bool:
        if self.stairs_zone is None:
            return False
        start, end = self.stairs_zone
        return start <= x < end


STAGE_2 = Stage(
    number=2,
    length=9000,
    goal_x=8800,
    player_start_x=150,
    stairs_zone=(4200, 5400),
    obstacles=(
        ObstacleSpec(TOURIST, 1000),
        ObstacleSpec(FLYER, 1800),
        ObstacleSpec(BOSS, 3300),
        ObstacleSpec(CROWD, 4700, count=4),
        ObstacleSpec(TOURIST, 5900),
        ObstacleSpec(FLYER, 7000),
        ObstacleSpec(CROWD, 7600, count=3),
    ),
    items=(
        ItemSpec(BREATH, 1150, height=150),  # 점프해야 닿는다
        ItemSpec(GUM, 3550, height=40),
        ItemSpec(BREATH, 6050, height=150),
        ItemSpec(SHORTCUT, 6500),  # 바닥의 표지판
    ),
    props=(
        PropSpec(PROP_TRAIN, 500),
        PropSpec(PROP_SIGN_WC, 1600, WALL),
        PropSpec(PROP_GATE, 2450),
        PropSpec(PROP_GATE, 2550),
        PropSpec(PROP_GATE, 2650),
        PropSpec(PROP_SIGN_WC, 3000, WALL),
        PropSpec(PROP_STAIRS_SIGN, 4150, WALL),
        PropSpec(PROP_SIGN_WC, 5700, WALL),
        PropSpec(PROP_SIGN_WC, 7300, WALL),
        PropSpec(PROP_SIGN_WC, 8300, WALL),
    ),
)

_STAGES = {stage.number: stage for stage in (STAGE_2,)}


def get_stage(number: int) -> Stage:
    try:
        return _STAGES[number]
    except KeyError:
        raise KeyError(f"스테이지 {number} 데이터는 아직 없습니다.") from None
