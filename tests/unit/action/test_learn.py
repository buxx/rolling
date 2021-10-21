# coding: utf-8
from aiohttp.test_utils import TestClient
import pytest
import typing

from rolling.action.knowledge import LearnKnowledgeAction
from rolling.action.knowledge import LearnKnowledgeModel
from rolling.action.knowledge import ProposeTeachKnowledgeAction
from rolling.action.knowledge import ProposeTeachKnowledgeModel
from rolling.exception import ImpossibleAction
from rolling.exception import WrongInputError
from rolling.kernel import Kernel
from rolling.model.character import CharacterModel
from rolling.rolling_types import ActionType
from tests.fixtures import description_serializer


@pytest.fixture
def learn_action(worldmapc_kernel: Kernel) -> LearnKnowledgeAction:
    return typing.cast(
        LearnKnowledgeAction,
        worldmapc_kernel.action_factory.create_action(
            ActionType.LEARN_KNOWLEDGE, ActionType.LEARN_KNOWLEDGE.name
        ),
    )


@pytest.fixture
def propose_teach_action(worldmapc_kernel: Kernel) -> ProposeTeachKnowledgeAction:
    return typing.cast(
        ProposeTeachKnowledgeAction,
        worldmapc_kernel.action_factory.create_action(
            ActionType.PROPOSE_TEACH_KNOWLEDGE, ActionType.PROPOSE_TEACH_KNOWLEDGE.name
        ),
    )


@pytest.mark.usefixtures("initial_universe_state")
class TestLearnKnowledgeAction:
    async def test_unit__learn__ok__nominal_case(
        self,
        worldmapc_kernel: Kernel,
        worldmapc_franck_model: CharacterModel,
        learn_action: LearnKnowledgeAction,
    ) -> None:
        kernel = worldmapc_kernel
        franck = worldmapc_franck_model

        assert "blacksmith" not in franck.knowledges
        assert kernel.character_lib.get_knowledge_progress(franck.id, "blacksmith") == 0

        descr = await learn_action.perform(
            franck, input_=LearnKnowledgeModel(knowledge_id="blacksmith")
        )
        assert descr.title == "Apprendre Forgeron"
        assert (
            descr.items[0].text
            == "Il reste 10 points d'actions à dépenser pour apprendre Forgeron"
        )
        assert descr.items[1].is_form
        assert descr.items[1].items[0].name == "ap"

        descr = await learn_action.perform(
            franck, input_=LearnKnowledgeModel(knowledge_id="blacksmith", ap=5)
        )
        assert descr.title == "Apprentissage effectué"

        franck = kernel.character_lib.get(franck.id)
        assert "blacksmith" not in franck.knowledges
        assert kernel.character_lib.get_knowledge_progress(franck.id, "blacksmith") == 5

        descr = await learn_action.perform(
            franck, input_=LearnKnowledgeModel(knowledge_id="blacksmith")
        )
        assert descr.title == "Apprendre Forgeron"
        assert (
            descr.items[0].text
            == "Il reste 5 points d'actions à dépenser pour apprendre Forgeron"
        )

        descr = await learn_action.perform(
            franck, input_=LearnKnowledgeModel(knowledge_id="blacksmith", ap=5)
        )
        assert descr.title == "Connaissance acquise !"

        franck = kernel.character_lib.get(franck.id)
        assert "blacksmith" in franck.knowledges

    def test_unit__learn__err__not_enough_ap(
        self,
        worldmapc_kernel: Kernel,
        worldmapc_franck_model: CharacterModel,
        learn_action: LearnKnowledgeAction,
    ) -> None:
        kernel = worldmapc_kernel
        franck = worldmapc_franck_model

        franck.action_points = 1
        with pytest.raises(WrongInputError) as caught:
            learn_action.check_request_is_possible(
                franck, input_=LearnKnowledgeModel(knowledge_id="blacksmith", ap=2)
            )
        assert str(caught.value) == "Pas assez de points d'actions"

    def test_unit__learn__err__already_knew(
        self,
        worldmapc_kernel: Kernel,
        worldmapc_franck_model: CharacterModel,
        learn_action: LearnKnowledgeAction,
    ) -> None:
        kernel = worldmapc_kernel
        franck = worldmapc_franck_model

        franck.knowledges["blacksmith"] = kernel.game.config.knowledge["blacksmith"]
        with pytest.raises(WrongInputError) as caught:
            learn_action.check_request_is_possible(
                franck, input_=LearnKnowledgeModel(knowledge_id="blacksmith", ap=2)
            )
        assert str(caught.value) == "Connaissance déjà acquise"

    def test_unit__learn__err__require_other_knowledge(
        self,
        worldmapc_kernel: Kernel,
        worldmapc_franck_model: CharacterModel,
        learn_action: LearnKnowledgeAction,
    ) -> None:
        kernel = worldmapc_kernel
        franck = worldmapc_franck_model

        with pytest.raises(WrongInputError) as caught:
            learn_action.check_request_is_possible(
                franck, input_=LearnKnowledgeModel(knowledge_id="blacksmith2", ap=2)
            )
        assert str(caught.value) == "Cette connaissance ne peut pas encore etre abordé"

    async def test_unit__propose_and_teach__ok__nominal_case(
        self,
        worldmapc_kernel: Kernel,
        worldmapc_xena_model: CharacterModel,
        worldmapc_arthur_model: CharacterModel,
        propose_teach_action: ProposeTeachKnowledgeAction,
        worldmapc_web_app: TestClient,
    ) -> None:
        kernel = worldmapc_kernel
        xena = worldmapc_xena_model
        arthur = worldmapc_arthur_model
        web = worldmapc_web_app

        assert kernel.character_lib.get_knowledge_progress(arthur.id, "blacksmith") == 0

        description = await propose_teach_action.perform(
            xena,
            arthur,
            input_=ProposeTeachKnowledgeModel(
                knowledge_id="blacksmith", ap=5, expire=2
            ),
        )
        assert description.title == "Proposition effectué"

        arthur = kernel.character_lib.get(arthur.id, compute_pending_actions=True)
        assert arthur.pending_actions == 1

        resp = await web.post(f"/_describe/character/{arthur.id}/on_place_actions")
        assert 200 == resp.status
        descr = description_serializer.load(await resp.json())
        item_urls = [p.form_action for p in descr.items]

        assert f"/_describe/character/{arthur.id}/pending_actions" in item_urls
        assert arthur.pending_actions == 1

        resp = await web.post(f"/_describe/character/{arthur.id}/pending_actions")
        assert 200 == resp.status
        descr = description_serializer.load(await resp.json())
        item_urls = [p.form_action for p in descr.items]
        item_labels = [p.label for p in descr.items]

        assert f"/_describe/character/{arthur.id}/pending_actions/1" in item_urls
        assert (
            "Prendre un cours de Forgeron avec xena pendant 5 points d'actions"
            in item_labels
        )

        resp = await web.post(f"/_describe/character/{arthur.id}/pending_actions/1")
        assert 200 == resp.status
        descr = description_serializer.load(await resp.json())
        item_urls = [p.form_action for p in descr.items]

        assert f"/_describe/character/{arthur.id}/pending_actions/1?do=1" in item_urls

        resp = await web.post(
            f"/_describe/character/{arthur.id}/pending_actions/1?do=1"
        )
        assert 200 == resp.status

        arthur = kernel.character_lib.get(arthur.id, compute_pending_actions=True)
        assert arthur.pending_actions == 0
        assert (
            kernel.character_lib.get_knowledge_progress(arthur.id, "blacksmith")
            == 5 * kernel.game.config.knowledge["blacksmith"].instructor_coeff
        )
