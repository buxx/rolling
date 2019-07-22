# coding: utf-8
import dataclasses
import enum
import typing

import serpyco

from rolling.action.base import ActionDescriptionModel
from rolling.model.resource import ResourceType
from rolling.model.types import MaterialType


class Unit(enum.Enum):
    LITTER = "L"


@dataclasses.dataclass
class StuffProperties:
    id: str
    name: str
    filled_at: typing.Optional[float] = None
    filled_with_resource: typing.Optional[ResourceType] = None
    filled_unity: typing.Optional[Unit] = None
    filled_capacity: typing.Optional[float] = None
    weight: typing.Optional[float] = None
    clutter: typing.Optional[float] = None
    image: typing.Optional[str] = None
    descriptions: typing.List[ActionDescriptionModel] = serpyco.field(
        default_factory=list
    )
    material_type: typing.Optional[MaterialType] = None


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
    filled_with_resource: typing.Optional[ResourceType] = None
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

        if self.filled_with_resource is not None:
            # TODO BS 2019-07-04: translation
            descriptions.append(f"{self.filled_with_resource.value}")

        return descriptions

    def get_light_description(self) -> typing.List[str]:
        descriptions: typing.List[str] = []

        if self.filled_at is not None:
            descriptions.append(f"{self.filled_at}%")

        if self.filled_with_resource is not None:
            # TODO BS 2019-07-04: translation
            descriptions.append(f"{self.filled_with_resource.value}")

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
