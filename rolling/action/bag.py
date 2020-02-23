import typing

import serpyco

from guilang.description import Description
from guilang.description import Part
from rolling.action.base import WithStuffAction
from rolling.action.base import get_with_stuff_action_url
from rolling.exception import ImpossibleAction
from rolling.server.link import CharacterActionLink
from rolling.types import ActionType
from rolling.util import EmptyModel

if typing.TYPE_CHECKING:
    from rolling.model.character import CharacterModel
    from rolling.model.stuff import StuffModel
    from rolling.game.base import GameConfig
    from rolling.kernel import Kernel


class NotUseAsBagAction(WithStuffAction):
    input_model: typing.Type[object] = EmptyModel
    input_model_serializer: serpyco.Serializer

    @classmethod
    def get_properties_from_config(cls, game_config: "GameConfig", action_config_raw: dict) -> dict:
        return {}

    def check_is_possible(self, character: "CharacterModel", stuff: "StuffModel") -> None:
        bag_ids = [bag.id for bag in character.bags]
        if stuff.id not in bag_ids:
            raise ImpossibleAction("Vous n'utilisez pas ce sac")

    def check_request_is_possible(
        self, character: "CharacterModel", stuff: "StuffModel", input_: typing.Any
    ) -> None:
        self.check_is_possible(character, stuff)

    def get_character_actions(
        self, character: "CharacterModel", stuff: "StuffModel"
    ) -> typing.List[CharacterActionLink]:
        actions: typing.List[CharacterActionLink] = [
            CharacterActionLink(
                name=f"Ne plus utiliser {stuff.name} comme sac",
                link=get_with_stuff_action_url(
                    character_id=character.id,
                    action_type=ActionType.NOT_USE_AS_BAG,
                    stuff_id=stuff.id,
                    query_params={},
                    action_description_id=self._description.id,
                ),
                cost=self.get_cost(character, stuff),
            )
        ]

        return actions

    def perform(
        self, character: "CharacterModel", stuff: "StuffModel", input_: typing.Any
    ) -> Description:
        self._kernel.stuff_lib.unset_as_used_as_bag(character.id, stuff.id)
        return Description(
            title="Action effectué", items=[Part(label="Continuer", go_back_zone=True)]
        )


class UseAsBagAction(WithStuffAction):
    input_model: typing.Type[object] = EmptyModel
    input_model_serializer: serpyco.Serializer

    @classmethod
    def get_properties_from_config(cls, game_config: "GameConfig", action_config_raw: dict) -> dict:
        return {}

    def check_is_possible(self, character: "CharacterModel", stuff: "StuffModel") -> None:
        # TODO BS 2019-09-03: permit multiple bags ?
        if character.bags:
            raise ImpossibleAction("Vous utilisez déjà un sac")

    def check_request_is_possible(
        self, character: "CharacterModel", stuff: "StuffModel", input_: typing.Any
    ) -> None:
        # TODO BS 2019-09-03: check stuff owned
        if character.bags:
            raise ImpossibleAction("Vous utilisez déjà un sac")

    def get_character_actions(
        self, character: "CharacterModel", stuff: "StuffModel"
    ) -> typing.List[CharacterActionLink]:
        actions: typing.List[CharacterActionLink] = [
            CharacterActionLink(
                name=f"Utiliser {stuff.name} comme sac",
                link=get_with_stuff_action_url(
                    character_id=character.id,
                    action_type=ActionType.USE_AS_BAG,
                    stuff_id=stuff.id,
                    query_params={},
                    action_description_id=self._description.id,
                ),
                cost=self.get_cost(character, stuff),
            )
        ]

        return actions

    def perform(
        self, character: "CharacterModel", stuff: "StuffModel", input_: typing.Any
    ) -> Description:
        self._kernel.stuff_lib.set_as_used_as_bag(character.id, stuff.id)
        return Description(
            title="Action effectué", items=[Part(label="Continuer", go_back_zone=True)]
        )
