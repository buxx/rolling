# coding: utf-8
import urwid
from urwid import BOX

from rolling.gui.map.render import MapRenderEngine


class MapWidget(urwid.Widget):
    _sizing = frozenset([BOX])

    def __init__(self, render_engine: MapRenderEngine) -> None:
        self._render_engine = render_engine
        self._horizontal_offset = 0
        self._vertical_offset = 0

    def render(self, size, focus=False):
        x, y = size
        self._render_engine.render(
            x,
            y,
            offset_horizontal=self._horizontal_offset,
            offset_vertical=self._vertical_offset,
        )

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
