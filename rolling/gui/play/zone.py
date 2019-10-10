# coding: utf-8
import typing

import urwid

from rolling.gui.dialog import FullContentDialog
from rolling.kernel import Kernel

if typing.TYPE_CHECKING:
    from rolling.gui.controller import Controller


class ChangeZoneDialog(FullContentDialog):
    def __init__(
        self,
        kernel: Kernel,
        controller: "Controller",
        original_widget: urwid.Widget,
        title: str,
        text: str,
        world_row_i: int,
        world_col_i: int,
    ) -> None:
        self._kernel = kernel
        self._controller = controller
        self._original_widget = original_widget
        self._world_row_i = world_row_i
        self.world_col_i = world_col_i
        super().__init__(title=title, text=text, get_buttons=self._get_buttons)

    def _get_buttons(self) -> typing.List[urwid.Button]:
        def change_zone(*args, **kwargs):
            self._controller.change_zone(self._world_row_i, self.world_col_i)

        def cancel(*args, **kwargs):
            self._controller.view.main_content_container.original_widget = self._original_widget

        return [
            urwid.Button("No, stay here", on_press=cancel),
            urwid.Button("Yes, i like to walk !", on_press=change_zone),
        ]
