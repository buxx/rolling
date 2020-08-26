# coding: utf-8
import typing
import urwid

if typing.TYPE_CHECKING:
    from rolling.gui.controller import Controller
    from rolling.gui.view import View


class BaseMenu(urwid.ListBox):
    title = "Menu"

    def __init__(self, controller: "Controller", main_view: "View") -> None:
        self._controller = controller
        self._main_view = main_view
        self._items = self._build_items()
        super().__init__(urwid.SimpleListWalker(self._items))

    def _get_menu_buttons(self):
        raise NotImplementedError()

    def _get_texts(self) -> typing.List[str]:
        return []

    def _build_items(self):
        menu_items = [urwid.Text(self.title), urwid.Divider()]

        texts = self._get_texts()
        for text in texts:
            text_widget = urwid.Text(text)
            menu_items.append(text_widget)

        if texts:
            menu_items.append(urwid.Text(""))

        button_data = self._get_menu_buttons()
        for button_name, button_callback in button_data:
            button = urwid.Button(button_name, button_callback)
            menu_items.append(button)

        return menu_items


class BaseSubMenu(urwid.ListBox):
    title = "SubMenu"

    def __init__(self, controller: "Controller", main_view: "View", parent_menu: BaseMenu) -> None:
        self._controller = controller
        self._main_view = main_view
        self._parent_menu = parent_menu
        self._items = self._build_items()
        super().__init__(urwid.SimpleFocusListWalker(self._items))

    def restore_parent_menu(self, *args, **kwargs) -> None:
        self._main_view.right_menu_container.original_widget = self._parent_menu

    def _get_menu_buttons(self):
        raise NotImplementedError()

    def _build_items(self):
        menu_items = [urwid.Text(self.title), urwid.Divider()]

        button_data = self._get_menu_buttons()
        for button_name, button_callback in button_data:
            button = urwid.Button(button_name, button_callback)
            menu_items.append(button)

        quit_button = urwid.Button("Go back", self.restore_parent_menu)
        menu_items.append(quit_button)

        return menu_items
