# coding: utf-8
import time
import typing

import urwid

from rolling.gui.menu import BaseMenu
from rolling.gui.menu import BaseSubMenu

if typing.TYPE_CHECKING:
    from rolling.gui.controller import Controller


class SubMenuExample(BaseSubMenu):
    title = "TestSubMenu"

    def _get_menu_buttons(self):
        return []


class RootMenu(BaseMenu):
    title = "MainMenu"

    def _get_menu_buttons(self):
        return [
            ("Test", self.test_callback),
            ("Test2", self.test2_callback),
            ("Quit", self.quit_callback),
        ]

    def test_callback(self, *args, **kwargs):
        self._main_view.main_content_widget.original_widget.set_text(str(time.time()))

        self._controller.loop.set_alarm_in(1.0, self.test_callback)

    def test2_callback(self, *args, **kwargs):
        sub_menu = SubMenuExample(self._controller, self._main_view, self)

        self._main_view.right_menu_widget.original_widget = sub_menu

    def quit_callback(self, *args, **kwargs):
        raise urwid.ExitMainLoop()


class View(urwid.WidgetWrap):
    def __init__(self, gui: "Controller") -> None:
        self._controller = gui
        self._main_content_widget = None
        self._right_menu_widget = None
        urwid.WidgetWrap.__init__(self, self._main_window())

    @property
    def main_content_widget(self):
        return self._main_content_widget

    @property
    def right_menu_widget(self):
        return self._right_menu_widget

    def _create_main_content_widget(self):
        text_widget = urwid.Text(str(time.time()))
        text_fill = urwid.Filler(text_widget)
        return text_fill

    def _create_right_menu_widget(self):
        root_menu = RootMenu(self._controller, self)
        return urwid.Padding(root_menu, left=0, right=0)

    def _main_window(self):
        self._main_content_widget = self._create_main_content_widget()
        self._right_menu_widget = self._create_right_menu_widget()

        vertical_line = urwid.AttrWrap(urwid.SolidFill(u"\u2502"), "line")
        columns = urwid.Columns(
            [
                ("weight", 2, self._main_content_widget),
                ("fixed", 1, vertical_line),
                ("fixed", 20, self._right_menu_widget),
            ],
            dividechars=1,
            focus_column=2,
        )

        window = urwid.Padding(columns, ("fixed left", 1), ("fixed right", 0))
        window = urwid.AttrWrap(window, "body")
        window = urwid.LineBox(window)
        window = urwid.AttrWrap(window, "line")

        return window
