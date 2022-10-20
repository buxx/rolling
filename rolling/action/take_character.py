# coding: utf-8
import dataclasses

import serpyco
from sqlalchemy.orm.exc import NoResultFound
import typing

from guilang.description import Description
from guilang.description import Part
from guilang.description import Type
from rolling.action.base import WithCharacterAction
from rolling.action.base import get_with_character_action_url
from rolling.exception import ImpossibleAction
from rolling.exception import WrongInputError
from rolling.model.resource import CarriedResourceDescriptionModel
from rolling.model.stuff import StuffModel
from rolling.rolling_types import ActionType
from rolling.server.controller.url import DESCRIBE_LOOK_AT_CHARACTER_URL
from rolling.server.link import CharacterActionLink
from rolling.server.transfer import TransferStuffOrResources
from rolling.util import InputQuantityContext

if typing.TYPE_CHECKING:
    from rolling.game.base import GameConfig
    from rolling.kernel import Kernel
    from rolling.model.character import CharacterModel


@dataclasses.dataclass
class TakeFromModel:
    take_stuff_id: typing.Optional[int] = serpyco.number_field(
        cast_on_load=True, default=None
    )
    take_stuff_quantity: typing.Optional[float] = serpyco.number_field(
        cast_on_load=True, default=None
    )
    take_resource_id: typing.Optional[str] = serpyco.number_field(
        cast_on_load=True, default=None
    )
    take_resource_quantity: typing.Optional[str] = None

    @property
    def take_stuff_quantity_int(self) -> typing.Optional[int]:
        if self.take_stuff_quantity is None:
            return None

        return int(self.take_stuff_quantity)


