# coding: utf-8
import typing

from rolling.map.type.base import MapTileType


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
                CopperDeposit.id: CopperDeposit,
                TinDeposit.id: TinDeposit,
                IronDeposit.id: IronDeposit,
            }

        return cls._list_cache


class Nothing(ZoneMapTileType):
    id = "NOTHING"


class Sand(ZoneMapTileType):
    id = "SAND"
    name = "Sable"
    foreground_high_color = "#fa0"


class ShortGrass(ZoneMapTileType):
    id = "SHORT_GRASS"
    name = "Herbe courte"
    foreground_high_color = "#080"


class HighGrass(ZoneMapTileType):
    id = "HIGH_GRASS"
    name = "Herbe haute"
    foreground_high_color = "#060"


class RockyGround(ZoneMapTileType):
    id = "ROCKY_GROUND"
    name = "Sol rocheux"
    foreground_high_color = "g31"


class DryBush(ZoneMapTileType):
    id = "DRY_BUSH"
    name = "Buisson sec"
    foreground_high_color = "#860"


class Rock(ZoneMapTileType):
    id = "ROCK"
    name = "Rocher"
    foreground_high_color = "g35"


class SeaWater(ZoneMapTileType):
    id = "SEA_WATER"
    name = "Eau de mer"
    foreground_high_color = "#06f"
    background_high_color = "#006"


class Dirt(ZoneMapTileType):
    id = "DIRT"
    name = "Terre"
    foreground_high_color = "#fd8"


class LeafTree(ZoneMapTileType):
    id = "LEAF_TREE"
    name = "Arbre feuillu"
    foreground_high_color = "#8a6"


class TropicalTree(ZoneMapTileType):
    id = "TROPICAL_TREE"
    name = "Arbre tropical"
    foreground_high_color = "#686"


class DeadTree(ZoneMapTileType):
    id = "DEAD_TREE"
    name = "Arbre mort"
    foreground_high_color = "#666"


class FreshWater(ZoneMapTileType):
    id = "FRESH_WATER"
    name = "Eau fraiche"
    foreground_high_color = "#08f"


class CopperDeposit(ZoneMapTileType):
    id = "COPPER_DEPOSIT"
    name = "Gisement de cuivre"
    foreground_high_color = "#08f"


class TinDeposit(ZoneMapTileType):
    id = "TIN_DEPOSIT"
    name = "Gisement d'étain"
    foreground_high_color = "#08f"


class IronDeposit(ZoneMapTileType):
    id = "IRON_DEPOSIT"
    name = "Gisement de fer"
    foreground_high_color = "#08f"
