# coding: utf-8
import abc
import typing

from rolling.map.generator.generator import TileMapGenerator
from rolling.map.source import WorldMapSource
from rolling.map.type.tile import RockyGround
from rolling.map.type.tile import Sand
from rolling.map.type.tile import SeaWater
from rolling.map.type.tile import ShortGrass
from rolling.map.type.tile import TileMapTileType
from rolling.map.type.world import Beach
from rolling.map.type.world import Hill
from rolling.map.type.world import Jungle
from rolling.map.type.world import Mountain
from rolling.map.type.world import Plain
from rolling.map.type.world import Sea
from rolling.map.type.world import WorldMapTileType


class TileMapFiller(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def get_char(self, tile_map_generator: TileMapGenerator) -> str:
        pass


class DummyTileMapFiller(TileMapFiller):
    def __init__(self, tile_type: typing.Type[TileMapTileType]) -> None:
        self._tile_type = tile_type

    def get_char(self, tile_map_generator: TileMapGenerator) -> str:
        return tile_map_generator.kernel.tile_map_legend.get_str_with_type(
            self._tile_type
        )


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


class DummyFillerFactory(FillerFactory):
    def __init__(self) -> None:
        self._matches: typing.Dict[WorldMapTileType, DummyTileMapFiller] = {
            Sea: DummyTileMapFiller(SeaWater),
            Mountain: DummyTileMapFiller(RockyGround),
            Jungle: DummyTileMapFiller(ShortGrass),
            Hill: DummyTileMapFiller(ShortGrass),
            Beach: DummyTileMapFiller(Sand),
            Plain: DummyTileMapFiller(ShortGrass),
        }

    def create(
        self,
        world_map_tile_type: WorldMapTileType,
        row_i: int,
        col_i: int,
        world_map_source: WorldMapSource,
    ) -> TileMapFiller:
        return self._matches[world_map_tile_type]
