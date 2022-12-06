# coding: utf-8
from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Numeric
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy.orm import relationship
import typing
import slugify

from sqlalchemy.sql.expression import null

from rolling.server.document.corpse import CorpseMixin
from rolling.server.document.resource import ResourceDocument
from rolling.server.document.stuff import StuffDocument
from rolling.server.extension import ServerSideDocument as Document


class CharacterDocument(CorpseMixin, Document):
    __tablename__ = "character"
    id = Column(String(255), primary_key=True)
    name = Column(String(255), nullable=False)

    @property
    def name_slug(self) -> str:
        return slugify.slugify(self.name)

    # role play characteristics
    background_story = Column(Text, nullable=False, default="")
    max_life_comp = Column(Numeric(10, 2, asdecimal=False), nullable=False, default=1.0)
    hunting_and_collecting_comp = Column(
        Numeric(10, 2, asdecimal=False), nullable=False, default=1.0
    )
    find_water_comp = Column(
        Numeric(10, 2, asdecimal=False), nullable=False, default=1.0
    )
    # percent of injured/died fighter before retreat
    attack_allowed_loss_rate = Column(Integer, nullable=False, default=30)
    defend_allowed_loss_rate = Column(Integer, nullable=False, default=30)

    # role game play
    action_points = Column(Numeric(10, 2, asdecimal=False), nullable=False)
    max_action_points = Column(Numeric(10, 2, asdecimal=False), nullable=False)
    life_points = Column(Numeric(10, 2, asdecimal=False), default=1.0)
    thirst = Column(Numeric(10, 2, asdecimal=False), nullable=False)
    hunger = Column(Numeric(10, 2, asdecimal=False), nullable=False)
    _effect_ids = Column(Text, default="")
    tiredness = Column(Integer, nullable=False, default=0)  # %

    # transport
    shipped_stuff = relationship(
        StuffDocument, foreign_keys=[StuffDocument.carried_by_id], uselist=True
    )
    used_as_bag = relationship(
        StuffDocument, foreign_keys=[StuffDocument.used_as_bag_by_id], uselist=True
    )
    used_as_primary_weapon = relationship(
        StuffDocument, foreign_keys=[StuffDocument.used_as_weapon_by_id], uselist=False
    )
    used_as_shield = relationship(
        StuffDocument, foreign_keys=[StuffDocument.used_as_shield_by_id], uselist=False
    )
    used_as_armor = relationship(
        StuffDocument, foreign_keys=[StuffDocument.used_as_armor_by_id], uselist=False
    )
    shipped_resource = relationship(
        ResourceDocument, foreign_keys=[ResourceDocument.carried_by_id], uselist=True
    )

    # Must match with data/character_avatar/{uuid}.png
    avatar_uuid = Column(String(255), nullable=True)
    avatar_is_validated = Column(Boolean(), nullable=False, default=False)

    account_id = Column(String(255), ForeignKey("account.id"), nullable=True)
    tracim_password = Column(String(255), nullable=True)
    tracim_user_id = Column(Integer(), nullable=True)
    tracim_home_space_id = Column(Integer(), nullable=True)
    spritesheet_identifiers = Column(Text(), nullable=True)
    spritesheet_body_type = Column(String(255), nullable=True)
    spritesheet_set = Column(Boolean(), default=False, nullable=False)

    @property
    def is_alive(self) -> bool:
        return self.life_points > 0

    @property
    def effect_ids(self) -> typing.List[str]:
        return self._effect_ids.split(",")

    @effect_ids.setter
    def effect_ids(self, value: typing.List[str]) -> None:
        value = [v for v in value if v]
        value = list(set(value))
        self._effect_ids = ",".join(value)


class FollowCharacterDocument(Document):
    __tablename__ = "follow_character"
    follower_id = Column(
        String(255), ForeignKey("character.id"), nullable=False, primary_key=True
    )
    followed_id = Column(
        String(255), ForeignKey("character.id"), nullable=False, primary_key=True
    )
    discreetly = Column(Boolean, default=False, nullable=False)
