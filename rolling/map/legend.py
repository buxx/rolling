# coding: utf-8
import typing

from rolling.map.world.type import WorldMapTileType


class WorldMapLegend(object):
    def __init__(self, raw_legend: typing.Dict[str, str]) -> None:
        self._str_to_type: typing.Dict[str, typing.Type[WorldMapTileType]] = {}
        self._type_to_str: typing.Dict[typing.Type[WorldMapTileType, str]] = {}

        for key, value in raw_legend.items():
            type_ = WorldMapTileType.get_for_id(value)

            self._str_to_type[key] = type_
            self._type_to_str[type_] = key

    def get_type_with_str(self, key: str) -> typing.Type[WorldMapTileType]:
        return self._str_to_type[key]

    def get_str_with_type(self, key: WorldMapTileType) -> str:
        return self._type_to_str[key]
