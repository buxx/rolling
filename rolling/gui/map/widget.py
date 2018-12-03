# coding: utf-8
import urwid
from urwid import BOX

from rolling.gui.map.render import WorldMapRenderEngine


class WorldMapWidget(urwid.Text):
    def get_text(self):
        return "toto", [('test', 11)]


class WorldMap2Widget(urwid.Widget):
    _sizing = frozenset([BOX])

    def __init__(self, render_engine: WorldMapRenderEngine) -> None:
        self._render_engine = render_engine

    def render(self, size, focus=False):
        x, y = size
        self._render_engine.render(x, y)

        return urwid.TextCanvas(
            text=self._render_engine.rows,
            attr=self._render_engine.attributes,
            maxcol=x,
        )
