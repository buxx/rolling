# coding: utf-8
import dataclasses
import typing

from serpyco import number_field

from rolling.map.type.base import MapTileType
from rolling.model.stuff import ZoneGenerationStuff


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


@dataclasses.dataclass
class GenerationInfo:
    count: int
    stuffs: typing.List[ZoneGenerationStuff]


@dataclasses.dataclass
class ZoneProperties:
    zone_type: typing.Type[MapTileType]
    generation_info: GenerationInfo
    move_cost: float


@dataclasses.dataclass
class ZoneRequiredPlayerData:
    weight_overcharge: bool
    clutter_overcharge: bool
