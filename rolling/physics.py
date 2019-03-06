# coding: utf-8
import typing

from rolling.map.source import ZoneMapSource
from rolling.model.character import CharacterModel
from rolling.model.meta import TransportType

if typing.TYPE_CHECKING:
    from rolling.gui.controller import Controller


class Physics(object):
    def __init__(
        self, controller: "Controller", zone_map_source: ZoneMapSource
    ) -> None:
        self._kernel = controller.kernel
        self._controller = controller
        self._zone_map_source = zone_map_source

    def player_can_move_at(
        self, player: CharacterModel, position: typing.Tuple[int, int]
    ) -> bool:
        row_i = position[0]
        col_i = position[1]
        tile_type = self._zone_map_source.geography.rows[col_i][row_i]
        tile_model = self._controller.zone_lib.get_zone_tile_type_model(tile_type)

        # TODO BS 2019-03-06: Currently WALKING is hardcoded
        # FIXME BS 2019-03-06: using str for now, see rolling.model.zone.ZoneTileTypeModel todo
        try:
            if not tile_model.traversable[TransportType.WALKING.value]:
                return False
        except KeyError:
            # KeyError means no information about traversable or not, so not traversable
            return False

        # TODO BS 2019-03-06: Parse existing objects on position (wall, etc)
        return True
