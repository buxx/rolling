# coding: utf-8
import typing

from sqlalchemy import Column
from sqlalchemy import Enum
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Numeric
from sqlalchemy import String

from rolling.exception import CantEmpty
from rolling.exception import CantFill
from rolling.model.measure import Unit
from rolling.server.extension import ServerSideDocument as Document

if typing.TYPE_CHECKING:
    from rolling.model.stuff import StuffProperties
    from rolling.kernel import Kernel


class StuffDocument(Document):
    __tablename__ = "stuff"
    id = Column(Integer, primary_key=True, autoincrement=True)
    stuff_id = Column(String(255), nullable=False)
    world_col_i = Column(Integer, nullable=True)
    world_row_i = Column(Integer, nullable=True)
    zone_col_i = Column(Integer, nullable=True)
    zone_row_i = Column(Integer, nullable=True)

    # properties
    filled_at = Column(Numeric(10, 2), nullable=True)
    filled_unity = Column(Enum(*[u.value for u in Unit]), nullable=True)
    filled_with_resource = Column(String(255), nullable=True)
    filled_capacity = Column(Numeric(10, 2), nullable=True)
    weight = Column(Numeric(10, 2), nullable=True)  # grams
    clutter = Column(Numeric(10, 2), nullable=True)

    # meta
    image = Column(String(255), nullable=True)

    # relations
    carried_by_id = Column(String(255), ForeignKey("character.id"), nullable=True)
    used_as_bag_by_id = Column(String(255), ForeignKey("character.id"), nullable=True)
    in_built_id = Column(String(255), ForeignKey("build.id"), nullable=True)

    def fill(self, kernel: "Kernel", with_resource: str, at: float) -> None:
        if self.filled_with_resource is not None and self.filled_with_resource != with_resource:
            raise CantFill("Cant fill with (yet) with two different resources")

        if self.filled_at == at:
            raise CantFill("Already full")

        self.filled_with_resource = with_resource
        self.filled_at = at
        resource_description = kernel.game.config.resources[with_resource]
        self.weight = resource_description.weight * float(self.filled_capacity)

    def empty(self, stuff_properties: "StuffProperties") -> None:
        if self.filled_at == 0.0:
            raise CantEmpty("Already empty")

        self.filled_with_resource = None
        self.filled_at = None
        self.weight = stuff_properties.weight
