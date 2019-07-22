# coding: utf-8
import dataclasses
import typing

from rolling.map.type.zone import ZoneMapTileType


@dataclasses.dataclass
class ExtractableResourceDescriptionModel:
    resource_id: str
    # FIXME BS NOW: extraction modality


@dataclasses.dataclass
class ExtractableDescriptionModel:
    zone_tile_type: typing.Type[ZoneMapTileType]
    resources: typing.Dict[str, ExtractableResourceDescriptionModel]
