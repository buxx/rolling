# coding: utf-8
import typing

import urwid


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
