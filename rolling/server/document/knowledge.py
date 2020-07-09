# coding: utf-8
from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String

from rolling.server.extension import ServerSideDocument as Document


class CharacterKnowledgeDocument(Document):
    __tablename__ = "character_knowledge"
    character_id = Column(String(255), ForeignKey("character.id"), nullable=False, primary_key=True)
    knowledge_id = Column(String(64), nullable=False, primary_key=True)
    acquired = Column(Boolean(), nullable=False, default=False)
    progress = Column(Integer(), nullable=False, default=0)
