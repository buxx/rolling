# coding: utf-8
import typing

from rolling.exception import NoDefaultTileType
from rolling.exception import TileTypeNotFound
from rolling.map.type.base import MapTileType
from rolling.map.type.world import WorldMapTileType


class MapLegend(object):
    def __init__(
        self, raw_legend: typing.Dict[str, str], map_tile_type: typing.Type[MapTileType]
    ) -> None:
        self._str_to_type: typing.Dict[str, typing.Type[MapTileType]] = {}
        self._type_to_str: typing.Dict[typing.Type[MapTileType, str]] = {}
        self._default_type: typing.Optional[typing.Type[MapTileType]] = None

        for key, raw_value in raw_legend.items():
            value = raw_value.strip()
            clean_value = value

            if value.endswith("*"):
                clean_value = value[:-1]
                self._default_type = map_tile_type.get_for_id(clean_value)

            type_ = map_tile_type.get_for_id(clean_value)
            self._str_to_type[key] = type_
            self._type_to_str[type_] = key

    def get_type_with_str(self, key: str) -> typing.Type[MapTileType]:
        try:
            return self._str_to_type[key]
        except KeyError:
            raise TileTypeNotFound('Tile type not found for str "{}"'.format(key))

    def get_str_with_type(self, key: typing.Type[WorldMapTileType]) -> str:
        try:
            return self._type_to_str[key]
        except KeyError:
            raise TileTypeNotFound('Tile str not found for type "{}"'.format(str(key)))

    def get_all_types(self) -> typing.Iterable[typing.Type[MapTileType]]:
        return self._str_to_type.values()

    def get_default_type(self) -> typing.Optional[typing.Type[MapTileType]]:
        if self._default_type is None:
            raise NoDefaultTileType()
        return self._default_type


class WorldMapLegend(MapLegend):
    pass


class TileMapLegend(MapLegend):
    pass
