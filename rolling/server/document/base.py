# coding: utf-8
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String

from rolling.server.extension import ServerSideDocument as Document

# FIXME BS NOW: Delete that
class ImageDocument(Document):
    __tablename__ = "image"
    id = Column(Integer, primary_key=True, autoincrement=True)
    extension = Column(String, nullable=False)
    checksum = Column(String, unique=True)
