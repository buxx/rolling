# coding: utf-8
import dataclasses

import serpyco
from sqlalchemy.orm.exc import NoResultFound
import typing

from guilang.description import Description
from rolling.action.base import WithBuildAction, get_with_build_action_url
from rolling.exception import ImpossibleAction
from rolling.model.resource import CarriedResourceDescriptionModel
from rolling.model.stuff import StuffModel
from rolling.rolling_types import ActionType
from rolling.server.link import CharacterActionLink
from rolling.server.transfer import TransferStuffOrResources

if typing.TYPE_CHECKING:
    from rolling.game.base import GameConfig
    from rolling.kernel import Kernel
    from rolling.model.character import CharacterModel
    from rolling.model.build import BuildDocument


class TakeStuffOrResources(TransferStuffOrResources):
    stuff_quantity_parameter_name = "take_stuff_quantity"
    resource_quantity_parameter_name = "take_resource_quantity"

    def __init__(
        self,
        kernel: "Kernel",
        from_character: "CharacterModel",
        from_build: "BuildDocument",
        description_id: str,
    ) -> None:
        super().__init__()
        self.__kernel = kernel
        self._from_character = from_character
        self._from_build = from_build
        self._description_id = description_id

    @property
    def _kernel(self) -> "Kernel":
        return self.__kernel

    def _get_available_stuffs(self) -> typing.List[StuffModel]:
        return self._kernel.stuff_lib.get_from_build(
            self._from_build.id
        )

    def _get_available_resources(self) -> typing.List[CarriedResourceDescriptionModel]:
        return self._kernel.resource_lib.get_stored_in_build(self._from_build.id)

    def _get_url(
        self,
        stuff_id: typing.Optional[int] = None,
        stuff_quantity: typing.Optional[int] = None,
        resource_id: typing.Optional[str] = None,
        resource_quantity: typing.Optional[float] = None,
    ) -> str:
        return get_with_build_action_url(
            character_id=self._from_character.id,
            build_id=self._from_build.id,
            action_type=ActionType.TAKE_FROM_BUILD,
            query_params=TakeFromBuildAction.input_model_serializer.dump(
                TakeFromModel(take_stuff_id=stuff_id, take_resource_id=resource_id)
            ),
            action_description_id=self._description_id,
        )

    def _get_title(
        self, stuff_id: typing.Optional[int] = None, resource_id: typing.Optional[str] = None
    ) -> str:
        build_name = self._kernel.game.config.builds[self._from_build.build_id].name

        if stuff_id is not None:
            stuff = self._kernel.stuff_lib.get_stuff(stuff_id)
            return f"Prendre {stuff.name} depuis {build_name}"

        if resource_id is not None:
            resource_description = self._kernel.game.config.resources[resource_id]
            return f"Prendre {resource_description.name} depuis {build_name}"

        return f"Prendre depuis {build_name}"

    def _get_footer_character_id(self, sizing_up_quantity: bool) -> typing.Optional[str]:
        return None

    def _get_footer_affinity_id(self, sizing_up_quantity: bool) -> typing.Optional[int]:
        return None

    def _get_footer_build_id(self, sizing_up_quantity: bool) -> typing.Optional[int]:
        return self._from_build.id

    def _get_stuff(self, stuff_id: int) -> StuffModel:
        return self._kernel.stuff_lib.get_stuff(stuff_id)

    def _get_likes_this_stuff(self, stuff_id: str) -> typing.List[StuffModel]:
        return self._kernel.stuff_lib.get_from_build(
            self._from_build.id, stuff_id=stuff_id
        )

    def _transfer_stuff(self, stuff_id: int) -> None:
        self._kernel.stuff_lib.set_carried_by(stuff_id, self._from_character.id)

    def _get_carried_resource(self, resource_id: str) -> CarriedResourceDescriptionModel:
        return self._kernel.resource_lib.get_one_stored_in_build(self._from_build.id, resource_id)

    def check_can_transfer_stuff(self, stuff_id: int, quantity: int = 1) -> None:
        try:
            stuff: StuffModel = self._kernel.stuff_lib.get_stuff(stuff_id)
        except NoResultFound:
            raise ImpossibleAction(f"Objet inexistant")

        if quantity > self._kernel.stuff_lib.get_stuff_count(
            build_id=self._from_build.id, stuff_id=stuff.stuff_id
        ):
            raise ImpossibleAction(f"Il n'y en à pas assez")

    def check_can_transfer_resource(self, resource_id: str, quantity: float) -> None:
        if not self._kernel.resource_lib.have_resource(
            build_id=self._from_build.id, resource_id=resource_id, quantity=quantity
        ):
            raise ImpossibleAction(f"Il n'y en à pas assez")

    def _transfer_resource(self, resource_id: str, quantity: float) -> None:
        self._kernel.resource_lib.reduce_stored_in(
            build_id=self._from_build.id, resource_id=resource_id, quantity=quantity
        )
        self._kernel.resource_lib.add_resource_to(
            character_id=self._from_character.id, resource_id=resource_id, quantity=quantity
        )


