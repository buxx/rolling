# coding: utf-8
import dataclasses

import serpyco
import typing

from rolling.model.meta import TransportType
from rolling.server.document.build import BuildDocument

if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel


@dataclasses.dataclass
class BuildRequireResourceDescription:
    resource_id: str
    quantity: float


@dataclasses.dataclass
class BuildBuildRequireResourceDescription:
    resource_id: str
    quantity: float


@dataclasses.dataclass
class BuildTurnRequireResourceDescription:
    resource_id: str
    quantity: float


@dataclasses.dataclass
class BuildPowerOnRequireResourceDescription:
    resource_id: str
    quantity: float


@dataclasses.dataclass
class BuildDescription:
    id: str
    name: str
    char: str
    building_char: str
    robustness: typing.Optional[int]  # None seems indestructible
    build_require_resources: typing.List[BuildBuildRequireResourceDescription]
    turn_require_resources: typing.List[BuildTurnRequireResourceDescription]
    power_on_require_resources: typing.List[BuildPowerOnRequireResourceDescription]
    ability_ids: typing.List[str]
    cost: float
    is_floor: bool
    is_door: bool
    classes: typing.List[str] = serpyco.field(default_factory=list)
    many: bool = False
    traversable: typing.Dict[TransportType, bool] = serpyco.field(
        default_factory=lambda: {TransportType.WALKING.value: True}
    )
    illustration: typing.Optional[str] = None
    default_is_on: bool = True
    abilities_if_is_on: bool = False
    allow_deposit: bool = False
    allow_deposit_limited: bool = False
    group_name: typing.Optional[str] = None
    description: typing.Optional[str] = None
    door_type: typing.Optional[str] = None
    spawn_point: bool = False

    @property
    def allowed_resource_ids(self) -> typing.List[str]:
        return list(
            set(
                [rd.resource_id for rd in self.build_require_resources]
                + [rd.resource_id for rd in self.turn_require_resources]
                + [rd.resource_id for rd in self.power_on_require_resources]
            )
        )


@dataclasses.dataclass
class LookBuildFromQuickActionQuery:
    zone_row_i: int = serpyco.number_field(cast_on_load=True)
    zone_col_i: int = serpyco.number_field(cast_on_load=True)


@dataclasses.dataclass
class LookBuildFromQuickActionPath:
    character_id: str


@dataclasses.dataclass
class DescribeBuildInputPath:
    character_id: str
    build_id: int = serpyco.number_field(cast_on_load=True)


def get_build_classes(desc: BuildDescription, doc: BuildDocument) -> typing.List[str]:
    classes = desc.classes + [doc.build_id]
    if desc.power_on_require_resources and not doc.is_on:
        classes = classes + list(map(lambda c: f"{c}__OFF", classes))
    return classes


@dataclasses.dataclass
class ZoneBuildModel:
    row_i: int = serpyco.number_field(getter=lambda b: b.doc.zone_row_i)
    col_i: int = serpyco.number_field(getter=lambda b: b.doc.zone_col_i)
    is_floor: bool = serpyco.field(getter=lambda b: b.doc.is_floor)
    char: str = serpyco.string_field(getter=lambda b: b.desc.char)
    id: int = serpyco.number_field(getter=lambda b: b.doc.id)
    build_id: str = serpyco.number_field(getter=lambda b: b.doc.build_id)
    classes: typing.List[str] = serpyco.field(
        default_factory=list,
        getter=lambda b: b.classes or get_build_classes(b.desc, b.doc),
    )
    traversable: typing.Dict[TransportType, bool] = serpyco.field(
        default_factory=dict, getter=lambda b: b.traversable or b.desc.traversable
    )
    under_construction: bool = serpyco.field(
        getter=lambda b: b.doc.under_construction, default=False
    )


@dataclasses.dataclass
class ZoneBuildModelContainer:
    doc: BuildDocument
    desc: BuildDescription
    traversable: typing.Optional[typing.Dict[TransportType, bool]] = None
    classes: typing.Optional[typing.List[str]] = None
