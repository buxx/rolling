# coding: utf-8
import typing

import urwid
from urwid import BOX

from rolling.gui.connector import ZoneMapConnector
from rolling.gui.map.object import Character
from rolling.gui.map.object import DisplayObject
from rolling.gui.map.object import DisplayObjectManager
from rolling.gui.map.render import MapRenderEngine

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

    @property
    def render_engine(self) -> MapRenderEngine:
        return self._render_engine

    def render(self, size, focus=False):
        x, y = size

        self._render_engine.render(
            x,
            y,
            offset_horizontal=self._horizontal_offset,
            offset_vertical=self._vertical_offset,
        )

        self._controller.loop.set_alarm_in(0.25, lambda *_, **__: self._invalidate())
        return urwid.TextCanvas(
            text=self._render_engine.rows, attr=self._render_engine.attributes, maxcol=x
        )

    def selectable(self):
        return True

    def keypress(self, size, key):
        new_offset = None

        if key == "up":
            self._vertical_offset += 1
            new_offset = (1, 0)
        if key == "down":
            self._vertical_offset -= 1
            new_offset = (-1, 0)
        if key == "left":
            self._horizontal_offset += 1
            new_offset = (0, 1)
        if key == "right":
            self._horizontal_offset -= 1
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
        self, controller: "Controller", render_engine: MapRenderEngine
    ) -> None:
        super().__init__(controller, render_engine)
        self._connector = ZoneMapConnector(self, self._controller)

    def _offset_change(self, new_offset: typing.Tuple[int, int]) -> None:
        self._connector.player_move(new_offset)
