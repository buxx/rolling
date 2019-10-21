# coding: utf-8
import datetime

from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text

from rolling.server.extension.sqlalchemy import ServerSideDocument as Document


class EventDocument(Document):
    __tablename__ = "event"
    id = Column(Integer, primary_key=True, autoincrement=True)
    text = Column(Text, nullable=False)
    character_id = Column(String(255), ForeignKey("character.id"), nullable=False)
    datetime = Column(DateTime, default=datetime.datetime.utcnow)
