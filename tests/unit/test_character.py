# coding: utf-8
import typing

from aiohttp.test_utils import TestClient
import pytest
import serpyco

from guilang.description import Part
from rolling.action.base import get_with_stuff_action_url
from rolling.kernel import Kernel
from rolling.model.character import CharacterModel
from rolling.model.stuff import StuffModel
from rolling.rolling_types import ActionType
from rolling.server.document.affinity import CHIEF_STATUS
from rolling.server.document.affinity import MEMBER_STATUS
from rolling.server.document.affinity import AffinityDirectionType
from rolling.server.document.affinity import AffinityJoinType
from tests.fixtures import description_serializer


class TestCharacter:
    @pytest.mark.parametrize(
        "attack,defend,expected_attack,expected_defend",
        [
            (0, 0, 0, 0),
            (0.0, 0.0, 0, 0),
            (30, 22, 30, 22),
            (20.5, 22, 20, 22),
            (22, 20.5, 22, 20),
            (105, 100, 100, 100),
            (105, 105, 100, 100),
            (-1, -1, 0, 0),
        ],
    )
    async def test_unit__update_retreat__ok__nominal_cases(
        self,
        worldmapc_xena_model: CharacterModel,
        worldmapc_web_app: TestClient,
        descr_serializer: serpyco.Serializer,
        worldmapc_kernel: Kernel,
        attack: typing.Union[int, float],
        defend: typing.Union[int, float],
        expected_attack: int,
        expected_defend: int,
    ) -> None:
        web = worldmapc_web_app
        xena = worldmapc_xena_model
        kernel = worldmapc_kernel

        resp = await web.post(f"/_describe/character/{xena.id}/card")
        descr = descr_serializer.load(await resp.json())

        form_action = f"/_describe/character/{xena.id}/card"
        item_actions = [i.form_action for i in descr.items]
        assert form_action in item_actions
        form_index = item_actions.index(form_action)
        assert "attack_allowed_loss_rate" == descr.items[form_index].items[1].name
        assert "defend_allowed_loss_rate" == descr.items[form_index].items[2].name
        assert "30" == descr.items[form_index].items[1].default_value
        assert "30" == descr.items[form_index].items[2].default_value

        resp = await web.post(
            f"/_describe/character/{xena.id}/card",
            json={"attack_allowed_loss_rate": str(attack), "defend_allowed_loss_rate": str(defend)},
        )
        assert 200 == resp.status
        resp = await web.post(f"/_describe/character/{xena.id}/card")
        descr = descr_serializer.load(await resp.json())
        assert str(expected_attack) == descr.items[form_index].items[1].default_value
        assert str(expected_defend) == descr.items[form_index].items[2].default_value

        doc = kernel.character_lib.get_document(xena.id)
        assert expected_attack == doc.attack_allowed_loss_rate
        assert expected_defend == doc.defend_allowed_loss_rate

    async def _get_card_item(self, web: TestClient, character_id: str, item_label: str) -> Part:
        resp = await web.post(f"/_describe/character/{character_id}/card")
        descr = description_serializer.load(await resp.json())

        item_by_label = {i.label: i for i in descr.items if i.label}
        return item_by_label[item_label]

    async def _use_as(self, web: TestClient, action: ActionType, character_id: str, stuff_id: int):
        resp = await web.post(
            get_with_stuff_action_url(
                character_id=character_id,
                action_type=action,
                stuff_id=stuff_id,
                query_params={},
                # WARNING: this is description id but in config action have same value
                action_description_id=action.value,
            )
        )
        assert 200 == resp.status

    async def test_unit__card_weapons__ok__set_then_unset(
        self,
        worldmapc_xena_model: CharacterModel,
        worldmapc_xena_haxe: StuffModel,
        worldmapc_xena_leather_jacket: StuffModel,
        worldmapc_xena_wood_shield: StuffModel,
        worldmapc_web_app: TestClient,
    ):
        web = worldmapc_web_app
        xena = worldmapc_xena_model
        haxe = worldmapc_xena_haxe
        jacket = worldmapc_xena_leather_jacket
        wood_shield = worldmapc_xena_wood_shield

        weapon = await self._get_card_item(web, xena.id, "Arme")
        shield = await self._get_card_item(web, xena.id, "Bouclier")
        armor = await self._get_card_item(web, xena.id, "Armure")
        assert weapon.text == "aucune"
        assert shield.text == "aucun"
        assert armor.text == "aucune"

        # set
        await self._use_as(web, ActionType.USE_AS_WEAPON, xena.id, haxe.id)
        weapon = await self._get_card_item(web, xena.id, "Arme")
        assert weapon.text == haxe.name

        await self._use_as(web, ActionType.USE_AS_SHIELD, xena.id, wood_shield.id)
        shield = await self._get_card_item(web, xena.id, "Bouclier")
        assert shield.text == wood_shield.name

        await self._use_as(web, ActionType.USE_AS_ARMOR, xena.id, jacket.id)
        armor = await self._get_card_item(web, xena.id, "Armure")
        assert armor.text == jacket.name

        # unset
        await self._use_as(web, ActionType.NOT_USE_AS_WEAPON, xena.id, haxe.id)
        weapon = await self._get_card_item(web, xena.id, "Arme")
        assert weapon.text == "aucune"

        await self._use_as(web, ActionType.NOT_USE_AS_SHIELD, xena.id, wood_shield.id)
        shield = await self._get_card_item(web, xena.id, "Bouclier")
        assert shield.text == "aucun"

        await self._use_as(web, ActionType.NOT_USE_AS_ARMOR, xena.id, jacket.id)
        armor = await self._get_card_item(web, xena.id, "Armure")
        assert armor.text == "aucune"

    async def test_unit__pick_from_inventory(
        self,
        worldmapc_xena_model: CharacterModel,
        worldmapc_xena_haxe: StuffModel,
        worldmapc_xena_wood: None,
        worldmapc_web_app: TestClient,
    ) -> None:
        web = worldmapc_web_app
        xena = worldmapc_xena_model

        pick_url = (
            f"/_describe/character/{xena.id}/pick_from_inventory"
            f"?callback_url=to_somewhere"
            f"&cancel_url=or_here"
            f"&title=The title"
        )
        resp = await web.post(pick_url)
        assert resp.status == 200
        descr = description_serializer.load(await resp.json())

        assert descr.title == "The title"
        assert descr.items[0].is_form
        assert descr.items[0].form_action == pick_url

        descr_links = [p.form_action for p in descr.items[0].items]
        stone_haxe_url = f"{pick_url}&stuff_id=STONE_HAXE"
        wood_url = f"{pick_url}&resource_id=WOOD"
        assert stone_haxe_url in descr_links
        assert wood_url in descr_links

        resp = await web.post(stone_haxe_url)
        assert resp.status == 200
        descr = description_serializer.load(await resp.json())
        assert descr.items[0].is_form
        assert descr.items[0].form_action == f"to_somewhere?&stuff_id=STONE_HAXE"
        assert descr.items[0].items[0].name == "stuff_quantity"
        assert descr.items[0].items[0].default_value == "1"
        assert descr.items[0].form_values_in_query

        resp = await web.post(wood_url)
        assert resp.status == 200
        descr = description_serializer.load(await resp.json())
        assert descr.items[0].is_form
        assert descr.items[0].form_action == f"to_somewhere?&resource_id=WOOD"
        assert descr.items[0].items[0].name == "resource_quantity"
        assert descr.items[0].items[0].default_value == "0.2"
        assert descr.items[0].form_values_in_query

    # FIXME BS NOW: Ajouter les trucs partagés avec l'affinité au TAKE
    @pytest.mark.parametrize("arthur_take", [False])
    async def test_unit__share_with_affinity_then_take(
        self,
        worldmapc_xena_model: CharacterModel,
        worldmapc_xena_haxe: StuffModel,
        worldmapc_xena_wood: None,
        worldmapc_arthur_model: CharacterModel,
        worldmapc_web_app: TestClient,
        worldmapc_kernel: Kernel,
        arthur_take: bool,
    ) -> None:
        web = worldmapc_web_app
        kernel = worldmapc_kernel
        xena = worldmapc_xena_model
        arthur = worldmapc_arthur_model

        # Create affinity
        affinity = kernel.affinity_lib.create(
            name="MyAffinity",
            join_type=AffinityJoinType.ACCEPT_ALL,
            direction_type=AffinityDirectionType.ONE_DIRECTOR,
        )
        kernel.affinity_lib.join(
            character_id=xena.id, affinity_id=affinity.id, accepted=True, status_id=CHIEF_STATUS[0]
        )
        kernel.affinity_lib.join(
            character_id=arthur.id,
            affinity_id=affinity.id,
            accepted=True,
            status_id=MEMBER_STATUS[0],
        )

        # Did see affinity button ?
        response = await web.post(f"/affinity/{xena.id}/see/{affinity.id}")
        assert response.status == 200
        desc = description_serializer.load(await response.json())
        labels = [i.label for i in desc.items]
        urls = [i.form_action for i in desc.items]
        assert "Voir ce que je partager avec (0)" in labels
        assert f"/_describe/character/{xena.id}/shared-inventory?affinity_id=1" in urls

        # See shared things
        response = await web.post(f"/_describe/character/{xena.id}/shared-inventory?affinity_id=1")
        assert response.status == 200
        desc = description_serializer.load(await response.json())
        labels = [i.label for i in desc.items]
        assert "Hache de pierre" not in labels
        assert "Bois (0.2 mètre cubes)" not in labels
        assert "Bois (0.1 mètre cubes)" not in labels
        footer_link_labels = [i.label for i in desc.footer_links]
        footer_link_urls = [i.form_action for i in desc.footer_links]
        assert "Partager quelque chose" in footer_link_labels
        assert (
            f"/_describe/character/{xena.id}/shared-inventory/add?affinity_id=1" in footer_link_urls
        )

        # See shareable things
        response = await web.post(
            f"/_describe/character/{xena.id}/shared-inventory/add?affinity_id=1"
        )
        assert response.status == 200
        desc = description_serializer.load(await response.json())
        labels = [i.label for i in desc.items]
        urls = [i.form_action for i in desc.items]
        assert "Hache de pierre" in labels
        assert "Bois (0.2 mètre cubes)" in labels
        assert (
            f"/_describe/character/{xena.id}/shared-inventory/add?affinity_id=1&stuff_id=1" in urls
        )
        assert (
            f"/_describe/character/{xena.id}/shared-inventory/add?affinity_id=1&resource_id=WOOD"
            in urls
        )

        # Share stuff
        response = await web.post(
            f"/_describe/character/{xena.id}/shared-inventory/add?affinity_id=1&stuff_id=1"
        )
        assert response.status == 200
        desc = description_serializer.load(await response.json())
        labels = [i.label for i in desc.items]
        assert "Hache de pierre" not in labels
        assert "Bois (0.2 mètre cubes)" in labels

        # Share wood
        response = await web.post(
            f"/_describe/character/{xena.id}/shared-inventory/add?affinity_id=1&resource_id=WOOD"
        )
        assert response.status == 200
        desc = description_serializer.load(await response.json())
        assert desc.items[0].is_form
        assert desc.items[0].form_values_in_query
        assert desc.items[0].items[0].name == "resource_quantity"

        # Share wood with quantity
        response = await web.post(
            f"/_describe/character/{xena.id}/shared-inventory/add?affinity_id=1"
            f"&resource_id=WOOD&resource_quantity=0.1"
        )
        assert response.status == 200
        desc = description_serializer.load(await response.json())
        labels = [i.label for i in desc.items]
        assert "Hache de pierre" not in labels
        assert "Bois (0.2 mètre cubes)" not in labels
        assert "Bois (0.1 mètre cubes)" in labels

        # See shared
        response = await web.post(f"/_describe/character/{xena.id}/shared-inventory?affinity_id=1")
        assert response.status == 200
        desc = description_serializer.load(await response.json())
        labels = [i.label for i in desc.items]
        urls = [i.form_action for i in desc.items]
        assert "Hache de pierre" in labels
        assert "Bois (0.1 mètre cubes)" in labels
        assert f"/_describe/character/{xena.id}/shared-inventory?affinity_id=1&stuff_id=1" in urls
        assert (
            f"/_describe/character/{xena.id}/shared-inventory?affinity_id=1&resource_id=WOOD"
            in urls
        )

        # See shared link in inventory
        response = await web.post(f"/_describe/character/{xena.id}/inventory")
        assert response.status == 200
        desc = description_serializer.load(await response.json())
        footer_link_labels = [i.label for i in desc.footer_links]
        footer_link_urls = [i.form_action for i in desc.footer_links]
        assert "Voir ce qui est paratgé (2)" in footer_link_labels
        assert f"/_describe/character/{xena.id}/inventory/shared-with" in footer_link_urls

        # See shared affinity with
        response = await web.post(f"/_describe/character/{xena.id}/inventory/shared-with")
        assert response.status == 200
        desc = description_serializer.load(await response.json())
        labels = [i.label for i in desc.items]
        urls = [i.form_action for i in desc.items]
        assert "Avec MyAffinity (2)" in labels
        assert f"/_describe/character/{xena.id}/shared-inventory?affinity_id=1" in urls

        if arthur_take:
            pass  # FIXME test take here
        else:
            # Unshare stuff
            response = await web.post(
                f"/_describe/character/{xena.id}/shared-inventory?affinity_id=1&stuff_id=1"
            )
            assert response.status == 200

            # Unshare resource
            response = await web.post(
                f"/_describe/character/{xena.id}/shared-inventory?"
                f"affinity_id=1&resource_id=WOOD&resource_quantity=0.1"
            )
            assert response.status == 200

            # See shared
            response = await web.post(
                f"/_describe/character/{xena.id}/shared-inventory?affinity_id=1"
            )
            assert response.status == 200
            desc = description_serializer.load(await response.json())
            labels = [i.label for i in desc.items]
            assert "Hache de pierre" not in labels
            assert "Bois (0.1 mètre cubes)" not in labels
