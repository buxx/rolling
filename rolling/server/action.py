# coding: utf-8
import typing

from guilang.description import Description
from rolling.action.base import CharacterAction
from rolling.action.base import WithBuildAction
from rolling.action.base import WithCharacterAction
from rolling.action.base import WithResourceAction
from rolling.action.base import WithStuffAction
from rolling.action.build import BeginBuildAction
from rolling.action.build import BringResourcesOnBuild
from rolling.action.build import BuildAction
from rolling.action.build import ConstructBuildAction
from rolling.action.build_deposit import DepositToBuildAction
from rolling.action.build_power import PowerOffBuildAction
from rolling.action.build_power import PowerOnBuildAction
from rolling.action.build_take import TakeFromBuildAction
from rolling.action.cheats import CheatsCharacterAction
from rolling.action.collect import CollectResourceAction
from rolling.action.craft import BeginStuffConstructionAction
from rolling.action.craft import ContinueStuffConstructionAction
from rolling.action.craft import CraftStuffWithResourceAction
from rolling.action.harvest import HarvestAction
from rolling.action.craft import CraftStuffWithStuffAction
from rolling.action.destroy import DestroyBuildAction
from rolling.action.drink import DrinkResourceAction
from rolling.action.drink import DrinkStuffAction
from rolling.action.drop import DropResourceAction
from rolling.action.drop import DropStuffAction
from rolling.action.eat import EatResourceAction
from rolling.action.empty import EmptyStuffAction
from rolling.action.fight import AttackCharacterAction
from rolling.action.fill import FillStuffAction
from rolling.action.follow import FollowCharacterAction
from rolling.action.follow import StopFollowCharacterAction
from rolling.action.give import GiveToCharacterAction
from rolling.action.hunt import SearchFoodAction
from rolling.action.kill import KillCharacterAction
from rolling.action.knowledge import LearnKnowledgeAction
from rolling.action.knowledge import ProposeTeachKnowledgeAction
from rolling.action.knowledge import TeachKnowledgeAction
from rolling.action.mix import MixResourcesAction
from rolling.action.search import SearchMaterialAction
from rolling.action.seed import SeedAction
from rolling.action.take import TakeAction
from rolling.action.take_character import TakeFromCharacterAction
from rolling.action.take_resource import TakeResourceAction
from rolling.action.take_stuff import TakeStuffAction
from rolling.action.transfer_ground import TransfertGroundCharacterAction
from rolling.action.transform import (
    TransformResourcesIntoResourcesAction,
    TransformStuffIntoStuffAction,
)
from rolling.action.transform import TransformStuffIntoResourcesAction
from rolling.action.travel import TravelAction
from rolling.action.use import NotUseAsArmorAction
from rolling.action.use import NotUseAsBagAction
from rolling.action.use import NotUseAsShieldAction
from rolling.action.use import NotUseAsWeaponAction
from rolling.action.use import UseAsArmorAction
from rolling.action.use import UseAsBagAction
from rolling.action.use import UseAsShieldAction
from rolling.action.use import UseAsWeaponAction
from rolling.rolling_types import ActionScope
from rolling.rolling_types import ActionType
from rolling.server.document.action import AuthorizePendingActionDocument
from rolling.server.document.action import PendingActionDocument

if typing.TYPE_CHECKING:
    from rolling.action.base import ActionDescriptionModel
    from rolling.kernel import Kernel


