# coding: utf-8
import collections
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
from rolling.server.link import CharacterActionLink, ExploitableTile
from rolling.util import get_on_and_around_coordinates

if typing.TYPE_CHECKING:
    from rolling.game.base import GameConfig
    from rolling.model.character import CharacterModel


DEFAULT_SPENT_TIME = 10.0


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

    async def check_request_is_possible(
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
        seen_resource_ids: typing.List[str] = []
        resources_and_coordinates: typing.DefaultDict[
            str, typing.List[typing.Tuple[int, int]]
        ] = collections.defaultdict(list)

        for inspect_row_i, inspect_col_i in inspect_zone_positions:
            for build in self._kernel.build_lib.get_zone_build(
                world_row_i=character.world_row_i,
                world_col_i=character.world_col_i,
                zone_row_i=inspect_row_i,
                zone_col_i=inspect_col_i,
                with_seeded_with=True,
            ):
                resources_and_coordinates[build.seeded_with].append(
                    (build.zone_row_i, build.zone_col_i)
                )
        for resource_id, coordinates in resources_and_coordinates.items():
            resource_description = self._kernel.game.config.resources[resource_id]
            query_params = self.input_model(resource_id=resource_id)
            character_actions.append(
                CharacterActionLink(
                    name=f"Récolter de {resource_description.name}",
                    link=get_character_action_url(
                        character_id=character.id,
                        action_type=ActionType.HARVEST,
                        action_description_id=self._description.id,
                        query_params=self.input_model_serializer.dump(query_params),
                    ),
                    additional_link_parameters_for_quick_action={
                        "ap": min(DEFAULT_SPENT_TIME, character.action_points)
                    },
                    cost=None,
                    group_name="Récolter",
                    classes1=["HARVEST"],
                    classes2=[build.seeded_with],
                    # rollgui2 compatibility
                    all_tiles_at_once=True,
                    exploitable_tiles=[
                        ExploitableTile(
                            zone_row_i=zone_row_i,
                            zone_col_i=zone_col_i,
                            classes=[resource_id],
                        )
                        for (zone_row_i, zone_col_i) in coordinates
                    ],
                )
            )

        return character_actions

    def get_quick_actions(
        self, character: "CharacterModel"
    ) -> typing.List[CharacterActionLink]:
        return [
            link.clone_for_quick_action()
            for link in self.get_character_actions(character)
        ]

    async def perform(
        self, character: "CharacterModel", input_: HarvestModel
    ) -> Description:
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
                                default_value="5.0",
                                min_value=1.0,
                                max_value=character.action_points,
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
        not_enough_ap = False
        for inspect_row_i, inspect_col_i in inspect_zone_positions:
            if character.action_points < resource_description.harvest_cost_per_tile:
                not_enough_ap = True
                break
            if expected_ap < resource_description.harvest_cost_per_tile:
                not_enough_ap = True
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
                    await self._kernel.farming_lib.harvest(
                        build, character_doc, commit=True
                    )

                    expected_ap -= resource_description.harvest_cost_per_tile
                    spent_ap += resource_description.harvest_cost_per_tile
                    collected_quantity += (
                        resource_description.harvest_production_per_tile
                    )

        quick_action_response = f"{collected_quantity}{self._kernel.translation.get(resource_description.unit, short=True)} ({resource_description.name})"
        if not collected_quantity:
            quick_action_response = "Rien à récolter"

        return Description(
            title=f"Récolter de {resource_description.name}",
            items=[
                Part(
                    text=f"{collected_quantity} {self._kernel.translation.get(resource_description.unit)} "
                    "récoltés ({spent_ap} Point d'Actions dépensés)"
                )
            ],
            quick_action_response=quick_action_response,
            not_enough_ap=not_enough_ap,
        )
