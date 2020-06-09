# coding: utf-8
import typing

from aiohttp import ClientResponse
from aiohttp.test_utils import TestClient
import pytest

from rolling.kernel import Kernel
from rolling.model.character import CharacterModel
from rolling.server.controller.business import ALL_OF_THEM
from rolling.server.controller.business import ONE_OF_THEM
from rolling.server.document.business import OfferDocument
from rolling.server.document.business import OfferItemDocument
from rolling.server.document.business import OfferItemPosition
from rolling.server.document.business import OfferOperand
from rolling.server.document.business import OfferStatus
from rolling.server.document.universe import UniverseStateDocument
from tests.fixtures import create_stuff
from tests.fixtures import description_serializer

EXPECTED_PLASTIC_BOTTLE_NAME = "Plastic bottle (1)"
EXPECTED_PLASTIC_BOTTLE_NAME_ = "(!) Plastic bottle (1)"


def _add_items(kernel: Kernel, offer_id: int) -> None:
    kernel.server_db_session.add(
        OfferItemDocument(
            offer_id=offer_id,
            position=OfferItemPosition.REQUEST.value,
            resource_id="RED_WINE",
            quantity=1.5,
        )
    )
    kernel.server_db_session.add(
        OfferItemDocument(
            offer_id=offer_id,
            position=OfferItemPosition.REQUEST.value,
            stuff_id="STONE_HAXE",
            quantity=1,
        )
    )
    kernel.server_db_session.add(
        OfferItemDocument(
            offer_id=offer_id,
            position=OfferItemPosition.OFFER.value,
            resource_id="WOOD",
            quantity=0.5,
        )
    )
    kernel.server_db_session.add(
        OfferItemDocument(
            offer_id=offer_id,
            position=OfferItemPosition.OFFER.value,
            stuff_id="LEATHER_JACKET",
            quantity=1,
        )
    )


@pytest.fixture
def xena_permanent_or_offer(worldmapc_xena_model: CharacterModel, worldmapc_kernel: Kernel):
    offer_doc = OfferDocument(
        character_id=worldmapc_xena_model.id,
        title="OfferTitle",
        request_operand=OfferOperand.OR.value,
        offer_operand=OfferOperand.OR.value,
        permanent=True,
        status=OfferStatus.OPEN.value,
    )
    worldmapc_kernel.server_db_session.add(offer_doc)
    worldmapc_kernel.server_db_session.commit()
    _add_items(worldmapc_kernel, offer_doc.id)
    worldmapc_kernel.server_db_session.commit()
    return offer_doc


@pytest.fixture
def xena_permanent_and_offer(worldmapc_xena_model: CharacterModel, worldmapc_kernel: Kernel):
    offer_doc = OfferDocument(
        character_id=worldmapc_xena_model.id,
        title="OfferTitle",
        request_operand=OfferOperand.AND.value,
        offer_operand=OfferOperand.AND.value,
        permanent=True,
        status=OfferStatus.OPEN.value,
    )
    worldmapc_kernel.server_db_session.add(offer_doc)
    worldmapc_kernel.server_db_session.commit()
    _add_items(worldmapc_kernel, offer_doc.id)
    worldmapc_kernel.server_db_session.commit()
    return offer_doc


