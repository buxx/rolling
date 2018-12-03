# coding: utf-8
import typing


class WorldMapTileType(object):
    _list_cache: typing.Dict[str, typing.Type["WorldMapTileType"]] = None

    id = NotImplemented
    foreground_color = NotImplemented
    background_color = NotImplemented

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


class Mountain(WorldMapTileType):
    id = "MOUNTAIN"


class Jungle(WorldMapTileType):
    id = "JUNGLE"


class Hill(WorldMapTileType):
    id = "HILL"


class Beach(WorldMapTileType):
    id = "BEACH"


class Plain(WorldMapTileType):
    id = "PLAIN"
