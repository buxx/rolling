# coding: utf-8
import dataclasses
import typing

from rolling.model.measure import Unit

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


@dataclasses.dataclass
class CarriedResourceDescriptionModel(ResourceDescriptionModel):
    quantity: float
    stored_in: typing.Optional[int] = None

    def get_full_description(self, kernel: "Kernel") -> str:
        return (
            f"{self.quantity} {kernel.translation.get(self.unit)} de {self.name} "
            f"({self.weight/1000} Kg et {self.clutter} d'encombrement)"
        )
