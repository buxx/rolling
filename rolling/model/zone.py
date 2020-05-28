# coding: utf-8
import dataclasses
import typing

from serpyco import number_field

from rolling.map.type.base import MapTileType
from rolling.map.type.zone import ZoneMapTileType
from rolling.model.resource import ResourceDescriptionModel
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


@dataclasses.dataclass(frozen=True)
class GetZoneCharacterPathModel:
    character_id: str
    row_i: int = number_field(cast_on_load=True)
    col_i: int = number_field(cast_on_load=True)


@dataclasses.dataclass(frozen=True)
class GetZoneMessageQueryModel:
    character_id: str


@dataclasses.dataclass
class ZoneMapModel:
    raw_source: str


@dataclasses.dataclass
class GenerationInfo:
    count: int
    stuffs: typing.List[ZoneGenerationStuff]


@dataclasses.dataclass
class ZoneResource:
    resource_id: str
    probability: float
    maximum: float
    regeneration: float


@dataclasses.dataclass
class ZoneStuff:
    stuff_id: str
    probability: float
    maximum: float
    regeneration: float


@dataclasses.dataclass
class ZoneProperties:
    zone_type: typing.Type[MapTileType]
    generation_info: GenerationInfo
    move_cost: float
    resources: typing.List[ZoneResource]
    stuffs: typing.List[ZoneStuff]
    description: str

    @property
    def resource_ids(self) -> typing.Iterator[str]:
        for zone_resource in self.resources:
            yield zone_resource.resource_id

    @property
    def stuff_ids(self) -> typing.Iterator[str]:
        for zone_stuff in self.stuffs:
            yield zone_stuff.stuff_id


@dataclasses.dataclass
class ZoneMapTileProduction:
    resource: ResourceDescriptionModel
    start_capacity: float
    regeneration: float


@dataclasses.dataclass
class ZoneTileProperties:
    tile_type: typing.Type[ZoneMapTileType]
    produce: typing.List[ZoneMapTileProduction]


@dataclasses.dataclass
class ZoneRequiredPlayerData:
    weight_overcharge: bool
    clutter_overcharge: bool


@dataclasses.dataclass
class MoveZoneInfos:
    can_move: bool
    cost: float
    cannot_move_reasons: typing.List[str]
