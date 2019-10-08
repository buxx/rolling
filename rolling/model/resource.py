# coding: utf-8
import dataclasses
import typing

from rolling.action.base import ActionDescriptionModel
from rolling.model.measure import Unit
from rolling.util import display_g_or_kg
from rolling.util import quantity_to_str

if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel


@dataclasses.dataclass
class ResourceDescriptionModel:
    id: str
    name: str
    weight: float
    material_type: str
    unit: Unit
    clutter: float
    descriptions: typing.List[ActionDescriptionModel]


# FIXME BS: rename (can be in build)
@dataclasses.dataclass
class CarriedResourceDescriptionModel(ResourceDescriptionModel):
    quantity: float
    stored_in: typing.Optional[int] = None

    def get_full_description(self, kernel: "Kernel") -> str:
        weight = display_g_or_kg(self.weight)
        quantity_str = quantity_to_str(self.quantity, self.unit, kernel=kernel)
        of = " "
        if self.unit != Unit.UNIT:
            of = " de "
        return (
            f"{quantity_str}{of}{self.name} "
            f"({weight} et {self.clutter} d'encombrement)"
        )
