# coding: utf-8
import enum
import typing

from rolling.model.material import MaterialType


class ResourceType(enum.Enum):
    FRESH_WATER = "FRESH_WATER"
    SALTED_WATER = "SALTED_WATER"
    BEACH_SAND = "BEACH_SAND"
    DIRT = "DIRT"
    PEBBLES = "PEBBLES"
    TWIGS = "TWIGS"
    HAY = "HAY"


resource_type_gram_per_unit: typing.Dict[ResourceType, float] = {
    ResourceType.FRESH_WATER: 1000.0,
    ResourceType.SALTED_WATER: 1000.0,
    ResourceType.BEACH_SAND: 1600.0,
    ResourceType.DIRT: 1500.0,
    ResourceType.PEBBLES: 2000.0,
    ResourceType.TWIGS: 300.0,
    ResourceType.HAY: 200.0,
}
resource_type_materials: typing.Dict[ResourceType, MaterialType] = {
    ResourceType.FRESH_WATER: MaterialType.LIQUID,
    ResourceType.SALTED_WATER: MaterialType.LIQUID,
    ResourceType.BEACH_SAND: MaterialType.SANDY,
    ResourceType.DIRT: MaterialType.SANDY,
    ResourceType.PEBBLES: MaterialType.LITTLE_OBJECT,
    ResourceType.TWIGS: MaterialType.SMALL_PIECE,
    ResourceType.HAY: MaterialType.SMALL_PIECE,
}
