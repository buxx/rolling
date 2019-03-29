# coding: utf-8
from functools import lru_cache
import typing

from rolling.exception import NoDefaultTileType
from rolling.exception import NoDisplayObjectAtThisPosition
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

        # Shortcuts
        self._map_width = self._world_map_source.geography.width
        self._map_height = self._world_map_source.geography.height
        self._map_rows = self._world_map_source.geography.rows
        self._map_legend = self._world_map_source.legend

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

    # TODO BS 2019-03-24: size depend of memory capacity
    @lru_cache(maxsize=128)
    def _get_matrix(
        self,
        width: int,
        height: int,
        offset_horizontal: int = 0,
        offset_vertical: int = 0,
    ) -> typing.List[typing.List[typing.Tuple[int, int]]]:
        # Build map tile coordinates
        matrix: typing.List[typing.List[typing.Tuple[int, int]]] = [
            [(None, None) for i in range(width)] for ii in range(height)
        ]
        for screen_row_i in range(height):
            for screen_col_i in range(width):
                map_row_i = screen_row_i - offset_vertical
                map_col_i = screen_col_i - offset_horizontal

                matrix[screen_row_i][screen_col_i] = map_row_i, map_col_i

        return matrix

    def render(
        self,
        width: int,
        height: int,
        offset_horizontal: int = 0,
        offset_vertical: int = 0,
    ) -> None:
        matrix = self._get_matrix(width, height, offset_horizontal, offset_vertical)

        # Build maps chars
        screen_chars: typing.List[str] = ["" for i in range(height)]
        for screen_row_i, row in enumerate(matrix):
            for map_row_i, map_col_i in row:
                # If it is outside map, use empty tile
                if (
                    map_row_i < 0
                    or map_row_i > (self._map_height - 1)
                    or map_col_i < 0
                    or map_col_i > (self._map_width - 1)
                ):
                    tile_type = Nothing
                else:
                    tile_type = self._map_rows[map_row_i][map_col_i]

                tile_chars = self._map_legend.get_str_with_type(tile_type)
                final_chars = self._display_objects_manager.get_final_str(
                    map_row_i, map_col_i, tile_chars
                )
                screen_chars[screen_row_i] += final_chars

        self._attributes = self._build_attributes(tuple(screen_chars), height)

        # Encore each rows
        self._rows = [None] * height
        for screen_row_i, row in enumerate(screen_chars):
            self._rows[screen_row_i] = row.encode()

    # TODO BS 2019-03-24: size depend of memory capacity
    @lru_cache(maxsize=128)
    def _build_attributes(
        self, screen_chars: typing.Tuple[str], height: int
    ) -> typing.List[typing.List[typing.Tuple[typing.Optional[str], int]]]:
        attributes: typing.List[
            typing.List[typing.Tuple[typing.Optional[str], int]]
        ] = [None] * height

        for screen_row_i, row in enumerate(screen_chars):
            last_seen_char = None
            attributes[screen_row_i] = []

            for screen_col_i, char in enumerate(row):
                if last_seen_char != char:
                    try:
                        tile_type = self._map_legend.get_type_with_str(char)
                        attributes[screen_row_i].append(
                            (tile_type.get_full_id(), len(char.encode()))
                        )
                    except TileTypeNotFound:
                        attributes[screen_row_i].append((None, len(char.encode())))
                else:
                    attributes[screen_row_i][-1] = (
                        attributes[screen_row_i][-1][0],
                        attributes[screen_row_i][-1][1] + len(char.encode()),
                    )
                last_seen_char = char

        return attributes


class WorldMapRenderEngine(MapRenderEngine):
    pass


class TileMapRenderEngine(MapRenderEngine):
    pass
