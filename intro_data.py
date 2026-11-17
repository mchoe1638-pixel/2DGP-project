"""인트로 컷신의 컷 목록. 자막·길이와 컷마다의 연출(자세·효과음·느낌표·흔들림)을 코드와 떼어 이곳에서만 고친다.

연출에 쓰는 시간은 모두 '그 컷이 시작된 뒤 몇 초'다. 간격·배율·위치 같은 수치는 config.py의 INTRO_* 에 있다.
"""

from dataclasses import dataclass
from typing import NamedTuple

import config
import sound
from util import smoothstep


class Pose(NamedTuple):
    """김급해가 컷이 시작된 뒤 at초부터 취하는 자세. sprite는 manifest의 스프라이트 이름이다."""

    at: float
    sprite: str


class SfxCue(NamedTuple):
    """컷이 시작된 뒤 at초에 효과음 name을 한 번 튼다."""

    at: float
    name: str


class Extra(NamedTuple):
    """배경에 서 있는 행인 한 명. x는 발 가운데의 가로 위치이고, flip이면 좌우를 뒤집어 그린다."""

    sprite: str
    x: int
    flip: bool = False


@dataclass(frozen=True)
class Cut:
    """컷 하나.

    text는 자막(줄바꿈은 \\n, 최대 INTRO_SUBTITLE_MAX_LINES줄), duration은 기본 길이(초).
    player_poses는 김급해의 자세표로, 첫 자세는 0초에 시작하고 시간이 커지는 차례로 늘어놓는다.
    sfx는 효과음 신호표 (시간이 커지는 차례), exclaim_at은 머리 위 느낌표가 뜨는 때 (없으면 None),
    sway_halt는 열차 흔들림이 서서히 잦아들어 멈추는 때 (None이면 컷이 끝날 때까지 그대로 흔들린다).
    """

    text: str
    duration: float
    player_poses: tuple[Pose, ...]
    sfx: tuple[SfxCue, ...] = ()
    exclaim_at: float | None = None
    sway_halt: float | None = None

    def __post_init__(self) -> None:
        if self.text.count("\n") + 1 > config.INTRO_SUBTITLE_MAX_LINES:
            raise ValueError(
                f"자막은 {config.INTRO_SUBTITLE_MAX_LINES}줄까지입니다: {self.text!r}"
            )
        if self.duration <= 0:
            raise ValueError(f"컷 길이는 0보다 커야 합니다: {self.duration}")
        self._check_staging()

    def _check_staging(self) -> None:
        """연출 시간표가 차례대로이고 컷 안에 들어 있는지 본다 (틀렸으면 컷을 만드는 순간 알린다)."""
        pose_times = [pose.at for pose in self.player_poses]
        cue_times = [cue.at for cue in self.sfx]
        if not pose_times or pose_times[0] != 0.0:
            raise ValueError(f"자세표는 0초의 자세로 시작해야 합니다: {self.text!r}")
        if pose_times != sorted(set(pose_times)):
            raise ValueError(f"자세표의 시간은 점점 커져야 합니다: {pose_times}")
        if cue_times != sorted(cue_times):
            raise ValueError(f"효과음 신호표의 시간은 차례여야 합니다: {cue_times}")
        times = [*pose_times, *cue_times]
        times += [t for t in (self.exclaim_at, self.sway_halt) if t is not None]
        if any(not 0.0 <= t <= self.run_time for t in times):
            raise ValueError(
                f"연출 시간은 0초부터 컷 길이({self.run_time}초) 안이어야 합니다: {self.text!r}"
            )
        if self.sway_halt is not None and self.sway_halt <= 0.0:
            raise ValueError(
                f"흔들림이 멈추는 때는 0초보다 뒤여야 합니다: {self.text!r}"
            )

    @property
    def run_time(self) -> float:
        """컷이 실제로 머무는 시간(초).

        자막을 다 치고 INTRO_LINE_HOLD만큼 보여 줄 시간이 duration보다 길면 그만큼으로 늘어난다.
        """
        typing_and_hold = (
            len(self.text) * config.INTRO_CHAR_INTERVAL + config.INTRO_LINE_HOLD
        )
        return max(self.duration, typing_and_hold)

    def pose_at(self, t: float) -> Pose:
        """컷이 시작된 뒤 t초일 때 김급해의 자세: t 이전에 시작한 자세 가운데 가장 늦은 것."""
        current = self.player_poses[0]
        for pose in self.player_poses[1:]:
            if pose.at > t:
                break
            current = pose
        return current

    def exclaim_age(self, t: float) -> float | None:
        """t초에 머리 위 느낌표가 떠 있으면 뜬 지 몇 초째인지, 아니면 None."""
        if self.exclaim_at is None:
            return None
        age = t - self.exclaim_at
        if 0.0 <= age < config.INTRO_EXCLAIM_TIME:
            return age
        return None

    def sway_strength(self, t: float) -> float:
        """t초의 열차 흔들림 세기: 1.0은 그대로, 0.0은 멈춤. sway_halt가 있으면 그때까지 서서히 잦아든다."""
        if self.sway_halt is None:
            return 1.0
        return 1.0 - smoothstep(t / self.sway_halt)


# 세 컷 모두 같은 자리에 서 있는 행인들. 둘째 행인은 좌우를 뒤집어 다른 쪽을 보게 한다
CROWD = (
    Extra("npc_commuter1", config.INTRO_CHAR_X["commuter1"]),
    Extra("npc_commuter2", config.INTRO_CHAR_X["commuter2"], flip=True),
    Extra("npc_commuter3", config.INTRO_CHAR_X["commuter3"]),
)

CUTS = (
    # 컷 1: 지하철 안, 아직 평온한 김급해
    Cut(
        text="현재 시각 8시 42분, 출근길 지하철 안.",
        duration=4.0,
        player_poses=(Pose(0.0, "player_calm_idle"),),
    ),
    # 컷 2: 꾸르륵 소리와 함께 머리 위에 느낌표가 뜨고 땀이 나다가, 안절부절못한다
    Cut(
        text="김급해는 갑작스럽게 똥이 마렵기 시작했다.",
        duration=4.0,
        player_poses=(
            Pose(0.0, "player_calm_idle"),
            Pose(config.INTRO_REACT_AT, "player_sweat_idle"),
            Pose(config.INTRO_WADDLE_AT, "player_strain_waddle"),
        ),
        sfx=(SfxCue(config.INTRO_REACT_AT, sound.GROWL),),
        exclaim_at=config.INTRO_REACT_AT,
    ),
    # 컷 3: 열차가 서고 (흔들림이 멈춘다), 김급해는 문 쪽(오른쪽, 그림의 기본 방향)을 본다
    Cut(
        text="다음 역에서 내리자마자 화장실로 달려가기로 마음먹는데…",
        duration=4.5,
        player_poses=(Pose(0.0, "player_strain_idle"),),
        sway_halt=config.INTRO_SWAY_HALT_TIME,
    ),
)
