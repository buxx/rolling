# coding: utf-8
import dataclasses
import typing

from serpyco import nested_field

from rolling.model.material import MaterialType
from rolling.model.resource import ResourceType
from rolling.model.zone import WorldTileTypeModel
from rolling.model.zone import ZoneProperties


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
    material_type: MaterialType
    name: str

    def __hash__(self) -> int:
        return hash(str(self.type_) + str(self.material_type))
