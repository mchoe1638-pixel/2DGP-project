"""모드 스택 기반 메인 루프.

모드 모듈은 init / finish / pause / resume / handle_events / update / draw 를 가진다.
"""

import time
from typing import Protocol

import config


class Mode(Protocol):
    """모드가 갖춰야 하는 함수들. title_mode처럼 모듈이어도, 객체여도 된다."""

    def init(self) -> None: ...

    def finish(self) -> None: ...

    def pause(self) -> None: ...

    def resume(self) -> None: ...

    def handle_events(self) -> None: ...

    def update(self) -> None: ...

    def draw(self) -> None: ...


stack: list[Mode] = []
running = False
frame_time = 0.0
clock = time.perf_counter  # 테스트에서 가짜 시계로 바꿀 수 있다


def change_mode(mode: Mode) -> None:
    """현재 모드를 끝내고 새 모드로 갈아탄다."""
    if stack:
        stack.pop().finish()
    stack.append(mode)
    mode.init()


def push_mode(mode: Mode) -> None:
    """현재 모드를 잠시 멈추고 그 위에 새 모드를 쌓는다."""
    if stack:
        stack[-1].pause()
    stack.append(mode)
    mode.init()


def pop_mode() -> None:
    """맨 위 모드를 끝내고 아래 모드를 다시 시작한다."""
    if stack:
        stack.pop().finish()
    if stack:
        stack[-1].resume()


def quit() -> None:
    """현재 프레임을 마친 뒤 루프를 종료한다."""
    global running
    running = False


def run(start_mode: Mode) -> None:
    global running, frame_time
    stack.clear()
    running = True
    change_mode(start_mode)
    previous = clock()
    while running and stack:
        now = clock()
        frame_time = min(now - previous, config.MAX_FRAME_TIME)
        previous = now
        # 이벤트 처리 중 모드가 바뀔 수 있으므로 매번 맨 위 모드를 다시 읽는다.
        stack[-1].handle_events()
        stack[-1].update()
        stack[-1].draw()
    while stack:
        stack.pop().finish()
