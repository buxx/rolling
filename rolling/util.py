# coding: utf-8
import dataclasses
import typing
import enum

from rolling.map.source import ZoneMapSource
from rolling.map.type.zone import ZoneMapTileType
from rolling.model.stuff import StuffModel

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


def is_there_resource_id_in_zone(
    kernel: "Kernel", resource_id: str, zone_source: ZoneMapSource
) -> bool:
    for row in zone_source.geography.rows:
        for zone_tile_type in row:
            zone_tile_type = typing.cast(typing.Type[ZoneMapTileType], zone_tile_type)
            for tile_resource_id in list(
                kernel.game.config.extractions[zone_tile_type].resources.keys()
            ):
                if tile_resource_id == resource_id:
                    return True
    return False


def get_stuffs_filled_with_resource_id(
    kernel: "Kernel", character_id: str, resource_id: str
) -> typing.Iterator[StuffModel]:
    from rolling.server.lib.stuff import StuffLib

    stuff_lib = StuffLib(kernel=kernel)
    character_stuffs = stuff_lib.get_carried_by(character_id)
    for stuff in character_stuffs:
        # FIXME BS 2019-07-10: case where not 100% ?
        if stuff.filled_with_resource == resource_id:
            yield stuff


class CornerEnum(enum.Enum):
    TOP = "TOP"
    TOP_RIGHT = "TOP_RIGHT"
    RIGHT = "RIGHT"
    BOTTOM_RIGHT = "BOTTOM_RIGHT"
    BOTTOM = "TOP"
    BOTTOM_LEFT = "BOTTOM_LEFT"
    LEFT = "LEFT"
    TOP_LEFT = "TOP_LEFT"


def get_corner(
    width: int, height: int, new_row_i: int, new_col_i: int,
) -> typing.Optional[CornerEnum]:
    left_col_i_end = width // 3
    right_col_i_start = (width // 3) * 2
    right_col_i = right_col_i_start + new_row_i
    left_col_i = left_col_i_end - new_row_i

    if new_row_i < 0:
        return CornerEnum.TOP

    if new_col_i < 0:
        return CornerEnum.LEFT

    if new_col_i > width:
        return CornerEnum.RIGHT

    if new_row_i > height:
        return CornerEnum.BOTTOM

    if new_col_i < left_col_i and new_row_i < height // 2:
        return CornerEnum.TOP_LEFT

    if new_col_i < left_col_i and new_row_i > height // 2:
        return CornerEnum.BOTTOM_LEFT

    if new_col_i >= right_col_i and new_row_i < height // 2:
        return CornerEnum.TOP_RIGHT

    if new_col_i >= right_col_i and new_row_i > height // 2:
        return CornerEnum.BOTTOM_RIGHT
