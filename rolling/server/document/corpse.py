# coding: utf-8
import enum
from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import Enum
from sqlalchemy import Integer
from sqlalchemy.ext.declarative import declared_attr

from rolling.server.extension import ServerSideDocument as Document


class AnimatedCorpseType(enum.Enum):
    CHARACTER = "CHARACTER"
    HARE = "HARE"
    PIG = "PIG"
    CRAB = "CRAB"
    MOORHEN = "MOORHEN"
    GOAT = "GOAT"


class CorpseMixin:
    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    __mapper_args__ = {"always_refresh": True}

    alive_since = Column(Integer, server_default="0", nullable=False)
    world_col_i = Column(Integer, nullable=True)
    world_row_i = Column(Integer, nullable=True)
    zone_col_i = Column(Integer, nullable=True)
    zone_row_i = Column(Integer, nullable=True)
    alive = Column(Boolean, default=True)
    type_ = Column(
        Enum(*[t.value for t in AnimatedCorpseType], name="animated_corpse__type_"), nullable=False
    )


class AnimatedCorpseDocument(CorpseMixin, Document):
    __tablename__ = "animated_corpse"
    id = Column(Integer, primary_key=True)
