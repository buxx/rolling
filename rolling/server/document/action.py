# coding: utf-8
from sqlalchemy import JSON, Enum
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String

from rolling.server.extension import ServerSideDocument as Document
from rolling.types import ActionScope
from rolling.types import ActionType


class PendingActionDocument(Document):
    __tablename__ = "pending_action"
    id = Column(Integer, autoincrement=True, primary_key=True)
    action_scope = Column(Enum(*[s.value for s in ActionScope]), nullable=False)
    action_type = Column(Enum(*[s.value for s in ActionType]), nullable=False)
    action_description_id = Column(String, nullable=False)
    parameters = Column(JSON, nullable=False, server_default="{}")
    character_id = Column(String(255), ForeignKey("character.id"), nullable=False)
    with_character_id = Column(String(255), ForeignKey("character.id"), nullable=True)
    stuff_id = Column(Integer, ForeignKey("stuff.id"), nullable=True)
    resource_id = Column(String, nullable=True)
    expire_at_turn = Column(Integer, nullable=False)
    suggested_by = Column(String(255), ForeignKey("character.id"), nullable=True)


class AuthorizePendingActionDocument(Document):
    __tablename__ = "authorize_pending_action"
    pending_action_id = Column(Integer, ForeignKey("pending_action.id"), nullable=False, primary_key=True)
    authorized_character_id = Column(String(255), ForeignKey("character.id"), nullable=True, primary_key=True)
    expire_at_turn = Column(Integer, nullable=False)
