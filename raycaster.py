"""레이캐스팅 렌더러: 바닥·천장 띠, 텍스처 벽, 벽에 가려지는 빌보드.

화면을 폭 strip_w px의 세로 띠로 나누고, 띠마다 광선 하나를 쏴 처음 닿는 벽까지의 거리를 구한다.

- 광선 방향 = 앞 + 오른쪽 × t (t = 화면 가운데에서 띠까지의 거리 / PROJ). 앞 성분이 늘 1이라
  광선을 따라 잰 값이 곧 카메라 평면까지의 수직 거리다 (물고기 눈 왜곡이 없다).
- 칸을 하나씩 밟는 DDA 대신 '줄 단위'로 건넌다. 광선이 한 줄(같은 y칸) 안에 머무는 동안
  지나는 칸들 가운데 벽이 있는지는 미리 만든 표(그 줄에서 앞쪽으로 가장 가까운 벽 칸)로 한 번에 찾는다.
  긴 통로를 정면으로 볼 때도 광선 하나가 건너는 줄 수(통로 폭)만큼만 돈다.
- 지도 맨 바깥 테두리는 모두 벽이다 (map_grid.build_grid가 바닥 둘레를 한 칸씩 더 둔다).
  그래서 광선은 범위 검사 없이 반드시 벽에서 멈춘다. 만들 때 한 번 확인한다.

벽 띠 아래끝 = 지평선 - 눈높이 × PROJ / d, 높이 = WALL_HEIGHT × PROJ / d.
벽 텍스처: 광선이 닿은 곳이 벽면의 어디쯤인지(u, 0~1)로 텍스처의 세로줄 한 겹(폭 1px)을 골라 띠 크기로
늘려 그린다. 거리에 따른 어두움은 텍스처에 색을 곱해(SDL_SetTextureColorMod) 주고, 텍스처가 없는 벽은
같은 자리에 단색 띠를 칠한다. 바닥·천장은 바닥 캐스팅 없이 GRADIENT_BANDS개의 단색 띠다 (지평선 쪽이 어둡다).

띠마다 거리를 zbuf에 남기고, 빌보드는 먼 것부터 그리되 자기보다 가까운 벽이 있는 띠에서는 잘라서 가린다.
빌보드는 늘 카메라를 마주 보는 그림 한 장이라 (x, y, z) 월드 위치와 높이(m)만 있으면 된다.
"""

import logging
import operator
from collections.abc import Iterable
from typing import Any, NamedTuple

import pico2d
import pico2d.pico2d as pico_core

import camera as cam
import config
import resource
from camera import Camera
from game_object import Billboard
from map_grid import DEFAULT_WALL, EMPTY, MapGrid
from stage_data import TEX_DOOR_WC
from util import clamp

Color = tuple[int, int, int]
ScreenRect = tuple[float, float, float, float]  # 왼쪽, 위(화면 위 끝에서 잰 y), 너비, 높이

DEFAULT_WALL_COLOR: Color = config.WALL_FALLBACK_COLORS[DEFAULT_WALL]
SIDE_X = 0  # x축에 수직인 벽면에 닿음 (광선이 x 방향으로 칸을 넘다가)
SIDE_Y = 1  # y축에 수직인 벽면에 닿음
FULL_TINT = 255  # 색을 곱하지 않은 밝기 (SDL_SetTextureColorMod의 최댓값)
WALL_SOLID_NOTE = "단색 벽으로 그립니다"

_log = logging.getLogger(__name__)


# ---------------------------------------------------------------- 빠른 사각형
class _RectPainter:
    """SDL에 바로 단색 사각형을 칠한다. SDL_Rect 하나를 다시 써서 띠 수백 개를 빠르게 그린다.

    좌표는 pico2d처럼 화면 아래가 0이다. [left, right) × [bottom, top)를 칠한다.
    """

    def __init__(self) -> None:
        self._rect = pico2d.SDL_Rect(0, 0, 0, 0)

    def fill(
        self, left: int, bottom: int, right: int, top: int, r: int, g: int, b: int
    ) -> None:
        if right <= left or top <= bottom:
            return
        renderer = pico_core.renderer
        rect = self._rect
        rect.x = left
        rect.y = config.SCREEN_H - top
        rect.w = right - left
        rect.h = top - bottom
        pico2d.SDL_SetRenderDrawColor(renderer, r, g, b, 255)
        pico2d.SDL_RenderFillRect(renderer, rect)


