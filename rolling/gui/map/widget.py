# coding: utf-8
import typing

import urwid
from urwid import BOX

from rolling.exception import CantMoveBecauseSurcharge
from rolling.exception import MoveToOtherZoneError
from rolling.gui.connector import ZoneMapConnector
from rolling.gui.dialog import SimpleDialog
from rolling.gui.map.render import MapRenderEngine
from rolling.gui.play.zone import ChangeZoneDialog
from rolling.map.source import ZoneMapSource
from rolling.model.zone import MoveZoneInfos
from rolling.util import CornerEnum

if typing.TYPE_CHECKING:
    from rolling.gui.controller import Controller


class MapWidget(urwid.Widget):
    _sizing = frozenset([BOX])

    def __init__(self, controller: "Controller", render_engine: MapRenderEngine) -> None:
        self._controller = controller
        self._render_engine = render_engine
        self._horizontal_offset = 0
        self._vertical_offset = 0
        self._current_row_size = 0
        self._current_col_size = 0
        self._first_display = True

    @property
    def render_engine(self) -> MapRenderEngine:
        return self._render_engine

    def render(self, size, focus=False):
        self._current_col_size, self._current_row_size = size
        return self._render(size, focus)

    def _render(self, size, focus=False):
        self._render_engine.render(
            self._current_col_size,
            self._current_row_size,
            offset_horizontal=self._horizontal_offset,
            offset_vertical=self._vertical_offset,
        )

        self._controller.loop.set_alarm_in(0.25, lambda *_, **__: self._invalidate())
        return urwid.TextCanvas(
            text=self._render_engine.rows,
            attr=self._render_engine.attributes,
            maxcol=self._current_col_size,
        )

    def selectable(self):
        return True

    def keypress(self, size, key):
        pass

    def _offset_change(self, new_offset: typing.Tuple[int, int]) -> None:
        pass


class WorldMapWidget(MapWidget):
    pass


# TODO BS 2019-01-22: Rename into ZoneMapWidget
class TileMapWidget(MapWidget):
    def __init__(
        self,
        controller: "Controller",
        render_engine: MapRenderEngine,
        zone_map_source: ZoneMapSource,
    ) -> None:
        super().__init__(controller, render_engine)
        self._connector = ZoneMapConnector(self, self._controller, zone_map_source=zone_map_source)

    def _offset_change(self, new_offset: typing.Tuple[int, int]) -> None:
        try:
            if not self._connector.move_is_possible(new_offset):
                return
        except MoveToOtherZoneError as exc:
            # FIXME BS 2019-03-06: Manage (try) change zone case
            self._change_zone_dialog(exc.corner)
            return
        except CantMoveBecauseSurcharge:
            if not self._first_display:
                self._controller.display_cant_move_because_surcharge()
                return

        # move player
        self._connector.player_move(new_offset)

        character_col_i = self._controller.display_objects_manager.current_player.col_i
        character_row_i = self._controller.display_objects_manager.current_player.row_i

        # center on player
        self._horizontal_offset = self._current_col_size // 2 - character_col_i
        self._vertical_offset = self._current_row_size // 2 - character_row_i

    def _render(self, size, focus=False):
        if self._first_display:
            self._offset_change((0, 0))  # to compute offset with player position
            self._first_display = False

        return super()._render(size, focus)

    def _change_zone_dialog(self, corner: CornerEnum) -> None:
        zone_map_widget = self._controller._view.main_content_container.original_widget
        world_row_i, world_col_i = self._connector.get_zone_coordinates(corner)

        move_zone_infos: MoveZoneInfos = self._controller.client.get_move_zone_infos(
            character_id=self._controller.player_character.id,
            world_row_i=world_row_i,
            world_col_i=world_col_i,
        )

        if not move_zone_infos.can_move:
            self._controller._view.main_content_container.original_widget = SimpleDialog(
                kernel=self._controller.kernel,
                controller=self._controller,
                original_widget=self._controller.view.main_content_container.original_widget,
                title=f"Vous ne pouvez pas marcher vers là-bas, "
                f"cela nécessiterait {move_zone_infos.cost} points d'actions",
                go_back=True,
            )
            return

        zones = self._controller.kernel.world_map_source.geography.rows
        try:
            zones[world_row_i][world_col_i]  # test if zone exist
            self._controller._view.main_content_container.original_widget = ChangeZoneDialog(
                kernel=self._controller.kernel,
                controller=self._controller,
                original_widget=zone_map_widget,
                title="Marchez vers là bas ?",
                text=f"Marchez pour arrivez à votre destination "
                f"vous coutera {move_zone_infos.cost} points d'actions",
                world_row_i=world_row_i,
                world_col_i=world_col_i,
            )
        except IndexError:
            self._controller._view.main_content_container.original_widget = SimpleDialog(
                kernel=self._controller.kernel,
                controller=self._controller,
                original_widget=self._controller.view.main_content_container.original_widget,
                title="Vous êtes au bord du monde ! Vous ne pouvez pas aller au delà.",
                go_back=True,
            )

    def keypress(self, size, key):
        new_offset = None

        if key == "up":
            new_offset = (1, 0)
        if key == "down":
            new_offset = (-1, 0)
        if key == "left":
            new_offset = (0, 1)
        if key == "right":
            new_offset = (0, -1)
        if key == "enter":
            self._controller.display_zone_actions_on_place()

        if new_offset is not None:
            self._offset_change(new_offset)

        self._invalidate()
