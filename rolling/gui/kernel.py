# coding: utf-8
import typing

from rolling.map.legend import TileMapLegend
from rolling.map.source import WorldMapSource
from rolling.map.type.tile import TileMapTileType


class Kernel(object):
    def __init__(self, world_map_str: str) -> None:
        self._world_map_source = WorldMapSource(self, world_map_str)
        self._tile_map_legend: typing.Optional[TileMapLegend] = None

    @property
    def world_map_source(self) -> WorldMapSource:
        return self._world_map_source

    @property
    def tile_map_legend(self) -> TileMapLegend:
        if self._tile_map_legend is None:
            # TODO BS 2018-12-20: Consider it can be an external source
            self._tile_map_legend = TileMapLegend(
                {
                    " ": "NOTHING",
                    "⡩": "SAND",
                    "⁘": "SHORT GRASS",
                    "ൖ": "DRY BUSH",
                    "#": "ROCK",
                    "⑉": "ROCKY GROUND",
                    "~": "SEA WATER",
                },
                TileMapTileType,
            )

        return self._tile_map_legend
