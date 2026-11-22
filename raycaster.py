"""레이캐스팅 렌더러: 바닥·천장 띠와 벽.

화면을 폭 strip_w px의 세로 띠로 나누고, 띠마다 광선 하나를 쏴 처음 닿는 벽까지의 거리를 구한다.

- 광선 방향 = 앞 + 오른쪽 × t (t = 화면 가운데에서 띠까지의 거리 / PROJ). 앞 성분이 늘 1이라
  광선을 따라 잰 값이 곧 카메라 평면까지의 수직 거리다 (물고기 눈 왜곡이 없다).
- 칸을 하나씩 밟는 DDA 대신 '줄 단위'로 건넌다. 광선이 한 줄(같은 y칸) 안에 머무는 동안
  지나는 칸들 가운데 벽이 있는지는 미리 만든 표(그 줄에서 앞쪽으로 가장 가까운 벽 칸)로 한 번에 찾는다.
  긴 통로를 정면으로 볼 때도 광선 하나가 건너는 줄 수(통로 폭)만큼만 돈다.
- 지도 맨 바깥 테두리는 모두 벽이다 (map_grid.build_grid가 바닥 둘레를 한 칸씩 더 둔다).
  그래서 광선은 범위 검사 없이 반드시 벽에서 멈춘다. 만들 때 한 번 확인한다.

벽 띠 아래끝 = 지평선 - 눈높이 × PROJ / d, 높이 = WALL_HEIGHT × PROJ / d.
띠마다 거리를 zbuf에 남겨, 빌보드가 벽 뒤에 가려지는지 띠 단위로 가린다.
바닥·천장은 바닥 캐스팅 없이 GRADIENT_BANDS개의 단색 띠로 칠한다 (지평선 쪽이 어둡다).
"""

import logging

import pico2d
import pico2d.pico2d as pico_core

import camera as cam
import config
from camera import Camera
from map_grid import DEFAULT_WALL, EMPTY, MapGrid
from stage_data import TEX_DOOR_WC

Color = tuple[int, int, int]

DEFAULT_WALL_COLOR: Color = config.WALL_FALLBACK_COLORS[DEFAULT_WALL]
SIDE_X = 0  # x축에 수직인 벽면에 닿음 (광선이 x 방향으로 칸을 넘다가)
SIDE_Y = 1  # y축에 수직인 벽면에 닿음

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
        self._door_code = (
            grid.code_of(TEX_DOOR_WC) if TEX_DOOR_WC in grid.textures else None
        )
        self.strip_w = config.RAY_STRIP_W
        self.zbuf: list[float] = []  # 띠마다 벽까지의 수직 거리(m)
        self._sides: list[int] = []
        self._codes: list[int] = []

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
        """골인 문을 연 색(초록)이나 닫힌 색(파랑)으로 그린다."""
        if self._door_code is None:
            return
        closed = config.WALL_FALLBACK_COLORS.get(TEX_DOOR_WC, DEFAULT_WALL_COLOR)
        self._base_colors[self._door_code] = (
            config.DOOR_OPEN_FALLBACK_COLOR if is_open else closed
        )

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
        """띠마다 광선을 쏴 zbuf·닿은 면·칸 값을 채운다."""
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
        cast = self._cast
        for strip in range(count):
            t = (strip * strip_w + strip_w / 2 - cam.HALF_W) / cam.PROJ
            dist, side, code = cast(
                origin_x, origin_y, forward_x + right_x * t, forward_y + right_y * t
            )
            zbuf[strip] = dist
            sides[strip] = side
            codes[strip] = code
        self.zbuf, self._sides, self._codes = zbuf, sides, codes

    def _cast(
        self, origin_x: float, origin_y: float, ray_x: float, ray_y: float
    ) -> tuple[float, int, int]:
        """지도 안 좌표 (origin_x, origin_y)에서 방향 (ray_x, ray_y)로 쏜 광선이 처음 닿는 벽.

        돌려주는 값: (수직 거리, 닿은 면 SIDE_X / SIDE_Y, 벽 칸 값).
        """
        width, cells = self.grid.width, self.grid.cells
        col, row = int(origin_x), int(origin_y)
        here = cells[row * width + col]
        if here != EMPTY:  # 벽 안에 있으면 눈앞이 모두 벽이다
            return config.RAY_MIN_DIST, SIDE_X, here
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
                return max(dist, config.RAY_MIN_DIST), SIDE_X, cells[base + wall_col]
            col = last_col
            row += step_y
            exit_y += step_y
            code = cells[row * width + col]
            if code != EMPTY:
                face = row if step_y > 0 else row + 1
                dist = (face - origin_y) * inv_y
                return max(dist, config.RAY_MIN_DIST), SIDE_Y, code

    def _draw_walls(self, camera: Camera) -> None:
        horizon = camera.horizon_y
        eye_z = camera.eye_z
        proj = cam.PROJ
        wall_h = config.WALL_HEIGHT
        screen_h = config.SCREEN_H
        strip_w = self.strip_w
        colors = self._base_colors
        fog_k = config.FOG_K
        side_shade = config.SIDE_SHADE
        fill = self._painter.fill
        for strip, dist in enumerate(self.zbuf):
            scale = proj / dist
            bottom = max(0, int(horizon - eye_z * scale))
            top = min(screen_h, int(horizon + (wall_h - eye_z) * scale))
            ratio = 1.0 / (1.0 + dist * fog_k)
            if self._sides[strip] == SIDE_Y:
                ratio *= side_shade
            red, green, blue = colors[self._codes[strip]]
            left = strip * strip_w
            fill(
                left,
                bottom,
                left + strip_w,
                top,
                int(red * ratio),
                int(green * ratio),
                int(blue * ratio),
            )