def fog(dist: float) -> float:
    """거리 dist(m)에서의 밝기 비율 (1 = 원래 색)."""
    return 1.0 / (1.0 + dist * config.FOG_K)


def shade(color: Color, ratio: float) -> Color:
    red, green, blue = color
    return int(red * ratio), int(green * ratio), int(blue * ratio)


def wall_colors(grid: MapGrid) -> list[Color]:
    """칸 값 → 벽 단색 (텍스처가 없을 때 쓰는 색). 0번(바닥) 자리는 쓰지 않는다."""
    colors = [DEFAULT_WALL_COLOR]
    for name in grid.textures:
        colors.append(config.WALL_FALLBACK_COLORS.get(name, DEFAULT_WALL_COLOR))
    return colors


# ---------------------------------------------------------------- 벽 텍스처
class _WallSkin(NamedTuple):
    """텍스처로 그리는 벽 한 종류. left는 지금 보여 줄 칸의 왼쪽 x(px)다 (문이 열리면 바뀐다)."""

    texture: Any
    left: int
    frame_w: int
    frame_h: int
    frames: int


def _load_skin(name: str) -> _WallSkin | None:
    """벽 텍스처 이름 → 그리는 데 쓸 값. manifest에 없으면 None (단색 벽으로 그린다)."""
    sprite = resource.find_sprite(name, WALL_SOLID_NOTE)
    if sprite is None:
        return None
    texture = sprite.image.texture
    return _WallSkin(texture, 0, sprite.frame_w, sprite.frame_h, sprite.frames)


# ---------------------------------------------------------------- 광선 표
def _walls_ahead(grid: MapGrid) -> tuple[list[int], list[int]]:
    """줄마다 '이 칸부터 +x 쪽으로 가장 가까운 벽 칸 열'과 '-x 쪽으로 가장 가까운 벽 칸 열'.

    둘 다 cells와 같은 순서(줄 × width + 열)의 평평한 목록이다. 테두리가 벽이라 늘 찾아진다.
    """
    width, cells = grid.width, grid.cells
    to_pos = [0] * len(cells)
    to_neg = [0] * len(cells)
    for row in range(grid.height):
        base = row * width
        nearest = width - 1
        for col in range(width - 1, -1, -1):
            if cells[base + col] != EMPTY:
                nearest = col
            to_pos[base + col] = nearest
        nearest = 0
        for col in range(width):
            if cells[base + col] != EMPTY:
                nearest = col
            to_neg[base + col] = nearest
    return to_pos, to_neg


def _check_border(grid: MapGrid) -> None:
    """맨 바깥 테두리가 모두 벽인지 확인한다. 아니면 광선이 지도 밖으로 나갈 수 있다."""
    width, height, cells = grid.width, grid.height, grid.cells
    border = [*range(width), *range((height - 1) * width, height * width)]
    border += [row * width for row in range(height)]
    border += [row * width + width - 1 for row in range(height)]
    if any(cells[index] == EMPTY for index in border):
        raise ValueError("지도 테두리에 바닥 칸이 있습니다. 테두리는 모두 벽이어야 합니다.")


