# coding: utf-8
import typing

import urwid

from rolling.client.http.client import HttpClient
from rolling.gui.palette import PaletteGenerator
from rolling.gui.view import View
from rolling.kernel import Kernel


class Controller(object):
    def __init__(self, client: HttpClient, kernel: Kernel) -> None:
        self._client = client
        self._loop = None
        self._kernel = kernel
        self._view = View(self)
        self._palette_generator = PaletteGenerator(self._kernel)

    @property
    def kernel(self) -> Kernel:
        return self._kernel

    @property
    def loop(self):
        return self._loop

    def main(self) -> None:
        self._loop = urwid.MainLoop(
            self._view, palette=self._palette_generator.create_palette()
        )
        self._loop.screen.set_terminal_properties(colors=256)
        self._loop.run()
