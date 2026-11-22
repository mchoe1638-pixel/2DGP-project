"""입력 상태: 눌려 있는 키와, 프레임마다 마우스가 움직인 양.

- 키는 이벤트(KEYDOWN/KEYUP)로 받아 '눌려 있는 키' 집합을 유지한다. 이번 프레임에 새로 눌린 키도 따로 기억한다.
- 마우스는 상대 모드로 잡아 두고, 한 프레임에 한 번 SDL_GetRelativeMouseState로 움직인 양을 읽는다.
  (MOUSEMOTION 이벤트는 쓰지 않는다: 창 가장자리에 막히지 않는 상대 이동 값이 필요하다.)
"""

import ctypes
import logging

import pico2d
from pico2d import SDL_KEYDOWN, SDL_KEYUP, Event

_log = logging.getLogger(__name__)
_warned_capture = False


# ---------------------------------------------------------------- 키
class InputState:
    """눌려 있는 키 목록. play_mode가 이벤트를 넘기고, 프레임 끝에 end_frame()을 부른다."""

    def __init__(self) -> None:
        self._held: set[int] = set()
        self._pressed: set[int] = set()  # 이번 프레임에 새로 눌린 키

    def handle_event(self, event: Event) -> bool:
        """키 이벤트면 반영하고 True. 다른 이벤트는 건드리지 않고 False."""
        if event.type == SDL_KEYDOWN:
            self._held.add(event.key)
            self._pressed.add(event.key)
            return True
        if event.type == SDL_KEYUP:
            self._held.discard(event.key)
            return True
        return False

    def is_held(self, *keys: int) -> bool:
        """keys 가운데 하나라도 눌려 있는지."""
        return any(key in self._held for key in keys)

    def was_pressed(self, key: int) -> bool:
        """이번 프레임에 새로 눌렸는지 (누르고 있는 동안 한 번만 True)."""
        return key in self._pressed

    def end_frame(self) -> None:
        self._pressed.clear()

    def release_all(self) -> None:
        """모든 키를 뗀 것으로 친다 (일시정지·골인처럼 키를 뗀 이벤트를 못 받는 경우)."""
        self._held.clear()
        self._pressed.clear()


# ---------------------------------------------------------------- 마우스
def set_mouse_captured(captured: bool) -> None:
    """마우스를 창에 가두고 커서를 숨긴다(상대 모드). False면 풀어 준다.

    켜고 끌 때마다 그동안 쌓인 움직임을 한 번 읽어 버린다 (다시 잡은 순간 시점이 튀지 않게).
    """
    global _warned_capture
    flag = pico2d.SDL_TRUE if captured else pico2d.SDL_FALSE
    if pico2d.SDL_SetRelativeMouseMode(flag) != 0 and not _warned_capture:
        _warned_capture = True
        reason = pico2d.SDL_GetError().decode("utf-8", errors="replace")
        _log.warning("마우스 상대 모드를 켜지 못했습니다: %s", reason)
    poll_mouse()


def poll_mouse() -> tuple[int, int]:
    """지난번에 읽은 뒤로 마우스가 움직인 양 (dx, dy) px. SDL의 dy는 아래가 +다."""
    dx, dy = ctypes.c_int(0), ctypes.c_int(0)
    pico2d.SDL_GetRelativeMouseState(ctypes.byref(dx), ctypes.byref(dy))
    return dx.value, dy.value