# ---------------------------------------------------------------- 렌더러
class Raycaster:
    def __init__(self, grid: MapGrid) -> None:
        _check_border(grid)
        self.grid = grid
        self._to_pos, self._to_neg = _walls_ahead(grid)
        self._painter = _RectPainter()
        self._base_colors = wall_colors(grid)
        # 칸 값 → 텍스처 (0번은 바닥이라 비워 둔다). None이면 단색 띠로 그린다.
        self._skins: list[_WallSkin | None] = [None, *map(_load_skin, grid.textures)]
        self._tint = [FULL_TINT] * len(self._skins)  # 텍스처마다 지금 걸려 있는 밝기
        self._door_code = (
            grid.code_of(TEX_DOOR_WC) if TEX_DOOR_WC in grid.textures else None
        )
        self._door_skin = (
            None if self._door_code is None else self._skins[self._door_code]
        )
        self._strip_src = pico2d.SDL_Rect(0, 0, 1, 1)  # 벽 띠: 텍스처에서 떼는 세로줄
        self._strip_dst = pico2d.SDL_Rect(0, 0, 1, 1)
        self._board_src = pico2d.SDL_Rect(0, 0, 1, 1)  # 빌보드: 시트에서 떼는 한 칸
        self._board_dst = pico2d.SDL_FRect(0.0, 0.0, 1.0, 1.0)
        self.strip_w = config.RAY_STRIP_W
        self.zbuf: list[float] = []  # 띠마다 벽까지의 수직 거리(m)
        self._sides: list[int] = []
        self._codes: list[int] = []
        self._us: list[float] = []  # 띠가 닿은 벽면 위의 가로 위치 (0~1)

    # ------------------------------------------------------------ 설정
    @property
    def strip_count(self) -> int:
        return -(-config.SCREEN_W // self.strip_w)  # 올림: 마지막 띠가 화면 끝을 넘어도 된다

    def cycle_strip_width(self) -> int:
        """띠 폭을 RAY_STRIP_CHOICES 순서대로 바꾼다. 바뀐 폭을 돌려준다."""
        choices = config.RAY_STRIP_CHOICES
        index = choices.index(self.strip_w) if self.strip_w in choices else -1
        self.strip_w = choices[(index + 1) % len(choices)]
        _log.info("광선 띠 폭 %dpx (광선 %d개)", self.strip_w, self.strip_count)
        return self.strip_w

    def set_door_open(self, is_open: bool) -> None:
        """골인 문을 연 모습으로 바꾸거나 닫는다.

        문 텍스처가 2칸 이상이면 둘째 칸이 열린 문이다. 1칸이면 열려 있는 동안 연 색(초록)
        단색으로 바꿔 칠하고, 텍스처가 아예 없으면 닫힌 색(파랑)과 연 색(초록)을 바꿔 칠한다.
        """
        code = self._door_code
        if code is None:
            return
        skin = self._door_skin
        if skin is not None and skin.frames >= 2:
            self._skins[code] = skin._replace(left=skin.frame_w if is_open else 0)
            return
        closed = config.WALL_FALLBACK_COLORS.get(TEX_DOOR_WC, DEFAULT_WALL_COLOR)
        self._base_colors[code] = config.DOOR_OPEN_FALLBACK_COLOR if is_open else closed
        if skin is not None:
            self._skins[code] = None if is_open else skin

    # ------------------------------------------------------------ 그리기
    def render(self, camera: Camera, floor_color: Color) -> None:
        """바닥·천장 띠를 깔고, 광선을 쏴 벽을 그린다. zbuf가 이번 프레임 값으로 바뀐다."""
        self._draw_backdrop(camera, floor_color)
        self._cast_all(camera)
        self._draw_walls(camera)

    def _draw_backdrop(self, camera: Camera, floor_color: Color) -> None:
        """지평선 아래는 바닥, 위는 천장. 띠마다 그 띠 가운데 줄이 보여 주는 거리로 어둡게 한다."""
        horizon = round(camera.horizon_y)
        bands = config.GRADIENT_BANDS
        ceiling_gap = max(config.WALL_HEIGHT - camera.eye_z, 0.0)
        self._draw_bands(0, horizon, bands, floor_color, camera.eye_z, horizon)
        self._draw_bands(
            horizon, config.SCREEN_H, bands, config.CEIL_COLOR, ceiling_gap, horizon
        )

    def _draw_bands(
        self,
        bottom: int,
        top: int,
        bands: int,
        color: Color,
        height_gap: float,
        horizon: int,
    ) -> None:
        """[bottom, top) 영역을 bands개의 띠로 나눠 칠한다.

        띠 가운데 줄이 지평선에서 r px 떨어져 있으면, 그 줄은 높이 차 height_gap(m)인 면을
        height_gap × PROJ / r m 앞에서 본 것이다. 그 거리로 어둡게 한다.
        """
        span = top - bottom
        if span <= 0:
            return
        for band in range(bands):
            low = bottom + span * band // bands
            high = bottom + span * (band + 1) // bands
            middle = (low + high) / 2
            gap_px = max(abs(middle - horizon), 1.0)
            red, green, blue = shade(color, fog(height_gap * cam.PROJ / gap_px))
            self._painter.fill(0, low, config.SCREEN_W, high, red, green, blue)

    def _cast_all(self, camera: Camera) -> None:
        """띠마다 광선을 쏴 zbuf·닿은 면·칸 값·벽면 위치를 채운다."""
        grid = self.grid
        origin_x = camera.x - grid.x_min
        origin_y = camera.y - grid.y_min
        forward_x, forward_y = camera.forward
        right_x, right_y = camera.right
        strip_w = self.strip_w
        count = self.strip_count
        zbuf = [0.0] * count
        sides = [0] * count
        codes = [0] * count
        us = [0.0] * count
        cast = self._cast
        for strip in range(count):
            t = (strip * strip_w + strip_w / 2 - cam.HALF_W) / cam.PROJ
            zbuf[strip], sides[strip], codes[strip], us[strip] = cast(
                origin_x, origin_y, forward_x + right_x * t, forward_y + right_y * t
            )
        self.zbuf, self._sides, self._codes, self._us = zbuf, sides, codes, us

    def _cast(
        self, origin_x: float, origin_y: float, ray_x: float, ray_y: float
    ) -> tuple[float, int, int, float]:
        """지도 안 좌표 (origin_x, origin_y)에서 방향 (ray_x, ray_y)로 쏜 광선이 처음 닿는 벽.

        돌려주는 값: (수직 거리, 닿은 면 SIDE_X / SIDE_Y, 벽 칸 값, 벽면 위 가로 위치 u).
        u는 벽면을 바깥에서 마주 볼 때 왼쪽 끝이 0, 오른쪽 끝이 1이다 (텍스처가 뒤집히지 않는다).
        u는 RAY_MIN_DIST로 거리를 끌어올리기 전의 거리로 구한다.
        """
        width, cells = self.grid.width, self.grid.cells
        col, row = int(origin_x), int(origin_y)
        here = cells[row * width + col]
        if here != EMPTY:  # 벽 안에 있으면 눈앞이 모두 벽이다
            return config.RAY_MIN_DIST, SIDE_X, here, 0.0
        positive_x = ray_x >= 0.0
        walls = self._to_pos if positive_x else self._to_neg
        step_y = 1 if ray_y > 0.0 else -1 if ray_y < 0.0 else 0
        inv_y = 1.0 / ray_y if step_y else 0.0
        exit_y = row + 1 if step_y > 0 else row  # 지금 줄을 벗어나는 경계의 y
        while True:
            base = row * width
            wall_col = walls[base + col]
            if step_y == 0:
                last_col = wall_col  # 줄을 벗어나지 않는다: 그 줄의 다음 벽까지 간다
            else:
                last_col = int(origin_x + ray_x * (exit_y - origin_y) * inv_y)
            if (wall_col <= last_col) if positive_x else (wall_col >= last_col):
                face = wall_col if positive_x else wall_col + 1
                dist = (face - origin_x) / ray_x
                along = (origin_y + ray_y * dist) % 1.0  # +y 쪽으로 갈수록 커진다
                u = 1.0 - along if positive_x else along  # +x를 보면 오른쪽이 -y
                return max(dist, config.RAY_MIN_DIST), SIDE_X, cells[base + wall_col], u
            col = last_col
            row += step_y
            exit_y += step_y
            code = cells[row * width + col]
            if code != EMPTY:
                face = row if step_y > 0 else row + 1
                dist = (face - origin_y) * inv_y
                along = (origin_x + ray_x * dist) % 1.0  # +x 쪽으로 갈수록 커진다
                u = along if step_y > 0 else 1.0 - along  # +y를 보면 오른쪽이 +x
                return max(dist, config.RAY_MIN_DIST), SIDE_Y, code, u

    # ------------------------------------------------------------ 벽 그리기
    def _draw_walls(self, camera: Camera) -> None:
        """띠마다 벽을 그린다. 텍스처가 있으면 그 세로줄 한 겹을, 없으면 단색 띠를 칠한다."""
        horizon, eye_z = camera.horizon_y, camera.eye_z
        rise = config.WALL_HEIGHT - eye_z
        proj, fog_k, side_shade = cam.PROJ, config.FOG_K, config.SIDE_SHADE
        skins, codes, sides, us = self._skins, self._codes, self._sides, self._us
        strip_w = self.strip_w
        for strip, dist in enumerate(self.zbuf):
            scale = proj / dist
            bottom = round(horizon - eye_z * scale)
            top = round(horizon + rise * scale)
            ratio = 1.0 / (1.0 + dist * fog_k)
            if sides[strip] == SIDE_Y:
                ratio *= side_shade
            code = codes[strip]
            skin = skins[code]
            left = strip * strip_w
            if skin is None:
                self._fill_strip(left, bottom, top, code, ratio)
            else:
                self._copy_strip(left, bottom, top, code, skin, us[strip], ratio)
        self._reset_tints()

    def _fill_strip(
        self, left: int, bottom: int, top: int, code: int, ratio: float
    ) -> None:
        """텍스처가 없는 벽: 단색을 거리만큼 어둡게 칠한다."""
        red, green, blue = self._base_colors[code]
        self._painter.fill(
            left,
            max(0, bottom),
            left + self.strip_w,
            min(config.SCREEN_H, top),
            int(red * ratio),
            int(green * ratio),
            int(blue * ratio),
        )

    def _copy_strip(
        self,
        left: int,
        bottom: int,
        top: int,
        code: int,
        skin: _WallSkin,
        u: float,
        ratio: float,
    ) -> None:
        """텍스처의 세로줄 한 겹(폭 1px)을 [bottom, top)으로 늘여 그린다.

        띠가 화면보다 커도 자르지 않고 그대로 넘긴다 (화면 밖은 그래픽 카드가 잘라 낸다).
        거리에 따른 어두움은 텍스처에 곱하는 색으로 주고, 값이 바뀔 때만 SDL을 부른다.
        """
        if top <= bottom:
            return
        texture = skin.texture
        value = int(FULL_TINT * ratio)
        if self._tint[code] != value:
            pico2d.SDL_SetTextureColorMod(texture, value, value, value)
            self._tint[code] = value
        src, dst = self._strip_src, self._strip_dst
        src.x = skin.left + min(int(u * skin.frame_w), skin.frame_w - 1)
        src.h = skin.frame_h
        dst.x = left
        dst.y = config.SCREEN_H - top
        dst.w = self.strip_w
        dst.h = top - bottom
        pico2d.SDL_RenderCopy(pico_core.renderer, texture, src, dst)

    def _reset_tints(self) -> None:
        """어둡게 곱해 둔 벽 텍스처를 원래 밝기로 되돌린다 (텍스처는 다른 곳과 공유될 수 있다)."""
        for code, skin in enumerate(self._skins):
            if skin is not None and self._tint[code] != FULL_TINT:
                pico2d.SDL_SetTextureColorMod(
                    skin.texture, FULL_TINT, FULL_TINT, FULL_TINT
                )
                self._tint[code] = FULL_TINT

    # ------------------------------------------------------------ 빌보드
    def draw_billboards(
        self, camera: Camera, billboards: Iterable[Billboard]
    ) -> None:
        """빌보드를 먼 것부터 그린다. render()로 zbuf를 채운 뒤에 부른다.

        카메라 뒤나 BILLBOARD_MIN_DIST보다 가까운 것은 건너뛴다. 빌보드보다 가까운 벽이 있는 띠는
        가려지므로, 그 띠를 뺀 구간마다 화면을 잘라(clip) 그린다.
        """
        placed = []
        for board in billboards:
            depth, lateral = camera.to_camera(board.x, board.y)
            if depth >= config.BILLBOARD_MIN_DIST:
                placed.append((depth, lateral, board))
        # 먼 것부터. 거리(첫 값)로만 정렬한다: Billboard끼리는 비교할 수 없다.
        placed.sort(key=operator.itemgetter(0), reverse=True)
        for depth, lateral, board in placed:
            self._draw_billboard(camera, depth, lateral, board)

    def _draw_billboard(
        self, camera: Camera, depth: float, lateral: float, board: Billboard
    ) -> None:
        rect = self._screen_rect(camera, depth, lateral, board)
        if rect is None:
            return
        left, _, width, _ = rect
        first = max(0, int(left) // self.strip_w)
        last = min(len(self.zbuf) - 1, int(left + width) // self.strip_w)
        runs = self._open_runs(first, last, depth)
        if not runs:
            return
        texture = board.sprite.image.texture
        alpha = clamp(0, int(FULL_TINT * board.alpha), FULL_TINT)
        self._modulate(texture, int(FULL_TINT * fog(depth)), alpha)
        try:
            if runs == [(first, last)]:
                self._blit(board, rect)  # 가려진 띠가 없으면 자르지 않는다
            else:
                self._blit_runs(board, rect, runs)
        finally:
            self._modulate(texture, FULL_TINT, FULL_TINT)  # 공유 텍스처라 되돌린다

    def _screen_rect(
        self, camera: Camera, depth: float, lateral: float, board: Billboard
    ) -> ScreenRect | None:
        """빌보드가 화면에서 차지하는 사각형. 화면 밖이거나 1px보다 작으면 None."""
        sprite = board.sprite
        scale = cam.PROJ / depth
        height = board.world_h * scale
        width = height * sprite.frame_w / sprite.frame_h
        left = cam.HALF_W + lateral * scale - width / 2
        # 그림 맨 아래는 발바닥보다 FOOT_OFFSET px(그림 기준) 더 아래다
        bottom = (
            camera.horizon_y
            + (board.z - camera.eye_z) * scale
            - height * config.FOOT_OFFSET / sprite.frame_h
        )
        top = config.SCREEN_H - (bottom + height)
        if height < 1.0 or left + width <= 0 or left >= config.SCREEN_W:
            return None
        if top + height <= 0 or top >= config.SCREEN_H:
            return None
        return left, top, width, height

    def _open_runs(
        self, first: int, last: int, depth: float
    ) -> list[tuple[int, int]]:
        """띠 first~last 가운데 벽이 depth보다 먼(= 가려지지 않은) 띠의 연속 구간 (처음, 끝)."""
        runs: list[tuple[int, int]] = []
        start = -1
        zbuf = self.zbuf
        for strip in range(first, last + 1):
            if depth < zbuf[strip]:
                if start < 0:
                    start = strip
            elif start >= 0:
                runs.append((start, strip - 1))
                start = -1
        if start >= 0:
            runs.append((start, last))
        return runs

    @staticmethod
    def _modulate(texture: Any, value: int, alpha: int) -> None:
        """텍스처에 곱하는 밝기(value)와 투명도(alpha)를 정한다. 둘 다 0~255다."""
        pico2d.SDL_SetTextureColorMod(texture, value, value, value)
        pico2d.SDL_SetTextureAlphaMod(texture, alpha)

    def _blit(self, board: Billboard, rect: ScreenRect) -> None:
        sprite = board.sprite
        src, dst = self._board_src, self._board_dst
        src.x = int(board.frame) % sprite.frames * sprite.frame_w
        src.y = 0
        src.w = sprite.frame_w
        src.h = sprite.frame_h
        dst.x, dst.y, dst.w, dst.h = rect
        flip = pico2d.SDL_FLIP_HORIZONTAL if board.flip else pico2d.SDL_FLIP_NONE
        pico2d.SDL_RenderCopyExF(
            pico_core.renderer, sprite.image.texture, src, dst, 0.0, None, flip
        )

    def _blit_runs(
        self, board: Billboard, rect: ScreenRect, runs: list[tuple[int, int]]
    ) -> None:
        """보이는 띠 구간마다 화면을 잘라 그린다. 끝나면 자르기를 푼다."""
        renderer = pico_core.renderer
        clip = pico2d.SDL_Rect(0, 0, 0, config.SCREEN_H)
        try:
            for start, end in runs:
                clip.x = start * self.strip_w
                clip.w = (end - start + 1) * self.strip_w
                pico2d.SDL_RenderSetClipRect(renderer, clip)
                self._blit(board, rect)
        finally:
            pico2d.SDL_RenderSetClipRect(renderer, None)
