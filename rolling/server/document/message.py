# coding: utf-8
import datetime
from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import JSON
from sqlalchemy import String
from sqlalchemy import Text

from rolling.server.extension import ServerSideDocument as Document


class MessageDocument(Document):
    __tablename__ = "message"
    id = Column(Integer, primary_key=True, autoincrement=True)
    subject = Column(String, nullable=True)
    text = Column(Text, nullable=False)
    character_id = Column(String(255), ForeignKey("character.id"), nullable=False)
    author_id = Column(String(255), ForeignKey("character.id"), nullable=False)
    author_name = Column(String, nullable=False)
    datetime = Column(DateTime, default=datetime.datetime.utcnow)
    read = Column(Boolean, default=False)
    zone_row_i = Column(Integer, nullable=True)
    zone_col_i = Column(Integer, nullable=True)
    zone = Column(Boolean, nullable=False)
    concerned = Column(JSON(), default="[]")  # list of character_id
    is_outzone_message = Column(Boolean, default=False)
    first_message = Column(Integer, ForeignKey("message.id"), nullable=True)
    is_first_message = Column(Boolean, nullable=False, default=False)
