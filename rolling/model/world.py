# coding: utf-8
import dataclasses
import typing

from serpyco import nested_field

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
    id: str
    material_type: str
    name: str
    weight: float

    def __hash__(self) -> int:
        return hash(self.id + self.material_type)
