# coding: utf-8
import dataclasses

import serpyco
from sqlalchemy.orm.exc import NoResultFound
import typing

from guilang.description import Description
from rolling.action.base import WithCharacterAction
from rolling.action.base import get_with_character_action_url
from rolling.exception import ImpossibleAction
from rolling.exception import WrongInputError
from rolling.model.resource import CarriedResourceDescriptionModel
from rolling.model.stuff import StuffModel
from rolling.rolling_types import ActionType
from rolling.server.link import CharacterActionLink
from rolling.server.transfer import TransferStuffOrResources
from rolling.util import InputQuantityContext

if typing.TYPE_CHECKING:
    from rolling.game.base import GameConfig
    from rolling.kernel import Kernel
    from rolling.model.character import CharacterModel


class GiveStuffOrResources(TransferStuffOrResources):
    stuff_quantity_parameter_name = "give_stuff_quantity"
    resource_quantity_parameter_name = "give_resource_quantity"

    def __init__(
        self,
        kernel: "Kernel",
        from_character: "CharacterModel",
        to_character: "CharacterModel",
        description_id: str,
    ) -> None:
        super().__init__()
        self.__kernel = kernel
        self._from_character = from_character
        self._to_character = to_character
        self._description_id = description_id

    @property
    def _kernel(self) -> "Kernel":
        return self.__kernel

    def _get_available_stuffs(self) -> typing.List[StuffModel]:
        return self._kernel.stuff_lib.get_carried_by(
            self._from_character.id, exclude_crafting=False
        )

    def _get_available_resources(self) -> typing.List[CarriedResourceDescriptionModel]:
        return self._kernel.resource_lib.get_carried_by(self._from_character.id)

    def _get_url(
        self,
        stuff_id: typing.Optional[int] = None,
        stuff_quantity: typing.Optional[int] = None,
        resource_id: typing.Optional[str] = None,
        resource_quantity: typing.Optional[float] = None,
    ) -> str:
        return get_with_character_action_url(
            character_id=self._from_character.id,
            with_character_id=self._to_character.id,
            action_type=ActionType.GIVE_TO_CHARACTER,
            query_params=GiveToCharacterAction.input_model_serializer.dump(
                GiveToModel(give_stuff_id=stuff_id, give_resource_id=resource_id)
            ),
            action_description_id=self._description_id,
        )

    def _get_title(
        self,
        stuff_id: typing.Optional[int] = None,
        resource_id: typing.Optional[str] = None,
    ) -> str:
        if stuff_id is not None:
            stuff = self._kernel.stuff_lib.get_stuff(stuff_id)
            return f"Donner {stuff.name} à {self._to_character.name}"

        if resource_id is not None:
            resource_description = self._kernel.game.config.resources[resource_id]
            return f"Donner {resource_description.name} à {self._to_character.name}"

        return f"Donner à {self._to_character.name}"

    def _get_footer_character_id(
        self, sizing_up_quantity: bool
    ) -> typing.Optional[str]:
        if sizing_up_quantity:
            return None
        return self._from_character.id

    def _get_footer_affinity_id(self, sizing_up_quantity: bool) -> typing.Optional[int]:
        return None

    def _get_footer_build_id(self, sizing_up_quantity: bool) -> typing.Optional[int]:
        return None

    def _get_stuff(self, stuff_id: int) -> StuffModel:
        return self._kernel.stuff_lib.get_stuff(stuff_id)

    def _get_likes_this_stuff(self, stuff_id: str) -> typing.List[StuffModel]:
        return self._kernel.stuff_lib.get_carried_by(
            self._from_character.id, exclude_crafting=False, stuff_id=stuff_id
        )

    def _transfer_stuff(self, stuff_id: int) -> None:
        self._kernel.stuff_lib.set_carried_by(stuff_id, self._to_character.id)

    def _get_carried_resource(
        self, resource_id: str
    ) -> CarriedResourceDescriptionModel:
        return self._kernel.resource_lib.get_one_carried_by(
            self._from_character.id, resource_id
        )

    def check_can_transfer_stuff(self, stuff_id: int, quantity: int = 1) -> None:
        try:
            stuff: StuffModel = self._kernel.stuff_lib.get_stuff(stuff_id)
        except NoResultFound:
            raise ImpossibleAction(f"Objet inexistant")

        if quantity > self._kernel.stuff_lib.get_stuff_count(
            character_id=self._from_character.id, stuff_id=stuff.stuff_id
        ):
            raise WrongInputError(f"{self._from_character.name} n'en a pas assez")

    def check_can_transfer_resource(self, resource_id: str, quantity: float) -> None:
        if not self._kernel.resource_lib.have_resource(
            character_id=self._from_character.id,
            resource_id=resource_id,
            quantity=quantity,
        ):
            raise WrongInputError(f"{self._from_character.name} n'en a pas assez")

    def _transfer_resource(self, resource_id: str, quantity: float) -> None:
        self._kernel.resource_lib.reduce_carried_by(
            character_id=self._from_character.id,
            resource_id=resource_id,
            quantity=quantity,
        )
        self._kernel.resource_lib.add_resource_to(
            character_id=self._to_character.id,
            resource_id=resource_id,
            quantity=quantity,
        )


