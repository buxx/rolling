# coding: utf-8
import typing

from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy.orm import relationship

from rolling.server.document.base import SqliteNumeric
from rolling.server.document.resource import ResourceDocument
from rolling.server.document.stuff import StuffDocument
from rolling.server.extension import ServerSideDocument as Document


class CharacterDocument(Document):
    __tablename__ = "character"
    id = Column(String(255), primary_key=True)
    alive_since = Column(Integer, server_default="0", nullable=False)
    name = Column(String(255), nullable=False)
    world_col_i = Column(Integer, nullable=True)
    world_row_i = Column(Integer, nullable=True)
    zone_col_i = Column(Integer, nullable=True)
    zone_row_i = Column(Integer, nullable=True)

    # role play characteristics
    background_story = Column(Text, nullable=True)
    max_life_comp = Column(SqliteNumeric(10, 2), nullable=False)
    hunting_and_collecting_comp = Column(SqliteNumeric(10, 2), nullable=False)
    find_water_comp = Column(SqliteNumeric(10, 2), nullable=False)

    # role game play
    action_points = Column(SqliteNumeric(10, 2), nullable=False)
    life_points = Column(SqliteNumeric(10, 2), default=1.0)
    feel_thirsty = Column(Boolean, default=True)
    dehydrated = Column(Boolean, default=False)
    _effect_ids = Column(Text, default="")
    feel_hungry = Column(Boolean, default=True)
    starved = Column(Boolean, default=False)

    # transport
    shipped_stuff = relationship(
        StuffDocument, foreign_keys=[StuffDocument.carried_by_id], uselist=True
    )
    used_as_bag = relationship(
        StuffDocument, foreign_keys=[StuffDocument.used_as_bag_by_id], uselist=True
    )
    shipped_resource = relationship(
        ResourceDocument, foreign_keys=[ResourceDocument.carried_by_id], uselist=True
    )

    @property
    def is_alive(self) -> bool:
        return self.life_points > 0

    @property
    def effect_ids(self) -> typing.List[str]:
        return self._effect_ids.split(",")

    @effect_ids.setter
    def effect_ids(self, value: typing.List[str]) -> None:
        self._effect_ids = ",".join(value)
