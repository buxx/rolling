# coding: utf-8
import typing

if typing.TYPE_CHECKING:
    from rolling.gui.controller import Controller
    from rolling.gui.map.widget import TileMapWidget


class ZoneMapConnector(object):
    def __init__(self, widget: "TileMapWidget", controller: "Controller") -> None:
        self._widget = widget
        self._controller = controller

    def player_move(self, new_offset: typing.Tuple[int, int]) -> None:
        current_player = (
            self._widget.render_engine.display_objects_manager.current_player
        )
        current_player.move_with_offset(new_offset)
        self._widget.render_engine.display_objects_manager.refresh_indexes()
        # TODO: Add event to send list
        pass
