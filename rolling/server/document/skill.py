# coding: utf-8
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String

from rolling.server.extension import ServerSideDocument as Document


class CharacterSkillDocument(Document):
    __tablename__ = "character_skill"
    character_id = Column(String(255), ForeignKey("character.id"), nullable=False, primary_key=True)
    skill_id = Column(String(64), nullable=False, primary_key=True)
    counter = Column(Integer, nullable=False)
    value = Column(String(32), nullable=False)
