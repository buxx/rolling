# coding: utf-8
import typing

import urwid

if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel
    from rolling.gui.controller import Controller


class FullContentDialog(urwid.WidgetWrap):
    def __init__(
        self,
        title: str,
        text: str,
        get_buttons: typing.Callable[[], typing.List[urwid.Button]],
    ):
        title_widget = urwid.Text(title)
        text_widget = urwid.Text(text)
        buttons = get_buttons()
        pile = urwid.Pile([title_widget, text_widget] + buttons)
        fill = urwid.Filler(pile)

        super().__init__(urwid.AttrWrap(fill, ""))


class SimpleDialog(FullContentDialog):
    def __init__(
        self,
        kernel: "Kernel",
        controller: "Controller",
        original_widget: urwid.Widget,
        title: str,
        text: typing.Optional[str] = None,
    ) -> None:
        self._kernel = kernel
        self._controller = controller
        self._original_widget = original_widget
        super().__init__(title=title, text=text or "", get_buttons=self._get_buttons)

    def _get_buttons(self) -> typing.List[urwid.Button]:
        return []
