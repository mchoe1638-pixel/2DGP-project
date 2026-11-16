"""레이어별 게임 오브젝트 목록과 충돌 쌍 관리.

오브젝트는 update(), draw(), get_bb(), handle_collision(group, other)를 가진다.
get_bb()는 (left, bottom, right, top) 또는 None(충돌 없음)을 돌려준다.
"""

from game_object import GameObject

LAYER_BACKGROUND = 0
LAYER_PROP = 1
LAYER_ITEM = 2
LAYER_OBSTACLE = 3
LAYER_PLAYER = 4
LAYER_FX = 5
LAYER_COUNT = 6

world: list[list[GameObject]] = [[] for _ in range(LAYER_COUNT)]
# 그룹 이름 -> [왼쪽 오브젝트 목록, 오른쪽 오브젝트 목록]
collision_pairs: dict[str, list[list[GameObject]]] = {}


def add_object(obj: GameObject, layer: int) -> None:
    world[layer].append(obj)


def remove_object(obj: GameObject) -> None:
    """월드와 모든 충돌 쌍에서 오브젝트를 뺀다. 이미 없으면 아무 일도 하지 않는다.

    한 프레임에 여러 콜백이 같은 오브젝트를 지우려 할 수 있어서 중복 제거를 허용한다.
    """
    for layer in world:
        if obj in layer:
            layer.remove(obj)
    for sides in collision_pairs.values():
        for side in sides:
            if obj in side:
                side.remove(obj)


def clear() -> None:
    for layer in world:
        layer.clear()
    collision_pairs.clear()


def all_objects() -> list[GameObject]:
    """모든 레이어의 오브젝트를 아래 레이어부터 담은 스냅샷."""
    return [obj for layer in world for obj in layer]


def update() -> None:
    for layer in world:
        for obj in list(layer):
            obj.update()


def render() -> None:
    for layer in world:
        for obj in list(layer):
            obj.draw()


def add_collision_pair(
    group: str, left: GameObject | None, right: GameObject | None
) -> None:
    """그룹의 왼쪽/오른쪽 목록에 오브젝트를 등록한다. 쓰지 않는 쪽은 None으로 둔다."""
    sides = collision_pairs.setdefault(group, [[], []])
    if left is not None:
        sides[0].append(left)
    if right is not None:
        sides[1].append(right)


def collide(a: GameObject, b: GameObject) -> bool:
    """두 오브젝트의 AABB가 겹치는지. 변만 맞닿은 경우는 겹침이 아니다."""
    box_a = a.get_bb()
    box_b = b.get_bb()
    if box_a is None or box_b is None:
        return False
    left_a, bottom_a, right_a, top_a = box_a
    left_b, bottom_b, right_b, top_b = box_b
    apart_horizontally = right_a <= left_b or right_b <= left_a
    apart_vertically = top_a <= bottom_b or top_b <= bottom_a
    return not (apart_horizontally or apart_vertically)


def handle_collisions() -> None:
    """등록된 모든 쌍을 검사해 겹친 두 오브젝트에 서로를 알린다.

    콜백이 오브젝트를 지울 수 있으므로 스냅샷을 돌면서도 아직 등록되어 있는지 매번 확인한다.
    """
    for group, (lefts, rights) in list(collision_pairs.items()):
        for a in list(lefts):
            for b in list(rights):
                if a not in lefts:
                    break  # a가 이번 검사 중 지워졌다
                if b in rights and collide(a, b):
                    a.handle_collision(group, b)
                    b.handle_collision(group, a)
