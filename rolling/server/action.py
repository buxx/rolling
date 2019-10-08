# coding: utf-8
import typing

from rolling.action.bag import NotUseAsBagAction
from rolling.action.bag import UseAsBagAction
from rolling.action.base import CharacterAction
from rolling.action.base import WithBuildAction
from rolling.action.base import WithResourceAction
from rolling.action.base import WithStuffAction
from rolling.action.build import BeginBuildAction
from rolling.action.build import BringResourcesOnBuild
from rolling.action.build import ConstructBuild
from rolling.action.collect import CollectResourceAction
from rolling.action.drink import DrinkResourceAction
from rolling.action.drink import DrinkStuffAction
from rolling.action.drop import DropResourceAction
from rolling.action.drop import DropStuffAction
from rolling.action.eat import EatResourceAction
from rolling.action.eat import EatStuffAction
from rolling.action.empty import EmptyStuffAction
from rolling.action.fill import FillStuffAction
from rolling.action.hunt import SearchFoodAction
from rolling.action.mix import MixResourcesAction
from rolling.types import ActionType

if typing.TYPE_CHECKING:
    from rolling.kernel import Kernel
    from rolling.action.base import ActionDescriptionModel


class ActionFactory:
    actions: typing.Dict[
        ActionType, typing.Type[typing.Union[CharacterAction, WithStuffAction]]
    ] = {
        ActionType.FILL_STUFF: FillStuffAction,
        ActionType.EMPTY_STUFF: EmptyStuffAction,
        ActionType.DRINK_STUFF: DrinkStuffAction,
        ActionType.DRINK_RESOURCE: DrinkResourceAction,
        ActionType.COLLECT_RESOURCE: CollectResourceAction,
        ActionType.USE_AS_BAG: UseAsBagAction,
        ActionType.NOT_USE_AS_BAG: NotUseAsBagAction,
        ActionType.DROP_STUFF: DropStuffAction,
        ActionType.DROP_RESOURCE: DropResourceAction,
        ActionType.MIX_RESOURCES: MixResourcesAction,
        ActionType.EAT_STUFF: EatStuffAction,
        ActionType.EAT_RESOURCE: EatResourceAction,
        ActionType.SEARCH_FOOD: SearchFoodAction,
        ActionType.BEGIN_BUILD: BeginBuildAction,
        ActionType.BRING_RESOURCE_ON_BUILD: BringResourcesOnBuild,
        ActionType.CONSTRUCT_BUILD: ConstructBuild,
    }

    def __init__(self, kernel: "Kernel") -> None:
        self._kernel = kernel
        self._with_stuff_actions: typing.Dict[
            ActionType, typing.Type[WithStuffAction]
        ] = {
            ActionType.FILL_STUFF: FillStuffAction,
            ActionType.EMPTY_STUFF: EmptyStuffAction,
            ActionType.DRINK_STUFF: DrinkStuffAction,
            ActionType.USE_AS_BAG: UseAsBagAction,
            ActionType.NOT_USE_AS_BAG: NotUseAsBagAction,
            ActionType.DROP_STUFF: DropStuffAction,
            ActionType.EAT_STUFF: EatStuffAction,
        }
        self._with_resource_actions: typing.Dict[
            ActionType, typing.Type[WithResourceAction]
        ] = {
            ActionType.DROP_RESOURCE: DropResourceAction,
            ActionType.MIX_RESOURCES: MixResourcesAction,
            ActionType.EAT_RESOURCE: EatResourceAction,
        }
        self._character_actions: typing.Dict[
            ActionType, typing.Type[CharacterAction]
        ] = {
            ActionType.DRINK_RESOURCE: DrinkResourceAction,
            ActionType.COLLECT_RESOURCE: CollectResourceAction,
            ActionType.SEARCH_FOOD: SearchFoodAction,
        }
        self._build_actions: typing.Dict[ActionType, typing.Type[CharacterAction]] = {
            ActionType.BEGIN_BUILD: BeginBuildAction
        }
        self._with_build_actions: typing.Dict[
            ActionType, typing.Type[WithBuildAction]
        ] = {
            ActionType.BRING_RESOURCE_ON_BUILD: BringResourcesOnBuild,
            ActionType.CONSTRUCT_BUILD: ConstructBuild,
        }

    def get_with_stuff_action(
        self, action_description: "ActionDescriptionModel"
    ) -> WithStuffAction:
        return self._with_stuff_actions[action_description.action_type](
            self._kernel, description=action_description
        )

    def get_with_resource_action(
        self, action_description: "ActionDescriptionModel"
    ) -> WithResourceAction:
        return self._with_resource_actions[action_description.action_type](
            self._kernel, description=action_description
        )

    def get_character_action(
        self, action_description: "ActionDescriptionModel"
    ) -> CharacterAction:
        return self._character_actions[action_description.action_type](
            self._kernel, description=action_description
        )

    def get_build_action(
        self, action_description: "ActionDescriptionModel"
    ) -> CharacterAction:
        return self._build_actions[action_description.action_type](
            self._kernel, description=action_description
        )

    def get_with_build_action(
        self, action_description: "ActionDescriptionModel"
    ) -> WithBuildAction:
        return self._with_build_actions[action_description.action_type](
            self._kernel, description=action_description
        )

    def get_all_character_actions(self) -> typing.List[CharacterAction]:
        actions: typing.List[CharacterAction] = []

        for action_type, action_class in self._character_actions.items():
            for action_description in self._kernel.game.config.actions[action_type]:
                actions.append(
                    action_class(kernel=self._kernel, description=action_description)
                )

        return actions

    def get_all_build_actions(self) -> typing.List[CharacterAction]:
        actions: typing.List[CharacterAction] = []

        for action_type, action_class in self._build_actions.items():
            for action_description in self._kernel.game.config.actions[action_type]:
                actions.append(
                    action_class(kernel=self._kernel, description=action_description)
                )

        return actions

    def get_all_with_build_actions(self) -> typing.List[WithBuildAction]:
        actions: typing.List[WithBuildAction] = []

        for action_type, action_class in self._with_build_actions.items():
            for action_description in self._kernel.game.config.actions[action_type]:
                actions.append(
                    action_class(kernel=self._kernel, description=action_description)
                )

        return actions

    def create_action(
        self,
        action_type: ActionType,
        action_description_id: typing.Optional[str] = None,
    ) -> typing.Union[CharacterAction, WithStuffAction]:
        if (
            action_type in self._with_stuff_actions
            or action_type in self._with_resource_actions
            or action_type in self._character_actions
            or action_type in self._build_actions
            or action_type in self._with_build_actions
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
