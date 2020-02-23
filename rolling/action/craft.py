# coding: utf-8
import dataclasses
import typing

import serpyco

from guilang.description import Description
from guilang.description import Part
from guilang.description import Type
from rolling.action.base import ActionDescriptionModel
from rolling.action.base import WithResourceAction
from rolling.action.base import WithStuffAction
from rolling.action.base import get_with_resource_action_url
from rolling.action.base import get_with_stuff_action_url
from rolling.action.utils import check_common_is_possible, fill_base_action_properties
from rolling.exception import ImpossibleAction
from rolling.exception import RollingError
from rolling.server.link import CharacterActionLink
from rolling.types import ActionType
from rolling.util import quantity_to_str

if typing.TYPE_CHECKING:
    from rolling.model.character import CharacterModel
    from rolling.model.stuff import StuffModel
    from rolling.game.base import GameConfig
    from rolling.kernel import Kernel


@dataclasses.dataclass
class CraftInput:
    quantity: typing.Optional[int] = serpyco.number_field(cast_on_load=True, default=None)


class BaseCraftStuff:
    @classmethod
    def _get_properties_from_config(
        cls, game_config: "GameConfig", action_config_raw: dict
    ) -> dict:
        for require in action_config_raw["require"]:
            if "resource" not in require and "stuff" not in require:
                raise RollingError(
                    "Misconfiguration for action "
                    "CraftStuffWithResourceAction/CraftStuffWithStuffAction (require "
                    "must contain stuff or resource key"
                )

        properties = fill_base_action_properties(cls, game_config, {}, action_config_raw)
        properties.update(
            {"produce": action_config_raw["produce"], "require": action_config_raw["require"]}
        )
        return properties

    def _perform(
        self,
        character: "CharacterModel",
        description: ActionDescriptionModel,
        input_: CraftInput,
        dry_run: bool = True,
    ) -> None:
        carried_resources = self._kernel.resource_lib.get_carried_by(character.id)
        carried_stuffs = self._kernel.stuff_lib.get_carried_by(character.id)

        for require in description.properties["require"]:
            if "stuff" in require:
                required_quantity = input_.quantity * int(require["quantity"])
                stuff_id = require["stuff"]
                stuff_properties = self._kernel.game.stuff_manager.get_stuff_properties_by_id(
                    stuff_id
                )
                carried_stuffs = [c for c in carried_stuffs if c.stuff_id == stuff_id]
                owned_quantity = len(carried_stuffs)

                if owned_quantity < required_quantity:
                    raise ImpossibleAction(
                        f"Il vous manque {required_quantity - owned_quantity} {stuff_properties.name}"
                    )

                if not dry_run:
                    for i in range(required_quantity):
                        stuff_to_destroy = carried_stuffs[i]
                        self._kernel.stuff_lib.destroy(stuff_to_destroy.id)

            elif "resource" in require:
                required_quantity = input_.quantity * require["quantity"]
                resource_id = require["resource"]
                resource_properties = self._kernel.game.config.resources[resource_id]
                try:
                    carried_resource = next((c for c in carried_resources if c.id == resource_id))
                except StopIteration:
                    raise ImpossibleAction(f"Vous ne possédez pas de {resource_properties.name}")
                if carried_resource.quantity < required_quantity:
                    missing_quantity_str = quantity_to_str(
                        kernel=self._kernel,
                        quantity=(required_quantity - carried_resource.quantity),
                        unit=carried_resource.unit,
                    )
                    raise ImpossibleAction(
                        f"Il vous manque {missing_quantity_str} de {carried_resource.name}"
                    )

                if not dry_run:
                    self._kernel.resource_lib.reduce_carried_by(
                        character_id=character.id,
                        resource_id=resource_id,
                        quantity=required_quantity,
                    )

        if dry_run:
            return

        for produce in description.properties["produce"]:
            stuff_id = produce["stuff"]
            quantity = produce["quantity"]
            stuff_properties = self._kernel.game.stuff_manager.get_stuff_properties_by_id(stuff_id)

            for i in range(int(quantity)):
                stuff_doc = self._kernel.stuff_lib.create_document_from_stuff_properties(
                    properties=stuff_properties,
                    world_row_i=character.world_row_i,
                    world_col_i=character.world_col_i,
                    zone_row_i=character.zone_row_i,
                    zone_col_i=character.zone_col_i,
                )
                self._kernel.stuff_lib.add_stuff(stuff_doc, commit=False)
                self._kernel.stuff_lib.set_carried_by__from_doc(
                    stuff_doc, character_id=character.id, commit=False
                )

        self._kernel.server_db_session.commit()


