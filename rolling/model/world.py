# coding: utf-8
import typing

from serpyco import nested_field

import dataclasses
from rolling.model.tile import WorldMapTileTypeModel


@dataclasses.dataclass(frozen=True)
class WorldMapLegendModel(object):
    all_types: typing.List[WorldMapTileTypeModel]
    default_type: WorldMapTileTypeModel = nested_field(default=None)
