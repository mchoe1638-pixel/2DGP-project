"""manifest.json 기반 이미지 로딩과 스프라이트 시트 도우미.

이미지는 처음 그릴 때 한 번만 불러온다(지연 로딩). 그래서 캔버스를 열기 전이나 테스트에서도
Sprite를 만들 수 있고, 테스트는 loader를 바꿔 끼워 그리기 호출만 검사한다.
스프라이트 시트는 모두 한 줄(single-row)이다.
Sprite.draw는 원본 크기 그대로 그린다(키우려면 scale 인자). 월드에 세운 빌보드는
레이캐스터가 거리에 맞춰 줄여서 직접 그린다.
"""

import json
import logging
import os
from collections.abc import Callable
from typing import Any, NamedTuple

import config
from util import snap

REQUIRED_FIELDS = ("file", "frame_w", "frame_h", "frames")

_log = logging.getLogger(__name__)


class SpriteInfo(NamedTuple):
    """manifest 한 줄: 이미지 파일 위치와 프레임 정보."""

    name: str
    path: str
    frame_w: int
    frame_h: int
    frames: int
    fps: float | None


def _to_info(name: str, entry: Any, root: str) -> SpriteInfo:
    if not isinstance(entry, dict):
        raise ValueError(f"manifest 항목 '{name}'이(가) 객체가 아닙니다.")
    missing = [field for field in REQUIRED_FIELDS if field not in entry]
    if missing:
        raise ValueError(
            f"manifest 항목 '{name}'에 필요한 값이 없습니다: {', '.join(missing)}"
        )
    path = os.path.normpath(os.path.join(root, entry["file"]))
    return SpriteInfo(
        name,
        path,
        entry["frame_w"],
        entry["frame_h"],
        entry["frames"],
        entry.get("fps"),
    )


def load_manifest(
    path: str = config.MANIFEST_PATH, root: str = config.ASSET_ROOT
) -> dict[str, SpriteInfo]:
    """manifest.json을 읽어 {이름: SpriteInfo}를 돌려준다. file 경로는 root 기준이다."""
    try:
        with open(path, encoding="utf-8") as manifest_file:
            raw = json.load(manifest_file)
    except FileNotFoundError:
        raise FileNotFoundError(f"manifest.json 을 찾을 수 없습니다: {path}") from None
    except json.JSONDecodeError as error:
        raise ValueError(
            f"manifest.json 을 읽을 수 없습니다 ({path}): {error}"
        ) from error
    return {name: _to_info(name, entry, root) for name, entry in raw.items()}


def _load_with_pico2d(path: str) -> Any:
    import pico2d  # 지연 import: 캔버스 없이 이 모듈을 import하는 테스트를 위해

    return pico2d.load_image(path)


