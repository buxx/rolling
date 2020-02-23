# coding: utf-8
import typing

import serpyco

from guilang.description import Description
from guilang.description import Part
from rolling.action.base import WithStuffAction
from rolling.action.base import get_with_stuff_action_url
from rolling.exception import ImpossibleAction
from rolling.exception import NotEnoughActionPoints
from rolling.server.link import CharacterActionLink
from rolling.types import ActionType
from rolling.util import EmptyModel
from rolling.util import quantity_to_str

if typing.TYPE_CHECKING:
    from rolling.model.character import CharacterModel
    from rolling.game.base import GameConfig
    from rolling.model.stuff import StuffModel
    from rolling.kernel import Kernel


class TransformStuffIntoResourcesAction(WithStuffAction):
    input_model = EmptyModel
    input_model_serializer = serpyco.Serializer(EmptyModel)

    @classmethod
    def get_properties_from_config(cls, game_config: "GameConfig", action_config_raw: dict) -> dict:
        return {
            "require_one_of_ability_ids": action_config_raw["require_one_of_ability"],
            "require_stuff_ids": action_config_raw["require_stuff"],
            "produce": action_config_raw["produce"],
        }

    def check_is_possible(self, character: "CharacterModel", stuff: "StuffModel") -> None:
        if stuff.stuff_id not in self._description.properties["require_stuff_ids"]:
            raise ImpossibleAction("Non concerné")

        abilities_ok = False

        require_one_of_ability_ids = self._description.properties["require_one_of_ability_ids"]
        if not require_one_of_ability_ids:
            abilities_ok = True
        elif self._kernel.character_lib.have_one_of_abilities(
            character, require_one_of_ability_ids
        ):
            abilities_ok = True

        if not abilities_ok:
            raise ImpossibleAction("Compétences ou matériel insuffisants")

    def get_character_actions(
        self, character: "CharacterModel", stuff: "StuffModel"
    ) -> typing.List[CharacterActionLink]:
        resources_str_parts = []
        for produce in self._description.properties["produce"]:
            resource_id = produce["resource"]
            resource_description = self._kernel.game.config.resources[resource_id]
            resources_str_parts.append(f"{resource_description.name}")
        resources_str = ", ".join(resources_str_parts)

        return [
            CharacterActionLink(
                name=f"Transformer en {resources_str}",
                link=get_with_stuff_action_url(
                    character_id=character.id,
                    stuff_id=stuff.id,
                    action_type=ActionType.TRANSFORM_STUFF_TO_RESOURCES,
                    query_params={},
                    action_description_id=self._description.id,
                ),
                cost=self.get_cost(character, stuff),
            )
        ]

    def check_request_is_possible(
        self, character: "CharacterModel", stuff: "StuffModel", input_: input_model
    ) -> None:
        self.check_is_possible(character, stuff)

    def perform(
        self, character: "CharacterModel", stuff: "StuffModel", input_: input_model
    ) -> Description:
        self.check_request_is_possible(character, stuff, input_)

        for produce in self._description.properties["produce"]:
            resource_id = produce["resource"]
            self._kernel.resource_lib.add_resource_to_character(
                character_id=character.id,
                resource_id=resource_id,
                quantity=produce["quantity"],
                commit=False,
            )

        self._kernel.stuff_lib.destroy(stuff.id)
        self._kernel.server_db_session.commit()

        return Description(
            title="Transformation effectué", items=[Part(label="Continuer", go_back_zone=True)]
        )
