# coding: utf-8
import typing

from serpyco import number_field

import dataclasses
from rolling.model.meta import TransportType


@dataclasses.dataclass(frozen=True)
class TileTypeModel(object):
    id: str
    foreground_color: str
    background_color: str
    mono: str
    foreground_high_color: str
    background_high_color: str


@dataclasses.dataclass(frozen=True)
class WorldTileTypeModel(TileTypeModel):
    pass


@dataclasses.dataclass(frozen=True)
class ZoneTileTypeModel(TileTypeModel):
    char: str
    traversable: typing.Optional[typing.Dict[TransportType, bool]]


@dataclasses.dataclass(frozen=True)
class GetZonePathModel(object):
    row_i: int = number_field(cast_on_load=True)
    col_i: int = number_field(cast_on_load=True)


@dataclasses.dataclass
class ZoneMapModel(object):
    raw_source: str
