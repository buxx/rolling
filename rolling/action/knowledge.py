# coding: utf-8
import dataclasses

import serpyco
import typing

from guilang.description import Description
from guilang.description import Part
from guilang.description import Type
from rolling.action.base import CharacterAction
from rolling.action.base import WithCharacterAction
from rolling.action.base import get_character_action_url
from rolling.action.base import get_with_character_action_url
from rolling.exception import ImpossibleAction
from rolling.rolling_types import ActionScope
from rolling.rolling_types import ActionType
from rolling.server.link import CharacterActionLink

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
        self._kernel.character_lib.reduce_action_points(character.id, cost=input_.ap)

        return Description(title=title)


@dataclasses.dataclass
class ProposeTeachKnowledgeModel:
    knowledge_id: str
    ap: typing.Optional[int] = serpyco.field(cast_on_load=True, default=None)
    expire: typing.Optional[int] = serpyco.field(cast_on_load=True, default=1)


class ProposeTeachKnowledgeAction(WithCharacterAction):
    input_model = ProposeTeachKnowledgeModel
    input_model_serializer = serpyco.Serializer(ProposeTeachKnowledgeModel)

    @classmethod
    def get_properties_from_config(cls, game_config: "GameConfig", action_config_raw: dict) -> dict:
        return {}

    def check_is_possible(
        self, character: "CharacterModel", with_character: "CharacterModel"
    ) -> None:
        # FIXME BS: en fait, toute les actions doivent tester si la cible est sur la meme zone ...
        if (
            character.world_row_i != with_character.world_row_i
            or character.world_col_i != with_character.world_col_i
        ):
            raise ImpossibleAction("Les personnages ne sont pas sur la meme zone")

    def check_request_is_possible(
        self,
        character: "CharacterModel",
        with_character: "CharacterModel",
        input_: ProposeTeachKnowledgeModel,
    ) -> None:
        self.check_is_possible(character, with_character)
        if input_.knowledge_id not in character.knowledges:
            raise ImpossibleAction(f"{character.name} n'a pas cette connaisance")

        if input_.ap is not None and character.action_points < input_.ap:
            raise ImpossibleAction(f"{character.name} n'a pas assez de points d'actions")

    def _get_url(
        self,
        character: "CharacterModel",
        with_character: "CharacterModel",
        input_: typing.Optional[ProposeTeachKnowledgeModel] = None,
    ) -> str:
        return get_with_character_action_url(
            character_id=character.id,
            with_character_id=with_character.id,
            action_type=ActionType.PROPOSE_TEACH_KNOWLEDGE,
            query_params=self.input_model_serializer.dump(input_) if input_ else {},
            action_description_id=self._description.id,
        )

    def get_character_actions(
        self, character: "CharacterModel", with_character: "CharacterModel"
    ) -> typing.List[CharacterActionLink]:
        action_links = []

        for knowledge_id, knowledge_description in character.knowledges.items():
            action_links.append(
                CharacterActionLink(
                    name=f"Proposer un cours de {knowledge_description.name}",
                    link=self._get_url(
                        character,
                        with_character,
                        ProposeTeachKnowledgeModel(knowledge_id=knowledge_id),
                    ),
                    group_name="Enseigner",
                )
            )

        return action_links

    def perform(
        self,
        character: "CharacterModel",
        with_character: "CharacterModel",
        input_: ProposeTeachKnowledgeModel,
    ) -> Description:
        knowledge_description = self._kernel.game.config.knowledge[input_.knowledge_id]
        if input_.ap is None:
            max_turns = self._kernel.game.config.max_action_propose_turns
            return Description(
                title=f"Enseigner {knowledge_description.name} à {with_character.name}",
                items=[
                    Part(
                        is_form=True,
                        form_values_in_query=True,
                        form_action=self._get_url(character, with_character, input_),
                        items=[
                            Part(
                                label=f"Passer combien de points d'actions sur ce cours ?",
                                type_=Type.NUMBER,
                                name="ap",
                            ),
                            Part(
                                label=(
                                    f"Proposition valable combien de tours "
                                    f"(max {max_turns}, en cours compris) ?"
                                ),
                                type_=Type.NUMBER,
                                name="expire",
                                default_value="1",
                            ),
                        ],
                    )
                ],
            )

        pending_action_document = self._kernel.action_factory.create_pending_action(
            action_scope=ActionScope.WITH_CHARACTER,
            action_type=ActionType.TEACH_KNOWLEDGE,
            action_description_id=ActionType.TEACH_KNOWLEDGE.value,
            character_id=character.id,
            with_character_id=with_character.id,
            parameters=TeachKnowledgeAction.input_model_serializer.dump(
                TeachKnowledgeModel(knowledge_id=input_.knowledge_id, ap=input_.ap)
            ),
            expire_at_turn=self._kernel.universe_lib.get_last_state().turn + (input_.expire - 1),
            suggested_by=character.id,
            name=(
                f"Prendre un cours de {knowledge_description.name} avec"
                f" {character.name} pendant {input_.ap} points d'actions"
            ),
            delete_after_first_perform=True,
        )
        self._kernel.action_factory.add_pending_action_authorization(
            pending_action_id=pending_action_document.id, authorized_character_id=with_character.id
        )

        return Description(title="Proposition effectué")


@dataclasses.dataclass
class TeachKnowledgeModel:
    knowledge_id: str
    ap: int


class TeachKnowledgeAction(WithCharacterAction):
    input_model = TeachKnowledgeModel
    input_model_serializer = serpyco.Serializer(TeachKnowledgeModel)

    @classmethod
    def get_properties_from_config(cls, game_config: "GameConfig", action_config_raw: dict) -> dict:
        return {}

    def check_is_possible(
        self, character: "CharacterModel", with_character: "CharacterModel"
    ) -> None:
        if (
            character.world_row_i != with_character.world_row_i
            or character.world_col_i != with_character.world_col_i
        ):
            raise ImpossibleAction("Les personnages ne sont pas sur la meme zone")

    def check_request_is_possible(
        self,
        character: "CharacterModel",
        with_character: "CharacterModel",
        input_: TeachKnowledgeModel,
    ) -> None:
        self.check_is_possible(character, with_character)
        if input_.knowledge_id not in character.knowledges:
            raise ImpossibleAction(f"{character.name} n'a pas cette connaisance")

        if input_.ap is not None and character.action_points < input_.ap:
            raise ImpossibleAction(f"{character.name} n'a pas assez de points d'actions")

    def get_character_actions(
        self, character: "CharacterModel", with_character: "CharacterModel"
    ) -> typing.List[CharacterActionLink]:
        return []  # should not be called because called from pending action

    def perform(
        self,
        character: "CharacterModel",
        with_character: "CharacterModel",
        input_: TeachKnowledgeModel,
    ) -> Description:
        knowledge_description = self._kernel.game.config.knowledge[input_.knowledge_id]
        if self._kernel.character_lib.increase_knowledge_progress(
            with_character.id,
            input_.knowledge_id,
            ap=int(input_.ap * knowledge_description.instructor_coeff),
        ):
            title = "Connaissance acquise !"
        else:
            title = "Apprentissage effectué"
        self._kernel.character_lib.reduce_action_points(character.id, cost=input_.ap)
        self._kernel.character_lib.reduce_action_points(with_character.id, cost=input_.ap)

        return Description(title=title)

    # FIXME BS NOW: Afficher dans les actions (ou ailleurs) les actions proposés par les autres
    # puis a tarvers une vue qui propose d'éxecuter cette action
