# coding: utf-8
import dataclasses

DEFAULT_MAXIMUM_SKILL = 5.0


@dataclasses.dataclass
class SkillDescription:
    id: str
    name: str
    default: float
    maximum: float


@dataclasses.dataclass
class CharacterSkillModel:
    id: str
    name: str
    value: float