class ActionFactory:
    actions: typing.Dict[
        ActionType, typing.Type[typing.Union[CharacterAction, WithStuffAction]]
    ] = {
        ActionType.FILL_STUFF: FillStuffAction,
        ActionType.EMPTY_STUFF: EmptyStuffAction,
        ActionType.DRINK_STUFF: DrinkStuffAction,
        ActionType.DRINK_RESOURCE: DrinkResourceAction,
        ActionType.COLLECT_RESOURCE: CollectResourceAction,
        ActionType.HARVEST: HarvestAction,
        ActionType.USE_AS_BAG: UseAsBagAction,
        ActionType.NOT_USE_AS_BAG: NotUseAsBagAction,
        ActionType.USE_AS_WEAPON: UseAsWeaponAction,
        ActionType.NOT_USE_AS_WEAPON: NotUseAsWeaponAction,
        ActionType.USE_AS_SHIELD: UseAsShieldAction,
        ActionType.NOT_USE_AS_SHIELD: NotUseAsShieldAction,
        ActionType.USE_AS_ARMOR: UseAsArmorAction,
        ActionType.NOT_USE_AS_ARMOR: NotUseAsArmorAction,
        ActionType.DROP_STUFF: DropStuffAction,
        ActionType.DROP_RESOURCE: DropResourceAction,
        ActionType.MIX_RESOURCES: MixResourcesAction,
        ActionType.EAT_RESOURCE: EatResourceAction,
        ActionType.SEARCH_FOOD: SearchFoodAction,
        ActionType.BEGIN_BUILD: BeginBuildAction,
        ActionType.BRING_RESOURCE_ON_BUILD: BringResourcesOnBuild,
        ActionType.CONSTRUCT_BUILD: ConstructBuildAction,
        ActionType.TRANSFORM_STUFF_TO_RESOURCES: TransformStuffIntoResourcesAction,
        ActionType.TRANSFORM_RESOURCES_TO_RESOURCES: TransformResourcesIntoResourcesAction,
        ActionType.CRAFT_STUFF_WITH_STUFF: CraftStuffWithStuffAction,
        ActionType.CRAFT_STUFF_WITH_RESOURCE: CraftStuffWithResourceAction,
        ActionType.TRANSFORM_STUFF_TO_STUFF: TransformStuffIntoStuffAction,
        ActionType.BEGIN_STUFF_CONSTRUCTION: BeginStuffConstructionAction,
        ActionType.CONTINUE_STUFF_CONSTRUCTION: ContinueStuffConstructionAction,
        ActionType.SEARCH_MATERIAL: SearchMaterialAction,
        ActionType.BUILD: BuildAction,
        ActionType.ATTACK_CHARACTER: AttackCharacterAction,
        ActionType.CHEATS: CheatsCharacterAction,
        ActionType.KILL_CHARACTER: KillCharacterAction,
        ActionType.TAKE_FROM_CHARACTER: TakeFromCharacterAction,
        ActionType.GIVE_TO_CHARACTER: GiveToCharacterAction,
        ActionType.FOLLOW_CHARACTER: FollowCharacterAction,
        ActionType.STOP_FOLLOW_CHARACTER: StopFollowCharacterAction,
        ActionType.LEARN_KNOWLEDGE: LearnKnowledgeAction,
        ActionType.PROPOSE_TEACH_KNOWLEDGE: ProposeTeachKnowledgeAction,
        ActionType.TEACH_KNOWLEDGE: TeachKnowledgeAction,
        ActionType.TRAVEL: TravelAction,
        ActionType.DEPOSIT_ON_BUILD: DepositToBuildAction,
        ActionType.TAKE_FROM_BUILD: TakeFromBuildAction,
        ActionType.POWER_ON_BUILD: PowerOnBuildAction,
        ActionType.POWER_OFF_BUILD: PowerOffBuildAction,
        ActionType.TRANSFER_GROUND: TransfertGroundCharacterAction,
        ActionType.TAKE_STUFF: TakeStuffAction,
        ActionType.TAKE_RESOURCE: TakeResourceAction,
        ActionType.SEED: SeedAction,
        ActionType.DESTROY_BUILD: DestroyBuildAction,
        ActionType.TAKE_AROUND: TakeAction,
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
            ActionType.TRANSFORM_STUFF_TO_RESOURCES: TransformStuffIntoResourcesAction,
            ActionType.CRAFT_STUFF_WITH_STUFF: CraftStuffWithStuffAction,
            ActionType.TRANSFORM_STUFF_TO_STUFF: TransformStuffIntoStuffAction,
            ActionType.CONTINUE_STUFF_CONSTRUCTION: ContinueStuffConstructionAction,
            ActionType.USE_AS_WEAPON: UseAsWeaponAction,
            ActionType.NOT_USE_AS_WEAPON: NotUseAsWeaponAction,
            ActionType.USE_AS_SHIELD: UseAsShieldAction,
            ActionType.NOT_USE_AS_SHIELD: NotUseAsShieldAction,
            ActionType.USE_AS_ARMOR: UseAsArmorAction,
            ActionType.NOT_USE_AS_ARMOR: NotUseAsArmorAction,
            ActionType.TAKE_STUFF: TakeStuffAction,
        }
        self._with_resource_actions: typing.Dict[
            ActionType, typing.Type[WithResourceAction]
        ] = {
            ActionType.DROP_RESOURCE: DropResourceAction,
            ActionType.MIX_RESOURCES: MixResourcesAction,
            ActionType.EAT_RESOURCE: EatResourceAction,
            ActionType.CRAFT_STUFF_WITH_RESOURCE: CraftStuffWithResourceAction,
            ActionType.TRANSFORM_RESOURCES_TO_RESOURCES: TransformResourcesIntoResourcesAction,
            ActionType.TAKE_RESOURCE: TakeResourceAction,
        }
        self._with_character_actions: typing.Dict[
            ActionType, typing.Type[WithCharacterAction]
        ] = {
            ActionType.ATTACK_CHARACTER: AttackCharacterAction,
            ActionType.KILL_CHARACTER: KillCharacterAction,
            ActionType.TAKE_FROM_CHARACTER: TakeFromCharacterAction,
            ActionType.GIVE_TO_CHARACTER: GiveToCharacterAction,
            ActionType.FOLLOW_CHARACTER: FollowCharacterAction,
            ActionType.STOP_FOLLOW_CHARACTER: StopFollowCharacterAction,
            ActionType.TEACH_KNOWLEDGE: TeachKnowledgeAction,
            ActionType.PROPOSE_TEACH_KNOWLEDGE: ProposeTeachKnowledgeAction,
        }
        self._character_actions: typing.Dict[
            ActionType, typing.Type[CharacterAction]
        ] = {
            ActionType.DRINK_RESOURCE: DrinkResourceAction,
            ActionType.COLLECT_RESOURCE: CollectResourceAction,
            ActionType.HARVEST: HarvestAction,
            ActionType.SEARCH_FOOD: SearchFoodAction,
            ActionType.BEGIN_STUFF_CONSTRUCTION: BeginStuffConstructionAction,
            ActionType.SEARCH_MATERIAL: SearchMaterialAction,
            ActionType.LEARN_KNOWLEDGE: LearnKnowledgeAction,
            ActionType.CHEATS: CheatsCharacterAction,
            ActionType.TRAVEL: TravelAction,
            ActionType.TRANSFER_GROUND: TransfertGroundCharacterAction,
            ActionType.SEED: SeedAction,
            ActionType.TAKE_AROUND: TakeAction,
        }
        self._build_actions: typing.Dict[ActionType, typing.Type[CharacterAction]] = {
            ActionType.BEGIN_BUILD: BeginBuildAction,
            ActionType.BUILD: BuildAction,
        }
        self._with_build_actions: typing.Dict[
            ActionType, typing.Type[WithBuildAction]
        ] = {
            ActionType.BRING_RESOURCE_ON_BUILD: BringResourcesOnBuild,
            ActionType.CONSTRUCT_BUILD: ConstructBuildAction,
            ActionType.DEPOSIT_ON_BUILD: DepositToBuildAction,
            ActionType.TAKE_FROM_BUILD: TakeFromBuildAction,
            ActionType.POWER_ON_BUILD: PowerOnBuildAction,
            ActionType.POWER_OFF_BUILD: PowerOffBuildAction,
            ActionType.DESTROY_BUILD: DestroyBuildAction,
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
            for action_description in self._kernel.game.config.actions.get(
                action_type, []
            ):
                actions.append(
                    action_class(kernel=self._kernel, description=action_description)
                )

        return actions

    def get_all_build_actions(self) -> typing.List[CharacterAction]:
        actions: typing.List[CharacterAction] = []

        for action_type, action_class in self._build_actions.items():
            for action_description in self._kernel.game.config.actions.get(
                action_type, []
            ):
                actions.append(
                    action_class(kernel=self._kernel, description=action_description)
                )

        return actions

    def get_all_with_build_actions(self) -> typing.List[WithBuildAction]:
        actions: typing.List[WithBuildAction] = []

        for action_type, action_class in self._with_build_actions.items():
            for action_description in self._kernel.game.config.actions.get(
                action_type, []
            ):
                actions.append(
                    action_class(kernel=self._kernel, description=action_description)
                )

        return actions

    def get_all_with_character_actions(self) -> typing.List[WithCharacterAction]:
        actions: typing.List[WithCharacterAction] = []

        for action_type, action_class in self._with_character_actions.items():
            for action_description in self._kernel.game.config.actions.get(
                action_type, []
            ):
                actions.append(
                    action_class(kernel=self._kernel, description=action_description)
                )

        return actions

    def create_action(
        self,
        action_type: ActionType,
        action_description_id: typing.Optional[str] = None,
    ) -> typing.Union[
        CharacterAction,
        WithStuffAction,
        WithCharacterAction,
        CharacterAction,
        WithResourceAction,
    ]:
        if (
            action_type in self._with_stuff_actions
            or action_type in self._with_resource_actions
            or action_type in self._character_actions
            or action_type in self._build_actions
            or action_type in self._with_build_actions
            or action_type in self._with_character_actions
        ):
            for action_description in self._kernel.game.config.actions.get(
                action_type, []
            ):
                if (
                    action_description_id is None
                    or action_description.id == action_description_id
                ):
                    return self.actions[action_type](
                        self._kernel, description=action_description
                    )

        raise NotImplementedError(f"Unknown {action_description_id}:{action_type}")

    def create_pending_action(
        self,
        action_scope: ActionScope,
        action_type: ActionType,
        action_description_id: str,
        character_id: str,
        parameters: dict,
        expire_at_turn: int,
        name: str,
        with_character_id: typing.Optional[str] = None,
        stuff_id: typing.Optional[int] = None,
        resource_id: typing.Optional[str] = None,
        suggested_by: typing.Optional[str] = None,
        delete_after_first_perform: bool = True,
    ) -> PendingActionDocument:
        pending_action_document = PendingActionDocument(
            action_scope=action_scope.value,
            action_type=action_type.value,
            action_description_id=action_description_id,
            character_id=character_id,
            parameters=parameters,
            expire_at_turn=expire_at_turn,
            with_character_id=with_character_id,
            stuff_id=stuff_id,
            resource_id=resource_id,
            suggested_by=suggested_by,
            name=name,
            delete_after_first_perform=delete_after_first_perform,
        )
        self._kernel.server_db_session.add(pending_action_document)
        self._kernel.server_db_session.commit()
        return pending_action_document

    def add_pending_action_authorization(
        self, pending_action_id: int, authorized_character_id: str
    ) -> AuthorizePendingActionDocument:
        authorization = AuthorizePendingActionDocument(
            pending_action_id=pending_action_id,
            authorized_character_id=authorized_character_id,
        )
        self._kernel.server_db_session.add(authorization)
        self._kernel.server_db_session.commit()
        return authorization

    async def execute_pending(
        self, pending_action: PendingActionDocument
    ) -> Description:
        action = self.create_action(
            action_type=ActionType(pending_action.action_type),
            action_description_id=pending_action.action_description_id,
        )
        character = self._kernel.character_lib.get(pending_action.character_id)
        if pending_action.action_scope == ActionScope.WITH_CHARACTER.value:
            with_character = self._kernel.character_lib.get(
                pending_action.with_character_id
            )
            input_ = action.input_model_from_request(pending_action.parameters)
            await action.check_request_is_possible(
                character, with_character, input_=input_
            )
            description = await action.perform(character, with_character, input_=input_)
        else:
            raise NotImplementedError("TODO")

        if pending_action.delete_after_first_perform:
            self._kernel.server_db_session.query(AuthorizePendingActionDocument).filter(
                AuthorizePendingActionDocument.pending_action_id == pending_action.id
            ).delete(synchronize_session=False)
            self._kernel.server_db_session.query(PendingActionDocument).filter(
                PendingActionDocument.id == pending_action.id
            ).delete(synchronize_session=False)
            self._kernel.server_db_session.commit()

        return description
