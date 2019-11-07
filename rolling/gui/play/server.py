# coding: utf-8
import typing

import urwid

if typing.TYPE_CHECKING:
    from rolling.gui.controller import Controller
    from rolling.gui.view import View


class ChooseServerMenu(urwid.ListBox):
    def __init__(self, controller: "Controller", main_view: "View") -> None:
        self._controller = controller
        self._main_view = main_view
        self._items = self._build_items()
        super().__init__(urwid.SimpleListWalker(self._items))

    def get_servers(self):
        return ["127.0.0.1:5000", "s2.bux.fr:7431"]

    def choose_server(self, widget: urwid.Button, server_address: str, **kwargs):
        self._controller._choose_server(server_address)

    def _build_items(self):
        menu_items = [urwid.Text("Choose server"), urwid.Divider()]

        for server_address in self.get_servers():
            button = urwid.Button(server_address, self.choose_server, user_data=server_address)
            menu_items.append(button)

        return menu_items