class CraftStuffWithResourceAction(WithResourceAction, BaseCraftStuff):
    input_model = CraftInput
    input_model_serializer = serpyco.Serializer(CraftInput)

    @classmethod
    def get_properties_from_config(cls, game_config: "GameConfig", action_config_raw: dict) -> dict:
        return cls._get_properties_from_config(game_config, action_config_raw)

    def check_is_possible(self, character: "CharacterModel", resource_id: str) -> None:
        # Consider action ca be possible (displayed in interface) if at least one of required
        # resources is owned by character
        carried = self._kernel.resource_lib.get_carried_by(character.id)
        carried_ids = [r.id for r in carried]

        for require in self._description.properties["require"]:
            if "resource" in require and require["resource"] in carried_ids:
                return

        raise ImpossibleAction("Aucune resource requise n'est possédé")

    def check_request_is_possible(
        self, character: "CharacterModel", resource_id: str, input_: CraftInput
    ) -> None:
        self.check_is_possible(character, resource_id=resource_id)
        check_common_is_possible(
            kernel=self._kernel, description=self._description, character=character
        )
        if input_.quantity is not None:
            self._perform(character, description=self._description, input_=input_, dry_run=True)

    def get_character_actions(
        self, character: "CharacterModel", resource_id: str
    ) -> typing.List[CharacterActionLink]:
        try:
            self.check_is_possible(character, resource_id)
        except ImpossibleAction:
            return []

        return [
            CharacterActionLink(
                name=self._description.name,
                link=get_with_resource_action_url(
                    character_id=character.id,
                    action_type=ActionType.CRAFT_STUFF_WITH_RESOURCE,
                    action_description_id=self._description.id,
                    resource_id=resource_id,
                    query_params={},
                ),
                cost=self.get_cost(character, resource_id),
            )
        ]

    def perform(
        self, character: "CharacterModel", resource_id: str, input_: typing.Any
    ) -> Description:
        if input_.quantity is None:
            return Description(
                title=self._description.name,
                items=[
                    Part(
                        is_form=True,
                        form_values_in_query=True,
                        form_action=get_with_resource_action_url(
                            character_id=character.id,
                            action_type=ActionType.CRAFT_STUFF_WITH_RESOURCE,
                            resource_id=resource_id,
                            query_params=self.input_model_serializer.dump(input_),
                            action_description_id=self._description.id,
                        ),
                        items=[
                            Part(label=f"Quelle quantité ?", type_=Type.NUMBER, name="quantity")
                        ],
                    )
                ],
            )

        self._perform(character, description=self._description, input_=input_, dry_run=True)
        self._perform(character, description=self._description, input_=input_, dry_run=False)
        return Description(
            title="Action effectué avec succès",
            items=[Part(items=[Part(label=f"Continuer", go_back_zone=True)])],
        )


class CraftStuffWithStuffAction(WithStuffAction, BaseCraftStuff):
    input_model = CraftInput
    input_model_serializer = serpyco.Serializer(CraftInput)

    @classmethod
    def get_properties_from_config(cls, game_config: "GameConfig", action_config_raw: dict) -> dict:
        return cls._get_properties_from_config(game_config, action_config_raw)

    def check_is_possible(self, character: "CharacterModel", stuff: "StuffModel") -> None:
        # Consider action ca be possible (displayed in interface) if at least one of required stuff
        # is owned by character
        carried = self._kernel.stuff_lib.get_carried_by(character.id)
        carried_stuff_ids = [r.stuff_id for r in carried]

        for require in self._description.properties["require"]:
            if "stuff" in require and require["stuff"] in carried_stuff_ids:
                return

        raise ImpossibleAction("Aucune resource requise n'est possédé")

    def check_request_is_possible(
        self, character: "CharacterModel", stuff: "StuffModel", input_: typing.Any
    ) -> None:
        self.check_is_possible(character, stuff=stuff)
        check_common_is_possible(
            kernel=self._kernel, description=self._description, character=character
        )
        if input_.quantity is not None:
            self._perform(character, description=self._description, input_=input_, dry_run=True)

    def get_character_actions(
        self, character: "CharacterModel", stuff: "StuffModel"
    ) -> typing.List[CharacterActionLink]:
        try:
            self.check_is_possible(character, stuff)
        except ImpossibleAction:
            return []

        return [
            CharacterActionLink(
                name=self._description.name,
                link=get_with_stuff_action_url(
                    character_id=character.id,
                    action_type=ActionType.CRAFT_STUFF_WITH_STUFF,
                    action_description_id=self._description.id,
                    stuff_id=stuff.id,
                    query_params={},
                ),
                cost=self.get_cost(character, stuff),
            )
        ]

    def perform(
        self, character: "CharacterModel", stuff: "StuffModel", input_: typing.Any
    ) -> Description:
        if input_.quantity is None:
            return Description(
                title=self._description.name,
                items=[
                    Part(
                        is_form=True,
                        form_values_in_query=True,
                        form_action=get_with_stuff_action_url(
                            character_id=character.id,
                            action_type=ActionType.CRAFT_STUFF_WITH_STUFF,
                            stuff_id=stuff.id,
                            query_params=self.input_model_serializer.dump(input_),
                            action_description_id=self._description.id,
                        ),
                        items=[
                            Part(label=f"Quelle quantité ?", type_=Type.NUMBER, name="quantity")
                        ],
                    )
                ],
            )

        self._perform(character, description=self._description, input_=input_, dry_run=True)
        self._perform(character, description=self._description, input_=input_, dry_run=False)
        return Description(
            title="Action effectué avec succès",
            items=[Part(items=[Part(label=f"Continuer", go_back_zone=True)])],
        )
