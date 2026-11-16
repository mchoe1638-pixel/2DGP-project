"""모든 게임 오브젝트의 공통 인터페이스 기본 구현.

game_world는 update / draw / get_bb / handle_collision 네 가지만 안다.
필요한 메서드만 덮어쓰면 되고, 나머지는 아무 일도 하지 않는다.
"""


class GameObject:
    def update(self) -> None:
        """매 프레임 상태를 갱신한다 (시간 값은 game_framework.frame_time)."""

    def draw(self) -> None:
        """화면에 그린다. 화면 x = 월드 x - camera.x."""

    def get_bb(self) -> tuple[float, float, float, float] | None:
        """(left, bottom, right, top) 충돌 상자. 충돌하지 않으면 None."""
        return None

    def handle_collision(self, group: str, other: "GameObject") -> None:
        """game_world.add_collision_pair로 등록한 그룹에서 충돌했을 때 호출된다."""
