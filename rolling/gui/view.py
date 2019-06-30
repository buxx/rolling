# coding: utf-8
import typing

import urwid

from rolling.gui.image.widget import ImageWidget
from rolling.gui.map.object import CurrentPosition
from rolling.gui.map.object import DisplayObjectManager
from rolling.gui.map.render import WorldMapRenderEngine
from rolling.gui.map.widget import WorldMapWidget
from rolling.gui.menu import BaseMenu
from rolling.gui.menu import BaseSubMenu
from rolling.gui.play.server import ChooseServerMenu

if typing.TYPE_CHECKING:
    from rolling.gui.controller import Controller


class WorldMapSubMenu(BaseSubMenu):
    def _get_menu_buttons(self):
        return []

    def restore_parent_menu(self, *args, **kwargs) -> None:
        self._controller.display_zone()
        super().restore_parent_menu()


class CharacterCardSubMenu(BaseSubMenu):
    def _get_menu_buttons(self):
        return []

    def restore_parent_menu(self, *args, **kwargs) -> None:
        self._controller.display_zone()
        super().restore_parent_menu()


class InventorySubMenu(BaseSubMenu):
    def _get_menu_buttons(self):
        return []

    def restore_parent_menu(self, *args, **kwargs) -> None:
        self._controller.display_zone()
        super().restore_parent_menu()


class GoBackSubMenu(BaseSubMenu):
    def _get_menu_buttons(self):
        return []

    def restore_parent_menu(self, *args, **kwargs) -> None:
        self._controller.display_zone()
        super().restore_parent_menu()


class ZoneMenu(BaseMenu):
    title = "Movement"

    def _get_menu_buttons(self):
        return [
            ("World map", self._display_world_map_callback),
            ("Character card", self._display_character_card),
            ("Inventory", self._display_inventory),
            ("Disconnect", self._go_back_root_callback),
        ]

    def _display_character_card(self, *args, **kwargs):
        widget = self._controller.guilang.generate_widget(
            self._controller.client.get_character_card_description(
                self._controller.player_character.id
            )
        )

        self._main_view.main_content_container.original_widget = widget
        self._main_view.right_menu_container.original_widget = CharacterCardSubMenu(
            self._controller, self._main_view, self
        )

    def _display_inventory(self, *args, **kwargs):
        widget = self._controller.guilang.generate_widget(
            self._controller.client.get_character_inventory(
                self._controller.player_character.id
            )
        )

        self._main_view.main_content_container.original_widget = widget
        self._main_view.right_menu_container.original_widget = InventorySubMenu(
            self._controller, self._main_view, self
        )

    def _display_world_map_callback(self, *args, **kwargs):
        display_objects_manager = DisplayObjectManager(
            [
                CurrentPosition(
                    col_i=self._controller.player_character.world_col_i,
                    row_i=self._controller.player_character.world_row_i,
                )
            ]
        )
        display_objects_manager.refresh_indexes()
        world_map_render_engine = WorldMapRenderEngine(
            self._controller.kernel.world_map_source,
            display_objects_manager=display_objects_manager,
        )
        text_widget = WorldMapWidget(self._controller, world_map_render_engine)
        self._main_view.main_content_container.original_widget = text_widget
        self._main_view.right_menu_container.original_widget = WorldMapSubMenu(
            self._controller, self._main_view, self
        )

    def _go_back_root_callback(self, *args, **kwargs):
        self._controller.disconnect()


class RootMenu(BaseMenu):
    title = "Welcome"

    def __init__(
        self, controller: "Controller", main_view: "View", mode: str = "normal"
    ) -> None:
        self._mode = mode
        super().__init__(controller, main_view)

    def _get_menu_buttons(self):
        if self._mode == "exit_only":
            return [
                ("Quit", self._quit_callback),
            ]

        return [
            ("Play", self._play_callback),
            ("Test image", self._test_image),
            ("Quit", self._quit_callback),
        ]

    def _play_callback(self, *args, **kwargs):
        self._main_view.main_content_container.original_widget = ChooseServerMenu(
            self._controller, self._main_view
        )

    def _test_image(self, *args, **kwargs):
        self._main_view.main_content_container.original_widget = ImageWidget("rock.jpeg", callback=lambda: True)

    def _quit_callback(self, *args, **kwargs):
        raise urwid.ExitMainLoop()


class View(urwid.WidgetWrap):
    def __init__(self, controller: "Controller") -> None:
        self._controller = controller
        self._main_content_container = None
        self._right_menu_container = None
        urwid.WidgetWrap.__init__(self, self._main_window())

    @property
    def main_content_container(self):
        return self._main_content_container

    @property
    def right_menu_container(self):
        return self._right_menu_container

    def _create_main_content_widget(self):
        txt = urwid.Text(u"Welcome to rolling")
        fill = urwid.Filler(txt, "top")
        return fill

    def display_root_menu_widget(self):
        self._right_menu_container.original_widget = RootMenu(self._controller, self)

    def display_zone_menu_widget(self):
        self._right_menu_container.original_widget = ZoneMenu(self._controller, self)

    def display_root_content(self):
        self._main_content_container.original_widget = (
            self._create_main_content_widget()
        )

    def _main_window(self):
        self._main_content_container = urwid.Padding(self._create_main_content_widget())
        self._right_menu_container = urwid.Padding(RootMenu(self._controller, self, mode=self._controller.root_menu_mode))

        vertical_line = urwid.AttrWrap(urwid.SolidFill(u"\u2502"), "line")
        columns = urwid.Columns(
            [
                ("weight", 2, self._main_content_container),
                ("fixed", 1, vertical_line),
                ("fixed", 20, self._right_menu_container),
            ],
            dividechars=1,
            focus_column=2,
        )

        window = urwid.Padding(columns, ("fixed left", 1), ("fixed right", 0))
        window = urwid.AttrWrap(window, "body")
        window = urwid.LineBox(window)
        window = urwid.AttrWrap(window, "line")

        return window
