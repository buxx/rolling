# coding: utf-8
import dataclasses
import typing

import serpyco

from rolling.server.document.build import BuildDocument


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
    build_require_resources: typing.List[BuildBuildRequireResourceDescription]
    turn_require_resources: typing.List[BuildTurnRequireResourceDescription]
    power_on_require_resources: typing.List[BuildPowerOnRequireResourceDescription]
    ability_ids: typing.List[str]
    cost: float


@dataclasses.dataclass
class DescribeBuildInputPath:
    character_id: str
    build_id: int = serpyco.number_field(cast_on_load=True)


@dataclasses.dataclass
class ZoneBuildModel:
    row_i: int = serpyco.number_field(getter=lambda b: b.doc.zone_row_i)
    col_i: int = serpyco.number_field(getter=lambda b: b.doc.zone_col_i)
    char: str = serpyco.string_field(getter=lambda b: b.desc.char)
    id: int = serpyco.number_field(getter=lambda b: b.doc.id)


@dataclasses.dataclass
class ZoneBuildModelContainer:
    doc: BuildDocument
    desc: BuildDescription
