# coding: utf-8
import typing

from rolling.kernel import Kernel
from rolling.map.type.property.traversable import traversable_properties
from rolling.map.type.tile import TileMapTileType
from rolling.model.tile import ZoneTileModel


class TileLib(object):
    def __init__(self, kernel: Kernel) -> None:
        self._kernel = kernel

    # FIXME BS 2019-01-01: Write simple test to test this function is working (all tile info
    # up to date, overwise it make errors)
    def get_all_tiles(self) -> typing.List[ZoneTileModel]:
        tiles: typing.List[ZoneTileModel] = []

        for tile_id, tile_class in TileMapTileType.get_all().items():
            tiles.append(
                ZoneTileModel(
                    id=tile_id,
                    char=self._kernel.tile_map_legend.get_str_with_type(tile_class),
                    traversable=traversable_properties[tile_class],
                )
            )

        return tiles
