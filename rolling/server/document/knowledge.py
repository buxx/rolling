# coding: utf-8
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import String

from rolling.server.extension import ServerSideDocument as Document


class CharacterKnowledge(Document):
    __tablename__ = "character_knowledge"
    character_id = Column(String(255), ForeignKey("character.id"), nullable=False, primary_key=True)
    knowledge_id = Column(String(64), nullable=False, primary_key=True)
