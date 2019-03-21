# coding: utf-8
import typing

from rolling.exception import NoDefaultTileType, NoDisplayObjectAtThisPosition
from rolling.exception import TileTypeNotFound
from rolling.gui.map.object import DisplayObject
from rolling.gui.map.object import DisplayObjectManager
from rolling.map.source import MapSource
from rolling.map.type.zone import Nothing

WORLD_VOID_STR = " "


class MapRenderEngine(object):
    def __init__(
        self, world_map_source: MapSource, display_objects_manager: DisplayObjectManager
    ) -> None:
        self._world_map_source = world_map_source
        self._rows: typing.List[str] = None
        self._attributes: typing.List[
            typing.List[typing.Tuple[typing.Optional[str], int]]
        ] = None
        self._display_objects_manager = display_objects_manager

    @property
    def rows(self) -> typing.List[str]:
        return self._rows

    @property
    def attributes(self):
        return self._attributes

    @property
    def display_objects_manager(self) -> DisplayObjectManager:
        return self._display_objects_manager

    @property
    def display_objects(self) -> typing.List[DisplayObject]:
        return self._display_objects_manager.display_objects

    @display_objects.setter
    def display_objects(self, display_objects: typing.List[DisplayObject]) -> None:
        self._display_objects_manager.display_objects = display_objects

    def render(
        self,
        width: int,
        height: int,
        offset_horizontal: int = 0,
        offset_vertical: int = 0,
    ) -> None:
        map_width = self._world_map_source.geography.width
        map_height = self._world_map_source.geography.height
        map_rows = self._world_map_source.geography.rows
        map_legend = self._world_map_source.legend
        display_objects_by_position: typing.Dict[typing.Tuple[int, int], DisplayObject] = {}

        # Build map tile coordinates
        matrix: typing.List[typing.List[typing.Tuple[int, int]]] = [
            [(None, None) for i in range(width)] for ii in range(height)
        ]
        for screen_row_i in range(height):
            for screen_col_i in range(width):
                map_row_i = screen_row_i - offset_vertical
                map_col_i = screen_col_i - offset_horizontal

                matrix[screen_row_i][screen_col_i] = map_row_i, map_col_i

        # Build maps chars
        screen_chars: typing.List[str] = ["" for i in range(height)]
        for screen_row_i, row in enumerate(matrix):
            for map_row_i, map_col_i in row:
                # If it is outside map, use empty tile
                if map_row_i < 0 or map_row_i > (map_height - 1) or map_col_i < 0 or map_col_i > (map_width - 1):
                    tile_type = Nothing
                else:
                    tile_type = map_rows[map_row_i][map_col_i]

                tile_chars = map_legend.get_str_with_type(tile_type)
                final_chars = self._display_objects_manager.get_final_str(map_row_i, map_col_i, tile_chars)
                screen_chars[screen_row_i] += final_chars

        # Build attributes
        self._attributes = [None] * height
        for screen_row_i, row in enumerate(screen_chars):
            last_seen_char = None
            self._attributes[screen_row_i] = []

            for screen_col_i, char in enumerate(row):
                if last_seen_char != char:
                    try:
                        tile_type = map_legend.get_type_with_str(char)
                        self._attributes[screen_row_i].append(
                            (tile_type.get_full_id(), len(char.encode()))
                        )
                    except TileTypeNotFound:
                        self._attributes[screen_row_i].append((None, len(char.encode())))
                else:
                    self._attributes[screen_row_i][-1] = (
                        self._attributes[screen_row_i][-1][0],
                        self._attributes[screen_row_i][-1][1] + len(char.encode()),
                    )
                last_seen_char = char

        # Encore each rows
        self._rows = [None] * height
        for screen_row_i, row in enumerate(screen_chars):
            self._rows[screen_row_i] = row.encode()


class WorldMapRenderEngine(MapRenderEngine):
    pass


class TileMapRenderEngine(MapRenderEngine):
    pass
