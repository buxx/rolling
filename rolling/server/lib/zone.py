# coding: utf-8
import typing

from rolling.kernel import Kernel
from rolling.map.type.property.traversable import traversable_properties
from rolling.map.type.zone import ZoneMapTileType
from rolling.model.zone import ZoneMapModel
from rolling.model.zone import ZoneTileTypeModel


class ZoneLib:
    def __init__(self, kernel: Kernel) -> None:
        self._kernel = kernel

    def get_all_tiles(self) -> typing.List[ZoneTileTypeModel]:
        tiles: typing.List[ZoneTileTypeModel] = []

        for tile_id, tile_class in ZoneMapTileType.get_all().items():
            tiles.append(
                ZoneTileTypeModel(
                    id=tile_id,
                    char=self._kernel.tile_map_legend.get_str_with_type(tile_class),
                    traversable=traversable_properties[tile_class],
                    foreground_color=tile_class.foreground_color,
                    background_color=tile_class.background_color,
                    mono=tile_class.mono,
                    foreground_high_color=tile_class.foreground_high_color,
                    background_high_color=tile_class.background_high_color,
                )
            )

        return tiles

    def get_zone(self, row_i: int, col_i: int) -> ZoneMapModel:
        return ZoneMapModel(raw_source=self._kernel.get_tile_map(row_i, col_i).source.raw_source)
