# coding: utf-8
import typing
import abc

from rolling.map.generator.generator import TileMapGenerator
from rolling.map.type.tile import TileMapTileType


class TileMapFiller(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def get_char(self, tile_map_generator: TileMapGenerator) -> str:
        pass


class DummyTileMapFiller(TileMapFiller):
    def __init__(self, tile_type: typing.Type[TileMapTileType]) -> None:
        self._tile_type = tile_type

    def get_char(self, tile_map_generator: TileMapGenerator) -> str:
        return tile_map_generator.kernel.tile_map_legend.get_str_with_type(self._tile_type)
