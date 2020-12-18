# coding: utf-8
import dataclasses

import typing

from rolling.map.type.zone import ZoneMapTileType


@dataclasses.dataclass
class ExtractableResourceDescriptionModel:
    resource_id: str
    cost_per_unit: float
    default_quantity: float


@dataclasses.dataclass
class ExtractableDescriptionModel:
    zone_tile_type: typing.Type[ZoneMapTileType]
    resources: typing.Dict[str, ExtractableResourceDescriptionModel]
