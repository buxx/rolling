# coding: utf-8
import dataclasses

from rolling.model.measure import Unit


@dataclasses.dataclass
class ResourceDescriptionModel:
    id: str
    name: str
    weight: float
    material_type: str
    unit: Unit
