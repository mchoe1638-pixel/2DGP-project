"""스테이지별 데이터(길이, 목표 지점, 구간). 밸런스 수치는 config.py에 둔다."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Stage:
    number: int
    length: int
    goal_x: int
    player_start_x: int
    stairs_zone: tuple[int, int] | None = None  # [시작, 끝) 월드 x. 없으면 None

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
)

_STAGES = {stage.number: stage for stage in (STAGE_2,)}


def get_stage(number: int) -> Stage:
    try:
        return _STAGES[number]
    except KeyError:
        raise KeyError(f"스테이지 {number} 데이터는 아직 없습니다.") from None
