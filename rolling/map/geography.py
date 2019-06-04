# coding: utf-8
import typing

from rolling.exception import SourceLoadError
from rolling.map.legend import MapLegend
from rolling.map.type.base import MapTileType
from rolling.map.type.world import WorldMapTileType


class MapGeography:
    def __init__(
        self,
        legend: MapLegend,
        raw_lines: typing.List[str],
        missing_right_tile_str: typing.Optional[str] = None,
    ) -> None:
        self._rows: typing.List[typing.List[typing.Type[WorldMapTileType]]] = []

        length = self._get_max_length(raw_lines)
        for raw_line in raw_lines:
            if length != len(raw_line) and missing_right_tile_str is None:
                raise SourceLoadError(
                    'Error loading geography: line should be "{}" length but is "{}"'.format(
                        length, len(raw_line)
                    )
                )
            elif length != len(raw_line) and missing_right_tile_str:
                raw_line += missing_right_tile_str * (length - len(raw_line))

            row_tile_types: typing.List[WorldMapTileType] = []
            for char in raw_line:
                char_tile_type = legend.get_type_with_str(char)
                row_tile_types.append(char_tile_type)

            self._rows.append(row_tile_types)

        self._width = length
        self._height = len(self._rows)

    def _get_max_length(self, raw_lines: typing.List[str]) -> int:
        max_length = 0
        for raw_line in raw_lines:
            if max_length < len(raw_line):
                max_length = len(raw_line)
        return max_length

    @property
    def rows(self) -> typing.List[typing.List[typing.Type[MapTileType]]]:
        return self._rows

    @property
    def width(self) -> int:
        return self._width

    @property
    def height(self) -> int:
        return self._height


class WorldMapGeography(MapGeography):
    pass


class ZoneMapGeography(MapGeography):
    pass
