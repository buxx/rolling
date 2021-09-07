# coding: utf-8
import dataclasses

from rolling.model.meta import FromType
from rolling.model.meta import RiskType


@dataclasses.dataclass
class AbilityDescription:
    id: str
    name: str


@dataclasses.dataclass
class HaveAbility:
    ability_id: str
    from_: FromType
    risk: RiskType
