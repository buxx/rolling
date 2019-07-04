# coding: utf-8
from sqlalchemy import Column
from sqlalchemy import Enum
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Numeric
from sqlalchemy import String

from rolling.model.resource import ResourceType
from rolling.model.stuff import Unit
from rolling.server.extension import ServerSideDocument as Document


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
    filled_with_resource = Column(
        Enum(*[rt.value for rt in ResourceType]), nullable=True
    )
    filled_capacity = Column(Numeric(10, 2), nullable=True)
    weight = Column(Numeric(10, 2), nullable=True)  # grams
    clutter = Column(Numeric(10, 2), nullable=True)

    # meta
    image = Column(String(255), nullable=True)

    # relations
    carried_by_id = Column(String(255), ForeignKey("character.id"), nullable=True)
