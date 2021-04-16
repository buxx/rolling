#  coding: utf-8
from aiohttp import web
from aiohttp.web_app import Application
from aiohttp.web_request import Request
from hapic.data import HapicData
from sqlalchemy.orm.exc import NoResultFound
import typing

from guilang.description import Description
from guilang.description import Part
from guilang.description import Type
from rolling.exception import WrongStrInput
from rolling.kernel import Kernel
from rolling.model.character import AddOfferItemQuery
from rolling.model.character import CreateOfferBodyModel
from rolling.model.character import CreateOfferQueryModel
from rolling.model.character import DealOfferQueryModel
from rolling.model.character import GetCharacterPathModel
from rolling.model.character import GetOfferBodyModel
from rolling.model.character import GetOfferPathModel
from rolling.model.character import RemoveOfferItemPathModel
from rolling.model.character import SeeOfferPathModel
from rolling.model.character import SeeOfferQueryModel
from rolling.model.character import SeeOffersQueryModel
from rolling.model.character import UpdateOfferQueryModel
from rolling.model.resource import ResourceDescriptionModel
from rolling.model.stuff import StuffProperties
from rolling.server.controller.base import BaseController
from rolling.server.document.business import OfferDocument
from rolling.server.document.business import OfferItemDocument
from rolling.server.document.business import OfferItemPosition
from rolling.server.document.business import OfferOperand
from rolling.server.document.business import OfferStatus
from rolling.server.extension import hapic
from rolling.util import ExpectedQuantityContext
from rolling.util import InputQuantityContext

ALL_OF_THEM = "tous les éléments ci-dessous"
ONE_OF_THEM = "un des éléments ci-dessous"

operand_enum_to_str = {OfferOperand.OR: ONE_OF_THEM, OfferOperand.AND: ALL_OF_THEM}
operand_str_to_enum = {ONE_OF_THEM: OfferOperand.OR, ALL_OF_THEM: OfferOperand.AND}


