# coding: utf-8
import dataclasses
import typing

from serpyco import nested_field

from rolling.model.zone import WorldTileTypeModel


@dataclasses.dataclass
class WorldMapLegendModel:
    all_types: typing.List[WorldTileTypeModel]
    default_type: typing.Optional[WorldTileTypeModel] = nested_field(default=None)


@dataclasses.dataclass
class WorldMapModel:
    raw_source: str
