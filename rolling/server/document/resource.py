# coding: utf-8
from sqlalchemy import Column
from sqlalchemy import Enum
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Numeric
from sqlalchemy import String

from rolling.model.measure import Unit
from rolling.server.extension import ServerSideDocument as Document


class ResourceDocument(Document):
    __tablename__ = "resource"
    id = Column(Integer, primary_key=True, autoincrement=True)
    resource_id = Column(String(255), nullable=False)
    world_col_i = Column(Integer, nullable=True)
    world_row_i = Column(Integer, nullable=True)
    zone_col_i = Column(Integer, nullable=True)
    zone_row_i = Column(Integer, nullable=True)

    # properties
    unit = Column(Enum(*[u.value for u in Unit]), nullable=True)
    quantity = Column(Numeric(10, 2), nullable=False)

    # relations
    carried_by_id = Column(String(255), ForeignKey("character.id"), nullable=False)
