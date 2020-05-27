# coding: utf-8
import dataclasses
import typing

import serpyco

from guilang.description import Description, Part, Type
from rolling.action.base import WithCharacterAction, get_with_character_action_url
from rolling.exception import ImpossibleAction
from rolling.model.stuff import StuffModel
from rolling.server.link import CharacterActionLink
from rolling.types import ActionType

if typing.TYPE_CHECKING:
    from rolling.game.base import GameConfig
    from rolling.model.character import CharacterModel


@dataclasses.dataclass
class TakeOnModel:
    take_stuff_id: typing.Optional[int] = None
    take_stuff_quantity: typing.Optional[int] = None
    take_resource_id: typing.Optional[str] = None
    take_resource_quantity: typing.Optional[float] = None


class TakeOnCharacterAction(WithCharacterAction):
    input_model = TakeOnModel
    input_model_serializer = serpyco.Serializer(TakeOnModel)

    @classmethod
    def get_properties_from_config(cls, game_config: "GameConfig", action_config_raw: dict) -> dict:
        return {}

    def check_is_possible(
        self, character: "CharacterModel", with_character: "CharacterModel"
    ) -> None:
        # TODO BS: Check here is possible too with affinities (like chief
        #  can manipulate, firendship, etc)
        if not with_character.vulnerable:
            raise ImpossibleAction(f"{with_character.name} est en capacité de se defendre")

    def check_request_is_possible(
        self, character: "CharacterModel", with_character: "CharacterModel", input_: TakeOnModel
    ) -> None:
        self.check_is_possible(character, with_character)

    def get_character_actions(
        self, character: "CharacterModel", with_character: "CharacterModel"
    ) -> typing.List[CharacterActionLink]:
        return [
            CharacterActionLink(
                name="Prendre",
                link=get_with_character_action_url(
                    character_id=character.id,
                    with_character_id=with_character.id,
                    action_type=ActionType.TAKE_ON_CHARACTER,
                    query_params={},
                    action_description_id=self._description.id,
                )
            )
        ]

    def perform(
        self, character: "CharacterModel", with_character: "CharacterModel", input_: TakeOnModel
    ) -> Description:
        if input_.take_stuff_id is None or input_.take_resource_id is None:
            return self._get_take_something_description(character, with_character, input_)

        if input_.take_stuff_id is not None and input_.take_stuff_quantity is None:
            stuff: StuffModel = self._kernel.stuff_lib.get_stuff_doc(input_.take_stuff_id)
            likes_this_stuff = self._kernel.stuff_lib.get(
                with_character.id, exclude_crafting=False, stuff_id=stuff.stuff_id,
            )
            if len(likes_this_stuff) > 1:
                return Description(
                    title=f"Prendre {stuff.name} sur {with_character.name}",
                    items=[
                        Part(
                            is_form=True,
                            form_values_in_query=True,
                            submit_label="Prendre",
                            items=[
                                Part(
                                    label="Quantité ?",
                                    type_=Type.NUMBER,
                                    name="take_stuff_quantity",
                                    default_value=str(len(likes_this_stuff)),
                                )
                            ]
                        )
                    ]
                )


