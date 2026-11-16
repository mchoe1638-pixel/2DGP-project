"""플레이 화면의 HUD: 참을성 게이지, 남은 거리와 진행 바, 스테이지 번호.

카메라와 상관없이 화면의 같은 자리에 그리고, 월드를 다 그린 뒤 맨 위에 얹는다.
디버그 키(F1~F4·G)가 켜 둔 것은 어디에도 표시하지 않는다 (녹화 화면에 나오면 안 된다).
"""

import config
import resource
import text
from fx import SpriteLookup
from gauge import Gauge
from player import Player
from stage_data import Stage
from util import clamp

Color = tuple[int, int, int]

GAUGE_FRAME = "ui_gauge_frame"
# 게이지 단계(평온·땀·긴장·한계·실패)별 채움 그림과, 그에 맞춘 퍼센트 글자 색
FILL_SHEETS = (
    "ui_gauge_fill_blue",
    "ui_gauge_fill_yellow",
    "ui_gauge_fill_orange",
    "ui_gauge_fill_red",
    "ui_gauge_fill_red",
)
FILL_COLORS: tuple[Color, ...] = (
    (126, 200, 242),
    (255, 210, 63),
    (243, 114, 44),
    (232, 85, 62),
    (232, 85, 62),
)
PROGRESS_FRAME = "ui_progress_frame"
PROGRESS_FILL = "ui_progress_fill"
HEAD_ICON = "ui_head_icon"
WC_BADGE = "ui_wc_badge"

TEXT_COLOR: Color = (253, 246, 227)  # 프레임 그림의 크림색
SHADOW_COLOR: Color = (26, 21, 48)  # 프레임 그림의 남색
STAGE_COLOR: Color = (255, 210, 63)  # 진행 바 채움과 같은 노랑
SHADOW_OFFSET = (2, -2)

MARGIN = 24  # 화면 가장자리와 HUD 사이의 틈
GAUGE_INSET = 6  # 게이지 프레임 안쪽으로 채움 바가 들어가는 거리 (상하좌우 같다)
PERCENT_DROP = 17  # 게이지 프레임 아래끝에서 퍼센트 글자 중심까지
PERCENT_SIZE = 22
GUM_GAP = 14  # 게이지 프레임 오른쪽 끝에서 껌 남은 시간 글자까지
GUM_SIZE = 22
DISTANCE_TEXT_Y = 686  # 위쪽 가운데 "WC까지" 글자의 세로 중심
DISTANCE_SIZE = 22
PROGRESS_BAR_Y = 650  # 진행 바 프레임의 아래끝
BADGE_GAP = 8  # 진행 바 오른쪽 끝에서 WC 배지까지의 틈
STAGE_SIZE = 33


def draw_label(
    string: str,
    x: int,
    y: int,
    size: int,
    color: Color,
    align: str = "left",
) -> None:
    """HUD 글자: 어떤 배경 위에서도 읽히도록 짙은 그림자를 한 겹 깐다."""
    shadow_x, shadow_y = SHADOW_OFFSET
    text.draw(
        string,
        x + shadow_x,
        y + shadow_y,
        size=size,
        color=SHADOW_COLOR,
        bold=True,
        align=align,
    )
    text.draw(string, x, y, size=size, color=color, bold=True, align=align)


class Hud:
    def __init__(
        self,
        stage: Stage,
        gauge: Gauge,
        player: Player,
        sprite_lookup: SpriteLookup = resource.get_sprite,
    ) -> None:
        self.stage = stage
        self.gauge = gauge
        self.player = player
        self._lookup = sprite_lookup

    # ------------------------------------------------------------ 값
    def remaining_metres(self) -> int:
        """골인 문까지 남은 거리(m). 반올림하고, 문을 지나쳤으면 0."""
        pixels = self.stage.goal_x - self.player.x
        return max(0, int(pixels / config.PIXELS_PER_METER + 0.5))

    def progress(self) -> float:
        """출발점(0.0)에서 골인 문(1.0)까지 얼마나 왔는지."""
        start = self.stage.player_start_x
        return clamp(0.0, (self.player.x - start) / (self.stage.goal_x - start), 1.0)

    # ------------------------------------------------------------ 그리기
    def draw(self) -> None:
        self._draw_gauge()
        self._draw_gum_timer()
        self._draw_distance()
        self._draw_progress_bar()
        self._draw_stage_number()

    def _top_row_middle(self) -> int:
        """위쪽 줄(게이지·스테이지 번호)의 세로 중심."""
        frame = self._lookup(GAUGE_FRAME)
        return config.SCREEN_H - MARGIN - frame.frame_h // 2

    def _draw_gauge(self) -> None:
        frame = self._lookup(GAUGE_FRAME)
        left = MARGIN
        bottom = config.SCREEN_H - MARGIN - frame.frame_h
        frame.draw_at_origin(left, bottom)
        level = int(self.gauge.stage)
        fill = self._lookup(FILL_SHEETS[level])
        width = round(fill.frame_w * self.gauge.value / config.GAUGE_MAX)
        if width > 0:
            fill.draw_at_origin(left + GAUGE_INSET, bottom + GAUGE_INSET, width)
        draw_label(
            f"{int(self.gauge.value)}%",  # 99.9%가 100%로 보이지 않게 버린다
            left + GAUGE_INSET,
            bottom - PERCENT_DROP,
            PERCENT_SIZE,
            FILL_COLORS[level],
        )

    def _draw_gum_timer(self) -> None:
        remaining = self.gauge.freeze_remaining  # 디버그 정지는 세지 않는다
        if remaining <= 0.0:
            return
        frame = self._lookup(GAUGE_FRAME)
        draw_label(
            f"껌 {remaining:.1f}초",
            MARGIN + frame.frame_w + GUM_GAP,
            self._top_row_middle(),
            GUM_SIZE,
            TEXT_COLOR,
        )

    def _draw_distance(self) -> None:
        draw_label(
            f"WC까지 {self.remaining_metres()}m",
            config.SCREEN_W // 2,
            DISTANCE_TEXT_Y,
            DISTANCE_SIZE,
            TEXT_COLOR,
            align="center",
        )

    def _draw_progress_bar(self) -> None:
        frame = self._lookup(PROGRESS_FRAME)
        left = config.SCREEN_W // 2 - frame.frame_w // 2
        frame.draw_at_origin(left, PROGRESS_BAR_Y)
        fill = self._lookup(PROGRESS_FILL)
        reached = round(fill.frame_w * self.progress())
        if reached > 0:
            fill.draw_at_origin(
                left + (frame.frame_w - fill.frame_w) // 2,
                PROGRESS_BAR_Y + (frame.frame_h - fill.frame_h) // 2,
                reached,
            )
        middle = PROGRESS_BAR_Y + frame.frame_h // 2
        head = self._lookup(HEAD_ICON)
        # 머리 그림이 바 밖으로 삐져나가지 않도록, 바 안쪽 길이만큼만 오간다
        travel = frame.frame_w - head.frame_w
        head.draw(left + head.frame_w / 2 + travel * self.progress(), middle)
        badge = self._lookup(WC_BADGE)
        badge.draw(left + frame.frame_w + BADGE_GAP + badge.frame_w / 2, middle)

    def _draw_stage_number(self) -> None:
        draw_label(
            f"STAGE {self.stage.number}",
            config.SCREEN_W - MARGIN,
            self._top_row_middle(),
            STAGE_SIZE,
            STAGE_COLOR,
            align="right",
        )
