# coding: utf-8
import typing

from rolling.map.type.base import MapTileType
from rolling.model.world import ResourceType


class ZoneMapTileType(MapTileType):
    _list_cache: typing.Dict[str, typing.Type["ZoneMapTileType"]] = None
    _full_id_pattern = "TILE__{}"

    @classmethod
    def get_all(cls) -> typing.Dict[str, typing.Type["ZoneMapTileType"]]:
        if cls._list_cache is None:
            # TODO BS 2018-12-29: Replace by auto class discover
            cls._list_cache = {
                Nothing.id: Nothing,
                Sand.id: Sand,
                DryBush.id: DryBush,
                Rock.id: Rock,
                SeaWater.id: SeaWater,
                ShortGrass.id: ShortGrass,
                RockyGround.id: RockyGround,
                HighGrass.id: HighGrass,
                Dirt.id: Dirt,
                LeafTree.id: LeafTree,
                TropicalTree.id: TropicalTree,
                DeadTree.id: DeadTree,
                FreshWater.id: FreshWater,
            }

        return cls._list_cache

    @classmethod
    def extractable(cls) -> typing.List[ResourceType]:
        return []


class Nothing(ZoneMapTileType):
    id = "NOTHING"


class Sand(ZoneMapTileType):
    id = "SAND"
    foreground_high_color = "#fa0"

    @classmethod
    def extractable(cls) -> typing.List[ResourceType]:
        return [ResourceType.BEACH_SAND]


class ShortGrass(ZoneMapTileType):
    id = "SHORT_GRASS"
    foreground_high_color = "#080"

    @classmethod
    def extractable(cls) -> typing.List[ResourceType]:
        return [ResourceType.DIRT, ResourceType.HAY]


class HighGrass(ZoneMapTileType):
    id = "HIGH_GRASS"
    foreground_high_color = "#060"

    @classmethod
    def extractable(cls) -> typing.List[ResourceType]:
        return [ResourceType.DIRT, ResourceType.HAY]


class RockyGround(ZoneMapTileType):
    id = "ROCKY_GROUND"
    foreground_high_color = "g31"

    @classmethod
    def extractable(cls) -> typing.List[ResourceType]:
        return [ResourceType.PEBBLES]


class DryBush(ZoneMapTileType):
    id = "DRY_BUSH"
    foreground_high_color = "#860"

    @classmethod
    def extractable(cls) -> typing.List[ResourceType]:
        return [ResourceType.TWIGS]


class Rock(ZoneMapTileType):
    id = "ROCK"
    foreground_high_color = "g35"


class SeaWater(ZoneMapTileType):
    id = "SEA_WATER"
    foreground_high_color = "#06f"
    background_high_color = "#006"

    @classmethod
    def extractable(cls) -> typing.List[ResourceType]:
        return [ResourceType.SALTED_WATER]


class Dirt(ZoneMapTileType):
    id = "DIRT"
    foreground_high_color = "#fd8"

    @classmethod
    def extractable(cls) -> typing.List[ResourceType]:
        return [ResourceType.DIRT]


class LeafTree(ZoneMapTileType):
    id = "LEAF_TREE"
    foreground_high_color = "#8a6"


class TropicalTree(ZoneMapTileType):
    id = "TROPICAL_TREE"
    foreground_high_color = "#686"


class DeadTree(ZoneMapTileType):
    id = "DEAD_TREE"
    foreground_high_color = "#666"


class FreshWater(ZoneMapTileType):
    id = "FRESH_WATER"
    foreground_high_color = "#08f"

    @classmethod
    def extractable(cls) -> typing.List[ResourceType]:
        return [ResourceType.FRESH_WATER]
