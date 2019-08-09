# coding: utf-8
import typing

from rolling.action.base import Action
from rolling.action.base import CharacterAction
from rolling.action.base import WithStuffAction
from rolling.action.drink import DrinkResourceAction
from rolling.action.drink import DrinkStuffAction
from rolling.action.empty import EmptyStuffAction
from rolling.action.fill import FillStuffAction
from rolling.types import ActionType

if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel
    from rolling.action.base import ActionDescriptionModel


# FIXME BS NOW: WTF two ActionFactory ?!
class ActionFactory:
    actions: typing.Dict[ActionType, typing.Type[Action]] = {
        ActionType.FILL_STUFF: FillStuffAction,
        ActionType.EMPTY_STUFF: EmptyStuffAction,
        ActionType.DRINK_STUFF: DrinkStuffAction,
        ActionType.DRINK_RESOURCE: DrinkResourceAction,
    }

    def __init__(self, kernel: "Kernel") -> None:
        self._kernel = kernel
        self._with_stuff_actions: typing.Dict[
            ActionType, typing.Type[WithStuffAction]
        ] = {
            ActionType.FILL_STUFF: FillStuffAction,
            ActionType.EMPTY_STUFF: EmptyStuffAction,
            ActionType.DRINK_STUFF: DrinkStuffAction,
        }
        self._character_actions: typing.Dict[
            ActionType, typing.Type[CharacterAction]
        ] = {ActionType.DRINK_RESOURCE: DrinkResourceAction}

    def get_with_stuff_action(
        self, action_description: "ActionDescriptionModel"
    ) -> WithStuffAction:
        return self._with_stuff_actions[action_description.action_type](
            self._kernel, description=action_description
        )

    def get_character_action(
        self, action_description: "ActionDescriptionModel"
    ) -> "CharacterAction":
        return self._character_actions[action_description.action_type](
            self._kernel, description=action_description
        )

    def create_action(
        self,
        action_type: ActionType,
        action_description_id: typing.Optional[str] = None,
    ) -> Action:
        if (
            action_type in self._with_stuff_actions
            or action_type in self._character_actions
        ):
            for action_description in self._kernel.game.config.actions[action_type]:
                if (
                    action_description_id is None
                    or action_description.id == action_description_id
                ):
                    return self.actions[action_type](
                        self._kernel, description=action_description
                    )

        raise NotImplementedError(f"Unknown {action_description_id}:{action_type}")
