# coding: utf-8
import dataclasses
import enum
import typing

import serpyco

from rolling.model.action import ActionProperties


class Unit(enum.Enum):
    LITTER = "L"


# FIXME BS 2019-07-03: move to MaterialType
class StuffMaterialType(enum.Enum):
    LIQUID = "LIQUID"
    SANDY = "SANDY"
    PASTY = "PASTY"
    GAS = "GAS"
    SOLID = "SOLID"
    LITTLE_OBJECT = "LITTLE_OBJECT"
    SMALL_PIECE = "SMALL_PIECE"


@dataclasses.dataclass
class StuffProperties:
    id: str
    name: str
    filled_at: typing.Optional[float] = None
    filled_unity: Unit = None
    weight: typing.Optional[float] = None
    clutter: typing.Optional[float] = None
    image: typing.Optional[str] = None
    actions: typing.List[ActionProperties] = serpyco.field(default_factory=list)
    material_type: typing.Optional[StuffMaterialType] = None


@dataclasses.dataclass
class StuffModel:
    """existing stuff (on zone or carried)"""

    id: int
    stuff_id: str
    name: str
    zone_col_i: int
    zone_row_i: int
    filled_at: typing.Optional[float] = None
    filled_unity: typing.Optional[Unit] = None
    weight: typing.Optional[float] = None
    clutter: typing.Optional[float] = None
    image: typing.Optional[str] = None
    carried_by: typing.Optional[str] = None

    def get_full_description(self) -> typing.List[str]:
        descriptions: typing.List[str] = []

        if self.weight:
            descriptions.append(f"{self.weight}g")

        if self.filled_at is not None:
            descriptions.append(f"{self.filled_at}%")

        return descriptions

    def get_light_description(self) -> typing.List[str]:
        descriptions: typing.List[str] = []

        if self.filled_at is not None:
            descriptions.append(f"{self.filled_at}%")

        return descriptions

    def get_name_and_light_description(self) -> str:
        descriptions = self.get_light_description()

        if not descriptions:
            return self.name

        description = "(" + ", ".join(descriptions) + ")"
        return f"{self.name} ({description})"


@dataclasses.dataclass
class ZoneGenerationStuff:
    stuff: StuffProperties
    probability: float
    meta: typing.Dict[str, typing.Any]


@dataclasses.dataclass
class CharacterInventoryModel:
    stuff: typing.List[StuffModel]
    weight: float = 0.0
    clutter: float = 0.0
