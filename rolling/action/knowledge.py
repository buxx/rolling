# coding: utf-8
import dataclasses
import typing

import serpyco

from guilang.description import Description
from guilang.description import Part
from guilang.description import Type
from rolling.action.base import CharacterAction
from rolling.action.base import get_character_action_url
from rolling.exception import ImpossibleAction
from rolling.server.link import CharacterActionLink
from rolling.types import ActionType

if typing.TYPE_CHECKING:
    from rolling.game.base import GameConfig
    from rolling.model.character import CharacterModel


@dataclasses.dataclass
class LearnKnowledgeModel:
    knowledge_id: str
    ap: typing.Optional[int] = serpyco.field(cast_on_load=True, default=None)


class LearnKnowledgeAction(CharacterAction):
    input_model = LearnKnowledgeModel
    input_model_serializer = serpyco.Serializer(LearnKnowledgeModel)

    @classmethod
    def get_properties_from_config(cls, game_config: "GameConfig", action_config_raw: dict) -> dict:
        return {}

    def check_is_possible(self, character: "CharacterModel") -> None:
        pass

    def check_request_is_possible(
        self, character: "CharacterModel", input_: LearnKnowledgeModel
    ) -> None:
        if input_.knowledge_id is not None:
            if input_.knowledge_id in character.knowledges:
                raise ImpossibleAction("Connaissance déjà acquise")
            knowledge_description = self._kernel.game.config.knowledge[input_.knowledge_id]
            for required_knowledge_id in knowledge_description.requires:
                if required_knowledge_id not in character.knowledges:
                    raise ImpossibleAction(f"Cette connaissance ne peut pas encore etre abordé")

        if input_.ap is not None:
            if character.action_points < input_.ap:
                raise ImpossibleAction("Pas assez de points d'actions")

    def get_character_actions(
        self, character: "CharacterModel"
    ) -> typing.List[CharacterActionLink]:
        action_links = []

        for knowledge_id, knowledge_description in self._kernel.game.config.knowledge.items():
            continue_ = False

            if knowledge_id in character.knowledges:
                continue_ = True
            for required_knowledge_id in knowledge_description.requires:
                if required_knowledge_id not in character.knowledges:
                    continue_ = True

            if continue_:
                continue

            action_links.append(
                CharacterActionLink(
                    name=knowledge_description.name,
                    link=self._get_url(character, LearnKnowledgeModel(knowledge_id=knowledge_id)),
                    group_name="Apprentissages",
                )
            )

        return action_links

    def _get_url(
        self, character: "CharacterModel", input_: typing.Optional[LearnKnowledgeModel] = None
    ) -> str:
        return get_character_action_url(
            character_id=character.id,
            action_type=ActionType.LEARN_KNOWLEDGE,
            query_params=self.input_model_serializer.dump(input_) if input_ else {},
            action_description_id=self._description.id,
        )

    def perform(self, character: "CharacterModel", input_: LearnKnowledgeModel) -> Description:
        knowledge_description = self._kernel.game.config.knowledge[input_.knowledge_id]
        current_progress = self._kernel.character_lib.get_knowledge_progress(
            character.id, input_.knowledge_id
        )
        left = knowledge_description.ap_required - current_progress
        if input_.ap is None:
            return Description(
                title=f"Apprendre {knowledge_description.name}",
                items=[
                    Part(
                        text=(
                            f"Il reste {left} points d'actions à "
                            f"dépenser pour apprendre {knowledge_description.name}"
                        )
                    ),
                    Part(
                        is_form=True,
                        form_values_in_query=True,
                        form_action=self._get_url(character, input_),
                        items=[
                            Part(
                                label=f"Points d'actions à dépenser ?", type_=Type.NUMBER, name="ap"
                            )
                        ],
                    ),
                ],
            )

        if self._kernel.character_lib.increase_knowledge_progress(
            character.id, input_.knowledge_id, input_.ap
        ):
            title = "Connaissance acquise !"
        else:
            title = "Apprentissage effectué"

        return Description(
            title=title,
            footer_links=[
                Part(is_link=True, go_back_zone=True, label="Retourner à l'écran de déplacements")
            ],
        )
