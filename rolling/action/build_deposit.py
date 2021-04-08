# coding: utf-8
import dataclasses

import serpyco
from sqlalchemy.orm.exc import NoResultFound
import typing

from guilang.description import Description
from rolling.action.base import WithBuildAction
from rolling.action.base import get_with_build_action_url
from rolling.exception import ImpossibleAction
from rolling.model.resource import CarriedResourceDescriptionModel
from rolling.model.stuff import StuffModel
from rolling.rolling_types import ActionType
from rolling.server.link import CharacterActionLink
from rolling.server.transfer import TransferStuffOrResources
from rolling.util import ExpectedQuantityContext
from rolling.util import InputQuantityContext

if typing.TYPE_CHECKING:
    from rolling.game.base import GameConfig
    from rolling.kernel import Kernel
    from rolling.model.build import BuildDocument
    from rolling.model.character import CharacterModel


class DepositStuffOrResources(TransferStuffOrResources):
    stuff_quantity_parameter_name = "deposit_stuff_quantity"
    resource_quantity_parameter_name = "deposit_resource_quantity"

    def __init__(
        self,
        kernel: "Kernel",
        from_character: "CharacterModel",
        to_build: "BuildDocument",
        description_id: str,
    ) -> None:
        super().__init__()
        self.__kernel = kernel
        self._from_character = from_character
        self._to_build = to_build
        self._description_id = description_id

    @property
    def _kernel(self) -> "Kernel":
        return self.__kernel

    def _get_available_stuffs(self) -> typing.List[StuffModel]:
        if self._kernel.game.config.builds[self._to_build.build_id].allow_deposit_limited:
            return []

        return self._kernel.stuff_lib.get_carried_by(
            self._from_character.id, exclude_crafting=False
        )

    def _get_available_resources(self) -> typing.List[CarriedResourceDescriptionModel]:
        carried_resources = self._kernel.resource_lib.get_carried_by(self._from_character.id)

        build_description = self._kernel.game.config.builds[self._to_build.build_id]
        if build_description.allow_deposit_limited:
            return [
                carried_resource
                for carried_resource in carried_resources
                if carried_resource.id in build_description.allowed_resource_ids
            ]

        return carried_resources

    def _get_url(
        self,
        stuff_id: typing.Optional[int] = None,
        stuff_quantity: typing.Optional[int] = None,
        resource_id: typing.Optional[str] = None,
        resource_quantity: typing.Optional[float] = None,
    ) -> str:
        return get_with_build_action_url(
            character_id=self._from_character.id,
            build_id=self._to_build.id,
            action_type=ActionType.DEPOSIT_ON_BUILD,
            query_params=DepositToBuildAction.input_model_serializer.dump(
                DepositToModel(deposit_stuff_id=stuff_id, deposit_resource_id=resource_id)
            ),
            action_description_id=self._description_id,
        )

    def _get_title(
        self, stuff_id: typing.Optional[int] = None, resource_id: typing.Optional[str] = None
    ) -> str:
        build_name = self._kernel.game.config.builds[self._to_build.build_id].name

        if stuff_id is not None:
            stuff = self._kernel.stuff_lib.get_stuff(stuff_id)
            return f"Déposer {stuff.name} sur {build_name}"

        if resource_id is not None:
            resource_description = self._kernel.game.config.resources[resource_id]
            return f"Déposer {resource_description.name} sur {build_name}"

        return f"Déposer sur {build_name}"

    def _get_footer_character_id(self, sizing_up_quantity: bool) -> typing.Optional[str]:
        return None

    def _get_footer_affinity_id(self, sizing_up_quantity: bool) -> typing.Optional[int]:
        return None

    def _get_footer_build_id(self, sizing_up_quantity: bool) -> typing.Optional[int]:
        return self._to_build.id

    def _get_stuff(self, stuff_id: int) -> StuffModel:
        return self._kernel.stuff_lib.get_stuff(stuff_id)

    def _get_likes_this_stuff(self, stuff_id: str) -> typing.List[StuffModel]:
        return self._kernel.stuff_lib.get_carried_by(
            self._from_character.id, exclude_crafting=False, stuff_id=stuff_id
        )

    def _transfer_stuff(self, stuff_id: int) -> None:
        self._kernel.stuff_lib.place_in_build(stuff_id, self._to_build.id)

    def _get_carried_resource(self, resource_id: str) -> CarriedResourceDescriptionModel:
        return self._kernel.resource_lib.get_one_carried_by(self._from_character.id, resource_id)

    def check_can_transfer_stuff(self, stuff_id: int, quantity: int = 1) -> None:
        build_description = self._kernel.game.config.builds[self._to_build.build_id]
        if not build_description.allow_deposit or build_description.allow_deposit_limited:
            raise ImpossibleAction("Vous ne pouvez pas déposer ça ici")

        try:
            stuff: StuffModel = self._kernel.stuff_lib.get_stuff(stuff_id)
        except NoResultFound:
            raise ImpossibleAction(f"Objet inexistant")

        if quantity > self._kernel.stuff_lib.get_stuff_count(
            character_id=self._from_character.id, stuff_id=stuff.stuff_id
        ):
            raise ImpossibleAction(f"{self._from_character.name} n'en a pas assez")

    def check_can_transfer_resource(self, resource_id: str, quantity: float) -> None:
        build_description = self._kernel.game.config.builds[self._to_build.build_id]
        if not build_description.allow_deposit or (
            build_description.allow_deposit_limited
            and resource_id
            not in self._kernel.game.config.builds[self._to_build.build_id].allowed_resource_ids
        ):
            raise ImpossibleAction("Vous ne pouvez pas déposer de cela ici")

        if not self._kernel.resource_lib.have_resource(
            character_id=self._from_character.id, resource_id=resource_id, quantity=quantity
        ):
            raise ImpossibleAction(f"{self._from_character.name} n'en a pas assez")

    def _transfer_resource(self, resource_id: str, quantity: float) -> None:
        self._kernel.resource_lib.reduce_carried_by(
            character_id=self._from_character.id, resource_id=resource_id, quantity=quantity
        )
        self._kernel.resource_lib.add_resource_to(
            build_id=self._to_build.id, resource_id=resource_id, quantity=quantity
        )


