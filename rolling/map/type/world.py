# coding: utf-8
import typing

from rolling.map.type.base import MapTileType
from rolling.model.meta import TransportType


class WorldMapTileType(MapTileType):
    _list_cache: typing.Dict[str, typing.Type["WorldMapTileType"]] = None
    _full_id_pattern = "WORLD_TILE__{}"
    require_transport_type: typing.List[TransportType] = []

    @classmethod
    def get_all(cls) -> typing.Dict[str, typing.Type["WorldMapTileType"]]:
        if cls._list_cache is None:
            cls._list_cache = {
                Sea.id: Sea,
                Mountain.id: Mountain,
                Jungle.id: Jungle,
                Hill.id: Hill,
                Beach.id: Beach,
                Plain.id: Plain,
            }

        return cls._list_cache

    @classmethod
    def get_for_id(cls, id_: str) -> typing.Type["WorldMapTileType"]:
        return cls.get_all()[id_]


class Sea(WorldMapTileType):
    id = "SEA"
    name = "Mer"
    foreground_high_color = "#06f"
    background_high_color = "#006"
    require_transport_type = [TransportType.BOAT]


class Mountain(WorldMapTileType):
    id = "MOUNTAIN"
    name = "Montagne"
    foreground_color = ""
    background_color = ""
    mono = ""
    foreground_high_color = "#860"


class Jungle(WorldMapTileType):
    id = "JUNGLE"
    name = "Jungle"
    foreground_high_color = "#060"


class Hill(WorldMapTileType):
    id = "HILL"
    name = "Colline"
    foreground_high_color = "#660"


class Beach(WorldMapTileType):
    id = "BEACH"
    name = "Plage"
    foreground_high_color = "#fa0"


class Plain(WorldMapTileType):
    id = "PLAIN"
    name = "Plaine"
    foreground_high_color = "#fda"
