# coding: utf-8
import json
from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import Enum
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Numeric
from sqlalchemy import String
from sqlalchemy import Text
import typing

from rolling.exception import CantEmpty
from rolling.exception import CantFill
from rolling.exception import NotEnoughResource
from rolling.model.measure import Unit
from rolling.server.extension import ServerSideDocument as Document

if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel
    from rolling.model.stuff import StuffProperties


class StuffDocument(Document):
    __tablename__ = "stuff"
    id = Column(Integer, primary_key=True, autoincrement=True)
    stuff_id = Column(String(255), nullable=False)
    world_col_i = Column(Integer, nullable=True)
    world_row_i = Column(Integer, nullable=True)
    zone_col_i = Column(Integer, nullable=True)
    zone_row_i = Column(Integer, nullable=True)

    # properties
    filled_value = Column(Numeric(10, 2), nullable=True)
    filled_unity = Column(Enum(*[u.value for u in Unit]), nullable=True)
    filled_with_resource = Column(String(255), nullable=True)
    filled_capacity = Column(Numeric(10, 2), nullable=True)
    weight = Column(Numeric(10, 2), nullable=True)  # grams
    clutter = Column(Numeric(10, 2), nullable=True)

    # crafting
    ap_required = Column(Numeric(10, 4), nullable=False, default=0.0)
    ap_spent = Column(Numeric(10, 4), nullable=False, default=0.0)
    under_construction = Column(Boolean(), nullable=False, default=False)
    description = Column(String, nullable=False, default="")

    # meta
    image = Column(String(255), nullable=True)

    # relations
    carried_by_id = Column(String(255), ForeignKey("character.id"), nullable=True)
    used_as_bag_by_id = Column(String(255), ForeignKey("character.id"), nullable=True)
    used_as_weapon_by_id = Column(String(255), ForeignKey("character.id"), nullable=True)
    used_as_shield_by_id = Column(String(255), ForeignKey("character.id"), nullable=True)
    used_as_armor_by_id = Column(String(255), ForeignKey("character.id"), nullable=True)
    in_built_id = Column(String(255), ForeignKey("build.id"), nullable=True)
    shared_with_affinity_id = Column(Integer, ForeignKey("affinity.id"), nullable=True)

    def fill(self, kernel: "Kernel", with_resource: str, add_value: float) -> None:
        if self.filled_with_resource is not None and self.filled_with_resource != with_resource:
            raise CantFill("Impossible de mélanger")

        if float(self.filled_value or 0.0) + add_value > float(self.filled_capacity):
            raise CantFill("Capacité maximale dépassé")

        self.filled_with_resource = with_resource
        self.filled_value = float(self.filled_value or 0.0) + add_value
        resource_description = kernel.game.config.resources[self.filled_with_resource]
        stuff_properties = kernel.game.stuff_manager.get_stuff_properties_by_id(self.stuff_id)
        self.weight = (
            resource_description.weight * float(self.filled_value)
        ) + stuff_properties.weight

    def empty(
        self, kernel: "Kernel", remove_value: float, force_before_raise: bool = False
    ) -> None:
        raise_not_enough_exc = None

        if not self.filled_value:
            raise CantEmpty("Vide")

        if float(self.filled_value or 0.0) - remove_value < 0.0:
            raise_not_enough_exc = NotEnoughResource(
                resource_id=self.filled_with_resource,
                required_quantity=remove_value,
                available_quantity=float(self.filled_value) or 0.0,
            )

            if not force_before_raise:
                raise raise_not_enough_exc

        self.filled_value = max(0.0, float(self.filled_value or 0.0) - remove_value)
        resource_description = kernel.game.config.resources[self.filled_with_resource]
        stuff_properties = kernel.game.stuff_manager.get_stuff_properties_by_id(self.stuff_id)
        self.weight = (
            resource_description.weight * float(self.filled_value)
        ) + stuff_properties.weight

        if not self.filled_value:
            self.filled_with_resource = None
            self.filled_value = None

        if raise_not_enough_exc:
            raise raise_not_enough_exc