class TakeStuffOrResources(TransferStuffOrResources):
    stuff_quantity_parameter_name = "take_stuff_quantity"
    resource_quantity_parameter_name = "take_resource_quantity"

    def __init__(
        self,
        kernel: "Kernel",
        character: "CharacterModel",
        from_character: "CharacterModel",
        description_id: str,
    ) -> None:
        self.__kernel = kernel
        self._character = character
        self._from_character = from_character
        self._description_id = description_id

    @property
    def _kernel(self) -> "Kernel":
        return self.__kernel

    def get_can_take_from_affinity_relation_ids(self) -> typing.List[int]:
        have_with_affinity_ids = []
        for affinity_relation in self._kernel.affinity_lib.get_accepted_affinities(
            self._character.id
        ):
            if self._kernel.affinity_lib.count_things_shared_with_affinity(
                self._from_character.id, affinity_relation.affinity_id
            ):
                have_with_affinity_ids.append(affinity_relation.affinity_id)

        return have_with_affinity_ids

    def can_take_by_force(self, raise_: bool = True) -> bool:
        if self._from_character.vulnerable:
            return True

        if raise_:
            raise ImpossibleAction(
                f"{self._from_character.name} est en capacité de se defendre "
                f"ou {self._character.name} ne peut contraindre {self._from_character.name}"
            )
        return False

    def _get_available_stuffs(self) -> typing.List[StuffModel]:
        if self.can_take_by_force(raise_=False):
            return self._kernel.stuff_lib.get_carried_by(
                self._from_character.id, exclude_crafting=False
            )

        can_take_from_affinity_relation_ids = (
            self.get_can_take_from_affinity_relation_ids()
        )
        if can_take_from_affinity_relation_ids:
            return self._kernel.stuff_lib.get_carried_by(
                self._from_character.id,
                exclude_crafting=False,
                shared_with_affinity_ids=can_take_from_affinity_relation_ids,
            )

        return []

    def _get_available_resources(self) -> typing.List[CarriedResourceDescriptionModel]:
        if self.can_take_by_force(raise_=False):
            return self._kernel.resource_lib.get_carried_by(self._from_character.id)

        can_take_from_affinity_relation_ids = (
            self.get_can_take_from_affinity_relation_ids()
        )
        if can_take_from_affinity_relation_ids:
            return self._kernel.resource_lib.get_carried_by(
                self._from_character.id,
                shared_with_affinity_ids=can_take_from_affinity_relation_ids,
            )

        return []

    def _get_url(
        self,
        stuff_id: typing.Optional[int] = None,
        stuff_quantity: typing.Optional[int] = None,
        resource_id: typing.Optional[str] = None,
        resource_quantity: typing.Optional[float] = None,
    ) -> str:
        return get_with_character_action_url(
            character_id=self._character.id,
            with_character_id=self._from_character.id,
            action_type=ActionType.TAKE_FROM_CHARACTER,
            query_params=TakeFromCharacterAction.input_model_serializer.dump(
                TakeFromModel(
                    take_stuff_id=stuff_id,
                    take_stuff_quantity=stuff_quantity,
                    take_resource_id=resource_id,
                    take_resource_quantity=resource_quantity,
                )
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
            return f"Prendre {stuff.name} de {self._from_character.name}"

        if resource_id is not None:
            resource_description = self._kernel.game.config.resources[resource_id]
            return f"Prendre {resource_description.name} de {self._from_character.name}"

        return f"Prendre de {self._from_character.name}"

    def _get_footer_character_id(
        self, sizing_up_quantity: bool
    ) -> typing.Optional[str]:
        return self._from_character.id

    def _get_footer_affinity_id(self, sizing_up_quantity: bool) -> typing.Optional[int]:
        return None

    def _get_footer_build_id(self, sizing_up_quantity: bool) -> typing.Optional[int]:
        return None

    def _get_stuff(self, stuff_id: int) -> StuffModel:
        return self._kernel.stuff_lib.get_stuff(stuff_id)

    def _get_likes_this_stuff(self, stuff_id: str) -> typing.List[StuffModel]:
        if self.can_take_by_force(raise_=False):
            return self._kernel.stuff_lib.get_carried_by(
                self._from_character.id, exclude_crafting=False, stuff_id=stuff_id
            )

        can_take_from_affinity_relation_ids = (
            self.get_can_take_from_affinity_relation_ids()
        )
        if can_take_from_affinity_relation_ids:
            return self._kernel.stuff_lib.get_carried_by(
                self._from_character.id,
                exclude_crafting=False,
                shared_with_affinity_ids=can_take_from_affinity_relation_ids,
                stuff_id=stuff_id,
            )

        return []

    def _transfer_stuff(self, stuff_id: int) -> None:
        self._kernel.stuff_lib.set_carried_by(stuff_id, self._character.id)

    def _get_carried_resource(
        self, resource_id: str
    ) -> CarriedResourceDescriptionModel:
        if self.can_take_by_force(raise_=False):
            return self._kernel.resource_lib.get_one_carried_by(
                self._from_character.id, resource_id=resource_id
            )

        can_take_from_affinity_relation_ids = (
            self.get_can_take_from_affinity_relation_ids()
        )
        if can_take_from_affinity_relation_ids:
            return self._kernel.resource_lib.get_one_carried_by(
                self._from_character.id,
                resource_id=resource_id,
                shared_with_affinity_ids=can_take_from_affinity_relation_ids,
            )

        assert False, "should not be here"

    def check_can_transfer_stuff(self, stuff_id: int, quantity: int = 1) -> None:
        shared_with_affinity_ids = self.get_can_take_from_affinity_relation_ids()

        if self.can_take_by_force(raise_=False):
            shared_with_affinity_ids = None
        elif not shared_with_affinity_ids:
            raise ImpossibleAction("Il n'est pas possible de prendre quoi que ce soit")

        try:
            stuff: StuffModel = self._kernel.stuff_lib.get_stuff(stuff_id)
        except NoResultFound:
            raise ImpossibleAction(f"objet inexistant")
        carried_count = self._kernel.stuff_lib.get_stuff_count(
            character_id=self._from_character.id,
            stuff_id=stuff.stuff_id,
            shared_with_affinity_ids=shared_with_affinity_ids,
        )
        if carried_count < (quantity or 1):
            raise ImpossibleAction(f"{self._from_character.name} n'en a pas assez")

    def check_can_transfer_resource(self, resource_id: str, quantity: float) -> None:
        shared_with_affinity_ids = self.get_can_take_from_affinity_relation_ids()

        if self.can_take_by_force(raise_=False):
            shared_with_affinity_ids = None
        elif not shared_with_affinity_ids:
            raise ImpossibleAction("Il n'est pas possible de prendre quoi que ce soit")

        if not self._kernel.resource_lib.have_resource(
            character_id=self._from_character.id,
            resource_id=resource_id,
            quantity=quantity,
            shared_with_affinity_ids=shared_with_affinity_ids,
        ):
            raise WrongInputError(f"{self._from_character.name} n'en a pas assez")

    def _transfer_resource(self, resource_id: str, quantity: float) -> None:
        shared_with_affinity_ids = self.get_can_take_from_affinity_relation_ids()

        if self.can_take_by_force(raise_=False):
            shared_with_affinity_ids = None
        elif not shared_with_affinity_ids:
            raise ImpossibleAction("Il n'est pas possible de prendre quoi que ce soit")

        self._kernel.resource_lib.reduce_carried_by(
            character_id=self._from_character.id,
            resource_id=resource_id,
            quantity=quantity,
            shared_with_affinity_ids=shared_with_affinity_ids,
        )
        self._kernel.resource_lib.add_resource_to(
            character_id=self._character.id, resource_id=resource_id, quantity=quantity
        )

    def _get_classes(self) -> typing.List[str]:
        return []

    def _get_zone_coordinates(self) -> typing.Optional[typing.Tuple[int, int]]:
        return self._from_character.zone_row_i, self._from_character.zone_col_i


class TakeFromCharacterAction(WithCharacterAction):
    input_model = TakeFromModel
    input_model_serializer = serpyco.Serializer(TakeFromModel)

    @classmethod
    def get_properties_from_config(
        cls, game_config: "GameConfig", action_config_raw: dict
    ) -> dict:
        return {}

    def check_is_possible(
        self, character: "CharacterModel", with_character: "CharacterModel"
    ) -> None:
        # TODO BS: Add possibility to take when chief or warlord
        take = TakeStuffOrResources(
            self._kernel,
            character=character,
            from_character=with_character,
            description_id=self._description.id,
        )

        if (
            not take.can_take_by_force(raise_=False)
            and not take.get_can_take_from_affinity_relation_ids()
        ):
            raise ImpossibleAction(
                f"{character.name} ne peut contraindre {with_character.name}"
            )

    async def check_request_is_possible(
        self,
        character: "CharacterModel",
        with_character: "CharacterModel",
        input_: TakeFromModel,
    ) -> None:
        self.check_is_possible(character, with_character)
        take = TakeStuffOrResources(
            self._kernel,
            character=character,
            from_character=with_character,
            description_id=self._description.id,
        )

        if input_.take_resource_id is not None and input_.take_resource_quantity:
            carried_resource = self._kernel.resource_lib.get_one_carried_by(
                with_character.id, resource_id=input_.take_resource_id
            )
            user_input_context = InputQuantityContext.from_carried_resource(
                user_input=input_.take_resource_quantity,
                carried_resource=carried_resource,
            )
            take.check_can_transfer_resource(
                input_.take_resource_id, quantity=user_input_context.real_quantity
            )

        if input_.take_stuff_id:
            take.check_can_transfer_stuff(
                input_.take_stuff_id, quantity=input_.take_stuff_quantity_int
            )

    def get_character_actions(
        self, character: "CharacterModel", with_character: "CharacterModel"
    ) -> typing.List[CharacterActionLink]:
        return [
            CharacterActionLink(
                name="Prendre", link=self._get_url(character, with_character)
            )
        ]

    def _get_url(
        self,
        character: "CharacterModel",
        with_character: "CharacterModel",
        input_: typing.Optional[TakeFromModel] = None,
    ) -> str:
        return get_with_character_action_url(
            character_id=character.id,
            with_character_id=with_character.id,
            action_type=ActionType.TAKE_FROM_CHARACTER,
            query_params=self.input_model_serializer.dump(input_) if input_ else {},
            action_description_id=self._description.id,
        )

    async def perform(
        self,
        character: "CharacterModel",
        with_character: "CharacterModel",
        input_: TakeFromModel,
    ) -> Description:
        return TakeStuffOrResources(
            self._kernel,
            character=character,
            from_character=with_character,
            description_id=self._description.id,
        ).get_description(
            stuff_id=input_.take_stuff_id,
            stuff_quantity=input_.take_stuff_quantity_int,
            resource_id=input_.take_resource_id,
            resource_quantity=input_.take_resource_quantity,
        )