@dataclasses.dataclass
class TakeFromModel:
    take_stuff_id: typing.Optional[int] = serpyco.number_field(cast_on_load=True, default=None)
    take_stuff_quantity: typing.Optional[int] = serpyco.number_field(
        cast_on_load=True, default=None
    )
    take_resource_id: typing.Optional[str] = serpyco.number_field(cast_on_load=True, default=None)
    take_resource_quantity: typing.Optional[float] = serpyco.number_field(
        cast_on_load=True, default=None
    )


class TakeFromBuildAction(WithBuildAction):
    input_model = TakeFromModel
    input_model_serializer = serpyco.Serializer(TakeFromModel)

    @classmethod
    def get_properties_from_config(cls, game_config: "GameConfig", action_config_raw: dict) -> dict:
        return {}

    def check_is_possible(
        self, character: "CharacterModel", build_id: int
    ) -> None:
        pass  # TODO: check build is accessible

    def check_request_is_possible(
        self, character: "CharacterModel", build_id: int, input_: TakeFromModel
    ) -> None:
        self.check_is_possible(character, build_id)
        build_doc = self._kernel.build_lib.get_build_doc(build_id)

        if input_.take_resource_id is not None and input_.take_resource_quantity:
            TakeStuffOrResources(
                self._kernel,
                from_character=character,
                from_build=build_doc,
                description_id=self._description.id,
            ).check_can_transfer_resource(
                resource_id=input_.take_resource_id, quantity=input_.take_resource_quantity
            )

        if input_.take_stuff_id and input_.take_stuff_quantity:
            TakeStuffOrResources(
                self._kernel,
                from_character=character,
                from_build=build_doc,
                description_id=self._description.id,
            ).check_can_transfer_stuff(
                stuff_id=input_.take_stuff_id, quantity=input_.take_stuff_quantity
            )

    def get_character_actions(
        self, character: "CharacterModel", build_id: int
    ) -> typing.List[CharacterActionLink]:
        return [CharacterActionLink(name="Prendre", link=self._get_url(character, build_id))]

    def _get_url(
        self,
        character: "CharacterModel",
        build_id: int,
        input_: typing.Optional[TakeFromModel] = None,
    ) -> str:
        return get_with_build_action_url(
            character_id=character.id,
            build_id=build_id,
            action_type=ActionType.TAKE_FROM_BUILD,
            query_params=self.input_model_serializer.dump(input_) if input_ else {},
            action_description_id=self._description.id,
        )

    def perform(
        self, character: "CharacterModel", build_id: int, input_: TakeFromModel
    ) -> Description:
        build_doc = self._kernel.build_lib.get_build_doc(build_id)
        return TakeStuffOrResources(
            self._kernel,
            from_character=character,
            from_build=build_doc,
            description_id=self._description.id,
        ).get_description(
            stuff_id=input_.take_stuff_id,
            stuff_quantity=input_.take_stuff_quantity,
            resource_id=input_.take_resource_id,
            resource_quantity=input_.take_resource_quantity,
        )
