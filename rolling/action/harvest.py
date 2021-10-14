# coding: utf-8
import dataclasses

import serpyco
import typing

from guilang.description import Description
from guilang.description import Part
from guilang.description import Type
from rolling.action.base import CharacterAction
from rolling.action.base import get_character_action_url
from rolling.exception import ImpossibleAction
from rolling.rolling_types import ActionType
from rolling.server.link import CharacterActionLink
from rolling.util import get_on_and_around_coordinates

if typing.TYPE_CHECKING:
    from rolling.game.base import GameConfig
    from rolling.model.character import CharacterModel


@dataclasses.dataclass
class HarvestModel:
    resource_id: str
    ap: typing.Optional[float] = serpyco.number_field(cast_on_load=True, default=None)


class HarvestAction(CharacterAction):
    input_model = HarvestModel
    input_model_serializer = serpyco.Serializer(input_model)

    @classmethod
    def get_properties_from_config(
        cls, game_config: "GameConfig", action_config_raw: dict
    ) -> dict:
        return {}

    def check_is_possible(self, character: "CharacterModel") -> None:
        # Search for seeded around
        inspect_zone_positions = get_on_and_around_coordinates(
            character.zone_row_i, character.zone_col_i
        )
        for inspect_row_i, inspect_col_i in inspect_zone_positions:
            for _ in self._kernel.build_lib.get_zone_build(
                world_row_i=character.world_row_i,
                world_col_i=character.world_col_i,
                zone_row_i=inspect_row_i,
                zone_col_i=inspect_col_i,
                # To permit action display, simply check if seeded
                with_seeded_with=True,
            ):
                return

        raise ImpossibleAction("Il n'y a rien à récolter ici")

    def check_request_is_possible(
        self, character: "CharacterModel", input_: input_model
    ) -> None:
        inspect_zone_positions = get_on_and_around_coordinates(
            character.zone_row_i, character.zone_col_i
        )
        for inspect_row_i, inspect_col_i in inspect_zone_positions:
            for build in self._kernel.build_lib.get_zone_build(
                world_row_i=character.world_row_i,
                world_col_i=character.world_col_i,
                zone_row_i=inspect_row_i,
                zone_col_i=inspect_col_i,
                with_seeded_with=True,
                seeded_with=input_.resource_id,
            ):
                if self._kernel.farming_lib.can_be_collected(build):
                    return True

        resource_description = self._kernel.game.config.resources[input_.resource_id]
        raise ImpossibleAction(
            f"Il n'y a pas (encore ?) de '{resource_description.name}' à récolter"
        )

    def get_character_actions(
        self, character: "CharacterModel"
    ) -> typing.List[CharacterActionLink]:
        inspect_zone_positions = get_on_and_around_coordinates(
            character.zone_row_i, character.zone_col_i
        )
        character_actions: typing.List[CharacterActionLink] = []

        inspect_zone_positions = get_on_and_around_coordinates(
            character.zone_row_i, character.zone_col_i
        )
        for inspect_row_i, inspect_col_i in inspect_zone_positions:
            for build in self._kernel.build_lib.get_zone_build(
                world_row_i=character.world_row_i,
                world_col_i=character.world_col_i,
                zone_row_i=inspect_row_i,
                zone_col_i=inspect_col_i,
                with_seeded_with=True,
            ):
                resource_description = self._kernel.game.config.resources[
                    build.seeded_with
                ]
                query_params = self.input_model(resource_id=build.seeded_with)
                character_actions.append(
                    CharacterActionLink(
                        name=f"Récolter de {resource_description.name}",
                        link=get_character_action_url(
                            character_id=character.id,
                            action_type=ActionType.HARVEST,
                            action_description_id=self._description.id,
                            query_params=self.input_model_serializer.dump(query_params),
                        ),
                        cost=None,
                        group_name="Récolter",
                    )
                )

        return character_actions

    def perform(self, character: "CharacterModel", input_: HarvestModel) -> Description:
        resource_description = self._kernel.game.config.resources[input_.resource_id]

        if input_.ap is None:
            return Description(
                title=f"Récolter de {resource_description.name}",
                items=[
                    Part(
                        is_form=True,
                        form_values_in_query=True,
                        form_action=get_character_action_url(
                            character_id=character.id,
                            action_type=ActionType.HARVEST,
                            action_description_id=self._description.id,
                            query_params=self.input_model_serializer.dump(input_),
                        ),
                        items=[
                            Part(
                                label=f"Y passer combien de temps (Points d'Actions) ?",
                                type_=Type.NUMBER,
                                name="ap",
                            )
                        ],
                    )
                ],
            )

        inspect_zone_positions = get_on_and_around_coordinates(
            character.zone_row_i, character.zone_col_i
        )
        collected_quantity = 0.0
        expected_ap = input_.ap
        spent_ap = 0.0
        character_doc = self._kernel.character_lib.get_document(character.id)
        for inspect_row_i, inspect_col_i in inspect_zone_positions:
            if character.action_points < resource_description.harvest_cost_per_tile:
                break
            if expected_ap < resource_description.harvest_cost_per_tile:
                break

            # In reality, should be only one land per position
            for build in self._kernel.build_lib.get_zone_build(
                world_row_i=character.world_row_i,
                world_col_i=character.world_col_i,
                zone_row_i=inspect_row_i,
                zone_col_i=inspect_col_i,
                with_seeded_with=True,
                seeded_with=input_.resource_id,
            ):
                if self._kernel.farming_lib.can_be_collected(build):
                    self._kernel.farming_lib.harvest(build, character_doc, commit=True)

                    expected_ap -= resource_description.harvest_cost_per_tile
                    spent_ap += resource_description.harvest_cost_per_tile
                    collected_quantity += (
                        resource_description.harvest_production_per_tile
                    )

        return Description(
            title=f"Récolter de {resource_description.name}",
            items=[
                Part(
                    text=f"{collected_quantity} {self._kernel.translation.get(resource_description.unit)} "
                    "récoltés ({spent_ap} Point d'Actions dépensés)"
                )
            ],
        )
