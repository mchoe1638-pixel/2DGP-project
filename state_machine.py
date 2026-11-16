"""범용 상태 머신 (강의 방식).

상태는 enter / exit / do / draw 를 가진 클래스이고, 전이표는
{상태: {이벤트 판정 함수: 다음 상태}} 모양이다. 이벤트는 (이름, 값) 튜플이다.
주인 객체가 무엇인지(플레이어든 NPC든)는 전혀 모른다.
"""

from collections.abc import Callable
from typing import Any

Event = tuple[str, Any]
Predicate = Callable[[Event], bool]


class State:
    """상태의 기본형. 필요한 메서드만 덮어쓰고, 나머지는 아무 일도 하지 않는다."""

    @staticmethod
    def enter(owner: Any, event: Event) -> None:
        """이 상태로 들어올 때 한 번 호출된다 (event는 전이를 일으킨 이벤트)."""

    @staticmethod
    def exit(owner: Any, event: Event) -> None:
        """이 상태에서 나갈 때 한 번 호출된다."""

    @staticmethod
    def do(owner: Any, dt: float) -> None:
        """매 프레임 dt초만큼 진행한다."""

    @staticmethod
    def draw(owner: Any) -> None:
        """주인 객체를 이 상태의 모습으로 그린다."""


Transitions = dict[type[State], dict[Predicate, type[State]]]


class StateMachine:
    START_EVENT: Event = ("START", None)

    def __init__(self, owner: Any) -> None:
        self.owner = owner
        self.state: type[State] = State  # start() 전에는 아무 일도 하지 않는 기본 상태
        self.transitions: Transitions = {}
        self._events: list[Event] = []

    def set_transitions(self, transitions: Transitions) -> None:
        self.transitions = transitions

    def start(self, state: type[State]) -> None:
        self.state = state
        state.enter(self.owner, self.START_EVENT)

    def add_event(self, event: Event) -> None:
        """다음 update()에서 처리할 이벤트를 줄 세운다."""
        self._events.append(event)

    def handle_state_event(self, event: Event) -> bool:
        """전이표에서 처음으로 맞는 전이를 골라 상태를 바꾼다. 바뀌었으면 True."""
        for matches, next_state in self.transitions.get(self.state, {}).items():
            if matches(event):
                self.state.exit(self.owner, event)
                self.state = next_state
                next_state.enter(self.owner, event)
                return True
        return False

    def update(self, dt: float) -> None:
        """상태를 dt초 진행한 뒤, 줄 선 이벤트를 처리한다.

        처리 중에 새로 줄 선 이벤트는 다음 update()로 넘어간다 (전이가 끝없이 이어지지 않게).
        """
        self.state.do(self.owner, dt)
        queued, self._events = self._events, []
        for event in queued:
            self.handle_state_event(event)

    def draw(self) -> None:
        self.state.draw(self.owner)
