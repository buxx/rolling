# coding: utf-8
import typing

from aiohttp.test_utils import TestClient
import pytest
import serpyco

from rolling.kernel import Kernel
from rolling.model.character import CharacterModel


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
