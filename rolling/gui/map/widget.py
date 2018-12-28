# coding: utf-8
import typing

import urwid
from urwid import BOX

from rolling.gui.map.object import Character
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
        # FIXME: BS 2018-12-28: currently hardcoded for test
        self._display_objects = [
            Character(
                8, 8,
            )
        ]

    def render(self, size, focus=False):
        x, y = size

        self._render_engine.display_objects = self._display_objects
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
        if key == "up":
            self._vertical_offset += 1
        if key == "down":
            self._vertical_offset -= 1
        if key == "left":
            self._horizontal_offset += 1
        if key == "right":
            self._horizontal_offset -= 1

        self._invalidate()


class WorldMapWidget(MapWidget):
    pass


class TileMapWidget(MapWidget):
    pass
