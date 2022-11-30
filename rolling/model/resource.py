# coding: utf-8
import dataclasses

import typing

from rolling.action.base import ActionDescriptionModel
from rolling.model.measure import Unit
from rolling.util import display_g_or_kg
from rolling.util import quantity_to_str

if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel


LAMBDA_RESOURCE_ID = "LAMBDA"


@dataclasses.dataclass
class ResourceDescriptionModel:
    id: str
    name: str
    weight: float
    material_type: str
    unit: Unit
    clutter: float
    descriptions: typing.List[ActionDescriptionModel]
    illustration: typing.Optional[str]
    grow_speed: typing.Optional[int]
    harvest_cost_per_tile: typing.Optional[float]
    harvest_production_per_tile: typing.Optional[float]
    drop_to_nowhere: bool


# FIXME BS: rename (can be in build)
@dataclasses.dataclass
class CarriedResourceDescriptionModelApi:
    id: str
    name: str
    weight: float
    clutter: float
    infos: str
    classes: typing.List[str]
    quantity: float
    quantity_str: str
    drop_base_url: str
    is_heavy: bool
    is_cumbersome: bool


# FIXME BS: rename (can be in build)
@dataclasses.dataclass
class CarriedResourceDescriptionModel(ResourceDescriptionModel):
    quantity: float
    stored_in: typing.Optional[int] = None
    ground_row_i: typing.Optional[int] = None
    ground_col_i: typing.Optional[int] = None

    @classmethod
    def default(
        cls, resource_id: str, resource_description: ResourceDescriptionModel
    ) -> "CarriedResourceDescriptionModel":
        return cls(
            id=resource_id,
            name=resource_description.name,
            weight=0.0,
            material_type=resource_description.material_type,
            unit=resource_description.unit,
            clutter=0.0,
            quantity=0.0,
            descriptions=resource_description.descriptions,
            illustration=resource_description.illustration,
            grow_speed=resource_description.grow_speed,
            drop_to_nowhere=resource_description.drop_to_nowhere,
            harvest_cost_per_tile=resource_description.harvest_cost_per_tile,
            harvest_production_per_tile=resource_description.harvest_production_per_tile,
        )

    @classmethod
    def lambda_(
        cls,
    ) -> "CarriedResourceDescriptionModel":
        return cls(
            id=LAMBDA_RESOURCE_ID,
            name="LAMBDA",
            weight=0.0,
            material_type="n/a",
            unit=Unit.UNIT,
            clutter=0.0,
            quantity=0.0,
            descriptions=[],
            illustration=None,
            grow_speed=None,
            drop_to_nowhere=False,
            harvest_cost_per_tile=None,
            harvest_production_per_tile=None,
        )

    def get_full_description(self, kernel: "Kernel") -> str:
        weight = display_g_or_kg(self.weight)
        quantity_str = quantity_to_str(self.quantity, self.unit, kernel=kernel)
        return (
            f"{self.name} "
            f"({quantity_str}, {weight}, {round(self.clutter, 3)} d'encombrement)"
        )

    def get_light_description(self, kernel: "Kernel") -> str:
        quantity_str = quantity_to_str(self.quantity, self.unit, kernel=kernel)
        return f"{self.name} " f"({quantity_str})"


@dataclasses.dataclass
class OnGroundResourceModel:
    id: str
    quantity: float
    zone_row_i: int
    zone_col_i: int
