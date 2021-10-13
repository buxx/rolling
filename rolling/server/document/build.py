# coding: utf-8
import datetime
from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Enum
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Numeric
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy import UniqueConstraint

from rolling.server.extension import ServerSideDocument as Document


class BuildDocument(Document):
    __tablename__ = "build"
    id = Column(Integer, primary_key=True, autoincrement=True)
    world_col_i = Column(Integer, nullable=False)
    world_row_i = Column(Integer, nullable=False)
    zone_col_i = Column(Integer, nullable=False)
    zone_row_i = Column(Integer, nullable=False)

    build_id = Column(String(255), nullable=False)
    ap_spent = Column(Numeric(10, 4, asdecimal=False), nullable=False, default=0.0)
    under_construction = Column(Boolean(), nullable=False, default=True)
    is_on = Column(Boolean(), nullable=False)
    is_floor = Column(Boolean(), nullable=False, default=False)
    is_door = Column(Boolean(), nullable=False, default=False)
    health = Column(Integer, nullable=True, default=None)

    # farming
    seeded_with = Column(String(255), nullable=True, default=None)
    grow_progress = Column(Integer, nullable=False, default=0)


DOOR_TYPE__SIMPLE = "SIMPLE"
DOOR_MODE__CLOSED = "CLOSED"
DOOR_MODE__CLOSED_EXCEPT_FOR = "CLOSED_EXCEPT_FOR"
DOOR_MODE_LABELS = {
    None: "Ne rien faire",
    DOOR_MODE__CLOSED: "Garder fermé",
    DOOR_MODE__CLOSED_EXCEPT_FOR: "Garder fermé sauf pour ...",
}


class DoorDocument(Document):
    __tablename__ = "door"
    __table_args__ = (UniqueConstraint("build_id", "character_id", name="door_unique"),)
    id = Column(Integer, primary_key=True, autoincrement=True)
    build_id = Column(
        Integer,
        ForeignKey("build.id"),
        nullable=False,
    )
    character_id = Column(String(255), ForeignKey("character.id"), nullable=False)
    mode = Column(
        Enum(DOOR_MODE__CLOSED, DOOR_MODE__CLOSED_EXCEPT_FOR, name="door__mode"),
        nullable=False,
    )
    affinity_ids = Column(Text(), server_default="[]", nullable=False)
    updated_datetime = Column(
        DateTime, default=datetime.datetime.utcnow, nullable=False
    )
