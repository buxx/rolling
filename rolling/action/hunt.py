# coding: utf-8
import random
import typing

import serpyco

from guilang.description import Description
from guilang.description import Part
from rolling.action.base import CharacterAction
from rolling.action.base import get_character_action_url
from rolling.action.utils import check_common_is_possible
from rolling.action.utils import fill_base_action_properties
from rolling.exception import ImpossibleAction
from rolling.exception import RollingError
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
    def get_properties_from_config(cls, game_config: "GameConfig", action_config_raw: dict) -> dict:
        for produce in action_config_raw["produce"]:
            if "resource" not in produce and "stuff" not in produce:
                raise RollingError(
                    "Misconfiguration for action SearchFoodAction (production "
                    "must contain stuff or resource key"
                )

        properties = fill_base_action_properties(cls, game_config, {}, action_config_raw)
        properties.update({"produce": action_config_raw["produce"]})
        return properties

    def check_is_possible(self, character: "CharacterModel") -> None:
        check_common_is_possible(
            kernel=self._kernel, description=self._description, character=character
        )

    def check_request_is_possible(self, character: "CharacterModel", input_: typing.Any) -> None:
        self.check_is_possible(character)

    def get_character_actions(
        self, character: "CharacterModel"
    ) -> typing.List[CharacterActionLink]:
        try:
            self.check_is_possible(character)
        except ImpossibleAction:
            return []

        return [
            CharacterActionLink(
                name=self._description.name,
                link=get_character_action_url(
                    character_id=character.id,
                    action_type=ActionType.SEARCH_FOOD,
                    action_description_id=self._description.id,
                    query_params={},
                ),
                group_name="Chercher de la nourriture",
                cost=self.get_cost(character),
            )
        ]

    def perform(self, character: "CharacterModel", input_: typing.Any) -> Description:
        productions = self._description.properties["produce"]
        production_per_resource_ids: typing.Dict[str, dict] = {}
        production_per_stuff_ids: typing.Dict[str, dict] = {}
        zone_available_production_resource_ids: typing.List[str] = []
        zone_available_production_stuff_ids: typing.List[str] = []
        zone_state = self._kernel.game.world_manager.get_zone_state(
            world_row_i=character.world_row_i, world_col_i=character.world_col_i
        )

        for production in productions:
            if "resource" in production:
                resource_id = production["resource"]
                if zone_state.is_there_resource(
                    resource_id, check_from_absolute=True, check_from_tiles=False
                ):
                    zone_available_production_resource_ids.append(resource_id)
                    production_per_resource_ids[resource_id] = production
            # FIXME BS: clarify "stuff" in hunt context
            elif "stuff" in production:
                stuff_id = production["stuff"]
                if zone_state.is_there_stuff(stuff_id):
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
            quantity_found = (
                production_per_resource_ids[resource_id]["quantity"] * quantity_found_coeff
            )
            if resource_description.unit == Unit.UNIT:
                quantity_found = round(quantity_found)

            if not quantity_found:
                continue

            unit_str = self._kernel.translation.get(resource_description.unit)
            result_resource_strs.append(
                f"{quantity_found} {unit_str} de {resource_description.name} "
            )
            self._kernel.resource_lib.add_resource_to(
                character_id=character.id,
                resource_id=resource_id,
                quantity=quantity_found,
                commit=False,
            )
            zone_state.reduce_resource(resource_id, quantity_found, commit=False)

        result_stuff_strs = []
        for stuff_id in found_stuff_ids:
            # TODO BS 2019-09-26: Modify here quantity found with skills, competences, stuffs ...
            stuff_properties = self._kernel.game.stuff_manager.get_stuff_properties_by_id(stuff_id)
            quantity_found_coeff = random.randint(0, 100) / 100
            quantity_found = round(
                production_per_stuff_ids[stuff_id]["quantity"] * quantity_found_coeff
            )
            result_stuff_strs.append(f"{quantity_found} de {stuff_properties.name} ")
            for i in range(quantity_found):
                stuff_doc = self._kernel.stuff_lib.create_document_from_properties(
                    stuff_properties,
                    stuff_id=stuff_id,
                    world_row_i=character.world_row_i,
                    world_col_i=character.world_col_i,
                    zone_col_i=character.zone_row_i,
                    zone_row_i=character.zone_col_i,
                )
                stuff_doc.carried_by_id = character.id

                self._kernel.stuff_lib.add_stuff(stuff_doc, commit=False)
            zone_state.reduce_stuff(stuff_id, quantity_found, commit=False)

        self._kernel.character_lib.reduce_action_points(
            character.id, cost=self.get_cost(character, input_)
        )
        self._kernel.server_db_session.commit()

        parts = []
        for result_resource_str in result_resource_strs:
            parts.append(Part(text=result_resource_str))

        for result_stuff_str in result_stuff_strs:
            parts.append(Part(text=result_stuff_str))

        parts.append(
            Part(is_link=True, go_back_zone=True, label="Retourner à l'écran de déplacements")
        )
        return Description(title="Vous avez trouvé", items=parts)
