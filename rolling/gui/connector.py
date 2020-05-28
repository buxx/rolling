# coding: utf-8
import typing

from rolling.exception import CantMoveBecauseSurcharge
from rolling.exception import MoveToOtherZoneError
from rolling.exception import SameZoneError
from rolling.map.source import ZoneMapSource
from rolling.model.event import PlayerMoveData
from rolling.model.event import ZoneEvent
from rolling.model.event import ZoneEventType
from rolling.physics import Physics
from rolling.util import CornerEnum
from rolling.util import get_corner

if typing.TYPE_CHECKING:
    from rolling.gui.controller import Controller
    from rolling.gui.map.widget import TileMapWidget


class ZoneMapConnector:
    def __init__(
        self, widget: "TileMapWidget", controller: "Controller", zone_map_source: ZoneMapSource
    ) -> None:
        self._widget = widget
        self._controller = controller
        self._physics = Physics(controller, zone_map_source=zone_map_source)
        self._zone_map_source = zone_map_source

    def move_is_possible(self, new_offset: typing.Tuple[int, int]) -> bool:
        if (
            # FIXME delete gui code
            True or
            self._controller.player_character.weight_overcharge
            or self._controller.player_character.clutter_overcharge
        ):
            raise CantMoveBecauseSurcharge()

        current_player = self._widget.render_engine.display_objects_manager.current_player
        new_row_i = current_player.row_i - new_offset[0]
        new_col_i = current_player.col_i - new_offset[1]

        corner = get_corner(
            self._zone_map_source.geography.width,
            self._zone_map_source.geography.height,
            new_row_i=new_row_i,
            new_col_i=new_col_i,
        )

        if corner:
            raise MoveToOtherZoneError(corner)

        return self._physics.player_can_move_at(current_player, (new_row_i, new_col_i))

    def player_move(self, new_offset: typing.Tuple[int, int]) -> None:
        # Apply move on player
        current_player = self._widget.render_engine.display_objects_manager.current_player
        # FIXME BS 2019-03-08: We update data of player in display_objects_manager, warning ! There
        # is another instance of it in controller ! (player_character). This must only one.
        current_player.move_with_offset(new_offset)
        self._widget.render_engine.display_objects_manager.refresh_indexes()

        # Add move to event send queue
        self._controller.to_send_zone_queue.put(
            ZoneEvent(
                type=ZoneEventType.PLAYER_MOVE,
                data=PlayerMoveData(
                    to_row_i=current_player.row_i,
                    to_col_i=current_player.col_i,
                    character_id=self._controller.player_character.id,
                ),
            )
        )

    def get_zone_coordinates(self, corner: CornerEnum) -> typing.Tuple[int, int]:
        player = self._controller.player_character

        if corner == corner.TOP_LEFT:
            return player.world_row_i - 1, player.world_col_i - 1

        if corner == corner.TOP:
            return player.world_row_i - 1, player.world_col_i

        if corner == corner.TOP_RIGHT:
            return player.world_row_i - 1, player.world_col_i + 1

        if corner == corner.RIGHT:
            return player.world_row_i, player.world_col_i + 1

        if corner == corner.BOTTOM_RIGHT:
            return player.world_row_i + 1, player.world_col_i - 1

        if corner == corner.BOTTOM:
            return player.world_row_i + 1, player.world_col_i

        if corner == corner.BOTTOM_LEFT:
            return player.world_row_i + 1, player.world_col_i - 1

        if corner == corner.LEFT:
            return player.world_row_i, player.world_col_i - 1

        raise NotImplementedError("should not be here :s")
