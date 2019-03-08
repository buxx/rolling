# coding: utf-8
import typing

import urwid
from urwid import BOX

from rolling.exception import MoveToOtherZoneError
from rolling.gui.connector import ZoneMapConnector
from rolling.gui.map.object import Character
from rolling.gui.map.object import DisplayObject
from rolling.gui.map.object import DisplayObjectManager
from rolling.gui.map.render import MapRenderEngine
from rolling.gui.play.zone import ChangeZoneDialog
from rolling.map.source import ZoneMapSource

if typing.TYPE_CHECKING:
    from rolling.gui.controller import Controller


class MapWidget(urwid.Widget):
    _sizing = frozenset([BOX])

    def __init__(
        self, controller: "Controller", render_engine: MapRenderEngine
    ) -> None:
        self._controller = controller
        self._render_engine = render_engine
        self._horizontal_offset = 0
        self._vertical_offset = 0
        self._current_row_size = 0
        self._current_col_size = 0
        self._first_display = True

    @property
    def render_engine(self) -> MapRenderEngine:
        return self._render_engine

    def render(self, size, focus=False):
        self._current_col_size, self._current_row_size = size
        return self._render(size, focus)

    def _render(self, size, focus=False):
        self._render_engine.render(
            self._current_col_size,
            self._current_row_size,
            offset_horizontal=self._horizontal_offset,
            offset_vertical=self._vertical_offset,
        )

        self._controller.loop.set_alarm_in(0.25, lambda *_, **__: self._invalidate())
        return urwid.TextCanvas(
            text=self._render_engine.rows,
            attr=self._render_engine.attributes,
            maxcol=self._current_col_size,
        )

    def selectable(self):
        return True

    def keypress(self, size, key):
        new_offset = None

        if key == "up":
            new_offset = (1, 0)
        if key == "down":
            new_offset = (-1, 0)
        if key == "left":
            new_offset = (0, 1)
        if key == "right":
            new_offset = (0, -1)

        if new_offset is not None:
            self._offset_change(new_offset)

        self._invalidate()

    def _offset_change(self, new_offset: typing.Tuple[int, int]) -> None:
        pass


class WorldMapWidget(MapWidget):
    pass


# TODO BS 2019-01-22: Rename into ZoneMapWidget
class TileMapWidget(MapWidget):
    def __init__(
        self,
        controller: "Controller",
        render_engine: MapRenderEngine,
        zone_map_source: ZoneMapSource,
    ) -> None:
        super().__init__(controller, render_engine)
        self._connector = ZoneMapConnector(
            self, self._controller, zone_map_source=zone_map_source
        )

    def _offset_change(self, new_offset: typing.Tuple[int, int]) -> None:
        try:
            if not self._connector.move_is_possible(new_offset):
                return
        except MoveToOtherZoneError as exc:
            # FIXME BS 2019-03-06: Manage (try) change zone case
            self._change_zone_dialog(exc.row_i, exc.col_i)
            return

        # move player
        self._connector.player_move(new_offset)

        # compute center of the map
        map_center_col = self._render_engine._world_map_source.geography.width // 2
        map_center_row = self._render_engine._world_map_source.geography.height // 2

        # compute void around the map
        left_void = (
            self._current_col_size
            - self._render_engine._world_map_source.geography.width
        ) // 2
        top_void = (
            self._current_row_size
            - self._render_engine._world_map_source.geography.height
        ) // 2
        left_void = left_void if left_void > 0 else 0
        top_void = top_void if top_void > 0 else 0

        # compute center of the map including voids
        display_center_col = (self._current_col_size // 2) - (
            map_center_col + left_void
        )
        display_center_row = (self._current_row_size // 2) - (map_center_row + top_void)

        # apply player position offsets
        player_center_col = display_center_col + (
            map_center_col
            - self._controller.display_objects_manager.current_player.col_i
        )
        player_center_row = display_center_row + (
            map_center_row
            - self._controller.display_objects_manager.current_player.row_i
        )

        # Set center of display on it
        self._horizontal_offset = player_center_col
        self._vertical_offset = player_center_row

    def _render(self, size, focus=False):
        if self._first_display:
            self._first_display = False
            self._offset_change((0, 0))  # to compute offset with player position

        return super()._render(size, focus)

    def _change_zone_dialog(self, row_i: int, col_i: int) -> None:
        zone_map_widget = self._controller._view.main_content_container.original_widget
        world_row_i, world_col_i = self._connector.get_zone_coordinates(row_i, col_i)

        self._controller._view.main_content_container.original_widget = ChangeZoneDialog(
            kernel=self._controller.kernel,
            controller=self._controller,
            original_widget=zone_map_widget,
            title="Move to an other zone",
            text="You are trying to move on other zone, continue ?",
            world_row_i=world_row_i,
            world_col_i=world_col_i,
        )
