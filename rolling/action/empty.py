# coding: utf-8
import typing

from rolling.action.base import WithStuffAction
from rolling.server.controller.url import DESCRIBE_EMPTY_STUFF
from rolling.server.link import CharacterActionLink


class EmptyStuffAction(WithStuffAction):
    def get_character_actions(
        self, character: "CharacterModel", stuff: "StuffModel"
    ) -> typing.List[CharacterActionLink]:
        actions: typing.List[CharacterActionLink] = [
            CharacterActionLink(
                name=f"Empty {stuff.name}",
                link=DESCRIBE_EMPTY_STUFF.format(
                    character_id=character.id, stuff_id=stuff.id
                ),
                cost=self.get_cost(character, stuff),
            )
        ]

        return actions
