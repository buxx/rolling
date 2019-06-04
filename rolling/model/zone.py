# coding: utf-8
import typing

from serpyco import number_field

import dataclasses
from rolling.model.meta import TransportType


@dataclasses.dataclass(frozen=True)
class TileTypeModel:
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
    # FIXME BS 2019-03-06: Serpyco bug when use enum as dict key, see
    # https://gitlab.com/sgrignard/serpyco/issues/21
    # traversable: typing.Optional[typing.Dict[TransportType, bool]]
    traversable: typing.Optional[typing.Dict[str, bool]]


@dataclasses.dataclass(frozen=True)
class GetZonePathModel:
    row_i: int = number_field(cast_on_load=True)
    col_i: int = number_field(cast_on_load=True)


@dataclasses.dataclass
class ZoneMapModel:
    raw_source: str
