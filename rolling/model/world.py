# coding: utf-8
import dataclasses
import enum
import typing

from serpyco import nested_field

from rolling.model.stuff import StuffMaterialType
from rolling.model.zone import WorldTileTypeModel
from rolling.model.zone import ZoneProperties


class ResourceType(enum.Enum):
    FRESH_WATER = "FRESH_WATER"
    SALTED_WATER = "SALTED_WATER"
    BEACH_SAND = "BEACH_SAND"
    DIRT = "DIRT"
    PEBBLES = "PEBBLES"
    TWIGS = "TWIGS"
    HAY = "HAY"


resource_type_materials: typing.Dict[ResourceType, StuffMaterialType] = {
    ResourceType.FRESH_WATER: StuffMaterialType.LIQUID,
    ResourceType.SALTED_WATER: StuffMaterialType.LIQUID,
    ResourceType.BEACH_SAND: StuffMaterialType.SANDY,
    ResourceType.DIRT: StuffMaterialType.SANDY,
    ResourceType.PEBBLES: StuffMaterialType.LITTLE_OBJECT,
    ResourceType.TWIGS: StuffMaterialType.SMALL_PIECE,
    ResourceType.HAY: StuffMaterialType.SMALL_PIECE,
}


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

    def __hash__(self) -> int:
        return hash(str(self.type_) + str(self.material_type))
