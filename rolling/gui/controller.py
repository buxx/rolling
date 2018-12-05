# coding: utf-8
import typing

import urwid

from rolling.client.http.client import HttpClient
from rolling.gui.kernel import Kernel
from rolling.gui.view import View


class Controller(object):
    def __init__(self, client: HttpClient, kernel: Kernel) -> None:
        self._client = client
        self._loop = None
        self._kernel = kernel
        self._view = View(self)

    @property
    def kernel(self) -> Kernel:
        return self._kernel

    @property
    def loop(self):
        return self._loop

    def create_palette(self) -> typing.List[typing.Tuple[str, str, str]]:
        palette = []

        for world_map_tile_type in self._kernel.world_map_source.legend.get_all_types():
            # palette can be:
            # (name, foreground, background, mono, foreground_high, background_high)
            palette.append(
                (
                    world_map_tile_type.get_full_id(),
                    world_map_tile_type.foreground_color,
                    world_map_tile_type.background_color,
                )
            )

        return palette

    def main(self) -> None:
        self._loop = urwid.MainLoop(self._view, palette=self.create_palette())
        self._loop.screen.set_terminal_properties(colors=256)
        self._loop.run()
