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


class ResourceDocument(Document):
    __tablename__ = "resource"
    id = Column(Integer, primary_key=True, autoincrement=True)
    resource_id = Column(String(255), nullable=False)
    world_col_i = Column(Integer, nullable=True)
    world_row_i = Column(Integer, nullable=True)
    zone_col_i = Column(Integer, nullable=True)
    zone_row_i = Column(Integer, nullable=True)

    # properties
    unity = Column(Enum(*[u.value for u in Unit]), nullable=True)

    filled_with_resource = Column(String(255), nullable=True)
    filled_capacity = Column(Numeric(10, 2), nullable=True)
    weight = Column(Numeric(10, 2), nullable=True)  # grams
    clutter = Column(Numeric(10, 2), nullable=True)

    # meta
    image = Column(String(255), nullable=True)

    # relations
    carried_by_id = Column(String(255), ForeignKey("character.id"), nullable=True)

    def fill(self, with_resource: str, at: float) -> None:
        if (
            self.filled_with_resource is not None
            and self.filled_with_resource != with_resource.value
        ):
            raise CantFill("Cant fill with (yet) with two different resources")

        if self.filled_at == at:
            raise CantFill("Already full")

        self.filled_with_resource = with_resource.value
        self.filled_at = at
        # FIXME BS NOW: from config !!
        # self.weight = resource_type_gram_per_unit[with_resource] * float(
        #     self.filled_capacity
        # )
        self.weight = 1.0

    def empty(self, stuff_properties: "StuffProperties") -> None:
        if self.filled_at == 0.0:
            raise CantEmpty("Already empty")

        self.filled_with_resource = None
        self.filled_at = None
        self.weight = stuff_properties.weight
