# coding: utf-8
import dataclasses

import serpyco
import typing

from rolling.action.base import ActionDescriptionModel
from rolling.model.measure import Unit
from rolling.model.resource import (
    CarriedResourceDescriptionModel,
    CarriedResourceDescriptionModelApi,
)
from rolling.util import display_g_or_kg

if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel


LAMBDA_STUFF_ID = "LAMBDA"


@dataclasses.dataclass
class StuffProperties:
    id: str
    name: str
    is_bag: bool = False
    filled_value: typing.Optional[float] = None
    filled_with_resource: typing.Optional[str] = None
    filled_unity: typing.Optional[Unit] = None
    filled_capacity: typing.Optional[float] = None
    weight: typing.Optional[float] = None
    clutter: typing.Optional[float] = None
    clutter_capacity: typing.Optional[float] = None
    image: typing.Optional[str] = None
    descriptions: typing.List[ActionDescriptionModel] = serpyco.field(
        default_factory=list
    )
    material_type: typing.Optional[str] = None
    abilities: typing.List[str] = serpyco.field(default_factory=list)
    weapon: bool = False
    shield: bool = False
    armor: bool = False
    estoc: int = 0  # estoc (pointe de lame)
    blunt: int = 0  # frappe (gourdin)
    sharp: int = 0  # taille (coupant de lame)
    protect_estoc: int = 0
    protect_blunt: int = 0
    protect_sharp: int = 0
    damages: float = 0.0
    classes: typing.List[str] = serpyco.field(default_factory=list)
    skills_bonus: typing.List[str] = serpyco.field(default_factory=list)
    illustration: typing.Optional[str] = None
    bonuses: typing.Dict[str, typing.Any] = serpyco.field(default_factory=dict)
    sprite_sheet_identifiers: typing.Optional[typing.List[str]] = None

    def have_abilities(self, abilities: typing.List[str]) -> typing.List[str]:
        have_abilities = []
        for ability_id in abilities:
            if ability_id in self.abilities:
                have_abilities.append(ability_id)
        return have_abilities

    def bonuses_strings(self) -> typing.List[str]:
        lines = []

        def walk(
            obj: typing.Dict[str, typing.Any]
        ) -> typing.Generator[str, None, None]:
            for key, value in obj.items():
                yield key
                if isinstance(value, dict):
                    yield from walk(key, value)

        for key, value in self.bonuses.items():
            lines.append(" -> ".join([key] + list(walk(value))))

        return lines


@dataclasses.dataclass
class StuffModelApi:
    ids: typing.List[int]
    stuff_id: str
    name: str
    infos: str
    under_construction: bool
    classes: typing.List[str]
    is_equipment: bool
    count: int
    drop_base_url: str
    is_heavy: bool
    is_cumbersome: bool
    is_equip: bool


@dataclasses.dataclass
class StuffModel:
    """existing stuff (on zone or carried)"""

    id: int
    stuff_id: str
    name: str
    zone_col_i: typing.Optional[int] = None
    zone_row_i: typing.Optional[int] = None
    is_bag: bool = False
    filled_value: typing.Optional[float] = None
    filled_unity: typing.Optional[Unit] = None
    filled_with_resource: typing.Optional[str] = None
    weight: typing.Optional[float] = None
    clutter: typing.Optional[float] = None
    clutter_capacity: typing.Optional[float] = None
    image: typing.Optional[str] = None
    carried_by: typing.Optional[str] = None
    stored_in: typing.Optional[int] = None
    ap_required: float = 0.0
    ap_spent: float = 0.0
    under_construction: bool = False
    description: str = ""
    weapon: bool = False
    shield: bool = False
    armor: bool = False
    estoc: int = 0
    blunt: int = 0
    sharp: int = 0
    protect_estoc: int = 0
    protect_blunt: int = 0
    protect_sharp: int = 0
    damages: float = 0.0
    classes: typing.List[str] = serpyco.field(default_factory=list)
    used_by: typing.Optional[str] = None
    illustration: typing.Optional[str] = None
    is_lambda: bool = False
    sprite_sheet_identifiers: typing.Optional[typing.List[str]] = None

    @classmethod
    def lambda_(cls) -> "StuffModel":
        return cls(
            id=0,
            stuff_id=LAMBDA_STUFF_ID,
            name="LAMBDA",
            is_lambda=True,
        )

    @property
    def ready_for_use(self) -> bool:
        # TODO BS: is broken, etc
        return not self.under_construction

    def get_full_description(self, kernel: "Kernel") -> typing.List[str]:
        descriptions: typing.List[str] = []

        if self.weight:
            descriptions.append(display_g_or_kg(self.weight))

        if self.filled_value is not None:
            descriptions.append(str(round(self.filled_value, 2)))

        if self.filled_with_resource is not None:
            resource_description = kernel.game.config.resources[
                self.filled_with_resource
            ]
            unit_str = kernel.translation.get(resource_description.unit)
            descriptions.append(unit_str)
            descriptions.append(resource_description.name)

        if self.clutter:
            descriptions.append(f"{round(self.clutter, 3)} d'encombrement")

        return descriptions

    def get_light_description(self, kernel: "Kernel") -> typing.List[str]:
        descriptions: typing.List[str] = []

        if self.filled_value is not None:
            descriptions.append(str(round(self.filled_value, 2)))

        if self.filled_with_resource is not None:
            resource_description = kernel.game.config.resources[
                self.filled_with_resource
            ]
            unit_str = kernel.translation.get(resource_description.unit)
            descriptions.append(unit_str)
            descriptions.append(f"{resource_description.name}")

        return descriptions

    def get_name_and_light_description(self, kernel: "Kernel") -> str:
        descriptions = self.get_light_description(kernel)

        if not descriptions:
            return self.name

        description = "(" + ", ".join(descriptions) + ")"
        return f"{self.get_name()} {description}"

    def get_name(self) -> str:
        under_construction_char = "*" if self.under_construction else ""
        return f"{self.name}{under_construction_char}"


@dataclasses.dataclass
class ZoneGenerationStuff:
    stuff: StuffProperties
    probability: float
    meta: typing.Dict[str, typing.Any]


@dataclasses.dataclass
class CharacterInventoryModel:
    stuff: typing.List[StuffModel]
    resource: typing.List[CarriedResourceDescriptionModel]
    over_weight: bool
    over_clutter: bool
    weight: float = 0.0
    clutter: float = 0.0


@dataclasses.dataclass
class CharacterInventoryModelApi:
    stuff: typing.List[StuffModelApi]
    resource: typing.List[CarriedResourceDescriptionModelApi]
    over_weight: bool
    over_clutter: bool
    weight: float = 0.0
    clutter: float = 0.0
