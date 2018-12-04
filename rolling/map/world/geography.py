# coding: utf-8
import typing

from rolling.exception import SourceLoadError
from rolling.map.legend import WorldMapLegend
from rolling.map.world.type import WorldMapTileType


class WorldMapGeography(object):
    def __init__(self, legend: WorldMapLegend, raw_lines: typing.List[str]) -> None:
        self._rows: typing.List[typing.List[WorldMapTileType]] = []

        length = len(raw_lines[0])
        for raw_line in raw_lines:
            if length != len(raw_line):
                raise SourceLoadError(
                    'Error loading geography: line should be "{}" length but is "{}"'.format(
                        length, len(raw_line)
                    )
                )

            row_tile_types: typing.List[WorldMapTileType] = []
            for char in raw_line:
                char_tile_type = legend.get_type_with_str(char)
                row_tile_types.append(char_tile_type)

            self._rows.append(row_tile_types)

        self._width = length
        self._height = len(self._rows)

    @property
    def rows(self) -> typing.List[typing.List[WorldMapTileType]]:
        return self._rows

    @property
    def width(self) -> int:
        return self._width

    @property
    def height(self) -> int:
        return self._height
