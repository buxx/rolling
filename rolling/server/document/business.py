# coding: utf-8
import enum
from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import Enum
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Numeric
from sqlalchemy import String
from sqlalchemy.orm import relationship
import typing

from rolling.server.document.character import CharacterDocument
from rolling.server.extension import ServerSideDocument as Document
from rolling.util import quantity_to_str

if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel


class OfferItemPosition(enum.Enum):
    REQUEST = "REQUEST"
    OFFER = "OFFER"


class OfferOperand(enum.Enum):
    AND = "AND"
    OR = "OR"


class OfferStatus(enum.Enum):
    DRAFT = "DRAFT"
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    ACCEPTED = "ACCEPTED"
    REFUSED = "REFUSED"


class OfferItemDocument(Document):
    __tablename__ = "offer_item"
    id = Column(Integer, autoincrement=True, primary_key=True)
    offer_id = Column(Integer, ForeignKey("offer.id"))
    position = Column(
        Enum(*[p.value for p in OfferItemPosition], name="offer_item__position"),
        nullable=False,
    )
    resource_id = Column(String(255), nullable=True)
    stuff_id = Column(String(255), nullable=True)
    quantity = Column(Numeric(12, 6, asdecimal=False), nullable=False, default=0.0)
    offer: "OfferDocument" = relationship("OfferDocument", back_populates="items")

    def get_name(self, kernel: "Kernel", quantity: bool = False) -> str:
        quantity_str = ""

        if self.resource_id:
            resource_properties = kernel.game.config.resources[self.resource_id]
            if quantity:
                quantity_str = quantity_to_str(
                    self.quantity, resource_properties.unit, kernel
                )
                quantity_str = f" ({quantity_str})"
            return f"{resource_properties.name}{quantity_str}"

        stuff_properties = kernel.game.stuff_manager.get_stuff_properties_by_id(
            self.stuff_id
        )
        if quantity:
            quantity_str = f" ({round(self.quantity)})"
        return f"{stuff_properties.name}{quantity_str}"


class OfferDocument(Document):
    __tablename__ = "offer"
    id = Column(Integer, autoincrement=True, primary_key=True)
    character_id = Column(String(255), ForeignKey("character.id"))
    title = Column(String(255), nullable=False)
    read = Column(Boolean, default=False)
    request_operand = Column(
        Enum(*[o.value for o in OfferOperand], name="request_operand"),
        nullable=False,
        default=OfferOperand.OR.value,
    )
    offer_operand = Column(
        Enum(*[o.value for o in OfferOperand], name="offer_operand"),
        nullable=False,
        default=OfferOperand.OR.value,
    )
    permanent = Column(Boolean, nullable=False, default=False)
    with_character_id = Column(String(255), ForeignKey("character.id"))
    status = Column(
        Enum(*[s.value for s in OfferStatus], name="status"),
        nullable=False,
        default=OfferStatus.DRAFT.value,
    )

    from_character = relationship(
        "CharacterDocument",
        foreign_keys=[character_id],
        primaryjoin=CharacterDocument.id == character_id,
    )
    to_character = relationship(
        "CharacterDocument",
        foreign_keys=[with_character_id],
        primaryjoin=CharacterDocument.id == with_character_id,
    )
    items: typing.List["OfferItemDocument"] = relationship(
        "OfferItemDocument",
        back_populates="offer",
        primaryjoin=OfferItemDocument.offer_id == id,
    )

    @property
    def request_items(self) -> typing.List[OfferItemDocument]:
        return [i for i in self.items if i.position == OfferItemPosition.REQUEST.value]

    @property
    def offer_items(self) -> typing.List[OfferItemDocument]:
        return [i for i in self.items if i.position == OfferItemPosition.OFFER.value]
