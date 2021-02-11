# coding: utf-8
import dataclasses

import serpyco
from sqlalchemy.orm.exc import NoResultFound
import typing

from guilang.description import Description
from guilang.description import Part
from guilang.description import Type
from rolling.action.base import WithResourceAction
from rolling.action.base import WithStuffAction
from rolling.action.base import get_with_resource_action_url
from rolling.action.base import get_with_stuff_action_url
from rolling.exception import ImpossibleAction
from rolling.rolling_types import ActionType
from rolling.server.link import CharacterActionLink
from rolling.server.util import with_multiple_carried_stuffs
from rolling.util import EmptyModel

if typing.TYPE_CHECKING:
    from rolling.game.base import GameConfig
    from rolling.kernel import Kernel
    from rolling.model.character import CharacterModel
    from rolling.model.stuff import StuffModel


@dataclasses.dataclass
class DropResourceModel:
    quantity: typing.Optional[float] = serpyco.number_field(cast_on_load=True, default=None)


@dataclasses.dataclass
class DropStuffModel:
    quantity: typing.Optional[int] = serpyco.number_field(cast_on_load=True, default=None)


class DropStuffAction(WithStuffAction):
    input_model: typing.Type[DropStuffModel] = DropStuffModel
    input_model_serializer = serpyco.Serializer(DropStuffModel)

    def check_is_possible(self, character: "CharacterModel", stuff: "StuffModel") -> None:
        if stuff.carried_by != character.id:
            raise ImpossibleAction("Vous ne possedez pas cet objet")

    def check_request_is_possible(
        self, character: "CharacterModel", stuff: "StuffModel", input_: input_model
    ) -> None:
        self.check_is_possible(character, stuff)

    @classmethod
    def get_properties_from_config(cls, game_config: "GameConfig", action_config_raw: dict) -> dict:
        return {}

    def get_character_actions(
        self, character: "CharacterModel", stuff: "StuffModel"
    ) -> typing.List[CharacterActionLink]:
        actions: typing.List[CharacterActionLink] = [
            CharacterActionLink(
                name=f"Laisser {stuff.name} ici",
                link=get_with_stuff_action_url(
                    character_id=character.id,
                    action_type=ActionType.DROP_STUFF,
                    stuff_id=stuff.id,
                    query_params={},
                    action_description_id=self._description.id,
                ),
                cost=self.get_cost(character, stuff),
            )
        ]

        return actions

    def perform(
        self, character: "CharacterModel", stuff: "StuffModel", input_: DropStuffModel
    ) -> Description:
        def do_for_one(
            character_: "CharacterModel", stuff_: "StuffModel", input__: DropStuffModel
        ) -> typing.List[Part]:
            self._kernel.stuff_lib.drop(
                stuff_.id,
                world_row_i=character_.world_row_i,
                world_col_i=character_.world_col_i,
                zone_row_i=character_.zone_row_i,
                zone_col_i=character_.zone_col_i,
            )
            return [Part(text=f"{stuff_.name} laissé ici")]

        return with_multiple_carried_stuffs(
            self,
            self._kernel,
            character=character,
            stuff=stuff,
            input_=input_,
            action_type=ActionType.DROP_STUFF,
            do_for_one_func=do_for_one,
            title="Laisser quelque-chose ici",
            success_parts=[
                Part(
                    is_link=True,
                    label="Voir l'inventaire",
                    form_action=f"/_describe/character/{character.id}/inventory",
                    classes=["primary"],
                )
            ],
        )


class DropResourceAction(WithResourceAction):
    input_model: typing.Type[DropResourceModel] = DropResourceModel
    input_model_serializer = serpyco.Serializer(input_model)

    def check_is_possible(self, character: "CharacterModel", resource_id: str) -> None:
        if not self._kernel.resource_lib.have_resource(
            character_id=character.id, resource_id=resource_id
        ):
            raise ImpossibleAction("Vous ne possedez pas cette resource")

    def check_request_is_possible(
        self, character: "CharacterModel", resource_id: str, input_: input_model
    ) -> None:
        if not self._kernel.resource_lib.have_resource(
            character_id=character.id, resource_id=resource_id, quantity=input_.quantity
        ):
            raise ImpossibleAction("Vous ne possedez pas assez de cette resource")

    @classmethod
    def get_properties_from_config(cls, game_config: "GameConfig", action_config_raw: dict) -> dict:
        return {}

    def get_character_actions(
        self, character: "CharacterModel", resource_id: str
    ) -> typing.List[CharacterActionLink]:
        # TODO BS 2019-09-09: perfs
        carried_resources = self._kernel.resource_lib.get_carried_by(character.id)
        carried_resource = next((r for r in carried_resources if r.id == resource_id))

        actions: typing.List[CharacterActionLink] = [
            CharacterActionLink(
                name=f"Laisser de {carried_resource.name} ici",
                link=get_with_resource_action_url(
                    character_id=character.id,
                    action_type=ActionType.DROP_RESOURCE,
                    resource_id=carried_resource.id,
                    query_params={},
                    action_description_id=self._description.id,
                ),
                cost=None,
            )
        ]

        return actions

    def perform(
        self, character: "CharacterModel", resource_id: str, input_: input_model
    ) -> Description:
        # TODO BS 2019-09-09: perfs
        carried_resources = self._kernel.resource_lib.get_carried_by(character.id)
        carried_resource = next((r for r in carried_resources if r.id == resource_id))

        if input_.quantity is None:
            unit_trans = self._kernel.translation.get(carried_resource.unit)
            return Description(
                title=carried_resource.get_full_description(self._kernel),
                items=[
                    Part(
                        is_form=True,
                        form_values_in_query=True,
                        form_action=get_with_resource_action_url(
                            character_id=character.id,
                            action_type=ActionType.DROP_RESOURCE,
                            resource_id=resource_id,
                            query_params={},
                            action_description_id=self._description.id,
                        ),
                        items=[
                            Part(
                                label=f"Quantité à laisser ici ({unit_trans}) ?",
                                type_=Type.NUMBER,
                                name="quantity",
                                default_value=str(carried_resource.quantity),
                            )
                        ],
                    )
                ],
                back_url=f"/_describe/character/{character.id}/inventory",
            )

        self._kernel.resource_lib.drop(
            character.id,
            resource_id,
            quantity=input_.quantity,
            world_row_i=character.world_row_i,
            world_col_i=character.world_col_i,
            zone_row_i=character.zone_row_i,
            zone_col_i=character.zone_col_i,
        )
        return Description(
            title=f"Action effectué", back_url=f"/_describe/character/{character.id}/inventory"
        )
