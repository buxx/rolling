# coding: utf-8
from sqlalchemy import Column
from sqlalchemy import String

from rolling.server.extension import ClientSideDocument as Document


class ServerDocument(Document):
    __tablename__ = "server"
    server_address = Column(String(255), primary_key=True)
    current_character_id = Column(String(255), nullable=True, default=None)
