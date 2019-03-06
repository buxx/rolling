# coding: utf-8
import typing

from rolling.exception import MoveToOtherZoneError
from rolling.map.source import ZoneMapSource
from rolling.model.event import PlayerMoveData
from rolling.model.event import ZoneEvent
from rolling.model.event import ZoneEventType
from rolling.physics import Physics

if typing.TYPE_CHECKING:
    from rolling.gui.controller import Controller
    from rolling.gui.map.widget import TileMapWidget


class ZoneMapConnector(object):
    def __init__(
        self,
        widget: "TileMapWidget",
        controller: "Controller",
        zone_map_source: ZoneMapSource,
    ) -> None:
        self._widget = widget
        self._controller = controller
        self._physics = Physics(controller, zone_map_source=zone_map_source)
        self._zone_map_source = zone_map_source

    def move_is_possible(self, new_offset: typing.Tuple[int, int]) -> bool:
        current_player = (
            self._widget.render_engine.display_objects_manager.current_player
        )
        new_row_i = current_player.row_i - new_offset[0]
        new_col_i = current_player.col_i - new_offset[1]

        # FIXME BS 2019-03-06: Move must be changed into change zone on corner to
        if (
            new_col_i < 0
            or new_col_i > self._zone_map_source.geography.width
            or new_row_i < 0
            or new_row_i > self._zone_map_source.geography.height
        ):
            raise MoveToOtherZoneError()

        return self._physics.player_can_move_at(current_player, (new_row_i, new_col_i))

    def player_move(self, new_offset: typing.Tuple[int, int]) -> None:
        # Apply move on player
        current_player = (
            self._widget.render_engine.display_objects_manager.current_player
        )
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
