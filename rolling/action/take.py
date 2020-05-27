# coding: utf-8
import dataclasses
import typing

import serpyco
from sqlalchemy.orm.exc import NoResultFound

from guilang.description import Description
from guilang.description import Part
from guilang.description import Type
from rolling.action.base import WithCharacterAction
from rolling.action.base import get_with_character_action_url
from rolling.exception import ImpossibleAction
from rolling.model.stuff import StuffModel
from rolling.server.controller.url import DESCRIBE_LOOK_AT_CHARACTER_URL
from rolling.server.link import CharacterActionLink
from rolling.types import ActionType

if typing.TYPE_CHECKING:
    from rolling.game.base import GameConfig
    from rolling.model.character import CharacterModel


@dataclasses.dataclass
class TakeOnModel:
    take_stuff_id: typing.Optional[int] = serpyco.number_field(cast_on_load=True, default=None)
    take_stuff_quantity: typing.Optional[int] = serpyco.number_field(
        cast_on_load=True, default=None
    )
    take_resource_id: typing.Optional[str] = serpyco.number_field(cast_on_load=True, default=None)
    take_resource_quantity: typing.Optional[float] = serpyco.number_field(
        cast_on_load=True, default=None
    )


class TakeOnCharacterAction(WithCharacterAction):
    input_model = TakeOnModel
    input_model_serializer = serpyco.Serializer(TakeOnModel)

    @classmethod
    def get_properties_from_config(cls, game_config: "GameConfig", action_config_raw: dict) -> dict:
        return {}

    def check_is_possible(
        self, character: "CharacterModel", with_character: "CharacterModel"
    ) -> None:
        # TODO BS: Check here is possible too with affinities (like chief
        #  can manipulate, firendship, etc)
        if not with_character.vulnerable:
            raise ImpossibleAction(f"{with_character.name} est en capacité de se defendre")
        else:
            if not character.is_attack_ready():
                raise ImpossibleAction(
                    f"{character.name} ne peut contraindre {with_character.name}"
                )

    def check_request_is_possible(
        self, character: "CharacterModel", with_character: "CharacterModel", input_: TakeOnModel
    ) -> None:
        self.check_is_possible(character, with_character)

        if input_.take_resource_id is not None and input_.take_resource_quantity:
            if not self._kernel.resource_lib.have_resource(
                character_id=with_character.id,
                resource_id=input_.take_resource_id,
                quantity=input_.take_resource_quantity,
            ):
                raise ImpossibleAction(f"{with_character.name} n'en à pas assez")

        if input_.take_stuff_id:
            try:
                stuff: StuffModel = self._kernel.stuff_lib.get_stuff(input_.take_stuff_id)
            except NoResultFound:
                raise ImpossibleAction(f"{with_character.name} n'en à pas assez")
            carried_count = self._kernel.stuff_lib.have_stuff_count(
                character_id=with_character.id, stuff_id=stuff.stuff_id
            )
            if carried_count < (input_.take_stuff_quantity or 1):
                raise ImpossibleAction(f"{with_character.name} n'en à pas assez")

    def get_character_actions(
        self, character: "CharacterModel", with_character: "CharacterModel"
    ) -> typing.List[CharacterActionLink]:
        return [CharacterActionLink(name="Prendre", link=self._get_url(character, with_character))]

    def _get_url(
        self,
        character: "CharacterModel",
        with_character: "CharacterModel",
        input_: typing.Optional[TakeOnModel] = None,
    ) -> str:
        return get_with_character_action_url(
            character_id=character.id,
            with_character_id=with_character.id,
            action_type=ActionType.TAKE_ON_CHARACTER,
            query_params=self.input_model_serializer.dump(input_) if input_ else {},
            action_description_id=self._description.id,
        )

    def _get_take_something_description(
        self, character: "CharacterModel", with_character: "CharacterModel", input_: TakeOnModel
    ) -> Description:
        parts = []
        carried_stuffs = self._kernel.stuff_lib.get_carried_by(
            with_character.id, exclude_crafting=False
        )
        carried_resources = self._kernel.resource_lib.get_carried_by(with_character.id)

        displayed_stuff_ids: typing.List[str] = []
        for carried_stuff in carried_stuffs:
            if carried_stuff.stuff_id not in displayed_stuff_ids:
                parts.append(
                    Part(
                        is_link=True,
                        label=f"Prendre {carried_stuff.name}",
                        form_action=self._get_url(
                            character, with_character, TakeOnModel(take_stuff_id=carried_stuff.id)
                        ),
                    )
                )
                displayed_stuff_ids.append(carried_stuff.stuff_id)

        for carried_resource in carried_resources:
            parts.append(
                Part(
                    is_link=True,
                    label=f"Prendre {carried_resource.name}",
                    form_action=self._get_url(
                        character, with_character, TakeOnModel(take_resource_id=carried_resource.id)
                    ),
                )
            )

        return Description(
            title=f"Prendre sur {with_character.name}",
            items=parts
            + [
                Part(is_link=True, go_back_zone=True, label="Retourner à l'écran de déplacements"),
                Part(
                    is_link=True,
                    label="Retourner à la fiche personnage",
                    form_action=DESCRIBE_LOOK_AT_CHARACTER_URL.format(
                        character_id=character.id, with_character_id=with_character.id
                    ),
                ),
            ],
            can_be_back_url=True,
        )

    def perform(
        self, character: "CharacterModel", with_character: "CharacterModel", input_: TakeOnModel
    ) -> Description:
        if input_.take_stuff_id is not None:
            stuff: StuffModel = self._kernel.stuff_lib.get_stuff(input_.take_stuff_id)
            likes_this_stuff = self._kernel.stuff_lib.get_carried_by(
                with_character.id, exclude_crafting=False, stuff_id=stuff.stuff_id
            )

            if input_.take_stuff_quantity is None:
                if len(likes_this_stuff) > 1:
                    return Description(
                        title=f"Prendre {stuff.name} sur {with_character.name}",
                        items=[
                            Part(
                                is_form=True,
                                form_values_in_query=True,
                                form_action=self._get_url(character, with_character, input_),
                                submit_label="Prendre",
                                items=[
                                    Part(
                                        label="Quantité ?",
                                        type_=Type.NUMBER,
                                        name="take_stuff_quantity",
                                        default_value=str(len(likes_this_stuff)),
                                    )
                                ],
                            )
                        ],
                        can_be_back_url=True,
                    )
                input_.take_stuff_quantity = 1

            for i in range(input_.take_stuff_quantity):
                self._kernel.stuff_lib.set_carried_by(likes_this_stuff[i].id, character.id)

        if input_.take_resource_id is not None:
            resource_description = self._kernel.game.config.resources[input_.take_resource_id]
            carried_resource = self._kernel.resource_lib.get_one_carried_by(
                with_character.id, input_.take_resource_id
            )

            if input_.take_resource_quantity is None:
                unit_str = self._kernel.translation.get(resource_description.unit)
                return Description(
                    title=f"Prendre {resource_description.name} sur {with_character.name}",
                    items=[
                        Part(
                            is_form=True,
                            form_values_in_query=True,
                            form_action=self._get_url(character, with_character, input_),
                            submit_label="Prendre",
                            items=[
                                Part(
                                    label=f"Quantité ({unit_str}) ?",
                                    type_=Type.NUMBER,
                                    name="take_resource_quantity",
                                    default_value=str(carried_resource.quantity),
                                )
                            ],
                        )
                    ],
                    can_be_back_url=True,
                )
            self._kernel.resource_lib.reduce_carried_by(
                character_id=with_character.id,
                resource_id=input_.take_resource_id,
                quantity=input_.take_resource_quantity,
            )
            self._kernel.resource_lib.add_resource_to(
                character_id=character.id,
                resource_id=input_.take_resource_id,
                quantity=input_.take_resource_quantity,
            )

        return self._get_take_something_description(character, with_character, input_)
