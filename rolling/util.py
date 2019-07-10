# coding: utf-8
import dataclasses
import typing

from rolling.map.source import ZoneMapSource
from rolling.map.type.zone import ZoneMapTileType
from rolling.model.resource import ResourceType
from rolling.model.stuff import StuffModel
from rolling.server.lib.stuff import StuffLib

if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel


@dataclasses.dataclass
class EmptyModel:
    pass


def get_on_and_around_coordinates(
    x: int, y: int
) -> typing.List[typing.Tuple[int, int]]:
    return [
        (x, y),
        (x - 1, y - 1),
        (x, y - 1),
        (x + 1, y - 1),
        (x - 1, y),
        (x + 1, y),
        (x - 1, y + 1),
        (x, y + 1),
        (x + 1, y + 1),
    ]


def is_there_resource_type_in_zone(
    resource_type: ResourceType, zone_source: ZoneMapSource
) -> bool:
    for row in zone_source.geography.rows:
        for zone_tile_type in row:
            zone_tile_type = typing.cast(ZoneMapTileType, zone_tile_type)
            for resource_type in zone_tile_type.extractable():
                if resource_type == ResourceType.FRESH_WATER:
                    return True
    return False


def get_stuffs_filled_with_resource_type(
    kernel: "Kernel", character_id: str, resource_type: ResourceType
) -> typing.Iterator[StuffModel]:
    stuff_lib = StuffLib(kernel=kernel)
    character_stuffs = stuff_lib.get_carried_by(character_id)
    for stuff in character_stuffs:
        # FIXME BS 2019-07-10: case where not 100% ?
        if stuff.filled_with_resource == resource_type:
            yield stuff
