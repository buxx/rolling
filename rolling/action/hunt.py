# coding: utf-8
import typing

import serpyco

from guilang.description import Description
from rolling.action.base import CharacterAction, get_character_action_url
from rolling.exception import ImpossibleAction, RollingError
from rolling.server.link import CharacterActionLink
from rolling.types import ActionType
from rolling.util import EmptyModel

if typing.TYPE_CHECKING:
    from rolling.model.character import CharacterModel
    from rolling.game.base import GameConfig


class SearchFoodAction(CharacterAction):
    input_model = EmptyModel
    input_model_serializer = serpyco.Serializer(EmptyModel)

    @classmethod
    def get_properties_from_config(
        cls, game_config: "GameConfig", action_config_raw: dict
    ) -> dict:
        for produce in action_config_raw["produce"]:
            if "resource" not in produce and "stuff" not in produce:
                raise RollingError("Misconfiguration for action SearchFoodAction")

        return {
            "required_one_of_stuff_ids": action_config_raw["required_one_of_stuffs"],
            "required_all_stuff_ids": action_config_raw["required_all_stuffs"],
            "required_one_of_skill_ids": action_config_raw["required_one_of_skills"],
            "required_all_skill_ids": action_config_raw["required_all_skills"],
            "produce": action_config_raw["produce"],
        }

    def check_is_possible(self, character: "CharacterModel") -> None:
        character_stuff_ids = [s.id for s in self._kernel.stuff_lib.get_carried_by(character.id)]
        character_skill_ids = []  # TODO BS 2019-09-26: code it
        one_of_required_stuff_found = False
        one_of_required_skill_found = False

        for required_one_of_stuff_id in self._description.properties["required_one_of_stuff_ids"]:
            if required_one_of_stuff_id in character_stuff_ids:
                one_of_required_stuff_found = True

        for required_one_of_skill_id in self._description.properties["required_one_of_skill_ids"]:
            if required_one_of_skill_id in character_skill_ids:
                one_of_required_skill_found = True

        if self._description.properties["required_one_of_stuff_ids"] and not one_of_required_stuff_found:
            raise ImpossibleAction("Manque de matériel")

        if self._description.properties["required_one_of_skill_ids"] and not one_of_required_skill_found:
            raise ImpossibleAction("Manque de compétence")

        for required_all_stuff_id in self._description.properties["required_all_stuff_ids"]:
            if required_all_stuff_id not in character_stuff_ids:
                raise ImpossibleAction("Manque de matériels")

        for required_all_skill_id in self._description.properties["required_all_skill_ids"]:
            if required_all_skill_id not in character_skill_ids:
                raise ImpossibleAction("Manque de compétences")

    def check_request_is_possible(
        self, character: "CharacterModel", input_: typing.Any
    ) -> None:
        self.check_is_possible(character)

    def get_character_actions(
        self, character: "CharacterModel"
    ) -> typing.List[CharacterActionLink]:
        return [
            CharacterActionLink(
                name=f"Chercher de la nourriture: {self._description.name}",
                link=get_character_action_url(
                    character_id=character.id,
                    action_type=ActionType.SEARCH_FOOD,
                    action_description_id=self._description.id,
                    query_params={},
                ),
                cost=self.get_cost(character),
            ),
        ]

    def perform(self, character: "CharacterModel", input_: typing.Any) -> Description:
        zone_available_production_resource_ids: typing.List[str] = []
        zone_available_production_stuff_ids: typing.List[str] = []

        for production in self._description.properties["produce"]:
            if "resource" in production:
                resource_id = production["resource"]
                if self._kernel.game.world_manager.is_there_resource_in_zone(
                    world_row_i=character.world_row_i,
                    world_col_i=character.world_col_i,
                    resource_id=resource_id,
                ):
                    zone_available_production_resource_ids.append(resource_id)
            elif "stuff" in production:
                stuff_id = production["stuff"]
                if self._kernel.game.world_manager.is_there_stuff_in_zone(
                    world_row_i=character.world_row_i,
                    world_col_i=character.world_col_i,
                    resource_id=stuff_id,
                ):
                    zone_available_production_stuff_ids.append(stuff_id)
            else:
                raise NotImplementedError()

        # idée: Pour chaques resource/stuff faire une proba pour voir si on en trouve
        # pour chaque trouvé, faire une proba pour voir combien on en trouve
        # appliquer des facteurs de résussite à chaque fois.
