# coding: utf-8
import dataclasses

import serpyco
import typing

from guilang.description import Description
from guilang.description import Part
from rolling.action.base import WithCharacterAction
from rolling.action.base import get_with_character_action_url
from rolling.exception import ImpossibleAction
from rolling.rolling_types import ActionType
from rolling.server.controller.url import DESCRIBE_LOOK_AT_CHARACTER_URL
from rolling.server.link import CharacterActionLink

if typing.TYPE_CHECKING:
    from rolling.game.base import GameConfig
    from rolling.model.character import CharacterModel


@dataclasses.dataclass
class FollowModel:
    discreetly: int = serpyco.number_field(cast_on_load=True, default=0)


@dataclasses.dataclass
class StopFollowModel:
    pass


class FollowCharacterAction(WithCharacterAction):
    input_model = FollowModel
    input_model_serializer = serpyco.Serializer(FollowModel)

    @classmethod
    def get_properties_from_config(cls, game_config: "GameConfig", action_config_raw: dict) -> dict:
        return {}

    def check_is_possible(
        self, character: "CharacterModel", with_character: "CharacterModel"
    ) -> None:
        if not (
            character.world_row_i == with_character.world_row_i
            and character.world_col_i == with_character.world_col_i
            and not self._kernel.character_lib.is_following(character.id, with_character.id)
        ):
            raise ImpossibleAction(f"{with_character.name} ne se trouve pas ici")

    def check_request_is_possible(
        self, character: "CharacterModel", with_character: "CharacterModel", input_: FollowModel
    ) -> None:
        self.check_is_possible(character, with_character)

    def _get_url(
        self,
        character: "CharacterModel",
        with_character: "CharacterModel",
        input_: typing.Optional[FollowModel] = None,
    ) -> str:
        return get_with_character_action_url(
            character_id=character.id,
            with_character_id=with_character.id,
            action_type=ActionType.FOLLOW_CHARACTER,
            query_params=self.input_model_serializer.dump(input_) if input_ else {},
            action_description_id=self._description.id,
        )

    def get_character_actions(
        self, character: "CharacterModel", with_character: "CharacterModel"
    ) -> typing.List[CharacterActionLink]:
        return [
            CharacterActionLink(
                name=f"Suivre {with_character.name}", link=self._get_url(character, with_character)
            ),
            CharacterActionLink(
                name=f"Suivre {with_character.name} discrètement",
                link=self._get_url(character, with_character, input_=FollowModel(discreetly=1)),
            ),
        ]

    def perform(
        self, character: "CharacterModel", with_character: "CharacterModel", input_: FollowModel
    ) -> Description:
        self._kernel.character_lib.set_following(
            character.id, with_character.id, discreetly=input_.discreetly
        )

        return Description(
            title=(
                f"Vous suivez {with_character.name}"
                + (" discrètement" if input_.discreetly else "")
            ),
            footer_with_character_id=with_character.id,
        )


class StopFollowCharacterAction(WithCharacterAction):
    input_model = StopFollowModel
    input_model_serializer = serpyco.Serializer(StopFollowModel)

    @classmethod
    def get_properties_from_config(cls, game_config: "GameConfig", action_config_raw: dict) -> dict:
        return {}

    def check_is_possible(
        self, character: "CharacterModel", with_character: "CharacterModel"
    ) -> None:
        if not self._kernel.character_lib.is_following(character.id, with_character.id):
            raise ImpossibleAction(f"{with_character.name} n'est pass uivis'")

    def check_request_is_possible(
        self, character: "CharacterModel", with_character: "CharacterModel", input_: FollowModel
    ) -> None:
        self.check_is_possible(character, with_character)

    def _get_url(
        self,
        character: "CharacterModel",
        with_character: "CharacterModel",
        input_: typing.Optional[FollowModel] = None,
    ) -> str:
        return get_with_character_action_url(
            character_id=character.id,
            with_character_id=with_character.id,
            action_type=ActionType.STOP_FOLLOW_CHARACTER,
            query_params=self.input_model_serializer.dump(input_) if input_ else {},
            action_description_id=self._description.id,
        )

    def get_character_actions(
        self, character: "CharacterModel", with_character: "CharacterModel"
    ) -> typing.List[CharacterActionLink]:
        if self._kernel.character_lib.is_following(
            character.id, with_character.id, discreetly=True
        ):
            return [
                CharacterActionLink(
                    name=f"Arreter de suivre {with_character.name} discrètement",
                    link=self._get_url(character, with_character),
                )
            ]
        return [
            CharacterActionLink(
                name=f"Arreter de suivre {with_character.name}",
                link=self._get_url(character, with_character),
            )
        ]

    def perform(
        self, character: "CharacterModel", with_character: "CharacterModel", input_: FollowModel
    ) -> Description:
        self._kernel.character_lib.set_not_following(character.id, with_character.id)

        return Description(
            title=f"Vous ne suivez plus {with_character.name}",
            footer_with_character_id=with_character.id,
        )
