# coding: utf-8
import typing

import serpyco

from guilang.description import Description
from guilang.description import Part
from rolling.action.base import WithStuffAction
from rolling.action.base import get_with_stuff_action_url
from rolling.exception import CantEmpty
from rolling.exception import ImpossibleAction
from rolling.server.link import CharacterActionLink
from rolling.types import ActionType
from rolling.util import EmptyModel

if typing.TYPE_CHECKING:
    from rolling.model.character import CharacterModel
    from rolling.model.stuff import StuffModel
    from rolling.game.base import GameConfig


class DropStuffAction(WithStuffAction):
    input_model: typing.Type[EmptyModel] = EmptyModel
    input_model_serializer = serpyco.Serializer(input_model)

    def check_is_possible(
        self, character: "CharacterModel", stuff: "StuffModel"
    ) -> None:
        if stuff.carried_by != character.id:
            raise ImpossibleAction("Vous ne possedez pas cet objet")

    def check_request_is_possible(
        self, character: "CharacterModel", stuff: "StuffModel", input_: input_model
    ) -> None:
        self.check_is_possible(character, stuff)

    @classmethod
    def get_properties_from_config(
        cls, game_config: "GameConfig", action_config_raw: dict
    ) -> dict:
        return {}

    def get_character_actions(
        self, character: "CharacterModel", stuff: "StuffModel"
    ) -> typing.List[CharacterActionLink]:
        actions: typing.List[CharacterActionLink] = [
            CharacterActionLink(
                name=f"Laisser {stuff.name} ici",
                link=get_with_stuff_action_url(
                    character_id=character.id,
                    action_type=ActionType.DROP_STUFF,
                    stuff_id=stuff.id,
                    query_params={},
                ),
                cost=self.get_cost(character, stuff),
            )
        ]

        return actions

    def perform(
        self, character: "CharacterModel", stuff: "StuffModel", input_: input_model
    ) -> Description:
        self._kernel.stuff_lib.drop(
            stuff.id,
            world_row_i=character.world_row_i,
            world_col_i=character.world_col_i,
            zone_row_i=character.zone_row_i,
            zone_col_i=character.zone_col_i,
        )
        return Description(
            title=f"{stuff.name} laissé ici",
            items=[Part(label="Continuer", go_back_zone=True)],
        )
