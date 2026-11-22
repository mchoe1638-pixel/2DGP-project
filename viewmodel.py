"""1인칭 팔 (뷰모델): 벽과 빌보드 위, HUD 아래에 겹쳐 그리는 두 손. 플레이어의 걸음에 맞춰 움직인다.

시트 고르기 (플레이어의 움직임 상태와 게이지 단계로)
- 멈춤: 넘어졌으면 arms_fall (쓰러지는 동안 0칸, 쓰러진 뒤 1칸), 아니면 arms_idle
- 공중: arms_jump (오르는 동안 0칸, 내려오는 동안 1칸)
- 긴장 단계(80%~)에서 걷거나 달릴 때: arms_hold (배를 움켜쥔다)
- 달리기 arms_run, 걷기 arms_walk. 이 둘과 arms_hold는 걸음 위상으로 칸을 넘긴다
  (한 걸음에 ARMS_FRAMES_PER_STEP칸)
- 서기: arms_idle (ARMS_IDLE_FPS로 두 칸을 오가며 숨 쉰다)

그리는 곳: (화면 가운데 + bob_x, ARMS_BASE_Y + bob_y × ARMS_BOB_PX_PER_M)을 중심으로 원본 크기.
팔 시트는 칸 아래 끝에 그림이 붙어 있어, 걸음으로 올라와도 화면 아래가 비지 않게
ARMS_SHEET_SINK_PX만큼 내려 그린다 (단색 팔은 그대로).
땀 단계(50%~)에서는 fx_sweat_hand를 손 위에 겹친다 (그림이 있을 때만, 없으면 생략).
땀 그림은 팔을 따라 같은 높이에 그린다.

manifest에 팔 그림이 없으면 단색 팔(흰 소매 끝의 살색 손)을 대신 그린다. 걷고 달릴 때 두 손이 걸음에 맞춰
엇갈려 오르내리고, 시트가 바뀌면 ARMS_POSE_BLEND_TIME 동안 새 자세로 옮겨 가 손이 튀지 않는다.
"""

import math
from typing import NamedTuple

import config
import game_framework
import gfx
import resource
from gauge import Gauge, GaugeStage
from player import Motion, Player

IDLE_SHEET = "arms_idle"
WALK_SHEET = "arms_walk"
RUN_SHEET = "arms_run"
JUMP_SHEET = "arms_jump"
HOLD_SHEET = "arms_hold"
FALL_SHEET = "arms_fall"
ARM_SHEETS = (IDLE_SHEET, WALK_SHEET, RUN_SHEET, JUMP_SHEET, HOLD_SHEET, FALL_SHEET)
SWEAT_SHEET = "fx_sweat_hand"
POSE_FRAMES = 2  # 서기·점프·넘어짐 시트의 칸 수. 단색 팔은 1번 칸에서 둘째 자세를 쓴다
MISSING_ARMS_NOTE = "대신 단색 팔을 그립니다"
MISSING_SWEAT_NOTE = "손 땀 그림을 생략합니다"


class ArmPose(NamedTuple):
    """단색 팔의 자세(px). 두 손은 화면 가운데를 두고 좌우 대칭이다."""

    spread: float  # 가운데에서 손 중심까지의 가로 거리
    lift: float  # ARMS_BASE_Y에서 손 중심까지의 높이
    swing: float  # 걸음에 맞춰 두 손이 엇갈려 오르내리는 폭
    second: float  # 1번 칸에서 lift에 더하는 높이 (음수면 내린다)


FALLBACK_POSES = {
    name: ArmPose(*values) for name, values in config.ARMS_FALLBACK_POSES.items()
}


def blend_pose(current: ArmPose, target: ArmPose, amount: float) -> ArmPose:
    """current에서 target 쪽으로 amount(0~1)만큼 옮긴 새 자세."""
    return ArmPose(
        *(now + (goal - now) * amount for now, goal in zip(current, target))
    )


