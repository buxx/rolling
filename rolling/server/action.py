# coding: utf-8
import typing

from rolling.model.action import DrinkResourceAction
from rolling.model.action import EmptyStuffAction
from rolling.model.action import FillStuffAction
from rolling.model.action import OnStuffAction
from rolling.types import ActionType

if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel
    from rolling.model.action import ActionProperties
    from rolling.model.action import CharacterAction


class ActionFactory:
    def __init__(self, kernel: "Kernel") -> None:
        self._kernel = kernel
        self._with_stuff_actions: typing.Dict[
            ActionType, typing.Type[OnStuffAction]
        ] = {
            ActionType.FILL_STUFF: FillStuffAction,
            ActionType.EMPTY_STUFF: EmptyStuffAction,
        }
        self._character_actions: typing.Dict[
            ActionType, typing.Type[CharacterAction]
        ] = {ActionType.DRINK_RESOURCE: DrinkResourceAction}

    def get_with_stuff_action(
        self, action_properties: "ActionProperties"
    ) -> OnStuffAction:
        return self._with_stuff_actions[action_properties.type_](
            self._kernel, action_properties
        )

    def get_character_action(
        self, action_properties: "ActionProperties"
    ) -> CharacterAction:
        return self._character_actions[action_properties.type_](
            self._kernel, action_properties
        )

    def get_all_character_actions(self) -> typing.List["CharacterAction"]:
        actions: typing.List["CharacterAction"] = []

        for action_class in self._character_actions.values():
            actions.append(action_class(self._kernel))

        return actions
