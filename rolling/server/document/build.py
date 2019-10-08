# coding: utf-8
import typing

from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import Enum
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Numeric
from sqlalchemy import String

from rolling.server.extension import ServerSideDocument as Document


class BuildDocument(Document):
    __tablename__ = "build"
    id = Column(Integer, primary_key=True, autoincrement=True)
    world_col_i = Column(Integer, nullable=False)
    world_row_i = Column(Integer, nullable=False)
    zone_col_i = Column(Integer, nullable=False)
    zone_row_i = Column(Integer, nullable=False)

    build_id = Column(String(255), nullable=False)
    ap_spent = Column(Numeric(10, 4), nullable=False, default=0.0)
    under_construction = Column(Boolean(), nullable=False, default=True)
