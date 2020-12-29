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
        offer_count = self._kernel.business_lib.get_offers_query(
            hapic_data.path.character_id,
            statuses=[OfferStatus.OPEN, OfferStatus.DRAFT, OfferStatus.CLOSED],
        ).count()
        transaction_count = self._kernel.business_lib.get_transactions_query(
            hapic_data.path.character_id
        ).count()

        transaction_label = f"Voir les transactions en attente ({transaction_count} en cours)"
        if (
            self._kernel.business_lib.get_incoming_transactions_query(hapic_data.path.character_id)
            .filter(OfferDocument.read == False)
            .count()
        ):
            transaction_label = f"*{transaction_label}"

        return Description(
            title="Commerce",
            items=[
                Part(
                    label=f"Voir les offres que vous proposez ({offer_count} en cours)",
                    is_link=True,
                    form_action=f"/business/{hapic_data.path.character_id}/offers",
                ),
                Part(
                    label=transaction_label,
                    is_link=True,
                    form_action=f"/business/{hapic_data.path.character_id}/transactions",
                ),
            ],
            can_be_back_url=True,
        )

    @hapic.with_api_doc()
    @hapic.input_path(GetCharacterPathModel)
    @hapic.output_body(Description)
    async def offers(self, request: Request, hapic_data: HapicData) -> Description:
        offers: typing.List[OfferDocument] = self._kernel.business_lib.get_offers_query(
            hapic_data.path.character_id,
            statuses=[OfferStatus.OPEN, OfferStatus.DRAFT, OfferStatus.CLOSED],
        ).all()
        parts: typing.List[Part] = [
            Part(
                label="Créer une nouvelle offre",
                is_link=True,
                form_action=f"/business/{hapic_data.path.character_id}/offers-create?permanent=1",
            ),
            Part(text="Ci-dessous les les offres existantes (X: innactive, V: active)"),
        ]

        for offer in offers:
            state = "X"
            if offer.status == OfferStatus.OPEN.value:
                state = "V"
            parts.append(
                Part(
                    label=f"({state}) {offer.title}",
                    is_link=True,
                    form_action=f"/business/{hapic_data.path.character_id}/offers/{offer.id}",
                )
            )

        return Description(
            title="Commerce: vos offres",
            items=parts,
            footer_links=[
                Part(
                    is_link=True,
                    label="Retourner sur la page Commerce",
                    form_action=f"/business/{hapic_data.path.character_id}",
                )
            ],
            can_be_back_url=True,
        )

    @hapic.with_api_doc()
    @hapic.input_path(GetCharacterPathModel)
    @hapic.output_body(Description)
    async def transactions(self, request: Request, hapic_data: HapicData) -> Description:
        transactions: typing.List[OfferDocument] = self._kernel.business_lib.get_transactions_query(
            hapic_data.path.character_id
        ).all()
        parts: typing.List[Part] = []

        for offer in transactions:
            form_action = f"/business/{hapic_data.path.character_id}/offers/{offer.id}"
            state = " (X)"
            is_new = ""
            with_info = f" (avec {offer.to_character.name})"
            if offer.status == OfferStatus.OPEN.value:
                state = " (V)"

            if offer.with_character_id == hapic_data.path.character_id:
                state = ""
                form_action = (
                    f"/business/{hapic_data.path.character_id}"
                    f"/see-offer/{offer.character_id}/{offer.id}?mark_as_read=1"
                )
                with_info = f" (de {offer.from_character.name})"

            if not offer.read and offer.with_character_id == hapic_data.path.character_id:
                is_new = "*"

            parts.append(
                Part(
                    label=f"{is_new}{offer.title}{state}{with_info}",
                    is_link=True,
                    form_action=form_action,
                )
            )

        return Description(
            title="Commerce: vos transaction avec des personnes",
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

        return Description(
            title=offer.title,
            items=[
                Part(
                    is_form=True, form_action=here_url, items=form_parts, submit_label="Enregistrer"
                )
            ]
            + parts,
            footer_links=[
                Part(
                    is_link=True,
                    label="Retourner sur la page Commerce",
                    form_action=f"/business/{hapic_data.path.character_id}",
                    classes=["primary"],
                )
            ],
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
        if hapic_data.query.with_character_id:
            # FIXME BS NOW: code it
            with_character = self._kernel.character_lib.get(hapic_data.query.with_character_id)
            title = f"Faire une offre à {with_character.name}"
            form_action = (
                f"/business/{hapic_data.path.character_id}/offers-create"
                f"?with_character_id={with_character.id}"
            )
        else:
            title = "Créer une offre"
            form_action = f"/business/{hapic_data.path.character_id}/offers-create?permanent=1"

        if hapic_data.body.title:
            offer = self._kernel.business_lib.create_draft(
                hapic_data.path.character_id,
                hapic_data.body.title,
                permanent=hapic_data.query.permanent,
                with_character_id=hapic_data.query.with_character_id,
            )
            return Description(
                redirect=f"/business/{hapic_data.path.character_id}/offers/{offer.id}"
            )

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
            footer_links=[
                Part(
                    is_link=True,
                    label="Retourner sur la page Commerce",
                    form_action=f"/business/{hapic_data.path.character_id}",
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
            parts: typing.List[Part] = [
                Part(text="Eléments que vous demandez"),
                Part(
                    name="request_operand",
                    choices=[ONE_OF_THEM, ALL_OF_THEM],
                    value=operand_enum_to_str[OfferOperand(offer.request_operand)],
                ),
            ] + request_item_parts + [
                Part(text="Eléments que vous donnez"),
                Part(
                    name="offer_operand",
                    choices=[ONE_OF_THEM, ALL_OF_THEM],
                    value=operand_enum_to_str[OfferOperand(offer.offer_operand)],
                ),
            ] + offer_item_parts
        else:
            request_operand_str = operand_enum_to_str[OfferOperand(offer.request_operand)]
            offer_operand_str = operand_enum_to_str[OfferOperand(offer.offer_operand)]
            parts: typing.List[Part] = [
                Part(text=f"Eléments demandé(s) ({request_operand_str})")
            ] + request_item_parts + [
                Part(text=f"Eléments donné(s) ({offer_operand_str})")
            ] + offer_item_parts

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
                web.post("/business/{character_id}/transactions", self.transactions),
                # web.post("/business/{character_id}/transactions/{offer_id}", self.transaction),
            ]
        )