class Sprite:
    """한 줄짜리 스프라이트 시트. 좌표는 모두 픽셀 단위로 반올림해서 그린다."""

    def __init__(
        self, info: SpriteInfo, loader: Callable[[str], Any] = _load_with_pico2d
    ) -> None:
        self.info = info
        self.frame_w = info.frame_w
        self.frame_h = info.frame_h
        self.frames = info.frames
        self.fps = info.fps if info.fps is not None else config.DEFAULT_ANIM_FPS
        self._loader = loader
        self._image: Any = None

    def _get_image(self) -> Any:
        if self._image is None:
            self._image = self._loader(self.info.path)
        return self._image

    def load(self) -> None:
        """이미지를 지금 불러온다. 캔버스를 연 직후 호출하면 첫 그리기에서 끊기지 않는다."""
        self._get_image()

    @property
    def image(self) -> Any:
        """pico2d 이미지 (아직 안 불렀으면 이때 불러온다). 텍스처를 SDL로 바로 그릴 때 쓴다."""
        return self._get_image()

    def next_frame(self, frame: float, dt: float) -> float:
        """애니메이션 프레임 번호(소수)를 dt초만큼 진행시킨다."""
        return (frame + self.fps * dt) % self.frames

    def ground_center_y(self, height: float = 0) -> float:
        """발이 지면 위 height만큼 떠 있을 때 스프라이트 중심의 y 좌표."""
        return config.GROUND_Y + self.frame_h / 2 - config.FOOT_OFFSET + height

    def draw(
        self,
        x: float,
        y: float,
        frame: float = 0,
        flip: bool = False,
        scale: float = 1,
        alpha: float = 1.0,
    ) -> None:
        """(x, y)를 중심으로 frame번째 칸을 그린다. flip은 좌우 반전, alpha는 투명도."""
        image = self._get_image()
        left = int(frame) % self.frames * self.frame_w
        translucent = alpha < 1.0
        if translucent:
            image.opacify(alpha)
        try:
            self._clip_draw(image, left, snap(x), snap(y), flip, scale)
        finally:
            if translucent:
                image.opacify(1.0)  # 텍스처는 공유되므로 반드시 되돌린다

    def _clip_draw(
        self, image: Any, left: int, x: int, y: int, flip: bool, scale: float
    ) -> None:
        width, height = snap(self.frame_w * scale), snap(self.frame_h * scale)
        if flip:
            # clip_composite_draw는 w/h를 생략하면 시트 전체 크기를 쓰므로 항상 명시한다.
            image.clip_composite_draw(
                left, 0, self.frame_w, self.frame_h, 0, "h", x, y, width, height
            )
        elif scale == 1:
            image.clip_draw(left, 0, self.frame_w, self.frame_h, x, y)
        else:
            image.clip_draw(left, 0, self.frame_w, self.frame_h, x, y, width, height)

    def draw_at_origin(self, x: float, y: float, clip_w: int | None = None) -> None:
        """(x, y)를 왼쪽 아래 모서리로 하여 첫 칸을 그린다. 타일링용(clip_w로 오른쪽을 자른다)."""
        width = self.frame_w if clip_w is None else clip_w
        self._get_image().clip_draw_to_origin(
            0, 0, width, self.frame_h, snap(x), snap(y)
        )

    def draw_stretched(
        self,
        left: float,
        bottom: float,
        width: float,
        height: float,
        alpha: float = 1.0,
    ) -> None:
        """첫 칸을 왼쪽 아래 (left, bottom)에서 width × height 크기로 늘려 그린다 (단색 띠·가림막용)."""
        image = self._get_image()
        translucent = alpha < 1.0
        if translucent:
            image.opacify(alpha)
        try:
            image.clip_draw_to_origin(
                0,
                0,
                self.frame_w,
                self.frame_h,
                snap(left),
                snap(bottom),
                snap(width),
                snap(height),
            )
        finally:
            if translucent:
                image.opacify(1.0)  # 텍스처는 공유되므로 반드시 되돌린다


SpriteLookup = Callable[[str], Sprite]  # 이름 → 스프라이트 (테스트·폴백에서 바꿔 끼운다)

_manifest: dict[str, SpriteInfo] | None = None
_sprites: dict[str, Sprite] = {}
_reported_missing: set[str] = set()  # 이미 알린 이름 (로그를 되풀이하지 않는다)


def _manifest_entries() -> dict[str, SpriteInfo]:
    global _manifest
    if _manifest is None:
        _manifest = load_manifest()
    return _manifest


def get_sprite(name: str) -> Sprite:
    """manifest에 등록된 스프라이트를 이름으로 가져온다. 같은 이름은 항상 같은 객체다."""
    cached = _sprites.get(name)
    if cached is not None:
        return cached
    info = _manifest_entries().get(name)
    if info is None:
        raise KeyError(f"manifest에 없는 스프라이트: {name}")
    sprite = Sprite(info)
    _sprites[name] = sprite
    return sprite


def find_sprite(name: str, substitute: str = "") -> Sprite | None:
    """get_sprite와 같지만 manifest에 없으면 예외 대신 None을 돌려준다 (없어도 되는 꾸밈 그림용).

    substitute에 그림 대신 하는 일을 적어 두면, 없을 때 처음 한 번만 이름과 함께 로그로 알린다.
    """
    if name in _manifest_entries():
        return get_sprite(name)
    if substitute and name not in _reported_missing:
        _reported_missing.add(name)
        _log.warning("manifest에 %s 이(가) 없어 %s", name, substitute)
    return None


def preload_all() -> None:
    """manifest의 모든 이미지를 미리 불러온다 (캔버스를 연 뒤에 호출).

    처음 그릴 때 불러오면 게임 도중 한두 프레임이 끊기므로 시작할 때 한꺼번에 읽어 둔다.
    """
    for name in _manifest_entries():
        get_sprite(name).load()


def require_font_file(path: str) -> str:
    """폰트 파일이 있는지 확인하고 경로를 그대로 돌려준다. 없으면 어디를 봐야 하는지 알려 준다."""
    if not os.path.isfile(path):
        raise FileNotFoundError(
            f"폰트 파일을 찾을 수 없습니다: {path}\n"
            f"resource/font/ 폴더에 {os.path.basename(path)} 가 있는지 확인하세요."
        )
    return path
