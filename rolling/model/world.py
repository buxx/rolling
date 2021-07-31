# coding: utf-8
import dataclasses

from serpyco import nested_field
import typing

from rolling.map.type.zone import ZoneMapTileType
from rolling.model.zone import WorldTileTypeModel
from rolling.model.zone import ZoneProperties
from rolling.model.zone import ZoneTileProperties


@dataclasses.dataclass
class WorldMapLegendModel:
    all_types: typing.List[WorldTileTypeModel]
    default_type: typing.Optional[WorldTileTypeModel] = nested_field(default=None)


@dataclasses.dataclass
class WorldMapModel:
    raw_source: str


@dataclasses.dataclass
class World:
    zones_properties: typing.List[ZoneProperties]
    tiles_properties: typing.Dict[typing.Type[ZoneMapTileType], ZoneTileProperties]


# @dataclasses.dataclass
# class Resource:
#     id: str
#     material_type: str
#     name: str
#     weight: float
#
#     def __hash__(self) -> int:
#         return hash(self.id + self.material_type)
