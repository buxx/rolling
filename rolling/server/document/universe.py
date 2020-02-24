# coding: utf-8
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import DateTime

from rolling.server.extension import ServerSideDocument as Document


class UniverseStateDocument(Document):
    __tablename__ = "universe_state"
    turn = Column(Integer, primary_key=True, autoincrement=True)
    turned_at = Column(DateTime)
