# coding: utf-8
import random
import typing

import serpyco

from guilang.description import Description, Part
from rolling.action.base import CharacterAction, get_character_action_url
from rolling.exception import ImpossibleAction, RollingError
from rolling.model.measure import Unit
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
        productions = self._description.properties["produce"]
        production_per_resource_ids: typing.Dict[str, dict] = {}
        production_per_stuff_ids: typing.Dict[str, dict] = {}
        zone_available_production_resource_ids: typing.List[str] = []
        zone_available_production_stuff_ids: typing.List[str] = []

        for production in productions:
            if "resource" in production:
                resource_id = production["resource"]
                if self._kernel.game.world_manager.is_there_resource_in_zone(
                    world_row_i=character.world_row_i,
                    world_col_i=character.world_col_i,
                    resource_id=resource_id,
                ):
                    zone_available_production_resource_ids.append(resource_id)
                    production_per_resource_ids[resource_id] = production
            elif "stuff" in production:
                stuff_id = production["stuff"]
                if self._kernel.game.world_manager.is_there_stuff_in_zone(
                    world_row_i=character.world_row_i,
                    world_col_i=character.world_col_i,
                    resource_id=stuff_id,
                ):
                    zone_available_production_stuff_ids.append(stuff_id)
                    production_per_stuff_ids[stuff_id] = production
            else:
                raise NotImplementedError()

        # idée: Pour chaques resource/stuff faire une proba pour voir si on en trouve
        # pour chaque trouvé, faire une proba pour voir combien on en trouve
        # appliquer des facteurs de résussite à chaque fois.
        found_resource_ids: typing.List[str] = []
        found_stuff_ids: typing.List[str] = []

        for resource_id in zone_available_production_resource_ids:
            # TODO BS 2019-09-26: modify probability here if skill or stuff helping
            probability = production_per_resource_ids[resource_id]["probability"]
            if random.randint(0, 100) <= probability:
                found_resource_ids.append(resource_id)

        for stuff_id in zone_available_production_stuff_ids:
            # TODO BS 2019-09-26: modify probability here if skill or stuff helping
            probability = production_per_stuff_ids[stuff_id]["probability"]
            if random.randint(0, 100) <= probability:
                found_stuff_ids.append(stuff_id)

        result_resource_strs = []
        for resource_id in found_resource_ids:
            # TODO BS 2019-09-26: Modify here quantity found with skills, competences, stuffs ...
            resource_description = self._kernel.game.config.resources[resource_id]
            quantity_found_coeff = random.randint(0, 100) / 100
            quantity_found = production_per_resource_ids[resource_id]["quantity"] * quantity_found_coeff
            if resource_description.unit == Unit.UNIT:
                quantity_found = round(quantity_found)

            if not quantity_found:
                continue

            unit_str = self._kernel.translation.get(resource_description.unit)
            result_resource_strs.append(f"{quantity_found} {unit_str} de {resource_description.name} ")
            self._kernel.resource_lib.add_resource_to_character(
                character.id,
                resource_id=resource_id,
                quantity=quantity_found,
                commit=False,
            )

        result_stuff_strs = []
        for stuff_id in found_stuff_ids:
            # TODO BS 2019-09-26: Modify here quantity found with skills, competences, stuffs ...
            quantity_found_coeff = random.randint(0, 100) / 100
            quantity_found = round(
                production_per_stuff_ids[stuff_id]["quantity"] * quantity_found_coeff
            )
            result_stuff_strs.append(f"{quantity_found} de TODO ")
            for i in range(quantity_found):
                raise NotImplementedError("TODO")

        self._kernel.character_lib.reduce_action_points(character.id, cost=self.get_cost(character, input_))
        self._kernel.server_db_session.commit()

        parts = []
        for result_resource_str in result_resource_strs:
            parts.append(Part(text=result_resource_str))
        parts.append(Part(label="Continuer", go_back_zone=True))
        return Description(title="Vous avez trouvé", items=parts)
