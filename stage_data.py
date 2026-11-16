"""스테이지별 데이터(길이, 목표 지점, 구간). 밸런스 수치는 config.py에 둔다."""

from dataclasses import dataclass

TOURIST = "tourist"  # 관광객: 길을 묻는다 (멈춤)
FLYER = "flyer"  # 전단지 나눔이: 느려짐
BOSS = "boss"  # 상사: 경고 뒤 걸어와 붙잡는다
CROWD = "crowd"  # 인파: 뚫을 수 없는 벽, 주기적으로 틈이 열린다


@dataclass(frozen=True)
class ObstacleSpec:
    """배치표 한 줄: kind 장애물을 월드 x에 둔다. count는 인파의 사람 수."""

    kind: str
    x: int
    count: int = 1


@dataclass(frozen=True)
class Stage:
    number: int
    length: int
    goal_x: int
    player_start_x: int
    stairs_zone: tuple[int, int] | None = None  # [시작, 끝) 월드 x. 없으면 None
    obstacles: tuple[ObstacleSpec, ...] = ()  # x 오름차순

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
)

_STAGES = {stage.number: stage for stage in (STAGE_2,)}


def get_stage(number: int) -> Stage:
    try:
        return _STAGES[number]
    except KeyError:
        raise KeyError(f"스테이지 {number} 데이터는 아직 없습니다.") from None
