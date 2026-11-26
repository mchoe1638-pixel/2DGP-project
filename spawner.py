"""스테이지 데이터의 장애물·행인·승강장 기둥과 벤치 목록을 월드에 세울 오브젝트로 만든다.

오브젝트를 월드에 넣고 충돌 쌍에 등록하는 일은 부르는 쪽(play_mode)이 한다.
"""

from collections.abc import Sequence

import crowd
import obstacle
import pedestrian
import prop
import resource
import stage_data
from game_object import GameObject
from player import Player
from resource import SpriteLookup
from stage import ObstacleSpec, Stage

# 홀로 서는 장애물: 종류 이름 → 클래스
_SINGLES: dict[str, type[obstacle.Npc]] = {
    stage_data.TOURIST: obstacle.Tourist,
    stage_data.FLYER: obstacle.Flyer,
    stage_data.BOSS: obstacle.Boss,
}


def spawn_obstacles(
    stage: Stage,
    player: Player,
    sprite_lookup: SpriteLookup = resource.get_sprite,
) -> list[GameObject]:
    """스테이지의 장애물 전부. 시계처럼 보이지 않는 오브젝트도 함께 들어 있다."""
    objects: list[GameObject] = []
    for spec in stage.obstacles:
        objects.extend(spawn_obstacle(spec, stage, player, sprite_lookup))
    return objects


def spawn_obstacle(
    spec: ObstacleSpec,
    stage: Stage,
    player: Player,
    sprite_lookup: SpriteLookup = resource.get_sprite,
) -> list[GameObject]:
    """장애물 한 줄(spec)을 오브젝트로 만든다. 인파는 시계와 여러 사람이라 목록으로 돌려준다."""
    if spec.kind == stage_data.CROWD:
        # 인파는 그 x의 통로 폭 전체를 막는다 (y를 따로 정하지 않는다)
        segment = stage.segment_at(spec.x)
        return crowd.make_crowd(
            spec.x, segment.y0, segment.y1, spec.count, player, sprite_lookup
        )
    npc_class = _SINGLES.get(spec.kind)
    if npc_class is None:
        raise ValueError(f"알 수 없는 장애물: {spec.kind}")
    if spec.y is None:
        raise ValueError(f"{spec.kind}에는 y 위치가 있어야 합니다: x = {spec.x}")
    return [npc_class(spec.x, spec.y, stage.grid, player, sprite_lookup)]


def spawn_props(
    stage: Stage,
    player: Player,
    sprite_lookup: SpriteLookup = resource.get_sprite,
) -> list[prop.SolidProp]:
    """스테이지의 승강장 기둥·벤치 전부. 플레이어를 막으므로 부르는 쪽이 충돌 쌍에 넣어야 한다."""
    return [
        prop.SolidProp(spec.name, sprite_lookup(spec.name), spec.x, spec.y, player)
        for spec in stage.props
    ]


def spawn_pedestrians(
    stage: Stage, player: Player, blockers: Sequence[prop.SolidProp] = ()
) -> list[GameObject]:
    """스테이지의 행인 전부. 장애물이 아니라서 충돌 쌍에는 넣지 않는다.

    blockers(기둥·벤치)는 행인도 몸으로 비껴 가므로 걷는 사람마다 알려 준다.
    """
    return [
        pedestrian.Pedestrian(
            spec.name, spec.x, spec.y, stage.grid, player, index, blockers
        )
        for index, spec in enumerate(stage.pedestrians)
    ]