@dataclasses.dataclass
class GiveToModel:
    give_stuff_id: typing.Optional[int] = serpyco.number_field(
        cast_on_load=True, default=None
    )
    give_stuff_quantity: typing.Optional[int] = serpyco.number_field(
        cast_on_load=True, default=None
    )
    give_resource_id: typing.Optional[str] = serpyco.number_field(
        cast_on_load=True, default=None
    )
    give_resource_quantity: typing.Optional[str] = None


class GiveToCharacterAction(WithCharacterAction):
    input_model = GiveToModel
    input_model_serializer = serpyco.Serializer(GiveToModel)

    @classmethod
    def get_properties_from_config(
        cls, game_config: "GameConfig", action_config_raw: dict
    ) -> dict:
        return {}

    def check_is_possible(
        self, character: "CharacterModel", with_character: "CharacterModel"
    ) -> None:
        pass  # TODO: user config to refuse receiving ?

    async def check_request_is_possible(
        self,
        character: "CharacterModel",
        with_character: "CharacterModel",
        input_: GiveToModel,
    ) -> None:
        self.check_is_possible(character, with_character)

        if input_.give_resource_id is not None and input_.give_resource_quantity:
            carried_resource = self._kernel.resource_lib.get_one_carried_by(
                character.id, resource_id=input_.give_resource_id
            )
            user_input_context = InputQuantityContext.from_carried_resource(
                user_input=input_.give_resource_quantity,
                carried_resource=carried_resource,
            )
            GiveStuffOrResources(
                self._kernel,
                from_character=character,
                to_character=with_character,
                description_id=self._description.id,
            ).check_can_transfer_resource(
                resource_id=input_.give_resource_id,
                quantity=user_input_context.real_quantity,
            )

        if input_.give_stuff_id and input_.give_stuff_quantity:
            GiveStuffOrResources(
                self._kernel,
                from_character=character,
                to_character=with_character,
                description_id=self._description.id,
            ).check_can_transfer_stuff(
                stuff_id=input_.give_stuff_id, quantity=input_.give_stuff_quantity
            )

    def get_character_actions(
        self, character: "CharacterModel", with_character: "CharacterModel"
    ) -> typing.List[CharacterActionLink]:
        return [
            CharacterActionLink(
                name="Donner", link=self._get_url(character, with_character)
            )
        ]

    def _get_url(
        self,
        character: "CharacterModel",
        with_character: "CharacterModel",
        input_: typing.Optional[GiveToModel] = None,
    ) -> str:
        return get_with_character_action_url(
            character_id=character.id,
            with_character_id=with_character.id,
            action_type=ActionType.GIVE_TO_CHARACTER,
            query_params=self.input_model_serializer.dump(input_) if input_ else {},
            action_description_id=self._description.id,
        )

    async def perform(
        self,
        character: "CharacterModel",
        with_character: "CharacterModel",
        input_: GiveToModel,
    ) -> Description:
        return GiveStuffOrResources(
            self._kernel,
            from_character=character,
            to_character=with_character,
            description_id=self._description.id,
        ).get_description(
            stuff_id=input_.give_stuff_id,
            stuff_quantity=input_.give_stuff_quantity,
            resource_id=input_.give_resource_id,
            resource_quantity=input_.give_resource_quantity,
        )
