# coding: utf-8
import typing

import pytest

from rolling.action.knowledge import LearnKnowledgeAction
from rolling.action.knowledge import LearnKnowledgeModel
from rolling.exception import ImpossibleAction
from rolling.kernel import Kernel
from rolling.model.character import CharacterModel
from rolling.types import ActionType


@pytest.fixture
def learn_action(worldmapc_kernel: Kernel) -> LearnKnowledgeAction:
    return typing.cast(
        LearnKnowledgeAction,
        worldmapc_kernel.action_factory.create_action(
            ActionType.LEARN_KNOWLEDGE, ActionType.LEARN_KNOWLEDGE.name
        ),
    )


class TestLearnKnowledgeAction:
    def test_unit__learn__ok__nominal_case(
        self,
        worldmapc_kernel: Kernel,
        worldmapc_xena_model: CharacterModel,
        learn_action: LearnKnowledgeAction,
    ) -> None:
        kernel = worldmapc_kernel
        xena = worldmapc_xena_model

        assert "blacksmith" not in xena.knowledges
        assert kernel.character_lib.get_knowledge_progress(xena.id, "blacksmith") == 0

        descr = learn_action.perform(xena, input_=LearnKnowledgeModel(knowledge_id="blacksmith"))
        assert descr.title == "Apprendre Forgeron"
        assert (
            descr.items[0].text == "Il reste 10 points d'actions à dépenser pour apprendre Forgeron"
        )
        assert descr.items[1].is_form
        assert descr.items[1].items[0].name == "ap"

        descr = learn_action.perform(
            xena, input_=LearnKnowledgeModel(knowledge_id="blacksmith", ap=5)
        )
        assert descr.title == "Apprentissage effectué"

        xena = kernel.character_lib.get(xena.id)
        assert "blacksmith" not in xena.knowledges
        assert kernel.character_lib.get_knowledge_progress(xena.id, "blacksmith") == 5

        descr = learn_action.perform(xena, input_=LearnKnowledgeModel(knowledge_id="blacksmith"))
        assert descr.title == "Apprendre Forgeron"
        assert (
            descr.items[0].text
            == "Il reste 5.0 points d'actions à dépenser pour apprendre Forgeron"
        )

        descr = learn_action.perform(
            xena, input_=LearnKnowledgeModel(knowledge_id="blacksmith", ap=5)
        )
        assert descr.title == "Connaissance acquise !"

        xena = kernel.character_lib.get(xena.id)
        assert "blacksmith" in xena.knowledges

    def test_unit__learn__err__not_enough_ap(
        self,
        worldmapc_kernel: Kernel,
        worldmapc_xena_model: CharacterModel,
        learn_action: LearnKnowledgeAction,
    ) -> None:
        kernel = worldmapc_kernel
        xena = worldmapc_xena_model

        xena.action_points = 1
        with pytest.raises(ImpossibleAction) as caught:
            learn_action.check_request_is_possible(
                xena, input_=LearnKnowledgeModel(knowledge_id="blacksmith", ap=2)
            )
        assert str(caught.value) == "Pas assez de points d'actions"

    def test_unit__learn__err__already_knew(
        self,
        worldmapc_kernel: Kernel,
        worldmapc_xena_model: CharacterModel,
        learn_action: LearnKnowledgeAction,
    ) -> None:
        kernel = worldmapc_kernel
        xena = worldmapc_xena_model

        xena.knowledges["blacksmith"] = kernel.game.config.knowledge["blacksmith"]
        with pytest.raises(ImpossibleAction) as caught:
            learn_action.check_request_is_possible(
                xena, input_=LearnKnowledgeModel(knowledge_id="blacksmith", ap=2)
            )
        assert str(caught.value) == "Connaissance déjà acquise"

    def test_unit__learn__err__require_other_knowledge(
        self,
        worldmapc_kernel: Kernel,
        worldmapc_xena_model: CharacterModel,
        learn_action: LearnKnowledgeAction,
    ) -> None:
        kernel = worldmapc_kernel
        xena = worldmapc_xena_model

        with pytest.raises(ImpossibleAction) as caught:
            learn_action.check_request_is_possible(
                xena, input_=LearnKnowledgeModel(knowledge_id="blacksmith2", ap=2)
            )
        assert str(caught.value) == "Cette connaissance ne peut pas encore etre abordé"
