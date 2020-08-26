# coding: utf-8
from aiohttp.test_utils import TestClient
import contextlib
import pytest
import unittest

from rolling.action.base import ActionDescriptionModel
from rolling.action.follow import FollowCharacterAction
from rolling.action.follow import FollowModel
from rolling.kernel import Kernel
from rolling.model.character import CharacterModel
from rolling.rolling_types import ActionType
from tests.fixtures import description_serializer


@pytest.fixture
def follow_action(worldmapc_kernel: Kernel) -> FollowCharacterAction:
    return FollowCharacterAction(
        kernel=worldmapc_kernel,
        description=ActionDescriptionModel(
            action_type=ActionType.FOLLOW_CHARACTER,
            base_cost=0.0,
            id="FOLLOW_CARACHTER",
            properties={},
        ),
    )


@pytest.mark.usefixtures("initial_universe_state")
class TestFollowAction:
    async def test_unit__follow__ok__nominal_case(
        self,
        worldmapc_kernel: Kernel,
        worldmapc_xena_model: CharacterModel,
        worldmapc_arthur_model: CharacterModel,
        worldmapc_franck_model: CharacterModel,
        follow_action: FollowCharacterAction,
        worldmapc_web_app: TestClient,
    ) -> None:
        xena = worldmapc_xena_model
        arthur = worldmapc_arthur_model
        franck = worldmapc_franck_model
        web = worldmapc_web_app
        kernel = worldmapc_kernel

        follow_action.perform(arthur, xena, input_=FollowModel())
        follow_action.perform(franck, xena, input_=FollowModel(discreetly=True))

        resp = await web.post(f"/_describe/character/{xena.id}/move-to-zone/{1}/{2}")
        assert 200 == resp.status
        descr = description_serializer.load(await resp.json())

        texts = [p.text for p in descr.items]
        url_by_label = {p.label: p.form_action for p in descr.items}

        assert "1 personnage(s) vous suivront dans ce déplacement" in texts
        resp = await web.post(url_by_label["Effectuer le voyage"])
        assert 200 == resp.status

        xena_doc = kernel.character_lib.get_document(xena.id)
        arthur_doc = kernel.character_lib.get_document(arthur.id)
        franck_doc = kernel.character_lib.get_document(franck.id)

        assert (xena_doc.world_row_i, xena_doc.world_col_i) == (1, 2)
        assert (arthur_doc.world_row_i, arthur_doc.world_col_i) == (1, 2)
        assert (franck_doc.world_row_i, franck_doc.world_col_i) == (1, 2)

        assert (
            list(kernel.character_lib.get_last_events(arthur_doc.id, 1))[0].text
            == "Vous avez suivis xena"
        )
        assert (
            list(kernel.character_lib.get_last_events(franck_doc.id, 1))[0].text
            == "Vous avez suivis xena"
        )

    @pytest.mark.parametrize("reason", ["weight", "clutter", "exhausted"])
    async def test_unit__follow__error__cannot(
        self,
        worldmapc_kernel: Kernel,
        worldmapc_xena_model: CharacterModel,
        worldmapc_arthur_model: CharacterModel,
        follow_action: FollowCharacterAction,
        worldmapc_web_app: TestClient,
        reason: str,
    ) -> None:
        xena = worldmapc_xena_model
        arthur = worldmapc_arthur_model
        web = worldmapc_web_app
        kernel = worldmapc_kernel

        follow_action.perform(arthur, xena, input_=FollowModel())

        def _fake_weight(self, kernel):
            if self.id == "arthur":
                return -1.0
            return 200.0

        _fake_clutter = _fake_weight

        def _fake_is_exhausted(self):
            if self.id == "arthur":
                return True
            return False

        @contextlib.contextmanager
        def _apply_patch():
            if reason == "weight":
                with unittest.mock.patch(
                    "rolling.model.character.CharacterModel.get_weight_capacity", new=_fake_weight
                ):
                    yield
            elif reason == "clutter":
                with unittest.mock.patch(
                    "rolling.model.character.CharacterModel.get_clutter_capacity", new=_fake_clutter
                ):
                    yield
            elif reason == "exhausted":
                with unittest.mock.patch(
                    "rolling.model.character.CharacterModel.is_exhausted", new=_fake_is_exhausted
                ):
                    yield
            else:
                raise NotImplementedError

        kernel.resource_lib.add_resource_to("WOOD", 200.0, arthur.id)

        with _apply_patch():
            resp = await web.post(f"/_describe/character/{xena.id}/move-to-zone/{1}/{2}")
            assert 200 == resp.status
            descr = description_serializer.load(await resp.json())

            texts = [p.text for p in descr.items]
            url_by_label = {p.label: p.form_action for p in descr.items}

            assert (
                "1 personnage(s) ne pourront pas vous suivre dans ce déplacement: arthur" in texts
            )
            resp = await web.post(url_by_label["Effectuer le voyage"])
            assert 200 == resp.status

            xena_doc = kernel.character_lib.get_document(xena.id)
            arthur_doc = kernel.character_lib.get_document(arthur.id)

            assert (xena_doc.world_row_i, xena_doc.world_col_i) == (1, 2)
            assert (arthur_doc.world_row_i, arthur_doc.world_col_i) == (1, 1)

            assert (
                list(kernel.character_lib.get_last_events(arthur_doc.id, 1))[0].text
                == "Vous n'avez pas pu suivre xena (fatigue ou surcharge)"
            )
