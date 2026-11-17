"""인트로 컷신의 컷 목록. 자막과 길이는 코드와 떼어 이곳에서만 고친다."""

from dataclasses import dataclass

import config


@dataclass(frozen=True)
class Cut:
    """컷 하나. text는 자막(줄바꿈은 \\n, 최대 INTRO_SUBTITLE_MAX_LINES줄), duration은 기본 길이(초)."""

    text: str
    duration: float

    def __post_init__(self) -> None:
        if self.text.count("\n") + 1 > config.INTRO_SUBTITLE_MAX_LINES:
            raise ValueError(
                f"자막은 {config.INTRO_SUBTITLE_MAX_LINES}줄까지입니다: {self.text!r}"
            )
        if self.duration <= 0:
            raise ValueError(f"컷 길이는 0보다 커야 합니다: {self.duration}")

    @property
    def run_time(self) -> float:
        """컷이 실제로 머무는 시간(초).

        자막을 다 치고 INTRO_LINE_HOLD만큼 보여 줄 시간이 duration보다 길면 그만큼으로 늘어난다.
        """
        typing_and_hold = (
            len(self.text) * config.INTRO_CHAR_INTERVAL + config.INTRO_LINE_HOLD
        )
        return max(self.duration, typing_and_hold)


CUTS = (
    Cut("현재 시각 8시 42분, 출근길 지하철 안.", 4.0),
    Cut("김급해는 갑작스럽게 똥이 마렵기 시작했다.", 4.0),
    Cut("다음 역에서 내리자마자 화장실로 달려가기로 마음먹는데…", 4.5),
)
