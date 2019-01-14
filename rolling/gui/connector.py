# coding: utf-8
import typing

from rolling.model.event import PlayerMoveData
from rolling.model.event import ZoneEvent
from rolling.model.event import ZoneEventType

if typing.TYPE_CHECKING:
    from rolling.gui.controller import Controller
    from rolling.gui.map.widget import TileMapWidget


class ZoneMapConnector(object):
    def __init__(self, widget: "TileMapWidget", controller: "Controller") -> None:
        self._widget = widget
        self._controller = controller

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
