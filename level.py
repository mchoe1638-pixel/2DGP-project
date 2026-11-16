"""배치표(stage_data)를 실제 객체(장애물·아이템·장식·골인 문)로 만든다.

만들기만 하고 월드에 올리지는 않는다. 월드에 올리고 충돌을 등록하는 일은 플레이 화면이 맡는다.
"""

import resource
import stage_data
from camera import Camera
from crowd import Crowd
from fx import SpriteLookup
from game_object import GameObject
from item import Breath, Gum, Item, Shortcut
from obstacle import Boss, Flyer, Npc, Tourist
from player import Player
from prop import Prop, WcDoor
from stage_data import ItemSpec, ObstacleSpec, Stage

NPC_BY_KIND: dict[str, type[Npc]] = {
    stage_data.TOURIST: Tourist,
    stage_data.FLYER: Flyer,
    stage_data.BOSS: Boss,
}

ITEM_BY_KIND: dict[str, type[Item]] = {
    stage_data.BREATH: Breath,
    stage_data.GUM: Gum,
    stage_data.SHORTCUT: Shortcut,
}


def create_obstacle(
    spec: ObstacleSpec,
    camera: Camera,
    player: Player,
    sprite_lookup: SpriteLookup = resource.get_sprite,
) -> GameObject:
    """배치표 한 줄에 맞는 장애물을 만든다. 모르는 종류면 ValueError."""
    if spec.kind == stage_data.CROWD:
        return Crowd(spec.x, spec.count, camera, player, sprite_lookup)
    npc_class = NPC_BY_KIND.get(spec.kind)
    if npc_class is None:
        raise ValueError(f"알 수 없는 장애물 종류입니다: {spec.kind}")
    return npc_class(spec.x, camera, player, sprite_lookup)


def create_obstacles(
    stage: Stage,
    camera: Camera,
    player: Player,
    sprite_lookup: SpriteLookup = resource.get_sprite,
) -> list[GameObject]:
    """스테이지 배치표 전체를 표의 순서대로 만든다."""
    return [
        create_obstacle(spec, camera, player, sprite_lookup) for spec in stage.obstacles
    ]


def create_item(
    spec: ItemSpec,
    camera: Camera,
    player: Player,
    sprite_lookup: SpriteLookup = resource.get_sprite,
) -> Item:
    """배치표 한 줄에 맞는 아이템을 만든다. 모르는 종류면 ValueError."""
    item_class = ITEM_BY_KIND.get(spec.kind)
    if item_class is None:
        raise ValueError(f"알 수 없는 아이템 종류입니다: {spec.kind}")
    return item_class(spec.x, spec.height, camera, player, sprite_lookup)


def create_items(
    stage: Stage,
    camera: Camera,
    player: Player,
    sprite_lookup: SpriteLookup = resource.get_sprite,
) -> list[Item]:
    """스테이지 배치표의 아이템 전체를 표의 순서대로 만든다."""
    return [create_item(spec, camera, player, sprite_lookup) for spec in stage.items]


def create_props(
    stage: Stage,
    camera: Camera,
    sprite_lookup: SpriteLookup = resource.get_sprite,
) -> list[Prop]:
    """스테이지 배치표의 장식 전체를 표의 순서대로 만든다 (골인 문은 따로 만든다)."""
    return [
        Prop(spec.sheet, spec.x, spec.height, camera, sprite_lookup)
        for spec in stage.props
    ]


def create_goal_door(
    stage: Stage,
    camera: Camera,
    sprite_lookup: SpriteLookup = resource.get_sprite,
) -> WcDoor:
    """골인 지점(goal_x)에 서는 WC 문을 만든다."""
    return WcDoor(stage.goal_x, camera, sprite_lookup)
