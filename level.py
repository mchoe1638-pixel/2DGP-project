"""배치표(stage_data.ObstacleSpec)를 실제 장애물 객체로 만든다.

만들기만 하고 월드에 올리지는 않는다. 월드에 올리고 충돌을 등록하는 일은 플레이 화면이 맡는다.
"""

import resource
import stage_data
from camera import Camera
from crowd import Crowd
from fx import SpriteLookup
from game_object import GameObject
from obstacle import Boss, Flyer, Npc, Tourist
from player import Player
from stage_data import ObstacleSpec, Stage

NPC_BY_KIND: dict[str, type[Npc]] = {
    stage_data.TOURIST: Tourist,
    stage_data.FLYER: Flyer,
    stage_data.BOSS: Boss,
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
