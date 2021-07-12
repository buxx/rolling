# coding: utf-8
import random
import typing

from rolling.exception import SourceLoadError
from rolling.exception import TileTypeNotFound
from rolling.map.legend import MapLegend
from rolling.map.type.base import MapTileType
from rolling.map.type.world import WorldMapTileType
import rolling.map.type.zone as zone
from rolling.map.type.zone import Nothing
from rolling.model.zone import ZoneTileProperties

if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel


class MapGeography:
    def __init__(
        self,
        legend: MapLegend,
        raw_lines: typing.List[str],
        missing_right_tile_str: typing.Optional[str] = None,
    ) -> None:
        self._rows: typing.List[typing.List[typing.Type[WorldMapTileType]]] = []
        self._tile_type_positions: typing.Dict[
            typing.Type[MapTileType], typing.List[typing.Tuple[int, int]]
        ] = {}
        self.legend = legend

        length = self._get_max_length(raw_lines)
        for row_i, raw_line in enumerate(raw_lines):
            if length != len(raw_line) and missing_right_tile_str is None:
                raise SourceLoadError(
                    'Error loading geography: line should be "{}" length but is "{}"'.format(
                        length, len(raw_line)
                    )
                )
            elif length != len(raw_line) and missing_right_tile_str:
                raw_line += missing_right_tile_str * (length - len(raw_line))

            row_tile_types: typing.List[WorldMapTileType] = []
            for col_i, char in enumerate(raw_line):
                char_tile_type = legend.get_type_with_str(char)
                row_tile_types.append(char_tile_type)
                if char_tile_type != Nothing:
                    self._tile_type_positions.setdefault(char_tile_type, []).append((row_i, col_i))

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

    @property
    def tile_type_positions(
        self,
    ) -> typing.Dict[typing.Type[MapTileType], typing.List[typing.Tuple[int, int]]]:
        return self._tile_type_positions

    def get_tile_type(self, row_i: int, col_i: int) -> typing.Type[MapTileType]:
        if row_i < 0 or col_i < 0:
            return zone.Nothing
        if row_i >= len(self.rows):
            return zone.Nothing

        cols = self.rows[row_i]
        if col_i >= len(cols):
            return zone.Nothing

        return cols[col_i]


class WorldMapGeography(MapGeography):
    pass


class ZoneMapGeography(MapGeography):
    def get_random_tile_position_containing_resource(
        self, resource_id: str, kernel: "Kernel"
    ) -> typing.Tuple[int, int]:
        for tile_type, tile_positions in self.tile_type_positions.items():
            tiles_properties = kernel.game.world_manager.world.tiles_properties
            try:
                tile_properties: ZoneTileProperties = tiles_properties[tile_type]
            except KeyError:
                continue
            try:
                next(
                    produce.resource.id
                    for produce in tile_properties.produce
                    if produce.resource.id == resource_id
                )
                return random.choice(self.tile_type_positions[tile_type])
            except StopIteration:
                pass

        raise TileTypeNotFound(f"No tile contaning {resource_id} in this zone")
