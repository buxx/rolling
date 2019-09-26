# coding: utf-8
import dataclasses
import enum
import typing

from rolling.map.source import ZoneMapSource
from rolling.map.type.zone import ZoneMapTileType
from rolling.model.stuff import StuffModel
from rolling.server.link import CharacterActionLink
from rolling.types import ActionType

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

            try:
                for tile_resource_id in list(
                    # FIXME BS 2019-09-14: Only for zero cost !
                    kernel.game.config.extractions[zone_tile_type].resources.keys()
                ):
                    if tile_resource_id == resource_id:
                        return True
            except KeyError:
                pass

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


def get_stuffs_eatable(
    kernel: "Kernel", character_id: str
) -> typing.Iterator[StuffModel]:
    for stuff in kernel.stuff_lib.get_carried_by(character_id):
        stuff_properties = kernel.game.stuff_manager.get_stuff_properties_by_id(
            stuff.stuff_id
        )
        for description in stuff_properties.descriptions:
            if description.action_type == ActionType.EAT_STUFF:
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
    width: int, height: int, new_row_i: int, new_col_i: int
) -> typing.Optional[CornerEnum]:
    left_col_i_end = width // 3
    right_col_i_start = (width // 3) * 2
    top_row_i_end = height // 3
    bottom_row_i_start = (height // 3) * 2

    more = new_row_i if new_row_i >= 0 else 0

    if new_row_i < top_row_i_end:
        right_col_i = right_col_i_start + more
        left_col_i = left_col_i_end - more
    elif new_row_i >= bottom_row_i_start:
        more = (height // 3) - (new_row_i - bottom_row_i_start + 1)
        more = more if more >= 0 else 0
        right_col_i = right_col_i_start + more
        left_col_i = left_col_i_end - more
    else:
        left_col_i = left_col_i_end
        right_col_i = right_col_i_start

    if new_col_i < left_col_i and new_row_i < top_row_i_end:
        return CornerEnum.TOP_LEFT

    if new_row_i < 0 and left_col_i <= new_col_i < right_col_i:
        return CornerEnum.TOP

    if new_col_i >= right_col_i and new_row_i < top_row_i_end:
        return CornerEnum.TOP_RIGHT

    if new_col_i > (width - 1) and top_row_i_end <= new_row_i < bottom_row_i_start:
        return CornerEnum.RIGHT

    if new_col_i >= right_col_i and new_row_i >= bottom_row_i_start:
        return CornerEnum.BOTTOM_RIGHT

    if new_row_i > (height - 1) and left_col_i_end <= new_col_i < right_col_i_start:
        return CornerEnum.BOTTOM

    if new_col_i < left_col_i and new_row_i >= bottom_row_i_start:
        return CornerEnum.BOTTOM_LEFT

    if new_col_i < 0 and top_row_i_end <= new_row_i < bottom_row_i_start:
        return CornerEnum.LEFT


def filter_action_links(
    links: typing.List[CharacterActionLink]
) -> typing.List[CharacterActionLink]:
    new_links: typing.List[CharacterActionLink] = []
    found_merge_type: typing.List[typing.Any] = []

    for link in links:
        if link.merge_by is None:
            new_links.append(link)
        else:
            if link.merge_by not in found_merge_type:
                new_links.append(link)
                found_merge_type.append(link.merge_by)

    return new_links