class Viewmodel:
    def __init__(self, player: Player, gauge: Gauge) -> None:
        self.player = player
        self.gauge = gauge
        self._sheets = {
            name: resource.find_sprite(name, MISSING_ARMS_NOTE) for name in ARM_SHEETS
        }
        self._sweat = resource.find_sprite(SWEAT_SHEET, MISSING_SWEAT_NOTE)
        self._sweat_frame = 0.0
        self._pose = self._target_pose()  # 단색 팔의 지금 자세 (목표 자세 쪽으로 옮겨 간다)

    # ------------------------------------------------------------ 시트와 칸
    def sheet_name(self) -> str:
        """지금 그릴 팔 시트의 이름."""
        state = self.player.state
        if state is Motion.STUNNED:
            return FALL_SHEET if self.player.fallen else IDLE_SHEET
        if state is Motion.AIR:
            return JUMP_SHEET
        if state is Motion.IDLE:
            return IDLE_SHEET
        if self.gauge.stage >= GaugeStage.STRAIN:
            return HOLD_SHEET
        return RUN_SHEET if state is Motion.RUN else WALK_SHEET

    def frame(self, sheet: str) -> int:
        """시트에서 그릴 칸. 걸음을 타는 시트는 걸음 위상으로, 나머지는 상태와 시간으로 정한다."""
        player = self.player
        if sheet == IDLE_SHEET:
            return int(player.state_time * config.ARMS_IDLE_FPS) % POSE_FRAMES
        if sheet == JUMP_SHEET:
            return 0 if player.vz > 0.0 else 1
        if sheet == FALL_SHEET:
            return 0 if player.state_time < config.EYE_DROP_TIME else 1
        return int(player.step_phase * config.ARMS_FRAMES_PER_STEP)

    def _target_pose(self) -> ArmPose:
        """단색 팔이 지금 향할 자세: 시트의 자세에 1번 칸이면 둘째 높이를 더한다."""
        sheet = self.sheet_name()
        pose = FALLBACK_POSES[sheet]
        if self.frame(sheet) % POSE_FRAMES == 1:
            return pose._replace(lift=pose.lift + pose.second, second=0.0)
        return pose._replace(second=0.0)

    # ------------------------------------------------------------ 갱신
    def update(self) -> None:
        """단색 팔의 자세를 목표 쪽으로 옮기고, 손 땀 그림의 칸을 넘긴다."""
        dt = game_framework.frame_time
        amount = 1.0 - math.exp(-dt / config.ARMS_POSE_BLEND_TIME)
        self._pose = blend_pose(self._pose, self._target_pose(), amount)
        if self._sweat is not None:
            self._sweat_frame = self._sweat.next_frame(self._sweat_frame, dt)

    # ------------------------------------------------------------ 그리기
    def draw(self) -> None:
        x = config.SCREEN_W / 2 + self.player.bob_x
        y = config.ARMS_BASE_Y + self.player.bob_y * config.ARMS_BOB_PX_PER_M
        sheet = self.sheet_name()
        sprite = self._sheets[sheet]
        if sprite is None:
            self._draw_fallback(x, y)
        else:
            y -= config.ARMS_SHEET_SINK_PX
            sprite.draw(x, y, self.frame(sheet))
        if self._sweat is not None and self.gauge.stage >= GaugeStage.SWEAT:
            self._sweat.draw(x, y, self._sweat_frame)

    def _draw_fallback(self, x: float, y: float) -> None:
        """단색 팔: 화면 아래 끝에서 올라온 흰 소매 끝에 살색 손. 걸음에 맞춰 두 손이 엇갈려 오르내린다."""
        pose = self._pose
        hand_w, hand_h = config.ARMS_FALLBACK_HAND_SIZE
        sleeve_w = config.ARMS_FALLBACK_SLEEVE_W
        wave = math.sin(math.pi * self.player.step_phase)
        for side in (-1, 1):  # 왼손, 오른손
            hand_x = x + side * pose.spread
            hand_y = y + pose.lift - side * pose.swing * wave
            hand_left = round(hand_x - hand_w / 2)
            hand_bottom = round(hand_y - hand_h / 2)
            sleeve_left = round(hand_x - sleeve_w / 2)
            gfx.fill_box(
                sleeve_left,
                0,
                sleeve_left + sleeve_w,
                hand_bottom,
                config.ARMS_FALLBACK_SLEEVE,
            )
            gfx.fill_box(
                hand_left,
                hand_bottom,
                hand_left + hand_w,
                hand_bottom + hand_h,
                config.ARMS_FALLBACK_SKIN,
            )
