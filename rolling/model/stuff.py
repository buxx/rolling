# coding: utf-8
import dataclasses
import typing

import serpyco

from rolling.action.base import ActionDescriptionModel
from rolling.model.measure import Unit
from rolling.model.resource import CarriedResourceDescriptionModel
from rolling.util import display_g_or_kg


@dataclasses.dataclass
class StuffGenerateResourceProperties:
    resource_id: str
    quantity: float
    require_one_of_ability: typing.List[str] = serpyco.field(default_factory=list)


@dataclasses.dataclass
class StuffProperties:
    id: str
    name: str
    is_bag: bool = False
    filled_at: typing.Optional[float] = None
    filled_with_resource: typing.Optional[str] = None
    filled_unity: typing.Optional[Unit] = None
    filled_capacity: typing.Optional[float] = None
    weight: typing.Optional[float] = None
    clutter: typing.Optional[float] = None
    clutter_capacity: typing.Optional[float] = None
    image: typing.Optional[str] = None
    descriptions: typing.List[ActionDescriptionModel] = serpyco.field(default_factory=list)
    material_type: typing.Optional[str] = None
    abilities: typing.List[str] = serpyco.field(default_factory=list)
    generate_resources: typing.List[StuffGenerateResourceProperties] = serpyco.field(
        default_factory=list
    )


@dataclasses.dataclass
class StuffModel:
    """existing stuff (on zone or carried)"""

    id: int
    stuff_id: str
    name: str
    zone_col_i: typing.Optional[int] = None
    zone_row_i: typing.Optional[int] = None
    is_bag: bool = False
    filled_at: typing.Optional[float] = None
    filled_unity: typing.Optional[Unit] = None
    filled_with_resource: typing.Optional[str] = None
    weight: typing.Optional[float] = None
    clutter: typing.Optional[float] = None
    clutter_capacity: typing.Optional[float] = None
    image: typing.Optional[str] = None
    carried_by: typing.Optional[str] = None
    stored_in: typing.Optional[int] = None

    def get_full_description(self) -> typing.List[str]:
        descriptions: typing.List[str] = []

        if self.weight:
            descriptions.append(display_g_or_kg(self.weight))

        if self.filled_at is not None:
            descriptions.append(f"{self.filled_at}%")

        if self.filled_with_resource is not None:
            # TODO BS 2019-07-04: translation
            descriptions.append(f"{self.filled_with_resource}")

        if self.clutter:
            descriptions.append(f"{self.clutter} d'encombrement")

        return descriptions

    def get_light_description(self) -> typing.List[str]:
        descriptions: typing.List[str] = []

        if self.filled_at is not None:
            descriptions.append(f"{self.filled_at}%")

        if self.filled_with_resource is not None:
            # TODO BS 2019-07-04: translation
            descriptions.append(f"{self.filled_with_resource}")

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
    resource: typing.List[CarriedResourceDescriptionModel]
    weight: float = 0.0
    clutter: float = 0.0
