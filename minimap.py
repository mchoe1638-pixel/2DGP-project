"""M 디버그: 위에서 내려다본 격자 지도를 화면 오른쪽 아래에 그린다.

+x가 오른쪽, +y가 위쪽이다. 세로로는 지도 전체를, 가로로는 플레이어 둘레 MINIMAP_VIEW_COLS칸만 보인다.
벽은 레이캐스터와 같은 단색, 바닥과 계단은 미니맵 색으로 칠한다. 줄마다 같은 색이 이어지는 칸은
사각형 하나로 묶어 그린다. B(충돌 원 표시)를 켜면 플레이어와 오브젝트의 충돌 원도 그린다.
"""

from collections.abc import Iterable, Sequence

from pico2d import draw_circle, draw_line

import config
import gfx
from camera import Camera
from map_grid import EMPTY, MapGrid
from raycaster import Color, wall_colors
from util import clamp

Circle = tuple[float, float, float]  # 월드 x, y, 반지름(m)


def color_runs(colors: Sequence[Color]) -> list[tuple[int, int, Color]]:
    """같은 색이 이어지는 구간들: (시작, 끝(미포함), 색)."""
    runs: list[tuple[int, int, Color]] = []
    start = 0
    for index in range(1, len(colors) + 1):
        if index == len(colors) or colors[index] != colors[start]:
            runs.append((start, index, colors[start]))
            start = index
    return runs


class Minimap:
    def __init__(self, grid: MapGrid) -> None:
        self.grid = grid
        self._colors = wall_colors(grid)
        self._cols = min(config.MINIMAP_VIEW_COLS, grid.width)
        self._right = config.SCREEN_W - config.MINIMAP_MARGIN
        self._left = self._right - self._cols * config.MINIMAP_CELL_PX
        self._bottom = config.MINIMAP_MARGIN

    # ------------------------------------------------------------ 그리기
    def draw(
        self, camera: Camera, objects: Iterable[Circle] = (), show_bb: bool = False
    ) -> None:
        """objects: 점으로 찍을 오브젝트의 충돌 원. show_bb면 원 테두리도 그린다."""
        first = self._first_column(camera.x)
        self._draw_cells(first)
        for x, y, radius in objects:
            self._draw_object(first, x, y, radius, show_bb)
        self._draw_player(first, camera, show_bb)

    def _first_column(self, world_x: float) -> int:
        """보이는 첫 열(지도 안 열 번호). 플레이어를 가운데 두되 지도 끝에서는 멈춘다."""
        local = int(world_x - self.grid.x_min)
        return int(clamp(0, local - self._cols // 2, self.grid.width - self._cols))

    def _cell_color(self, index: int) -> Color:
        code = self.grid.cells[index]
        if code != EMPTY:
            return self._colors[code]
        if self.grid.stairs[index]:
            return config.MINIMAP_STAIRS_COLOR
        return config.MINIMAP_FLOOR_COLOR

    def _draw_cells(self, first: int) -> None:
        cell = config.MINIMAP_CELL_PX
        for row in range(self.grid.height):
            base = row * self.grid.width + first
            colors = [self._cell_color(base + offset) for offset in range(self._cols)]
            bottom = self._bottom + row * cell
            for start, end, color in color_runs(colors):
                gfx.fill_box(
                    self._left + start * cell,
                    bottom,
                    self._left + end * cell,
                    bottom + cell,
                    color,
                )

    def _to_screen(self, first: int, x: float, y: float) -> tuple[int, int]:
        cell = config.MINIMAP_CELL_PX
        screen_x = self._left + (x - self.grid.x_min - first) * cell
        screen_y = self._bottom + (y - self.grid.y_min) * cell
        return int(screen_x), int(screen_y)

    def _draw_object(
        self, first: int, x: float, y: float, radius: float, show_bb: bool
    ) -> None:
        screen_x, screen_y = self._to_screen(first, x, y)
        if not self._left <= screen_x < self._right:
            return
        red, green, blue = config.MINIMAP_OBJECT_COLOR
        draw_circle(
            screen_x, screen_y, config.MINIMAP_OBJECT_PX, red, green, blue, 255, True
        )
        if show_bb:
            self._draw_ring(screen_x, screen_y, radius)

    def _draw_player(self, first: int, camera: Camera, show_bb: bool) -> None:
        screen_x, screen_y = self._to_screen(first, camera.x, camera.y)
        forward_x, forward_y = camera.forward
        length = config.MINIMAP_VIEW_LINE * config.MINIMAP_CELL_PX
        red, green, blue = config.MINIMAP_PLAYER_COLOR
        draw_line(
            screen_x,
            screen_y,
            int(screen_x + forward_x * length),
            int(screen_y + forward_y * length),
            red,
            green,
            blue,
        )
        draw_circle(
            screen_x, screen_y, config.MINIMAP_PLAYER_PX, red, green, blue, 255, True
        )
        if show_bb:
            self._draw_ring(screen_x, screen_y, config.PLAYER_RADIUS)

    @staticmethod
    def _draw_ring(screen_x: int, screen_y: int, radius: float) -> None:
        """충돌 원 테두리 (반지름 radius m)."""
        pixels = max(1, round(radius * config.MINIMAP_CELL_PX))
        red, green, blue = config.DEBUG_BB_COLOR
        draw_circle(screen_x, screen_y, pixels, red, green, blue, 255, False)
