# coding: utf-8
import typing

import serpyco

from guilang.description import Description
from guilang.description import Part
from rolling.action.base import WithStuffAction
from rolling.action.base import get_with_stuff_action_url
from rolling.exception import CantFill
from rolling.exception import ImpossibleAction
from rolling.model.character import FillStuffWithResourceModel
from rolling.server.link import CharacterActionLink
from rolling.types import ActionType

if typing.TYPE_CHECKING:
    from rolling.model.character import CharacterModel
    from rolling.model.stuff import StuffModel
    from rolling.game.base import GameConfig


class FillStuffAction(WithStuffAction):
    input_model: typing.Type[FillStuffWithResourceModel] = FillStuffWithResourceModel
    input_model_serializer = serpyco.Serializer(input_model)

    @classmethod
    def get_properties_from_config(cls, game_config: "GameConfig", action_config_raw: dict) -> dict:
        return {}

    def check_is_possible(self, character: "CharacterModel", stuff: "StuffModel") -> None:
        for fill_acceptable_type in self._kernel.game.config.fill_with_material_ids:
            for resource in self._kernel.game.world_manager.get_resource_on_or_around(
                world_row_i=character.world_row_i,
                world_col_i=character.world_col_i,
                zone_row_i=character.zone_row_i,
                zone_col_i=character.zone_col_i,
                material_type=fill_acceptable_type,
            ):
                return

        raise ImpossibleAction("Rien à proximité ne correspond")

    def check_request_is_possible(
        self, character: "CharacterModel", stuff: "StuffModel", input_: input_model
    ) -> None:
        # TODO BS 2019-08-01: check owned
        self.check_is_possible(character, stuff)

    def get_character_actions(
        self, character: "CharacterModel", stuff: "StuffModel"
    ) -> typing.List[CharacterActionLink]:
        actions: typing.List[CharacterActionLink] = []

        for fill_acceptable_type in self._kernel.game.config.fill_with_material_ids:
            for resource in self._kernel.game.world_manager.get_resource_on_or_around(
                world_row_i=character.world_row_i,
                world_col_i=character.world_col_i,
                zone_row_i=character.zone_row_i,
                zone_col_i=character.zone_col_i,
                material_type=fill_acceptable_type,
            ):
                query_params = self.input_model(resource_id=resource.id)
                actions.append(
                    CharacterActionLink(
                        name=f"Fill {stuff.name} with {resource.name}",
                        link=get_with_stuff_action_url(
                            character_id=character.id,
                            action_type=ActionType.FILL_STUFF,
                            stuff_id=stuff.id,
                            query_params=self.input_model_serializer.dump(query_params),
                        ),
                        cost=self.get_cost(character, stuff),
                    )
                )

        return actions

    def perform(
        self, character: "CharacterModel", stuff: "StuffModel", input_: input_model
    ) -> Description:
        try:
            self._kernel.stuff_lib.fill_stuff_with_resource(stuff, input_.resource_id)
        except CantFill as exc:
            return Description(title=str(exc), items=[Part(label="Revenir", go_back_zone=True)])

        return Description(
            title=f"{stuff.name} rempli(e) avec {input_.resource_id}",
            items=[Part(label="Continuer", go_back_zone=True)],
        )
