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


class EmptyStuffAction(WithStuffAction):
    input_model: typing.Type[EmptyModel] = EmptyModel
    input_model_serializer = serpyco.Serializer(input_model)

    def check_is_possible(self, character: "CharacterModel", stuff: "StuffModel") -> None:
        if not stuff.filled_with_resource:
            raise ImpossibleAction("Ne contient rien")

    def check_request_is_possible(
        self, character: "CharacterModel", stuff: "StuffModel", input_: input_model
    ) -> None:
        if not stuff.filled_with_resource:
            raise ImpossibleAction("Ne contient rien")

    @classmethod
    def get_properties_from_config(cls, game_config: "GameConfig", action_config_raw: dict) -> dict:
        return {}

    def get_character_actions(
        self, character: "CharacterModel", stuff: "StuffModel"
    ) -> typing.List[CharacterActionLink]:
        actions: typing.List[CharacterActionLink] = [
            CharacterActionLink(
                name=f"Empty {stuff.name}",
                link=get_with_stuff_action_url(
                    character_id=character.id,
                    action_type=ActionType.EMPTY_STUFF,
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
        try:
            self._kernel.stuff_lib.empty_stuff(stuff)
        except CantEmpty as exc:
            return Description(title=str(exc), items=[Part(label="Revenir", go_back_zone=True)])

        return Description(
            title=f"{stuff.name} vidé(e)", items=[Part(label="Continuer", go_back_zone=True)]
        )
