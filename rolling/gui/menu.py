# coding: utf-8
import abc
import typing

import urwid

if typing.TYPE_CHECKING:
    from rolling.gui.controller import Controller
    from rolling.gui.view import View


# FIXME BS 2018-11-22: Normalize buttons
class BaseMenu(urwid.ListBox):
    def __init__(self, controller: "Controller", main_view: "View"):
        self._controller = controller
        self._main_view = main_view
        super().__init__(urwid.SimpleFocusListWalker(self._get_menu_items()))

    def _get_menu_items(self):
        raise NotImplementedError()


class BaseSubMenu(urwid.ListBox):
    def __init__(
        self, controller: "Controller", main_view: "View", parent_menu: BaseMenu
    ) -> None:
        self._controller = controller
        self._main_view = main_view
        self._parent_menu = parent_menu
        super().__init__(urwid.SimpleFocusListWalker(self._get_menu_items()))

    def restore_parent_menu(self, *args, **kwargs) -> None:
        self._main_view.right_menu_widget.original_widget = self._parent_menu

    @abc.abstractmethod
    def _get_menu_items(self):
        raise NotImplementedError()
