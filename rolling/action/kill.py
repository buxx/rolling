# coding: utf-8
import dataclasses
import typing

import serpyco

from guilang.description import Description, Part
from rolling.action.base import WithCharacterAction, get_with_character_action_url
from rolling.exception import ImpossibleAction
from rolling.server.link import CharacterActionLink
from rolling.types import ActionType

if typing.TYPE_CHECKING:
    from rolling.game.base import GameConfig
    from rolling.model.character import CharacterModel


@dataclasses.dataclass
class EmptyModel:
    pass


class KillCharacterAction(WithCharacterAction):
    input_model = EmptyModel
    input_model_serializer = serpyco.Serializer(EmptyModel)

    @classmethod
    def get_properties_from_config(cls, game_config: "GameConfig", action_config_raw: dict) -> dict:
        return {}

    def check_is_possible(
        self, character: "CharacterModel", with_character: "CharacterModel"
    ) -> None:
        if not with_character.vulnerable:
            raise ImpossibleAction(f"{with_character.name} est en capacité de se defendre")

    def check_request_is_possible(
        self, character: "CharacterModel", with_character: "CharacterModel", input_: typing.Any
    ) -> None:
        self.check_is_possible(character, with_character)

    def get_character_actions(
        self, character: "CharacterModel", with_character: "CharacterModel"
    ) -> typing.List[CharacterActionLink]:
        return [
            CharacterActionLink(
                name="Tuer",
                link=get_with_character_action_url(
                    character_id=character.id,
                    with_character_id=with_character.id,
                    action_type=ActionType.KILL_CHARACTER,
                    query_params={},
                    action_description_id=self._description.id,
                ),
            )
        ]

    def perform(
        self, character: "CharacterModel", with_character: "CharacterModel", input_: typing.Any
    ) -> Description:
        self._kernel.character_lib.kill(with_character.id)
        return Description(
            title=f"Vous avez tué {with_character.name}",
            items=[
                Part(is_link=True, go_back_zone=True)
            ]
        )