class BusinessController(BaseController):
    def __init__(self, kernel: Kernel) -> None:
        super().__init__(kernel)

    @hapic.with_api_doc()
    @hapic.input_path(GetCharacterPathModel)
    @hapic.output_body(Description)
    async def main_page(self, request: Request, hapic_data: HapicData) -> Description:
        character = self._kernel.character_lib.get(hapic_data.path.character_id)

        # All character offers
        all_offer_count_from = self._kernel.business_lib.get_offers_query(
            [character.id],
            statuses=[OfferStatus.OPEN, OfferStatus.DRAFT, OfferStatus.CLOSED],
        ).count()

        # All character active offers
        active_offer_count_from = self._kernel.business_lib.get_offers_query(
            [character.id],
            statuses=[OfferStatus.OPEN],
        ).count()

        # All character transactions count
        all_transaction_count_from = self._kernel.business_lib.get_transactions_query_from(
            character.id, statuses=[OfferStatus.OPEN, OfferStatus.DRAFT]
        ).count()

        # All character transactions count where target character is in same zone
        all_transaction_count_is_here = self._kernel.business_lib.get_transactions_query_from(
            character.id,
            statuses=[OfferStatus.OPEN],
            alive_with_character_world_row_i=character.world_row_i,
            alive_with_character_world_col_i=character.world_col_i,
        ).count()

        other_here_character_ids = self._kernel.character_lib.get_zone_character_ids(
            row_i=character.world_row_i,
            col_i=character.world_col_i,
            alive=True,
            exclude_ids=[character.id],
        )

        # Other here character offers
        other_here_offers_count = self._kernel.business_lib.get_offers_query(
            other_here_character_ids,
            statuses=[OfferStatus.OPEN],
        ).count()

        # Other here characters transactions
        other_here_transactions_count = self._kernel.business_lib.get_transactions_query_for(
            character.id, statuses=[OfferStatus.OPEN]
        ).count()

        create_offer_url = f"/business/{hapic_data.path.character_id}/offers-create?permanent=1"
        create_transaction_url = f"/business/{hapic_data.path.character_id}/offers-create"
        return Description(
            title="Commerce",
            items=[
                Part(text="Que vous proposez", classes=["h2"]),
                Part(
                    columns=16,
                    items=[
                        Part(
                            is_column=True,
                            colspan=1,
                            items=[
                                Part(
                                    is_link=True,
                                    form_action=create_offer_url,
                                    label=create_offer_url,
                                    classes=["create"],
                                ),
                            ],
                        ),
                        Part(
                            is_column=True,
                            colspan=7,
                            items=[
                                Part(
                                    is_link=True,
                                    form_action=(
                                        f"/business/{hapic_data.path.character_id}/offers"
                                        f"?current_character_is_author=1&permanent=1"
                                    ),
                                    label=(
                                        f"{all_offer_count_from}({active_offer_count_from}) Offres"
                                    ),
                                ),
                            ],
                        ),
                        Part(
                            is_column=True,
                            colspan=1,
                            items=[
                                Part(
                                    is_link=True,
                                    form_action=create_transaction_url,
                                    label=create_transaction_url,
                                    classes=["create"],
                                ),
                            ],
                        ),
                        Part(
                            is_column=True,
                            colspan=7,
                            items=[
                                Part(
                                    is_link=True,
                                    form_action=(
                                        f"/business/{hapic_data.path.character_id}/offers"
                                        f"?current_character_is_author=1&permanent=0"
                                    ),
                                    label=(
                                        f"{all_transaction_count_from}"
                                        f"({all_transaction_count_is_here}) Propositions"
                                    ),
                                ),
                            ],
                        ),
                    ],
                ),
                Part(text="Que l'on vous propose", classes=["h2"]),
                Part(
                    columns=2,
                    items=[
                        Part(
                            is_column=True,
                            colspan=1,
                            items=[
                                Part(
                                    is_link=True,
                                    form_action=(
                                        f"/business/{hapic_data.path.character_id}/offers"
                                        f"?current_character_is_with=1&permanent=1"
                                    ),
                                    label=(f"{other_here_offers_count} Offres"),
                                ),
                            ],
                        ),
                        Part(
                            is_column=True,
                            colspan=1,
                            items=[
                                Part(
                                    is_link=True,
                                    form_action=(
                                        f"/business/{hapic_data.path.character_id}/offers"
                                        f"?current_character_is_with=1&permanent=0"
                                    ),
                                    label=(f"{other_here_transactions_count} Propositions"),
                                ),
                            ],
                        ),
                    ],
                ),
            ],
            can_be_back_url=True,
        )

    @hapic.with_api_doc()
    @hapic.input_path(GetCharacterPathModel)
    @hapic.input_query(SeeOffersQueryModel)
    @hapic.output_body(Description)
    async def offers(self, request: Request, hapic_data: HapicData) -> Description:
        current_character_is_author = hapic_data.query.current_character_is_author
        current_character_is_with = hapic_data.query.current_character_is_with
        permanent = hapic_data.query.permanent
        assert current_character_is_author or current_character_is_with

        query = self._kernel.business_lib.get_offers_query(
            [hapic_data.path.character_id],
        ).filter(OfferDocument.permanent == bool(permanent))

        if current_character_is_author:
            query = query.filter(
                OfferDocument.status.in_(
                    [s.value for s in [OfferStatus.OPEN, OfferStatus.DRAFT, OfferStatus.CLOSED]]
                )
            )
        elif current_character_is_with:
            query = query.filter(OfferDocument.status.in_([s.value for s in [OfferStatus.OPEN]]))

        text = None
        if current_character_is_author and permanent:
            text = "Ci-dessous, vos offres"
        elif current_character_is_author and not permanent:
            text = "Ci-dessous, vos propositions"
        elif current_character_is_with and permanent:
            text = "Ci-dessous, les offres disponibles"
        elif current_character_is_with and not permanent:
            text = "Ci-dessous, les propositions qui vous sont faites"
        assert text

        offers: typing.List[OfferDocument] = query.all()
        parts: typing.List[Part] = [Part(text=text)]

        for offer in offers:
            offer_name = None
            if current_character_is_author and permanent:
                offer_name = (
                    f"{offer.title}"
                    f"{' (innactive)' if offer.status != OfferStatus.OPEN.value else ''}"
                )
            elif current_character_is_author and not permanent:
                assert offer.with_character_id
                with_character = self._kernel.character_lib.get(offer.with_character_id)
                offer_name = f"({with_character.name}) {offer.title}"
            elif current_character_is_with and permanent:
                offer_name = f"{offer.title}"
            elif current_character_is_with and not permanent:
                from_character = self._kernel.character_lib.get(offer.character_id)
                offer_name = f"({from_character.id}) {offer.title}"
            assert offer_name

            parts.append(
                Part(
                    label=offer_name,
                    is_link=True,
                    form_action=f"/business/{hapic_data.path.character_id}/offers/{offer.id}",
                )
            )

        return Description(
            title="Commerce: vos offres",
            items=parts,
            can_be_back_url=True,
            back_url=f"/business/{hapic_data.path.character_id}",
        )

    # @hapic.with_api_doc()
    # @hapic.input_path(GetCharacterPathModel)
    # @hapic.output_body(Description)
    # async def transactions(self, request: Request, hapic_data: HapicData) -> Description:
    #     transactions: typing.List[OfferDocument] = self._kernel.business_lib.get_transactions_query(
    #         hapic_data.path.character_id
    #     ).all()
    #     parts: typing.List[Part] = []
    #
    #     for offer in transactions:
    #         form_action = f"/business/{hapic_data.path.character_id}/offers/{offer.id}"
    #         state = " (X)"
    #         is_new = ""
    #         with_info = f" (avec {offer.to_character.name})"
    #         if offer.status == OfferStatus.OPEN.value:
    #             state = " (V)"
    #
    #         if offer.with_character_id == hapic_data.path.character_id:
    #             state = ""
    #             form_action = (
    #                 f"/business/{hapic_data.path.character_id}"
    #                 f"/see-offer/{offer.character_id}/{offer.id}?mark_as_read=1"
    #             )
    #             with_info = f" (de {offer.from_character.name})"
    #
    #         if not offer.read and offer.with_character_id == hapic_data.path.character_id:
    #             is_new = "*"
    #
    #         parts.append(
    #             Part(
    #                 label=f"{is_new}{offer.title}{state}{with_info}",
    #                 is_link=True,
    #                 form_action=form_action,
    #             )
    #         )
    #
    #     return Description(
    #         title="Commerce: vos transaction avec des personnes",
    #         items=parts,
    #         back_url=f"/business/{hapic_data.path.character_id}/offers",
    #         can_be_back_url=True,
    #     )

    @hapic.with_api_doc()
    @hapic.input_path(GetOfferPathModel)
    @hapic.input_query(UpdateOfferQueryModel)
    @hapic.input_body(GetOfferBodyModel)
    @hapic.handle_exception(NoResultFound, http_code=404)
    @hapic.output_body(Description)
    async def offer(self, request: Request, hapic_data: HapicData) -> Description:
        # TODO: check owner
        offer: OfferDocument = self._kernel.business_lib.get_offer_query(
            hapic_data.path.offer_id
        ).one()

        if hapic_data.query.open:
            offer.status = OfferStatus.OPEN.value
            self._kernel.server_db_session.add(offer)
            self._kernel.server_db_session.commit()

        if hapic_data.query.close:
            offer.status = OfferStatus.CLOSED.value
            self._kernel.server_db_session.add(offer)
            self._kernel.server_db_session.commit()

        if hapic_data.body.request_operand:
            offer.request_operand = operand_str_to_enum[hapic_data.body.request_operand].value
            self._kernel.server_db_session.add(offer)
            self._kernel.server_db_session.commit()

        if hapic_data.body.offer_operand:
            offer.offer_operand = operand_str_to_enum[hapic_data.body.offer_operand].value
            self._kernel.server_db_session.add(offer)
            self._kernel.server_db_session.commit()

        form_parts = self._produce_offer_parts(
            hapic_data.path.character_id, hapic_data.path.character_id, offer, editing=True
        )
        here_url = f"/business/{hapic_data.path.character_id}/offers/{offer.id}?"

        parts = []
        if offer.status == OfferStatus.OPEN.value:
            parts.append(Part(label="Désactiver", is_link=True, form_action=here_url + "&close=1"))
        else:
            parts.append(Part(label="Activer", is_link=True, form_action=here_url + "&open=1"))

        back_url = (
            f"/business/{hapic_data.path.character_id}/offers"
            f"?current_character_is_author={int(offer.character_id == hapic_data.path.character_id)}"
            f"&current_character_is_with={int(offer.character_id != hapic_data.path.character_id)}"
            f"&permanent={int(offer.permanent)}"
        )
        return Description(
            title=offer.title,
            items=[
                Part(
                    is_form=True, form_action=here_url, items=form_parts, submit_label="Enregistrer"
                )
            ]
            + parts,
            back_url=back_url,
        )

    @hapic.with_api_doc()
    @hapic.input_path(SeeOfferPathModel)
    @hapic.input_query(SeeOfferQueryModel)
    @hapic.handle_exception(NoResultFound, http_code=404)
    @hapic.output_body(Description)
    async def see(self, request: Request, hapic_data: HapicData) -> Description:
        # TODO: check can see offer (same zone)
        offer: OfferDocument = self._kernel.business_lib.get_offer_query(
            hapic_data.path.offer_id
        ).one()
        offer_owner = self._kernel.character_lib.get_document(offer.character_id)

        if hapic_data.query.mark_as_read:
            self._kernel.business_lib.mark_as_read(offer.id)

        parts = self._produce_offer_parts(
            offer.character_id, hapic_data.path.character_id, offer, editing=False
        )

        if not self._kernel.business_lib.owner_can_deal(offer.id):
            parts.append(Part(label=f"{offer_owner.name} ne peut pas assurer cette opération"))

        if self._kernel.business_lib.character_can_deal(hapic_data.path.character_id, offer.id):
            parts.append(
                Part(
                    is_link=True,
                    label="Effectuer une transaction",
                    form_action=(
                        f"/business/{hapic_data.path.character_id}"
                        f"/see-offer/{offer.id}/{offer.id}/deal"
                    ),
                )
            )
        else:
            parts.append(Part(label="Vous ne possédez pas de quoi faire un marché"))

        with_str = ""
        if offer.to_character:
            with_str = f" ({offer.to_character.name})"

        title = f"{offer.title}{with_str}"

        return Description(
            title=title,
            items=parts,
            footer_links=[
                Part(
                    is_link=True,
                    label="Retourner sur la page Commerce",
                    form_action=f"/business/{hapic_data.path.character_id}",
                    classes=["primary"],
                )
            ],
            can_be_back_url=True,
        )

    @hapic.with_api_doc()
    @hapic.input_path(SeeOfferPathModel)
    @hapic.input_query(DealOfferQueryModel)
    @hapic.handle_exception(NoResultFound, http_code=404)
    @hapic.output_body(Description)
    async def deal(self, request: Request, hapic_data: HapicData) -> Description:
        # TODO: check can see offer (same zone)
        offer: OfferDocument = self._kernel.business_lib.get_offer_query(
            hapic_data.path.offer_id
        ).one()
        offer_owner = self._kernel.character_lib.get_document(offer.character_id)
        here_url = f"/business/{hapic_data.path.character_id}/see-offer/{offer.character_id}/{offer.id}/deal?"
        offer_url = (
            f"/business/{hapic_data.path.character_id}"
            f"/see-offer/{offer.character_id}/{offer.id}"
        )

        if not self._kernel.business_lib.owner_can_deal(offer.id):
            return Description(
                title=offer.title,
                items=[Part(text=f"{offer_owner.name} ne peut pas assurer cette opération")],
                footer_links=[
                    Part(
                        is_link=True,
                        label="Retourner sur la page Commerce",
                        form_action=f"/business/{hapic_data.path.character_id}",
                    ),
                    Part(
                        is_link=True,
                        label=f"Retourner sur la fiche de {offer.title}",
                        form_action=(
                            f"/business/{hapic_data.path.character_id}/see-offer/{offer.character_id}/{offer.id}"
                        ),
                        classes=["primary"],
                    ),
                ],
                can_be_back_url=True,
            )

        if not self._kernel.business_lib.character_can_deal(
            hapic_data.path.character_id, hapic_data.path.offer_id
        ):
            return Description(
                title=offer.title,
                items=[Part(text="Vous ne possédez pas ce qu'il faut pour faire ce marché")],
                footer_links=[
                    Part(
                        is_link=True,
                        label="Retourner sur la page Commerce",
                        form_action=f"/business/{hapic_data.path.character_id}",
                    ),
                    Part(
                        is_link=True,
                        label=f"Retourner sur la fiche de {offer.title}",
                        form_action=(
                            f"/business/{hapic_data.path.character_id}/see-offer/{offer.character_id}/{offer.id}"
                        ),
                        classes=["primary"],
                    ),
                ],
            )

        if (
            offer.request_operand == OfferOperand.AND.value
            and offer.offer_operand == OfferOperand.AND.value
        ):
            if hapic_data.query.confirm:
                self._kernel.business_lib.make_deal(offer.id, hapic_data.path.character_id)
                if not offer.permanent:
                    self._kernel.business_lib.changer_offer_status(offer.id, OfferStatus.ACCEPTED)
                return Description(
                    title=offer.title,
                    items=[Part(text="Marché effectué")],
                    footer_links=[
                        Part(
                            is_link=True,
                            label="Retourner sur la page Commerce",
                            form_action=f"/business/{hapic_data.path.character_id}",
                        ),
                        Part(
                            is_link=True,
                            label=f"Retourner sur la fiche de {offer.title}",
                            form_action=(
                                f"/business/{hapic_data.path.character_id}/see-offer/{offer.character_id}/{offer.id}"
                            ),
                            classes=["primary"],
                        ),
                    ],
                )
            return Description(
                title=offer.title,
                items=[
                    Part(
                        is_link=True,
                        form_action=here_url + "&confirm=1",
                        label="Je confirme vouloir faire ce marché",
                    )
                ],
                footer_links=[
                    Part(
                        is_link=True,
                        label="Retourner sur la page Commerce",
                        form_action=f"/business/{hapic_data.path.character_id}",
                    ),
                    Part(
                        is_link=True,
                        label=f"Retourner sur la fiche de {offer.title}",
                        form_action=(
                            f"/business/{hapic_data.path.character_id}/see-offer/{offer.character_id}/{offer.id}"
                        ),
                        classes=["primary"],
                    ),
                ],
            )

        if offer.request_items:
            if (
                offer.request_operand == OfferOperand.OR.value
                and not hapic_data.query.request_item_id
            ):
                parts = []
                for item in offer.request_items:
                    parts.append(
                        Part(
                            is_link=True,
                            label=f"Faire ce marché et donner {item.get_name(self._kernel, True)}",
                            form_action=here_url + f"&request_item_id={item.id}",
                        )
                    )
                return Description(
                    title=offer.title,
                    items=parts,
                    footer_links=[
                        Part(
                            is_link=True,
                            label="Retourner sur la page Commerce",
                            form_action=f"/business/{hapic_data.path.character_id}",
                        ),
                        Part(
                            is_link=True,
                            label=f"Retourner sur la fiche de {offer.title}",
                            form_action=(
                                f"/business/{hapic_data.path.character_id}/see-offer/{offer.character_id}/{offer.id}"
                            ),
                            classes=["primary"],
                        ),
                    ],
                    can_be_back_url=True,
                )

        if offer.offer_operand == OfferOperand.OR.value and not hapic_data.query.offer_item_id:
            parts = []
            request_item_str = (
                f"request_item_id={hapic_data.query.request_item_id}"
                if hapic_data.query.request_item_id
                else ""
            )
            for item in offer.offer_items:
                if self._kernel.business_lib.have_item(offer.character_id, item.id):
                    parts.append(
                        Part(
                            is_link=True,
                            label=f"Faire ce marché et obtenir {item.get_name(self._kernel, True)}",
                            form_action=(
                                here_url + f"&{request_item_str}" f"&offer_item_id={item.id}"
                            ),
                        )
                    )
            return Description(
                title=offer.title,
                items=parts,
                footer_links=[
                    Part(
                        is_link=True,
                        label="Retourner sur la page Commerce",
                        form_action=f"/business/{hapic_data.path.character_id}",
                    ),
                    Part(
                        is_link=True,
                        label=f"Retourner sur la fiche de {offer.title}",
                        form_action=(
                            f"/business/{hapic_data.path.character_id}/see-offer/{offer.character_id}/{offer.id}"
                        ),
                        classes=["primary"],
                    ),
                ],
            )

        self._kernel.business_lib.make_deal(
            offer.id,
            hapic_data.path.character_id,
            request_item_id=hapic_data.query.request_item_id,
            offer_item_id=hapic_data.query.offer_item_id,
        )

        footer_links = [
            Part(
                is_link=True,
                label="Retourner sur la page Commerce",
                form_action=f"/business/{hapic_data.path.character_id}",
                classes=["primary"],
            )
        ]

        if not offer.permanent:
            self._kernel.business_lib.changer_offer_status(offer.id, OfferStatus.ACCEPTED)
        else:
            footer_links.append(
                Part(
                    is_link=True,
                    label=f"Retourner sur la fiche de {offer.title}",
                    form_action=(
                        f"/business/{hapic_data.path.character_id}/see-offer/{offer.character_id}/{offer.id}"
                    ),
                )
            )

        return Description(
            title=offer.title, items=[Part(text="Marché effectué")], footer_links=footer_links
        )

    @hapic.with_api_doc()
    @hapic.input_path(GetCharacterPathModel)
    @hapic.input_query(CreateOfferQueryModel)
    @hapic.input_body(CreateOfferBodyModel)
    @hapic.output_body(Description)
    async def create(self, request: Request, hapic_data: HapicData) -> Description:
        character = self._kernel.character_lib.get(hapic_data.path.character_id)

        if not hapic_data.query.permanent:
            if hapic_data.query.with_character_id:
                # FIXME BS NOW: code it
                with_character = self._kernel.character_lib.get(hapic_data.query.with_character_id)
                title = f"Faire une proposition à {with_character.name}"
                form_action = (
                    f"/business/{character.id}/offers-create"
                    f"?with_character_id={with_character.id}"
                )
            else:
                parts = []
                here_characters = self._kernel.character_lib.get_zone_characters(
                    row_i=character.world_row_i,
                    col_i=character.world_col_i,
                    alive=True,
                    exclude_ids=[character.id],
                )
                for here_character in here_characters:
                    parts.append(
                        Part(
                            form_action=(
                                f"/business/{character.id}/offers-create"
                                f"?with_character_id={here_character.id}"
                            ),
                            label=here_character.name,
                        )
                    )
                if not here_characters:
                    parts.append(Part(text="Aucun personnage présent ici !"))
                return Description(
                    title="Faire une proposition",
                    items=[
                        Part(text="A qui faire cette proposition ?"),
                    ]
                    + parts,
                )
        else:
            title = "Créer une offre"
            form_action = f"/business/{character.id}/offers-create?permanent=1"

        if hapic_data.body.title:
            offer = self._kernel.business_lib.create_draft(
                character.id,
                hapic_data.body.title,
                permanent=hapic_data.query.permanent,
                with_character_id=hapic_data.query.with_character_id,
            )
            return Description(redirect=f"/business/{character.id}/offers/{offer.id}")

        return Description(
            title=title,
            items=[
                Part(
                    is_form=True,
                    form_action=form_action,
                    items=[
                        Part(
                            label="Veuillez choisir un nom pour cette offre",
                            name="title",
                            type_=Type.STRING,
                        )
                    ],
                )
            ],
        )

    def _produce_offer_parts(
        self, owner_id: str, character_id: str, offer: OfferDocument, editing: bool = False
    ) -> typing.List[Part]:
        request_item_parts: typing.List[Part] = []
        offer_item_parts: typing.List[Part] = []

        item: OfferItemDocument
        for item in offer.request_items:
            is_link = editing
            form_action = (
                f"/business/{owner_id}/offers/{offer.id}/remove-item/{item.id}" if editing else None
            )
            item_name = item.get_name(self._kernel, quantity=True)
            have_str = ""
            if not editing:
                if self._kernel.business_lib.have_item(character_id, item.id):
                    have_str = "(V) "
                else:
                    have_str = "(X) "
            item_name = item_name if editing else f"{have_str}{item_name}"
            request_item_parts.append(
                Part(label=item_name, is_link=is_link, form_action=form_action)
            )

        if editing:
            request_item_parts.append(
                Part(
                    label="...",
                    is_link=True,
                    form_action=(
                        f"/business/{owner_id}/offers/{offer.id}"
                        f"/add-item?position={OfferItemPosition.REQUEST.value}"
                    ),
                )
            )

        for item in offer.offer_items:
            form_action = (
                f"/business/{owner_id}/offers/{offer.id}/remove-item/{item.id}" if editing else None
            )
            item_name = item.get_name(self._kernel, quantity=True)
            have_str = ""
            if editing:
                if not self._kernel.business_lib.have_item(owner_id, item.id):
                    have_str = "(X) "
            else:
                if not self._kernel.business_lib.have_item(owner_id, item.id):
                    have_str = "(!) "
            item_name = f"{have_str}{item_name}"
            offer_item_parts.append(Part(label=item_name, is_link=editing, form_action=form_action))

        if editing:
            offer_item_parts.append(
                Part(
                    label="...",
                    is_link=True,
                    form_action=(
                        f"/business/{owner_id}/offers/{offer.id}"
                        f"/add-item?position={OfferItemPosition.OFFER.value}"
                    ),
                )
            )

        if editing:
            parts: typing.List[Part] = (
                [
                    Part(text="Eléments que vous demandez"),
                    Part(
                        name="request_operand",
                        choices=[ONE_OF_THEM, ALL_OF_THEM],
                        value=operand_enum_to_str[OfferOperand(offer.request_operand)],
                    ),
                ]
                + request_item_parts
                + [
                    Part(text="Eléments que vous donnez"),
                    Part(
                        name="offer_operand",
                        choices=[ONE_OF_THEM, ALL_OF_THEM],
                        value=operand_enum_to_str[OfferOperand(offer.offer_operand)],
                    ),
                ]
                + offer_item_parts
            )
        else:
            request_operand_str = operand_enum_to_str[OfferOperand(offer.request_operand)]
            offer_operand_str = operand_enum_to_str[OfferOperand(offer.offer_operand)]
            parts: typing.List[Part] = (
                [Part(text=f"Eléments demandé(s) ({request_operand_str})")]
                + request_item_parts
                + [Part(text=f"Eléments donné(s) ({offer_operand_str})")]
                + offer_item_parts
            )

        return parts

    @hapic.with_api_doc()
    @hapic.input_path(GetOfferPathModel)
    @hapic.input_query(AddOfferItemQuery)
    @hapic.handle_exception(NoResultFound, http_code=404)
    @hapic.handle_exception(WrongStrInput, http_code=400)
    @hapic.output_body(Description)
    async def add_item(self, request: Request, hapic_data: HapicData) -> Description:
        # TODO: check owner
        offer: OfferDocument = self._kernel.business_lib.get_offer_query(
            hapic_data.path.offer_id
        ).one()
        here_url = (
            f"/business/{hapic_data.path.character_id}/offers/{offer.id}"
            f"/add-item?position={hapic_data.query.position.value}"
        )

        if hapic_data.query.position == OfferItemPosition.REQUEST:
            title = f"Aouter un élément demandé à {offer.title}"
        else:
            title = f"Ajouter un élément échangé à {offer.title}"

        # TODO: compute it at startup in config ?
        resource_by_name: typing.Dict[str, ResourceDescriptionModel] = {}
        stuff_by_name: typing.Dict[str, StuffProperties] = {}
        for resource_description in self._kernel.game.config.resources.values():
            unit_str = self._kernel.translation.get(resource_description.unit)
            resource_by_name[f"{resource_description.name} ({unit_str})"] = resource_description
        for stuff_properties in self._kernel.game.stuff_manager.items:
            stuff_by_name[f"{stuff_properties.name} (unité)"] = stuff_properties

        # compatible for "pick from inventory" params
        quantity = None
        resource_id = None
        stuff_id = None

        if hapic_data.query.quantity:
            quantity = hapic_data.query.quantity

        if hapic_data.query.resource_quantity:
            quantity = hapic_data.query.resource_quantity

        if hapic_data.query.stuff_quantity:
            quantity = hapic_data.query.stuff_quantity

        if hapic_data.query.resource_id:
            resource_id = hapic_data.query.resource_id

        if hapic_data.query.stuff_id:
            stuff_id = hapic_data.query.stuff_id

        if hapic_data.query.value:
            if hapic_data.query.value in resource_by_name:
                resource_id = resource_by_name[hapic_data.query.value].id
            elif hapic_data.query.value in stuff_by_name:
                stuff_id = stuff_by_name[hapic_data.query.value].id

        if quantity and (resource_id or stuff_id):
            raw_quantity = quantity
            if resource_id:
                self._kernel.business_lib.add_item(
                    offer.id,
                    resource_id=resource_id,
                    quantity=raw_quantity,
                    position=hapic_data.query.position,
                )
            elif stuff_id:
                self._kernel.business_lib.add_item(
                    offer.id,
                    stuff_id=stuff_id,
                    quantity=int(raw_quantity),
                    position=hapic_data.query.position,
                )
            else:
                raise WrongStrInput(f"Unknown '{hapic_data.query.value}'")

            return Description(
                redirect=f"/business/{hapic_data.path.character_id}/offers/{offer.id}"
            )

        parts = []
        if not quantity and (resource_id or stuff_id):
            parts.append(
                Part(
                    text=(
                        "Vous devez choisir une quantité ! "
                        "(Veuillez saisir à nouveau l'objet ou la ressource)"
                    ),
                    classes=["error"],
                )
            )

        return Description(
            title=title,
            items=[
                Part(
                    is_form=True,
                    form_action=here_url,
                    form_values_in_query=True,
                    items=parts
                    + [
                        Part(
                            label="Sélectionnez une ressource ou un object",
                            name="value",
                            choices=list(
                                set(list(stuff_by_name.keys()) + list(resource_by_name.keys()))
                            ),
                            search_by_str=True,
                        ),
                        Part(label="Quantité ?", name="quantity", type_=Type.NUMBER),
                    ],
                ),
                Part(
                    label="Ou depuis votre inventaire",
                    is_link=True,
                    form_action=(
                        f"/_describe/character/{hapic_data.path.character_id}/pick_from_inventory"
                        f"?callback_url={here_url}"
                        f"&cancel_url={here_url}"
                        f"&title={title}"
                    ),
                ),
            ],
            footer_links=[
                Part(
                    is_link=True,
                    label="Retourner sur la page Commerce",
                    form_action=f"/business/{hapic_data.path.character_id}",
                ),
                Part(
                    is_link=True,
                    label=f"Retourner sur la fiche de {offer.title}",
                    form_action=(
                        f"/business/{hapic_data.path.character_id}/see-offer/{offer.character_id}/{offer.id}"
                    ),
                    classes=["primary"],
                ),
            ],
        )

    @hapic.with_api_doc()
    @hapic.input_path(RemoveOfferItemPathModel)
    @hapic.handle_exception(NoResultFound, http_code=404)
    @hapic.output_body(Description)
    async def remove_item(self, request: Request, hapic_data: HapicData) -> Description:
        # TODO: check is owner
        self._kernel.business_lib.get_offer_item_query(hapic_data.path.item_id).delete()
        return Description(
            redirect=f"/business/{hapic_data.path.character_id}/offers/{hapic_data.path.offer_id}"
        )

    def bind(self, app: Application) -> None:
        app.add_routes(
            [
                web.post("/business/{character_id}", self.main_page),
                web.post("/business/{character_id}/offers", self.offers),
                web.post("/business/{character_id}/offers-create", self.create),
                web.post("/business/{character_id}/offers/{offer_id}", self.offer),
                web.post("/business/{character_id}/see-offer/{owner_id}/{offer_id}", self.see),
                web.post(
                    "/business/{character_id}/see-offer/{owner_id}/{offer_id}/deal", self.deal
                ),
                web.post("/business/{character_id}/offers/{offer_id}/add-item", self.add_item),
                web.post(
                    "/business/{character_id}/offers/{offer_id}/remove-item/{item_id}",
                    self.remove_item,
                ),
                # web.post("/business/{character_id}/transactions", self.transactions),
                # web.post("/business/{character_id}/transactions/{offer_id}", self.transaction),
            ]
        )
