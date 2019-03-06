# coding: utf-8
import abc

from rolling.map.generator.generator import TileMapGenerator
from rolling.map.source import WorldMapSource
from rolling.map.type.world import WorldMapTileType


class TileMapFiller(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def get_char(self, tile_map_generator: TileMapGenerator) -> str:
        pass


class FillerFactory(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def create(
        self,
        world_map_tile_type: WorldMapTileType,
        row_i: int,
        col_i: int,
        world_map_source: WorldMapSource,
    ) -> TileMapFiller:
        pass
