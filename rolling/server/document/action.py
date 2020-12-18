# coding: utf-8
from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import Enum
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import JSON
from sqlalchemy import String

from rolling.rolling_types import ActionScope
from rolling.rolling_types import ActionType
from rolling.server.extension import ServerSideDocument as Document


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
    name = Column(String(255), nullable=False)
    delete_after_first_perform = Column(Boolean(), default=True)


class AuthorizePendingActionDocument(Document):
    __tablename__ = "authorize_pending_action"
    pending_action_id = Column(
        Integer, ForeignKey("pending_action.id"), nullable=False, primary_key=True
    )
    authorized_character_id = Column(
        String(255), ForeignKey("character.id"), nullable=True, primary_key=True
    )
