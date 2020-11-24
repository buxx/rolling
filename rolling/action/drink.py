# coding: utf-8
import dataclasses

import serpyco
import typing

from guilang.description import Description
from guilang.description import Part
from rolling.action.base import CharacterAction
from rolling.action.base import WithStuffAction
from rolling.action.base import get_character_action_url
from rolling.action.base import get_with_stuff_action_url
from rolling.exception import ImpossibleAction
from rolling.model.effect import CharacterEffectDescriptionModel
from rolling.rolling_types import ActionType
from rolling.server.link import CharacterActionLink

if typing.TYPE_CHECKING:
    from rolling.game.base import GameConfig
    from rolling.kernel import Kernel
    from rolling.model.character import CharacterModel
    from rolling.model.stuff import StuffModel


@dataclasses.dataclass
class DrinkResourceModel:
    resource_id: str


@dataclasses.dataclass
class DrinkStuffModel:
    stuff_id: int = serpyco.field(cast_on_load=True)


class DrinkResourceAction(CharacterAction):
    input_model: typing.Type[DrinkResourceModel] = DrinkResourceModel
    input_model_serializer = serpyco.Serializer(input_model)

    @classmethod
    def get_properties_from_config(cls, game_config: "GameConfig", action_config_raw: dict) -> dict:
        return {
            "accept_resources": [
                game_config.resources[r] for r in action_config_raw["accept_resources"]
            ],
            "effects": [
                game_config.character_effects[e] for e in action_config_raw["character_effects"]
            ],
        }

    def check_is_possible(self, character: "CharacterModel") -> None:
        accept_resources_ids = [rd.id for rd in self._description.properties["accept_resources"]]
        for resource in self._kernel.game.world_manager.get_resource_on_or_around(
            world_row_i=character.world_row_i,
            world_col_i=character.world_col_i,
            zone_row_i=character.zone_row_i,
            zone_col_i=character.zone_col_i,
            material_type=self._kernel.game.config.liquid_material_id,
        ):
            if resource.type_.value in accept_resources_ids:
                return

        raise ImpossibleAction("Il n'y a pas à boire à proximité")

    def check_request_is_possible(
        self, character: "CharacterModel", input_: DrinkResourceModel
    ) -> None:
        accept_resources_ids = [rd.id for rd in self._description.properties["accept_resources"]]
        for resource in self._kernel.game.world_manager.get_resource_on_or_around(
            world_row_i=character.world_row_i,
            world_col_i=character.world_col_i,
            zone_row_i=character.zone_row_i,
            zone_col_i=character.zone_col_i,
            material_type=self._kernel.game.config.liquid_material_id,
        ):
            if resource.id == input_.resource_id and input_.resource_id in accept_resources_ids:
                return

        raise ImpossibleAction(f"Il n'y a pas de {input_.resource_id} à proximité")

    def get_character_actions(
        self, character: "CharacterModel"
    ) -> typing.List[CharacterActionLink]:
        character_actions: typing.List[CharacterActionLink] = []
        accept_resources_ids = [rd.id for rd in self._description.properties["accept_resources"]]

        for resource in self._kernel.game.world_manager.get_resource_on_or_around(
            world_row_i=character.world_row_i,
            world_col_i=character.world_col_i,
            zone_row_i=character.zone_row_i,
            zone_col_i=character.zone_col_i,
            material_type=self._kernel.game.config.liquid_material_id,
        ):
            if resource.id in accept_resources_ids:
                query_params = self.input_model(resource_id=resource.id)
                character_actions.append(
                    CharacterActionLink(
                        name=f"Drink {resource.name}",
                        link=get_character_action_url(
                            character_id=character.id,
                            action_type=ActionType.DRINK_RESOURCE,
                            action_description_id=self._description.id,
                            query_params=self.input_model_serializer.dump(query_params),
                        ),
                        cost=self.get_cost(character),
                    )
                )

        return character_actions

    def perform(self, character: "CharacterModel", input_: input_model) -> Description:
        character_doc = self._character_lib.get_document(character.id)
        effects: typing.List[CharacterEffectDescriptionModel] = self._description.properties[
            "effects"
        ]

        for effect in effects:
            self._effect_manager.enable_effect(character_doc, effect)
            self._kernel.server_db_session.add(character_doc)
            self._kernel.server_db_session.commit()

        return Description(title="Action effectué")


class DrinkStuffAction(WithStuffAction):
    input_model: typing.Type[DrinkStuffModel] = DrinkStuffModel
    input_model_serializer = serpyco.Serializer(input_model)

    @classmethod
    def get_properties_from_config(cls, game_config: "GameConfig", action_config_raw: dict) -> dict:
        return {
            "accept_resources": [
                game_config.resources[r] for r in action_config_raw["accept_resources"]
            ],
            "effects": [
                game_config.character_effects[e] for e in action_config_raw["character_effects"]
            ],
        }

    def check_is_possible(self, character: "CharacterModel", stuff: "StuffModel") -> None:
        # TODO BS 2019-07-31: check is owned stuff
        accept_resources_ids = [rd.id for rd in self._description.properties["accept_resources"]]
        if (
            stuff.filled_with_resource is not None
            and stuff.filled_with_resource in accept_resources_ids
        ):
            return

        raise ImpossibleAction(f"Il n'y a pas de quoi boire la dedans")

    def check_request_is_possible(
        self, character: "CharacterModel", stuff: "StuffModel", input_: input_model
    ) -> None:
        # TODO BS 2019-07-31: check is owned stuff
        accept_resources_ids = [rd.id for rd in self._description.properties["accept_resources"]]

        if (
            stuff.filled_with_resource is not None
            and stuff.filled_with_resource in accept_resources_ids
        ):
            return

        raise ImpossibleAction(f"Il n'y a pas de quoi boire la dedans")

    def get_character_actions(
        self, character: "CharacterModel", stuff: "StuffModel"
    ) -> typing.List[CharacterActionLink]:
        accept_resources_ids = [rd.id for rd in self._description.properties["accept_resources"]]
        if (
            stuff.filled_with_resource is not None
            and stuff.filled_with_resource in accept_resources_ids
        ):
            query_params = self.input_model(stuff_id=stuff.id)
            resource_description = self._kernel.game.config.resources[stuff.filled_with_resource]
            return [
                CharacterActionLink(
                    name=f"Boire {resource_description.name}",
                    link=get_with_stuff_action_url(
                        character.id,
                        ActionType.DRINK_STUFF,
                        query_params=self.input_model_serializer.dump(query_params),
                        stuff_id=stuff.id,
                        action_description_id=self._description.id,
                    ),
                    cost=self.get_cost(character, stuff),
                )
            ]

        return []

    def perform(
        self, character: "CharacterModel", stuff: "StuffModel", input_: input_model
    ) -> Description:
        character_doc = self._character_lib.get_document(character.id)
        effects: typing.List[CharacterEffectDescriptionModel] = self._description.properties[
            "effects"
        ]

        for effect in effects:
            self._effect_manager.enable_effect(character_doc, effect)
            self._kernel.server_db_session.add(character_doc)

        self._kernel.character_lib.drink_stuff(character.id, stuff.id)
        self._kernel.server_db_session.commit()

        return Description(title="Vous avez bu")
