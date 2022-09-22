# coding: utf-8
import dataclasses

from functools import lru_cache
import typing

from rolling.model.resource import ResourceDescriptionModel


@dataclasses.dataclass
class RequiredResourceForMix:
    resource: ResourceDescriptionModel
    quantity: float

    def __hash__(self):
        return hash((self.resource.id, self.coeff))


@dataclasses.dataclass
class ResourceMixDescription:
    id: str
    required_resources: typing.List[RequiredResourceForMix]
    produce_resource: ResourceDescriptionModel
    produce_quantity: float
    cost_per_quantity: float
    properties: dict

    @property
    @lru_cache()
    def required_resources_ids(self) -> typing.Tuple[str]:
        return tuple([d.resource.id for d in self.required_resources])

    def __hash__(self):
        return hash(
            (
                tuple([d.resource.id for d in self.required_resources]),
                self.produce_resource.id,
            )
        )