class TestBusiness:
    async def _assert_owned_offers(
        self,
        kernel: Kernel,
        web: TestClient,
        character: CharacterModel,
        count: int,
        names: typing.Optional[typing.List[str]] = None,
    ) -> None:
        names = names or []

        # main page
        resp: ClientResponse = await web.post(f"/business/{character.id}")
        assert 200 == resp.status
        descr = description_serializer.load(await resp.json())
        item_labels = [i.label for i in descr.items]

        assert f"Voir les offres que vous proposez ({count} en cours)" in item_labels

        if not names:
            return

        # offers page
        resp: ClientResponse = await web.post(f"/business/{character.id}/offers")
        assert 200 == resp.status
        descr = description_serializer.load(await resp.json())
        item_labels = [i.label for i in descr.items]

        for name in names:
            assert next(l for l in item_labels if name in str(l))

    async def _assert_edit_offer(
        self,
        kernel: Kernel,
        web: TestClient,
        character: CharacterModel,
        offer_id: int,
        request_operand_str: str = ONE_OF_THEM,
        request_item_names: typing.Optional[typing.List[str]] = None,
        request_item_names_not: typing.Optional[typing.List[str]] = None,
        offer_operand_str: str = ONE_OF_THEM,
        offer_item_names: typing.Optional[typing.List[str]] = None,
        offer_item_names_not: typing.Optional[typing.List[str]] = None,
        open_: bool = False,
    ) -> None:
        request_item_names = request_item_names or []
        request_item_names_not = request_item_names_not or []
        offer_item_names = offer_item_names or []
        offer_item_names_not = offer_item_names_not or []

        resp = await web.post(f"/business/{character.id}/offers/{offer_id}")
        assert 200 == resp.status
        descr = description_serializer.load(await resp.json())

        form_item_by_name = {i.name: i for i in descr.items[0].items}
        form_item_labels = [i.label for i in descr.items[0].items]

        assert form_item_by_name["request_operand"].value == request_operand_str
        assert form_item_by_name["offer_operand"].value == offer_operand_str

        for request_item_name in request_item_names:
            assert request_item_name in form_item_labels

        for offer_item_name in offer_item_names:
            assert offer_item_name in form_item_labels

        for request_item_name_not in request_item_names_not:
            assert request_item_name_not not in form_item_labels

        for offer_item_name_not in offer_item_names_not:
            assert offer_item_name_not not in form_item_labels

        if not open_:
            assert "Activer" == descr.items[1].label
        else:
            assert "Désactiver" == descr.items[1].label

    async def _assert_read_offer(
        self,
        kernel: Kernel,
        web: TestClient,
        owner: CharacterModel,
        character: CharacterModel,
        offer_id: int,
        request_operand_str: str = ONE_OF_THEM,
        have_not_item_names: typing.Optional[typing.List[str]] = None,
        have_item_names: typing.Optional[typing.List[str]] = None,
        offer_operand_str: str = ONE_OF_THEM,
        offer_item_names: typing.Optional[typing.List[str]] = None,
        owner_can_make_deal: bool = True,
        can_make_deal: bool = False,
    ) -> None:
        have_not_item_names = have_not_item_names or []
        have_item_names = have_item_names or []
        offer_item_names = offer_item_names or []

        resp = await web.post(f"/business/{character.id}/see-offer/{owner.id}/{offer_id}")
        assert 200 == resp.status
        descr = description_serializer.load(await resp.json())

        form_item_labels = [i.label or i.text for i in descr.items]

        assert f"Eléments demandé(s) ({request_operand_str})" in form_item_labels
        assert f"Eléments donné(s) ({offer_operand_str})" in form_item_labels

        for have_not_item_name in have_not_item_names:
            assert f"(X) {have_not_item_name}" in form_item_labels

        for have_item_name in have_item_names:
            assert f"(V) {have_item_name}" in form_item_labels

        for offer_item_name in offer_item_names:
            assert offer_item_name in form_item_labels

        if owner_can_make_deal:
            if can_make_deal:
                assert "Effectuer une transaction" in form_item_labels
            else:
                assert "Vous ne possédez pas de quoi faire un marché" in form_item_labels
        else:
            assert f"{owner.name} ne peut pas assurer cette opération"

    async def test_create_offer__nominal_case(
        self,
        worldmapc_xena_model: CharacterModel,
        worldmapc_web_app: TestClient,
        worldmapc_kernel: Kernel,
    ) -> None:
        xena = worldmapc_xena_model
        kernel = worldmapc_kernel
        web = worldmapc_web_app

        await self._assert_owned_offers(kernel, web, xena, count=0)

        resp = await web.post(f"/business/{xena.id}/offers-create?permanent=1")
        assert 200 == resp.status

        resp = await web.post(
            f"/business/{xena.id}/offers-create?permanent=1", json={"title": "My offer"}
        )
        assert 200 == resp.status
        descr = description_serializer.load(await resp.json())
        assert descr.redirect == f"/business/{xena.id}/offers/1"
        await self._assert_owned_offers(kernel, web, xena, count=1, names=["My offer"])
        await self._assert_edit_offer(
            kernel,
            web,
            xena,
            offer_id=1,
            request_operand_str=ONE_OF_THEM,
            request_item_names=[],
            offer_operand_str=ONE_OF_THEM,
            offer_item_names=[],
            open_=False,
        )

    async def test_create_offer__change_operands(
        self,
        worldmapc_xena_model: CharacterModel,
        worldmapc_web_app: TestClient,
        worldmapc_kernel: Kernel,
    ) -> None:
        xena = worldmapc_xena_model
        kernel = worldmapc_kernel
        web = worldmapc_web_app

        await self._assert_owned_offers(kernel, web, xena, count=0)
        # see test_create_offer__nominal_case if in error
        assert (
            await web.post(
                f"/business/{xena.id}/offers-create?permanent=1", json={"title": "My offer"}
            )
        ).status == 200

        assert (
            await web.post(
                f"/business/{xena.id}/offers/{1}",
                json={"request_operand": ALL_OF_THEM, "offer_operand": ALL_OF_THEM},
            )
        ).status == 200

        await self._assert_edit_offer(
            kernel,
            web,
            xena,
            offer_id=1,
            request_operand_str=ALL_OF_THEM,
            offer_operand_str=ALL_OF_THEM,
        )

    async def test_create_offer__open_close(
        self,
        worldmapc_xena_model: CharacterModel,
        worldmapc_web_app: TestClient,
        worldmapc_kernel: Kernel,
    ) -> None:
        xena = worldmapc_xena_model
        kernel = worldmapc_kernel
        web = worldmapc_web_app

        await self._assert_owned_offers(kernel, web, xena, count=0)
        # see test_create_offer__nominal_case if in error
        assert (
            await web.post(
                f"/business/{xena.id}/offers-create?permanent=1", json={"title": "My offer"}
            )
        ).status == 200

        assert (await web.post(f"/business/{xena.id}/offers/{1}?open=1")).status == 200
        await self._assert_edit_offer(kernel, web, xena, offer_id=1, open_=True)
        await self._assert_owned_offers(kernel, web, xena, count=1, names=["(V) My offer"])
        assert (await web.post(f"/business/{xena.id}/offers/{1}?close=1")).status == 200
        await self._assert_edit_offer(kernel, web, xena, offer_id=1, open_=False)
        await self._assert_owned_offers(kernel, web, xena, count=1, names=["(X) My offer"])

    async def test_add_items__check_form(
        self,
        worldmapc_xena_model: CharacterModel,
        worldmapc_web_app: TestClient,
        worldmapc_kernel: Kernel,
    ) -> None:
        xena = worldmapc_xena_model
        kernel = worldmapc_kernel
        web = worldmapc_web_app

        assert (
            await web.post(
                f"/business/{xena.id}/offers-create?permanent=1", json={"title": "My offer"}
            )
        ).status == 200
        resp = await web.post(f"/business/{xena.id}/offers/{1}/add-item?position=REQUEST")
        assert resp.status == 200
        descr = description_serializer.load(await resp.json())

        assert descr.items[0].is_form
        assert descr.items[0].items[0].name == "value"
        for name in [
            "Bois (mètre cubes)",
            "Vin rouge (litres)",
            "Plastic bottle (unité)",
            "Bouclier de bois (unité)",
            "Hache de pierre (unité)",
            "Veste de cuir (unité)",
            "Pierre (unités)",
            "Corps (unité)",
            "Petit bois (mètre cubes)",
        ]:
            assert name in descr.items[0].items[0].choices
        assert descr.items[0].items[1].name == "quantity"

    async def test_update_offer__have_some_required__request_and(
        self,
        worldmapc_xena_model: CharacterModel,
        worldmapc_web_app: TestClient,
        worldmapc_kernel: Kernel,
    ) -> None:
        xena = worldmapc_xena_model
        kernel = worldmapc_kernel
        web = worldmapc_web_app

        await self._assert_owned_offers(kernel, web, xena, count=0)
        # see test_create_offer__nominal_case if in error
        assert (
            await web.post(
                f"/business/{xena.id}/offers-create?permanent=1", json={"title": "My offer"}
            )
        ).status == 200

        # Add one stuff
        assert (
            await web.post(
                f"/business/{xena.id}/offers/{1}/add-item"
                f"?position=REQUEST&value=Plastic bottle (unité)&quantity=1"
            )
        ).status == 200
        await self._assert_edit_offer(
            kernel, web, xena, offer_id=1, request_item_names=[EXPECTED_PLASTIC_BOTTLE_NAME]
        )

        # Add one resource
        assert (
            await web.post(
                f"/business/{xena.id}/offers/{1}/add-item"
                f"?position=REQUEST&value=Petit bois (mètre cubes)&quantity=1.50"
            )
        ).status == 200
        await self._assert_edit_offer(
            kernel,
            web,
            xena,
            offer_id=1,
            request_item_names=[EXPECTED_PLASTIC_BOTTLE_NAME, "Petit bois (1.5 mètre cubes)"],
        )

    async def test_update_offer__have_some_required__remove_item(
        self,
        worldmapc_xena_model: CharacterModel,
        worldmapc_web_app: TestClient,
        worldmapc_kernel: Kernel,
    ) -> None:
        xena = worldmapc_xena_model
        kernel = worldmapc_kernel
        web = worldmapc_web_app

        await self._assert_owned_offers(kernel, web, xena, count=0)
        # see test_create_offer__nominal_case if in error
        assert (
            await web.post(
                f"/business/{xena.id}/offers-create?permanent=1", json={"title": "My offer"}
            )
        ).status == 200

        # Add one stuff
        assert (
            await web.post(
                f"/business/{xena.id}/offers/{1}/add-item?position=REQUEST&value=Plastic bottle (unité)&quantity=1"
            )
        ).status == 200
        await self._assert_edit_offer(
            kernel, web, xena, offer_id=1, request_item_names=[EXPECTED_PLASTIC_BOTTLE_NAME]
        )

        # remove it
        assert (await web.post(f"/business/{xena.id}/offers/{1}/remove-item/{1}")).status == 200

        await self._assert_edit_offer(
            kernel, web, xena, offer_id=1, request_item_names_not=[EXPECTED_PLASTIC_BOTTLE_NAME]
        )

    async def test_edit_offer__test_owner_have_display(
        self,
        worldmapc_xena_model: CharacterModel,
        worldmapc_arthur_model: CharacterModel,
        worldmapc_web_app: TestClient,
        worldmapc_kernel: Kernel,
        xena_permanent_and_offer: OfferDocument,
    ) -> None:
        xena = worldmapc_xena_model
        kernel = worldmapc_kernel
        web = worldmapc_web_app

        await self._assert_edit_offer(
            kernel,
            web,
            xena,
            offer_id=1,
            offer_item_names=["(X) Bois (0.5 mètre cubes)", "(X) Veste de cuir (1)"],
            request_operand_str=ALL_OF_THEM,
            offer_operand_str=ALL_OF_THEM,
            open_=True,
        )
        # add one to offer owner
        kernel.resource_lib.add_resource_to("WOOD", 0.5, character_id=xena.id)

        await self._assert_edit_offer(
            kernel,
            web,
            xena,
            offer_id=1,
            offer_item_names=["Bois (0.5 mètre cubes)", "(X) Veste de cuir (1)"],
            request_operand_str=ALL_OF_THEM,
            offer_operand_str=ALL_OF_THEM,
            open_=True,
        )

        # add one to offer owner
        jacket = create_stuff(kernel, "LEATHER_JACKET")
        kernel.stuff_lib.set_carried_by(jacket.id, character_id=xena.id)

        await self._assert_edit_offer(
            kernel,
            web,
            xena,
            offer_id=1,
            request_item_names=["Bois (0.5 mètre cubes)", "Veste de cuir (1)"],
            request_operand_str=ALL_OF_THEM,
            offer_operand_str=ALL_OF_THEM,
            open_=True,
        )

    async def test_read_offer__have_some_required_items__and(
        self,
        worldmapc_xena_model: CharacterModel,
        worldmapc_arthur_model: CharacterModel,
        worldmapc_web_app: TestClient,
        worldmapc_kernel: Kernel,
        xena_permanent_and_offer: OfferDocument,
    ) -> None:
        xena = worldmapc_xena_model
        arthur = worldmapc_arthur_model
        kernel = worldmapc_kernel
        web = worldmapc_web_app
        offer = xena_permanent_and_offer

        await self._assert_read_offer(
            kernel,
            web,
            xena,
            arthur,
            offer_id=offer.id,
            request_operand_str=ALL_OF_THEM,
            offer_operand_str=ALL_OF_THEM,
            have_not_item_names=["Vin rouge (1.5 litres)", "Hache de pierre (1)"],
            offer_item_names=["(!) Bois (0.5 mètre cubes)", "(!) Veste de cuir (1)"],
            owner_can_make_deal=False,
        )

        kernel.resource_lib.add_resource_to("RED_WINE", 2.0, character_id=arthur.id)

        await self._assert_read_offer(
            kernel,
            web,
            xena,
            arthur,
            offer_id=offer.id,
            request_operand_str=ALL_OF_THEM,
            offer_operand_str=ALL_OF_THEM,
            have_not_item_names=["Hache de pierre (1)"],
            have_item_names=["Vin rouge (1.5 litres)"],
            owner_can_make_deal=False,
        )

        haxe = create_stuff(kernel, "STONE_HAXE")
        kernel.stuff_lib.set_carried_by(haxe.id, character_id=arthur.id)

        await self._assert_read_offer(
            kernel,
            web,
            xena,
            arthur,
            offer_id=offer.id,
            request_operand_str=ALL_OF_THEM,
            offer_operand_str=ALL_OF_THEM,
            have_item_names=["Vin rouge (1.5 litres)", "Hache de pierre (1)"],
            owner_can_make_deal=False,
        )

        # add wood to offer owner (remove the (!))
        kernel.resource_lib.add_resource_to("WOOD", 0.5, character_id=xena.id)
        await self._assert_read_offer(
            kernel,
            web,
            xena,
            arthur,
            offer_id=offer.id,
            request_operand_str=ALL_OF_THEM,
            offer_operand_str=ALL_OF_THEM,
            offer_item_names=["Bois (0.5 mètre cubes)", "(!) Veste de cuir (1)"],
            owner_can_make_deal=False,
        )

        # add jacket to offer owner (remove the (!))
        jacket = create_stuff(kernel, "LEATHER_JACKET")
        kernel.stuff_lib.set_carried_by(jacket.id, character_id=xena.id)
        await self._assert_read_offer(
            kernel,
            web,
            xena,
            arthur,
            offer_id=offer.id,
            request_operand_str=ALL_OF_THEM,
            offer_operand_str=ALL_OF_THEM,
            offer_item_names=["Bois (0.5 mètre cubes)", "Veste de cuir (1)"],
            owner_can_make_deal=True,
            can_make_deal=True,
        )

    async def test_read_offer__have_some_required_items__or(
        self,
        worldmapc_xena_model: CharacterModel,
        worldmapc_arthur_model: CharacterModel,
        worldmapc_web_app: TestClient,
        worldmapc_kernel: Kernel,
        xena_permanent_or_offer: OfferDocument,
    ) -> None:
        xena = worldmapc_xena_model
        arthur = worldmapc_arthur_model
        kernel = worldmapc_kernel
        web = worldmapc_web_app
        offer = xena_permanent_or_offer

        # ensure xena have all offered items
        kernel.resource_lib.add_resource_to("WOOD", 0.5, character_id=xena.id)
        jacket = create_stuff(kernel, "LEATHER_JACKET")
        kernel.stuff_lib.set_carried_by(jacket.id, character_id=xena.id)

        await self._assert_read_offer(
            kernel,
            web,
            xena,
            arthur,
            offer_id=offer.id,
            request_operand_str=ONE_OF_THEM,
            offer_operand_str=ONE_OF_THEM,
            have_not_item_names=["Vin rouge (1.5 litres)", "Hache de pierre (1)"],
            offer_item_names=["Bois (0.5 mètre cubes)", "Veste de cuir (1)"],
            can_make_deal=False,
        )

        kernel.resource_lib.add_resource_to("RED_WINE", 2.0, character_id=arthur.id)

        await self._assert_read_offer(
            kernel,
            web,
            xena,
            arthur,
            offer_id=offer.id,
            request_operand_str=ONE_OF_THEM,
            offer_operand_str=ONE_OF_THEM,
            have_not_item_names=["Hache de pierre (1)"],
            have_item_names=["Vin rouge (1.5 litres)"],
            can_make_deal=True,
        )

        haxe = create_stuff(kernel, "STONE_HAXE")
        kernel.stuff_lib.set_carried_by(haxe.id, character_id=arthur.id)

        await self._assert_read_offer(
            kernel,
            web,
            xena,
            arthur,
            offer_id=offer.id,
            request_operand_str=ONE_OF_THEM,
            offer_operand_str=ONE_OF_THEM,
            have_item_names=["Vin rouge (1.5 litres)", "Hache de pierre (1)"],
            can_make_deal=True,
        )

    async def test_read_offer__make_transaction__missing_request_and(
        self,
        worldmapc_xena_model: CharacterModel,
        worldmapc_arthur_model: CharacterModel,
        worldmapc_web_app: TestClient,
        worldmapc_kernel: Kernel,
        xena_permanent_and_offer: OfferDocument,
    ) -> None:
        xena = worldmapc_xena_model
        arthur = worldmapc_arthur_model
        kernel = worldmapc_kernel
        web = worldmapc_web_app
        offer = xena_permanent_and_offer

        # ensure xena have all offered items
        kernel.resource_lib.add_resource_to("WOOD", 0.5, character_id=xena.id)
        jacket = create_stuff(kernel, "LEATHER_JACKET")
        kernel.stuff_lib.set_carried_by(jacket.id, character_id=xena.id)

        # Give just a part of necessary to arthur
        kernel.resource_lib.add_resource_to("RED_WINE", 2.0, character_id=arthur.id)

        resp = await web.post(
            f"/business/{arthur.id}/see-offer/{offer.character_id}/{offer.id}/deal"
        )
        assert 200 == resp.status
        descr = description_serializer.load(await resp.json())

        item_labels = [i.label or i.text for i in descr.items]
        assert "Vous ne possédez pas ce qu'il faut pour faire ce marché" in item_labels

    async def test_read_offer__make_transaction__owner_missing_offer_and(
        self,
        worldmapc_xena_model: CharacterModel,
        worldmapc_arthur_model: CharacterModel,
        worldmapc_web_app: TestClient,
        worldmapc_kernel: Kernel,
        xena_permanent_and_offer: OfferDocument,
    ) -> None:
        xena = worldmapc_xena_model
        arthur = worldmapc_arthur_model
        kernel = worldmapc_kernel
        web = worldmapc_web_app
        offer = xena_permanent_and_offer

        # xena have just a part of offered items
        kernel.resource_lib.add_resource_to("WOOD", 0.5, character_id=xena.id)

        resp = await web.post(
            f"/business/{arthur.id}/see-offer/{offer.character_id}/{offer.id}/deal"
        )
        assert 200 == resp.status
        descr = description_serializer.load(await resp.json())

        item_labels = [i.label or i.text for i in descr.items]
        assert f"{xena.name} ne peut pas assurer cette opération" in item_labels

    async def test_read_offer__make_transaction__request_and(
        self,
        worldmapc_xena_model: CharacterModel,
        worldmapc_arthur_model: CharacterModel,
        worldmapc_web_app: TestClient,
        worldmapc_kernel: Kernel,
        xena_permanent_and_offer: OfferDocument,
        initial_universe_state: UniverseStateDocument,
    ) -> None:
        xena = worldmapc_xena_model
        arthur = worldmapc_arthur_model
        kernel = worldmapc_kernel
        web = worldmapc_web_app
        offer = xena_permanent_and_offer

        # Give all necessary to arthur
        kernel.resource_lib.add_resource_to("RED_WINE", 2.0, character_id=arthur.id)
        haxe = create_stuff(kernel, "STONE_HAXE")
        kernel.stuff_lib.set_carried_by(haxe.id, character_id=arthur.id)

        # ensure xena have all offered items
        kernel.resource_lib.add_resource_to("WOOD", 0.5, character_id=xena.id)
        jacket = create_stuff(kernel, "LEATHER_JACKET")
        kernel.stuff_lib.set_carried_by(jacket.id, character_id=xena.id)

        assert kernel.resource_lib.have_resource(xena.id, "WOOD", 0.5)
        assert kernel.stuff_lib.have_stuff_count(xena.id, "LEATHER_JACKET")
        assert not kernel.resource_lib.have_resource(xena.id, "RED_WINE", 1.5)
        assert not kernel.stuff_lib.have_stuff_count(xena.id, "STONE_HAXE")

        assert not kernel.resource_lib.have_resource(arthur.id, "WOOD", 0.5)
        assert not kernel.stuff_lib.have_stuff_count(arthur.id, "LEATHER_JACKET")
        assert kernel.resource_lib.have_resource(arthur.id, "RED_WINE", 1.5)
        assert kernel.stuff_lib.have_stuff_count(arthur.id, "STONE_HAXE")

        resp = await web.post(
            f"/business/{arthur.id}/see-offer/{offer.character_id}/{offer.id}/deal"
        )
        assert 200 == resp.status
        descr = description_serializer.load(await resp.json())

        item_labels = [i.label or i.text for i in descr.items]
        assert "Je confirme vouloir faire ce marché" in item_labels

        # Do the deal
        resp = await web.post(
            f"/business/{arthur.id}/see-offer/{offer.character_id}/{offer.id}/deal?confirm=1"
        )
        assert 200 == resp.status
        descr = description_serializer.load(await resp.json())

        item_labels = [i.label or i.text for i in descr.items]
        assert "Marché effectué" in item_labels

        assert not kernel.resource_lib.have_resource(xena.id, "WOOD", 0.5)
        assert not kernel.stuff_lib.have_stuff_count(xena.id, "LEATHER_JACKET")
        assert kernel.resource_lib.have_resource(xena.id, "RED_WINE", 1.5)
        assert kernel.stuff_lib.have_stuff_count(xena.id, "STONE_HAXE")

        assert kernel.resource_lib.have_resource(arthur.id, "WOOD", 0.5)
        assert kernel.stuff_lib.have_stuff_count(arthur.id, "LEATHER_JACKET")
        assert not kernel.resource_lib.have_resource(arthur.id, "RED_WINE", 1.5)
        assert not kernel.stuff_lib.have_stuff_count(arthur.id, "STONE_HAXE")

    async def test_read_offer__make_transaction__missing_all_request_or(
        self,
        worldmapc_xena_model: CharacterModel,
        worldmapc_arthur_model: CharacterModel,
        worldmapc_web_app: TestClient,
        worldmapc_kernel: Kernel,
        xena_permanent_or_offer: OfferDocument,
    ) -> None:
        xena = worldmapc_xena_model
        arthur = worldmapc_arthur_model
        kernel = worldmapc_kernel
        web = worldmapc_web_app
        offer = xena_permanent_or_offer

        # ensure xena have all offered items
        kernel.resource_lib.add_resource_to("WOOD", 0.5, character_id=xena.id)
        jacket = create_stuff(kernel, "LEATHER_JACKET")
        kernel.stuff_lib.set_carried_by(jacket.id, character_id=xena.id)

        resp = await web.post(
            f"/business/{arthur.id}/see-offer/{offer.character_id}/{offer.id}/deal"
        )
        assert 200 == resp.status
        descr = description_serializer.load(await resp.json())

        item_labels = [i.label or i.text for i in descr.items]
        assert "Vous ne possédez pas ce qu'il faut pour faire ce marché" in item_labels

    async def test_read_offer__make_transaction__request_or(
        self,
        worldmapc_xena_model: CharacterModel,
        worldmapc_arthur_model: CharacterModel,
        worldmapc_web_app: TestClient,
        worldmapc_kernel: Kernel,
        xena_permanent_or_offer: OfferDocument,
        initial_universe_state: UniverseStateDocument,
    ) -> None:
        xena = worldmapc_xena_model
        arthur = worldmapc_arthur_model
        kernel = worldmapc_kernel
        web = worldmapc_web_app
        offer = xena_permanent_or_offer

        # ensure xena have one of offered items
        kernel.resource_lib.add_resource_to("WOOD", 0.5, character_id=xena.id)

        # Give all necessary to arthur
        kernel.resource_lib.add_resource_to("RED_WINE", 1.5, character_id=arthur.id)
        haxe = create_stuff(kernel, "STONE_HAXE")
        kernel.stuff_lib.set_carried_by(haxe.id, character_id=arthur.id)

        assert kernel.resource_lib.have_resource(xena.id, "WOOD", 0.5)
        assert not kernel.resource_lib.have_resource(xena.id, "RED_WINE", 1.5)
        assert not kernel.stuff_lib.have_stuff_count(xena.id, "STONE_HAXE")

        assert not kernel.resource_lib.have_resource(arthur.id, "WOOD", 0.5)
        assert kernel.resource_lib.have_resource(arthur.id, "RED_WINE", 1.5)
        assert kernel.stuff_lib.have_stuff_count(arthur.id, "STONE_HAXE")

        resp = await web.post(
            f"/business/{arthur.id}/see-offer/{offer.character_id}/{offer.id}/deal"
        )
        assert 200 == resp.status
        descr = description_serializer.load(await resp.json())

        item_labels = [i.label or i.text for i in descr.items]
        item_by_label = {i.label: i for i in descr.items}
        give_wine_str = "Faire ce marché et donner Vin rouge (1.5 litres)"
        assert give_wine_str in item_labels
        assert "Faire ce marché et donner Hache de pierre (1)" in item_labels

        give_wine_url = item_by_label[give_wine_str].form_action
        resp = await web.post(give_wine_url)
        assert 200 == resp.status
        descr = description_serializer.load(await resp.json())

        item_labels = [i.label or i.text for i in descr.items]
        item_by_label = {i.label: i for i in descr.items}
        take_wood_str = "Faire ce marché et obtenir Bois (0.5 mètre cubes)"
        assert take_wood_str in item_labels
        assert "Faire ce marché et obtenir Veste de cuir (1)" not in item_labels

        # Give jacket to xena to permit take it
        jacket = create_stuff(kernel, "LEATHER_JACKET")
        kernel.stuff_lib.set_carried_by(jacket.id, character_id=xena.id)
        resp = await web.post(give_wine_url)
        assert 200 == resp.status
        descr = description_serializer.load(await resp.json())

        item_labels = [i.label or i.text for i in descr.items]
        item_by_label = {i.label: i for i in descr.items}
        take_wood_str = "Faire ce marché et obtenir Bois (0.5 mètre cubes)"
        assert take_wood_str in item_labels
        assert "Faire ce marché et obtenir Veste de cuir (1)" in item_labels

        take_wood_url = item_by_label[take_wood_str].form_action
        resp = await web.post(take_wood_url)
        assert 200 == resp.status

        assert not kernel.resource_lib.have_resource(xena.id, "WOOD", 0.5)
        assert kernel.resource_lib.have_resource(xena.id, "RED_WINE", 1.5)
        assert not kernel.stuff_lib.have_stuff_count(xena.id, "STONE_HAXE")

        assert kernel.resource_lib.have_resource(arthur.id, "WOOD", 0.5)
        assert not kernel.resource_lib.have_resource(arthur.id, "RED_WINE", 1.5)
        assert kernel.stuff_lib.have_stuff_count(arthur.id, "STONE_HAXE")

    async def test_create_with_character_transaction(
        self,
        worldmapc_xena_model: CharacterModel,
        worldmapc_arthur_model: CharacterModel,
        worldmapc_web_app: TestClient,
        worldmapc_kernel: Kernel,
        initial_universe_state: UniverseStateDocument,
    ) -> None:
        """+ conteur main page + vue depuis target + blinker"""
        xena = worldmapc_xena_model
        arthur = worldmapc_arthur_model
        kernel = worldmapc_kernel
        web = worldmapc_web_app

        assert (
            await web.post(
                f"/business/{xena.id}/offers-create?with_character_id={arthur.id}",
                json={"title": "My offer"},
            )
        ).status == 200
        assert (
            await web.post(
                f"/business/{xena.id}/offers/{1}/add-item"
                f"?position=REQUEST&value=Plastic bottle (unité)&quantity=1"
            )
        ).status == 200
        assert (
            await web.post(
                f"/business/{xena.id}/offers/{1}/add-item"
                f"?position=OFFER&value=Vin rouge (litres)&quantity=1.5"
            )
        ).status == 200
        assert (await web.post(f"/business/{xena.id}/offers/{1}?open=1")).status == 200

        await self._assert_edit_offer(
            kernel,
            web,
            character=xena,
            offer_id=1,
            request_operand_str=ONE_OF_THEM,
            offer_operand_str=ONE_OF_THEM,
            request_item_names=["Plastic bottle (1)"],
            offer_item_names=["(X) Vin rouge (1.5 litres)"],
            open_=True,
        )

        await self._assert_read_offer(
            kernel,
            web,
            owner=xena,
            character=arthur,
            offer_id=1,
            request_operand_str=ONE_OF_THEM,
            offer_operand_str=ONE_OF_THEM,
            have_not_item_names=["Plastic bottle (1)"],
            offer_item_names=["(!) Vin rouge (1.5 litres)"],
            can_make_deal=False,
        )

        # Give all necessary
        kernel.resource_lib.add_resource_to("RED_WINE", 1.5, character_id=xena.id)
        bottle = create_stuff(kernel, "PLASTIC_BOTTLE_1L")
        kernel.stuff_lib.set_carried_by(bottle.id, character_id=arthur.id)

        assert kernel.resource_lib.have_resource(xena.id, "RED_WINE", 1.5)
        assert not kernel.stuff_lib.have_stuff_count(xena.id, "PLASTIC_BOTTLE_1L")

        assert not kernel.resource_lib.have_resource(arthur.id, "RED_WINE", 1.5)
        assert kernel.stuff_lib.have_stuff_count(arthur.id, "PLASTIC_BOTTLE_1L")

        await self._assert_read_offer(
            kernel,
            web,
            owner=xena,
            character=arthur,
            offer_id=1,
            request_operand_str=ONE_OF_THEM,
            offer_operand_str=ONE_OF_THEM,
            have_item_names=["Plastic bottle (1)"],
            offer_item_names=["Vin rouge (1.5 litres)"],
            can_make_deal=True,
        )

        # xena main page
        resp: ClientResponse = await web.post(f"/business/{xena.id}")
        assert 200 == resp.status
        descr = description_serializer.load(await resp.json())
        item_labels = [i.label for i in descr.items]

        assert "Voir les transactions en attente (1 en cours)" in item_labels

        # arthur main page
        resp: ClientResponse = await web.post(f"/business/{arthur.id}")
        assert 200 == resp.status
        descr = description_serializer.load(await resp.json())
        item_labels = [i.label for i in descr.items]

        assert "*Voir les transactions en attente (1 en cours)" in item_labels

        resp = await web.post(f"/business/{arthur.id}/see-offer/{xena.id}/{1}/deal")
        assert 200 == resp.status
        descr = description_serializer.load(await resp.json())

        item_labels = [i.label or i.text for i in descr.items]
        item_by_label = {i.label: i for i in descr.items}

        deal_str = "Faire ce marché et donner Plastic bottle (1)"
        assert deal_str in item_labels
        go_url = item_by_label[deal_str].form_action

        resp = await web.post(go_url)
        assert 200 == resp.status
        descr = description_serializer.load(await resp.json())

        item_labels = [i.label or i.text for i in descr.items]
        item_by_label = {i.label: i for i in descr.items}

        deal_str = "Faire ce marché et obtenir Vin rouge (1.5 litres)"
        assert deal_str in item_labels
        go_url = item_by_label[deal_str].form_action

        assert (await web.post(go_url)).status == 200

        assert not kernel.resource_lib.have_resource(xena.id, "RED_WINE", 1.5)
        assert kernel.stuff_lib.have_stuff_count(xena.id, "PLASTIC_BOTTLE_1L")

        assert kernel.resource_lib.have_resource(arthur.id, "RED_WINE", 1.5)
        assert not kernel.stuff_lib.have_stuff_count(arthur.id, "PLASTIC_BOTTLE_1L")

        # xena main page
        resp: ClientResponse = await web.post(f"/business/{xena.id}")
        assert 200 == resp.status
        descr = description_serializer.load(await resp.json())
        item_labels = [i.label for i in descr.items]

        assert "Voir les transactions en attente (0 en cours)" in item_labels

        # arthur main page
        resp: ClientResponse = await web.post(f"/business/{arthur.id}")
        assert 200 == resp.status
        descr = description_serializer.load(await resp.json())
        item_labels = [i.label for i in descr.items]

        assert "Voir les transactions en attente (0 en cours)" in item_labels
