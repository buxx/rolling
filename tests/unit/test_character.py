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
from rolling.types import ActionType
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
