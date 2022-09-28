# coding: utf-8
import dataclasses

import serpyco
from serpyco import number_field
import typing

from rolling.map.type.base import MapTileType
from rolling.map.type.zone import ZoneMapTileType
from rolling.model.character import CharacterModel
from rolling.model.meta import TransportType
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
    hump: typing.Optional[typing.Dict[str, str]]


@dataclasses.dataclass(frozen=True)
class GetZonePathModel:
    row_i: int = number_field(cast_on_load=True)
    col_i: int = number_field(cast_on_load=True)


@dataclasses.dataclass(frozen=True)
class GetZoneQueryModel:
    disable_door_compute: bool = serpyco.field(cast_on_load=True, default=False)


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
    zone_type_id: str


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
    require_transport_type: typing.List[TransportType] = serpyco.field(
        default_factory=list
    )
    illustration: typing.Optional[str] = None

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
    destroy_when_empty: bool
    replace_by_when_destroyed: typing.Optional[typing.Type[MapTileType]]
    infinite: bool
    extract_cost_per_unit: float
    extract_quick_action_quantity: float
    ui_extract_default_quantity: str
    ui_extract_min_quantity: float
    ui_extract_max_quantity: float
    skills_bonus: typing.Dict[str, float]

    def __eq__(self, other: "ZoneMapTileProduction") -> bool:
        return self.resource.id == other.resource.id

    def __hash__(self) -> int:
        return hash(self.resource.id)


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
    followers_can: typing.List[CharacterModel] = serpyco.field(default_factory=list)
    followers_cannot: typing.List[CharacterModel] = serpyco.field(default_factory=list)
    followers_discreetly_can: typing.List[CharacterModel] = serpyco.field(
        default_factory=list
    )
    followers_discreetly_cannot: typing.List[CharacterModel] = serpyco.field(
        default_factory=list
    )
