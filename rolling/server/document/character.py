# coding: utf-8
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String

from rolling.server.extension import ServerSideDocument as Document


class CharacterDocument(Document):
    __tablename__ = "character"
    id = Column(String(255), primary_key=True)
    name = Column(String(255))
    world_col_i = Column(Integer, nullable=True)
    world_row_i = Column(Integer, nullable=True)
    zone_col_i = Column(Integer, nullable=True)
    zone_row_i = Column(Integer, nullable=True)