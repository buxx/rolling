# coding: utf-8
import dataclasses
import enum
import typing


class Unit(enum.Enum):
    LITTER = "L"


@dataclasses.dataclass
class StuffProperties:
    id: str
    name: str
    filled_at: float = None
    filled_unity: Unit = None
    weight: float = None
    clutter: float = None
    # TODO BS 2019-06-07: Add list of "capacity" who are object can be used in action
    #  like "Drink", etc


@dataclasses.dataclass
class StuffModel:
    """existing stuff (on zone or carried)"""

    id: int
    name: str
    zone_col_i: int
    zone_row_i: int
    filled_at: float = None
    filled_unity: Unit = None
    weight: float = None
    clutter: float = None


@dataclasses.dataclass
class ZoneGenerationStuff:
    stuff: StuffProperties
    probability: float
    meta: typing.Dict[str, typing.Any]
