# coding: utf-8
from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy.ext.declarative import declared_attr


class CorpseMixin(object):
    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    __mapper_args__ = {'always_refresh': True}

    alive_since = Column(Integer, server_default="0", nullable=False)
    world_col_i = Column(Integer, nullable=True)
    world_row_i = Column(Integer, nullable=True)
    zone_col_i = Column(Integer, nullable=True)
    zone_row_i = Column(Integer, nullable=True)
    alive = Column(Boolean, default=True)
