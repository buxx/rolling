# coding: utf-8
import typing

from rolling.kernel import Kernel
from rolling.map.type.property.traversable import traversable_properties
from rolling.map.type.tile import TileMapTileType
from rolling.model.tile import ZoneTileModel


class TileLib(object):
    def __init__(self, kernel: Kernel) -> None:
        self._kernel = kernel

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
