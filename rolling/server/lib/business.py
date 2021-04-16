# coding: utf-8
from sqlalchemy import and_
from sqlalchemy import or_
from sqlalchemy.orm import Query
import typing

from rolling.exception import RollingError
from rolling.server.document.business import OfferDocument
from rolling.server.document.business import OfferItemDocument
from rolling.server.document.business import OfferItemPosition
from rolling.server.document.business import OfferOperand
from rolling.server.document.business import OfferStatus
from rolling.server.document.event import EventDocument
from rolling.server.document.event import StoryPageDocument

if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel


class BusinessLib:
    def __init__(self, kernel: "Kernel") -> None:
        self._kernel = kernel

    def get_offers_query(
        self,
        character_ids: typing.List[str],
        statuses: typing.Optional[typing.List[OfferStatus]] = None,
    ) -> Query:
        query = self._kernel.server_db_session.query(OfferDocument).filter(
            OfferDocument.permanent == True,
            OfferDocument.character_id.in_(character_ids),
        )

        if statuses is not None:
            query = query.filter(OfferDocument.status.in_([s.value for s in statuses]))

        return query

    def get_offer_query(self, offer_id: int) -> Query:
        return self._kernel.server_db_session.query(OfferDocument).filter(
            OfferDocument.id == offer_id
        )

    def get_offer_item_query(self, item_id: int) -> Query:
        return self._kernel.server_db_session.query(OfferItemDocument).filter(
            OfferItemDocument.id == item_id
        )

    def get_transactions_query(self, character_id: str) -> Query:
        return self._kernel.server_db_session.query(OfferDocument).filter(
            OfferDocument.permanent == False,
            or_(
                and_(
                    OfferDocument.character_id == character_id,
                    OfferDocument.status.in_(
                        (OfferStatus.OPEN.value, OfferStatus.DRAFT.value, OfferStatus.CLOSED.value)
                    ),
                ),
                and_(
                    OfferDocument.with_character_id == character_id,
                    OfferDocument.status.in_((OfferStatus.OPEN.value,)),
                ),
            ),
        )

    def get_transactions_query_from(
        self,
        character_id: str,
        statuses: typing.List[OfferStatus],
        alive_with_character_world_row_i: typing.Optional[int] = None,
        alive_with_character_world_col_i: typing.Optional[int] = None,
    ) -> Query:
        query = self._kernel.server_db_session.query(OfferDocument).filter(
            OfferDocument.permanent == False,
            OfferDocument.character_id == character_id,
            OfferDocument.status.in_([s.value for s in statuses]),
        )

        if (
            alive_with_character_world_row_i is not None
            and alive_with_character_world_col_i is not None
        ):
            here_character_ids = self._kernel.character_lib.get_zone_character_ids(
                row_i=alive_with_character_world_row_i,
                col_i=alive_with_character_world_col_i,
                alive=True,
            )
            query = query.filter(OfferDocument.with_character_id.in_(here_character_ids))

        return query

    def get_transactions_query_for(
        self, character_id: str, statuses: typing.List[OfferStatus]
    ) -> Query:
        return self._kernel.server_db_session.query(OfferDocument).filter(
            OfferDocument.permanent == False,
            OfferDocument.with_character_id == character_id,
            OfferDocument.status.in_([s.value for s in statuses]),
        )

    def get_incoming_transactions_query(self, character_id: str) -> Query:
        return self._kernel.server_db_session.query(OfferDocument).filter(
            OfferDocument.with_character_id == character_id,
            OfferDocument.status.in_((OfferStatus.OPEN.value,)),
        )

    def create_draft(
        self,
        character_id: str,
        title: str,
        permanent: bool = False,
        with_character_id: typing.Optional[str] = None,
    ) -> OfferDocument:
        doc = OfferDocument(
            title=title,
            character_id=character_id,
            status=OfferStatus.DRAFT.value,
            permanent=permanent,
            with_character_id=with_character_id,
        )
        self._kernel.server_db_session.add(doc)
        self._kernel.server_db_session.commit()
        return doc

    def add_item(
        self,
        offer_id: int,
        quantity: typing.Union[float, int],
        position: OfferItemPosition,
        resource_id: typing.Optional[str] = None,
        stuff_id: typing.Optional[str] = None,
    ) -> OfferItemDocument:
        assert resource_id or stuff_id

        doc = OfferItemDocument(
            offer_id=offer_id,
            resource_id=resource_id,
            stuff_id=stuff_id,
            position=position.value,
            quantity=quantity,
        )
        self._kernel.server_db_session.add(doc)
        self._kernel.server_db_session.commit()
        return doc

    def have_item(self, character_id: str, item_id: int) -> bool:
        item: OfferItemDocument = self.get_offer_item_query(item_id).one()
        if item.resource_id:
            return self._kernel.resource_lib.have_resource(
                character_id=character_id, resource_id=item.resource_id, quantity=item.quantity
            )
        return (
            self._kernel.stuff_lib.get_stuff_count(
                character_id=character_id, stuff_id=item.stuff_id
            )
            >= item.quantity
        )

    def character_can_deal(self, character_id: str, offer_id: int) -> bool:
        offer: OfferDocument = self.get_offer_query(offer_id).one()
        item: OfferItemDocument
        request_items = [i for i in offer.items if i.position == OfferItemPosition.REQUEST.value]

        if not request_items:
            return True

        for item in request_items:
            have = self.have_item(character_id, item.id)
            if have and offer.request_operand == OfferOperand.OR.value:
                return True
            if not have and offer.request_operand == OfferOperand.AND.value:
                return False

        if offer.request_operand == OfferOperand.AND.value:
            return True
        return False

    def owner_can_deal(self, offer_id: int) -> bool:
        offer: OfferDocument = self.get_offer_query(offer_id).one()
        item: OfferItemDocument
        offer_items = [i for i in offer.items if i.position == OfferItemPosition.OFFER.value]

        if not offer_items:
            return True

        for item in offer_items:
            have = self.have_item(offer.character_id, item.id)
            if have and offer.request_operand == OfferOperand.OR.value:
                return True
            if not have and offer.request_operand == OfferOperand.AND.value:
                return False

        if offer.request_operand == OfferOperand.AND.value:
            return True
        return False

    def make_deal(
        self,
        offer_id: int,
        character_id: str,
        request_item_id: typing.Optional[int] = None,
        offer_item_id: typing.Optional[int] = None,
    ) -> None:
        offer: OfferDocument = self.get_offer_query(offer_id).one()
        request_items: typing.List[OfferItemDocument] = []
        offer_items: typing.List[OfferItemDocument] = []
        event_texts: typing.List[str] = ["Vous avez obtenu:"]

        if not self.character_can_deal(character_id, offer_id):
            raise RollingError(f"Character {character_id} cannot make deal {offer_id}")

        if offer.request_operand == OfferOperand.OR.value:
            if request_item_id:
                request_items.append(
                    next(i for i in offer.request_items if i.id == request_item_id)
                )
        else:
            request_items.extend(offer.request_items)

        if offer.offer_operand == OfferOperand.OR.value:
            if not offer_item_id:
                raise RollingError(f"Offer {offer_id} require an offer_item_id")
            offer_items.append(next(i for i in offer.offer_items if i.id == offer_item_id))
        else:
            offer_items.extend(offer.offer_items)

        def _deal_item(item: OfferItemDocument, giver_id: str, receiver_id: str) -> None:
            if item.resource_id:
                self._kernel.resource_lib.reduce_carried_by(
                    character_id=giver_id,
                    resource_id=item.resource_id,
                    quantity=float(item.quantity),
                    commit=False,
                )
                self._kernel.resource_lib.add_resource_to(
                    character_id=receiver_id,
                    resource_id=item.resource_id,
                    quantity=float(item.quantity),
                    commit=False,
                )
            if item.stuff_id:
                for _ in range(int(item.quantity)):
                    stuff = self._kernel.stuff_lib.get_first_carried_stuff(
                        character_id=giver_id, stuff_id=item.stuff_id
                    )
                    self._kernel.stuff_lib.un_use_stuff(stuff.id)  # TODO BS 20200719: test it
                    self._kernel.stuff_lib.set_carried_by(
                        stuff_id=stuff.id, character_id=receiver_id, commit=False
                    )

        for request_item in request_items:
            _deal_item(request_item, giver_id=character_id, receiver_id=offer.character_id)
            event_texts.append(f"- {request_item.get_name(self._kernel, quantity=True)}")

        event_texts.append("Vous avez donné:")
        for offer_item in offer_items:
            _deal_item(offer_item, giver_id=offer.character_id, receiver_id=character_id)
            event_texts.append(f"- {offer_item.get_name(self._kernel, quantity=True)}")

        self._kernel.character_lib.add_event(
            offer.character_id,
            title=f"Un affaire à été conclu: {offer.title}",
            story_pages=[StoryPageDocument(text="\n".join(event_texts))],
        )
        self._kernel.server_db_session.commit()

    def mark_as_read(self, offer_id: int) -> None:
        self.get_offer_query(offer_id).update({"read": True})
        self._kernel.server_db_session.commit()

    def changer_offer_status(self, offer_id: int, status: OfferStatus, commit: bool = True) -> None:
        offer: OfferDocument = self.get_offer_query(offer_id).one()
        offer.status = status.value
        self._kernel.server_db_session.add(offer)
        if commit:
            self._kernel.server_db_session.commit()