@dataclasses.dataclass
class DepositToModel:
    deposit_stuff_id: typing.Optional[int] = serpyco.number_field(cast_on_load=True, default=None)
    deposit_stuff_quantity: typing.Optional[int] = serpyco.number_field(
        cast_on_load=True, default=None
    )
    deposit_resource_id: typing.Optional[str] = serpyco.number_field(
        cast_on_load=True, default=None
    )
    deposit_resource_quantity: typing.Optional[str] = None


class DepositToBuildAction(WithBuildAction):
    input_model = DepositToModel
    input_model_serializer = serpyco.Serializer(DepositToModel)

    @classmethod
    def get_properties_from_config(cls, game_config: "GameConfig", action_config_raw: dict) -> dict:
        return {}

    def check_is_possible(self, character: "CharacterModel", build_id: int) -> None:
        build_doc = self._kernel.build_lib.get_build_doc(build_id)
        build_description = self._kernel.game.config.builds[build_doc.build_id]
        if not build_description.allow_deposit:
            raise ImpossibleAction("Ce batiment ne permet pas de déposer")
        pass  # TODO: check build is accessible

    def check_request_is_possible(
        self, character: "CharacterModel", build_id: int, input_: DepositToModel
    ) -> None:
        self.check_is_possible(character, build_id)
        build_doc = self._kernel.build_lib.get_build_doc(build_id)

        if input_.deposit_resource_id is not None and input_.deposit_resource_quantity:
            carried_resource = self._kernel.resource_lib.get_one_carried_by(
                character_id=character.id, resource_id=input_.deposit_resource_id
            )
            user_input_context = InputQuantityContext.from_carried_resource(
                user_input=input_.deposit_resource_quantity, carried_resource=carried_resource
            )
            DepositStuffOrResources(
                self._kernel,
                from_character=character,
                to_build=build_doc,
                description_id=self._description.id,
            ).check_can_transfer_resource(
                resource_id=input_.deposit_resource_id, quantity=user_input_context.real_quantity
            )

        if input_.deposit_stuff_id and input_.deposit_stuff_quantity:
            DepositStuffOrResources(
                self._kernel,
                from_character=character,
                to_build=build_doc,
                description_id=self._description.id,
            ).check_can_transfer_stuff(
                stuff_id=input_.deposit_stuff_id, quantity=input_.deposit_stuff_quantity
            )

    def get_character_actions(
        self, character: "CharacterModel", build_id: int
    ) -> typing.List[CharacterActionLink]:
        return [CharacterActionLink(name="Déposer", link=self._get_url(character, build_id))]

    def _get_url(
        self,
        character: "CharacterModel",
        build_id: int,
        input_: typing.Optional[DepositToModel] = None,
    ) -> str:
        return get_with_build_action_url(
            character_id=character.id,
            build_id=build_id,
            action_type=ActionType.DEPOSIT_ON_BUILD,
            query_params=self.input_model_serializer.dump(input_) if input_ else {},
            action_description_id=self._description.id,
        )

    def perform(
        self, character: "CharacterModel", build_id: int, input_: DepositToModel
    ) -> Description:
        build_doc = self._kernel.build_lib.get_build_doc(build_id)
        return DepositStuffOrResources(
            self._kernel,
            from_character=character,
            to_build=build_doc,
            description_id=self._description.id,
        ).get_description(
            stuff_id=input_.deposit_stuff_id,
            stuff_quantity=input_.deposit_stuff_quantity,
            resource_id=input_.deposit_resource_id,
            resource_quantity=input_.deposit_resource_quantity,
        )
