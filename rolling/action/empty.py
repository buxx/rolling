# coding: utf-8
import serpyco
import typing

from guilang.description import Description
from guilang.description import Part
from rolling.action.base import WithStuffAction
from rolling.action.base import get_with_stuff_action_url
from rolling.exception import CantEmpty
from rolling.exception import ImpossibleAction
from rolling.exception import WrongInputError
from rolling.rolling_types import ActionType
from rolling.server.controller.url import DESCRIBE_LOOK_AT_STUFF_URL
from rolling.server.link import CharacterActionLink
from rolling.util import EmptyModel

if typing.TYPE_CHECKING:
    from rolling.game.base import GameConfig
    from rolling.model.character import CharacterModel
    from rolling.model.stuff import StuffModel


class EmptyStuffAction(WithStuffAction):
    exclude_from_actions_page = True
    input_model: typing.Type[EmptyModel] = EmptyModel
    input_model_serializer = serpyco.Serializer(input_model)

    def check_is_possible(
        self, character: "CharacterModel", stuff: "StuffModel"
    ) -> None:
        if not stuff.filled_with_resource:
            raise ImpossibleAction("Ne contient rien")

    async def check_request_is_possible(
        self, character: "CharacterModel", stuff: "StuffModel", input_: input_model
    ) -> None:
        if not stuff.filled_with_resource:
            raise WrongInputError("Ne contient rien")

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
                name=f"Vider {stuff.name}",
                link=get_with_stuff_action_url(
                    character_id=character.id,
                    action_type=ActionType.EMPTY_STUFF,
                    stuff_id=stuff.id,
                    query_params={},
                    action_description_id=self._description.id,
                ),
                cost=self.get_cost(character, stuff),
            )
        ]

        return actions

    async def perform(
        self, character: "CharacterModel", stuff: "StuffModel", input_: input_model
    ) -> Description:
        footer_links = [
            Part(
                is_link=True,
                label="Voir l'objet",
                form_action=DESCRIBE_LOOK_AT_STUFF_URL.format(
                    character_id=character.id, stuff_id=stuff.id
                ),
                classes=["primary"],
            )
        ]

        try:
            self._kernel.stuff_lib.empty_stuff(stuff)
        except CantEmpty as exc:
            return Description(title=str(exc), footer_links=footer_links)
        return Description(
            title=f"{stuff.name} vidé(e)",
            footer_links=footer_links,
            reload_inventory=True,
        )
