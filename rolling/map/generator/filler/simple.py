# coding: utf-8
import random
import typing

from rolling.map.generator.filler.base import FillerFactory
from rolling.map.generator.filler.base import TileMapFiller
from rolling.map.generator.generator import Border
from rolling.map.generator.generator import TileMapGenerator
from rolling.map.source import WorldMapSource
from rolling.map.type.world import Beach
from rolling.map.type.world import Hill
from rolling.map.type.world import Jungle
from rolling.map.type.world import Mountain
from rolling.map.type.world import Plain
from rolling.map.type.world import Sea
from rolling.map.type.world import WorldMapTileType
from rolling.map.type.zone import DryBush
from rolling.map.type.zone import RockyGround
from rolling.map.type.zone import Sand
from rolling.map.type.zone import SeaWater
from rolling.map.type.zone import ShortGrass
from rolling.map.type.zone import ZoneMapTileType


class SimpleTileMapFiller(TileMapFiller):
    def __init__(
        self,
        row_i: int,
        col_i: int,
        world_map_source: WorldMapSource,
        distribution: typing.List[typing.Tuple[float, typing.Type[ZoneMapTileType]]],
    ) -> None:
        self._row_i = row_i
        self._col_i = col_i
        self._world_map_source = world_map_source
        self._tiles: typing.List[typing.Type[ZoneMapTileType]] = [
            td[1] for td in distribution
        ]
        self._probabilities: typing.List[float] = [td[0] for td in distribution]

    def get_char(
        self,
        tile_map_generator: TileMapGenerator,
        is_border: bool,
        distance_from_border: typing.Optional[int],
        border: typing.Optional[Border] = None,
    ) -> str:
        tile_type = random.choices(self._tiles, weights=self._probabilities)[0]
        return tile_map_generator.kernel.tile_map_legend.get_str_with_type(tile_type)


class SeaTileMapFiller(SimpleTileMapFiller):
    def __init__(
        self, row_i: int, col_i: int, world_map_source: WorldMapSource
    ) -> None:
        super().__init__(row_i, col_i, world_map_source, distribution=[(1.0, SeaWater)])


class MountainTileMapFiller(SimpleTileMapFiller):
    def __init__(
        self, row_i: int, col_i: int, world_map_source: WorldMapSource
    ) -> None:
        super().__init__(
            row_i, col_i, world_map_source, distribution=[(1.0, RockyGround)]
        )


class JungleTileMapFiller(SimpleTileMapFiller):
    def __init__(
        self, row_i: int, col_i: int, world_map_source: WorldMapSource
    ) -> None:
        super().__init__(
            row_i, col_i, world_map_source, distribution=[(1.0, ShortGrass)]
        )


class HillTileMapFiller(SimpleTileMapFiller):
    def __init__(
        self, row_i: int, col_i: int, world_map_source: WorldMapSource
    ) -> None:
        super().__init__(
            row_i, col_i, world_map_source, distribution=[(1.0, ShortGrass)]
        )


class BeachTileMapFiller(SimpleTileMapFiller):
    def __init__(
        self, row_i: int, col_i: int, world_map_source: WorldMapSource
    ) -> None:
        super().__init__(
            row_i, col_i, world_map_source, distribution=[(1.0, Sand), (0.05, DryBush)]
        )


class PlainTileMapFiller(SimpleTileMapFiller):
    def __init__(
        self, row_i: int, col_i: int, world_map_source: WorldMapSource
    ) -> None:
        super().__init__(
            row_i, col_i, world_map_source, distribution=[(1.0, ShortGrass)]
        )


class SimpleFillerFactory(FillerFactory):
    def __init__(self) -> None:
        self._matches: typing.Dict[
            WorldMapTileType, typing.Type[SimpleTileMapFiller]
        ] = {
            Sea: SeaTileMapFiller,
            Mountain: MountainTileMapFiller,
            Jungle: JungleTileMapFiller,
            Hill: HillTileMapFiller,
            Beach: BeachTileMapFiller,
            Plain: PlainTileMapFiller,
        }

    def create(
        self,
        world_map_tile_type: WorldMapTileType,
        row_i: int,
        col_i: int,
        world_map_source: WorldMapSource,
    ) -> TileMapFiller:
        return self._matches[world_map_tile_type](
            row_i=row_i, col_i=col_i, world_map_source=world_map_source
        )
