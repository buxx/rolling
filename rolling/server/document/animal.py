# coding: utf-8
import enum

from sqlalchemy import Column, Enum, Integer

from rolling.server.document.corpse import CorpseMixin
from rolling.server.extension import ServerSideDocument as Document


class AnimalType(enum.Enum):
    HARE = "HARE"


class AnimalDocument(CorpseMixin, Document):
    __tablename__ = "animal"
    id = Column(Integer, primary_key=True)
    type_ = Column(Enum(*[t.value for t in AnimalType]), nullable=False)
