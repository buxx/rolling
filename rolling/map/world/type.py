# coding: utf-8
import typing


class WorldMapTileType(object):
    _list_cache: typing.Dict[str, typing.Type["WorldMapTileType"]] = None

    id = NotImplemented
    foreground_color = "white"
    background_color = ""

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

    @classmethod
    def get_full_id(cls) -> str:
        return "WORLD_TILE__{}".format(cls.id)


class Sea(WorldMapTileType):
    id = "SEA"
    foreground_color = "dark blue"


class Mountain(WorldMapTileType):
    id = "MOUNTAIN"


class Jungle(WorldMapTileType):
    id = "JUNGLE"
    foreground_color = "dark green"


class Hill(WorldMapTileType):
    id = "HILL"


class Beach(WorldMapTileType):
    id = "BEACH"
    foreground_color = "yellow"


class Plain(WorldMapTileType):
    id = "PLAIN"
