# coding: utf-8
import dataclasses
import enum
import typing

from serpyco import nested_field

from rolling.model.stuff import StuffMaterialType
from rolling.model.zone import WorldTileTypeModel
from rolling.model.zone import ZoneProperties


class ResourceType(enum.Enum):
    WATER = "WATER"


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


@dataclasses.dataclass
class Resource:
    type_: ResourceType
    material_type: StuffMaterialType
    name: str
