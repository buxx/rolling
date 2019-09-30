# coding: utf-8
import dataclasses
import typing

import serpyco


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
