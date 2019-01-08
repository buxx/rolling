# coding: utf-8
import typing

from serpyco import nested_field

import dataclasses
from rolling.model.tile import WorldTileTypeModel


@dataclasses.dataclass
class WorldMapLegendModel(object):
    all_types: typing.List[WorldTileTypeModel]
    default_type: WorldTileTypeModel = nested_field(default=None)


@dataclasses.dataclass
class WorldMapModel(object):
    raw_source: str
